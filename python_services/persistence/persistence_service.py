import logging
import threading
import time
from typing import Callable, Any
import uuid
import grpc
import socket
import os
from concurrent import futures
from sqlalchemy import create_engine, Column, Integer, String, Sequence
from sqlalchemy.orm import sessionmaker, Session, declarative_base
import persistence.persistence_pb2 as persistence_pb2
import persistence.persistence_pb2_grpc as persistence_pb2_grpc
from grpc_reflection.v1alpha import reflection
from common.logging_config import setup_logger
import json
from collections import defaultdict
import ssl
from pathlib import Path

# Configure logging using the common logging configuration
logger = setup_logger("PersistenceService")

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine('sqlite:///persistence_service.db')
DbSession = sessionmaker(bind=engine)

# Define the path to the certificates
project_root = Path(__file__).parent.parent.parent  # Navigate up to the project root
cert_path = project_root / "certs" / "localhost.pem"  
key_path = project_root / "certs" / "localhost-key.pem"

# Load the TLS credentials
with open(cert_path, 'rb') as f:
    cert_data = f.read()
with open(key_path, 'rb') as f:
    key_data = f.read()

server_credentials = grpc.ssl_server_credentials(
    [(key_data, cert_data)],
    root_certificates=None,
    require_client_auth=False
)

class TerrainTile(Base):
    __tablename__ = 'terrain_tiles'
    id = Column(Integer, Sequence('tile_id_seq'), primary_key=True)
    x = Column(Integer)
    y = Column(Integer)
    terrain_type = Column(String(50))
    terrain_id = Column(String(50))

Base.metadata.create_all(engine)

class PersistenceService(persistence_pb2_grpc.PersistenceServiceServicer):
    """
    @brief Service for persisting data.
    """

    def __init__(self):
        """
        @brief Initializes the PersistenceService.
        """
        self.engine = create_engine('sqlite:///persistence_service.db')
        self.DbSession = sessionmaker(bind=self.engine)
        logger.info("PersistenceService initialized.")
        self.lock = threading.Lock()
        self.sessions = defaultdict(lambda: self.DbSession())
        self.transaction_locks = defaultdict(threading.Lock)

    def BeginTransaction(self, request, context):
        transaction_id = str(uuid.uuid4())
        self.sessions[transaction_id]  # Initialize session
        logger.info(f"Transaction {transaction_id} started.")
        return persistence_pb2.BeginTransactionResponse(transaction_id=transaction_id)

    def CommitTransaction(self, request, context):
        transaction_id = request.transaction_id
        with self.transaction_locks[transaction_id]:
            session = self.sessions.pop(transaction_id, None)
            if session:
                session.commit()
                session.close()
                logger.info(f"Transaction {transaction_id} committed.")
            else:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Transaction not found.")
        return persistence_pb2.CommitTransactionResponse()

    def RollbackTransaction(self, request, context):
        transaction_id = request.transaction_id
        with self.transaction_locks[transaction_id]:
            session = self.sessions.pop(transaction_id, None)
            if session:
                session.rollback()
                session.close()
                logger.info(f"Transaction {transaction_id} rolled back.")
            else:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Transaction not found.")
        return persistence_pb2.RollbackTransactionResponse()

    def StoreTerrain(self, request, context):
        """
        @brief Stores terrain data in the database.

        @param request The request containing terrain tiles to store.
        @param context The gRPC context.

        @return A response indicating success or failure.
        """
        try:
            with self.DbSession() as session:
                terrain_id = request.transaction_id or str(uuid.uuid4())
                tile_ids = []
                for tile in request.tiles:
                    if tile.id:  # Check if the tile has an ID, indicating an update
                        existing_tile = session.query(TerrainTile).filter_by(id=tile.id).first()
                        if existing_tile:
                            existing_tile.x = tile.x
                            existing_tile.y = tile.y
                            existing_tile.terrain_type = tile.terrain_type
                            tile_ids.append(existing_tile.id)
                        else:
                            context.set_code(grpc.StatusCode.NOT_FOUND)
                            context.set_details(f"Tile with ID {tile.id} not found for update")
                            return persistence_pb2.StoreTerrainResponse(success=False)
                    else:
                        new_tile = TerrainTile(
                            x=tile.x,
                            y=tile.y,
                            terrain_type=tile.terrain_type,
                            terrain_id=terrain_id
                        )
                        session.add(new_tile)
                        session.flush()  # Ensure the ID is generated
                        tile_ids.append(new_tile.id)
                session.commit()
                logger.info("Stored terrain successfully.")
                return persistence_pb2.StoreTerrainResponse(terrain_id=terrain_id, tile_ids=tile_ids, success=True)
        except Exception as e:
            logger.error(f"Failed to store terrain: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Failed to store terrain')
            return persistence_pb2.StoreTerrainResponse(success=False)

    def RetrieveTerrain(self, request, context):
        start_time = time.time()
        with self.lock:
            session = DbSession()
            tiles = session.query(TerrainTile).filter_by(terrain_id=request.terrain_id).all()
            if not tiles:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details('Terrain not found')
                logger.error(f"Terrain with ID {request.terrain_id} not found")
                return persistence_pb2.RetrieveTerrainResponse()
            response = persistence_pb2.RetrieveTerrainResponse()
            for tile in tiles:
                response.tiles.add(x=tile.x, y=tile.y, terrain_type=tile.terrain_type)
            session.close()
            logger.info(f"Retrieved terrain with ID: {request.terrain_id}")
            duration = time.time() - start_time
            logger.info(f"RetrieveTerrain invocation duration: {duration:.2f} seconds")
            return response

LOCK_FILE = "/tmp/persistence_service.lock"

def serve():
    if os.path.exists(LOCK_FILE):
        logger.error("Persistence Service is already running.")
        return

    with open(LOCK_FILE, 'w') as lock_file:
        lock_file.write(str(os.getpid()))

    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        persistence_pb2_grpc.add_PersistenceServiceServicer_to_server(PersistenceService(), server)
        
        # Enable reflection
        SERVICE_NAMES = (
            persistence_pb2.DESCRIPTOR.services_by_name['PersistenceService'].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(SERVICE_NAMES, server)

        # Replace any existing server.add_insecure_port with:
        server.add_secure_port('[::]:50052', server_credentials)

        server.start()
        logger.info("Persistence Service started on port 50052")
        server.wait_for_termination()
    except Exception as e:
        logger.error(f"Error starting Persistence Service: {e}")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

if __name__ == '__main__':
    serve()