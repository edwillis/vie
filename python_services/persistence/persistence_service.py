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

# Configure logging using the common logging configuration
logger = setup_logger("PersistenceService")

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine('sqlite:///persistence_service.db')
DbSession = sessionmaker(bind=engine)

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
        start_time = time.time()
        transaction_id = request.transaction_id
        session = self.sessions[transaction_id] if transaction_id else DbSession()
        with self.lock:
            terrain_id = str(uuid.uuid4())
            for tile in request.tiles:
                new_tile = TerrainTile(x=tile.x, y=tile.y, terrain_type=tile.terrain_type, terrain_id=terrain_id)
                session.add(new_tile)
            if not transaction_id:
                session.commit()
                session.close()
            logger.info(f"Stored terrain with ID: {terrain_id}")
            duration = time.time() - start_time
            logger.info(f"StoreTerrain invocation duration: {duration:.2f} seconds")
            return persistence_pb2.StoreTerrainResponse(terrain_id=terrain_id)

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

    def SaveData(self, request, context):
        """
        @brief Saves data to the persistence layer.
        
        @param request The data to save.
        @param context The gRPC context.
        @return The save data response.
        
        @exception context with appropriate HTTP response code on failure.
        """
        import time
        start_time = time.time()
        logger.debug("SaveData invocation started.")
        
        try:
            session = self.DbSession()
            # Data persistence logic
            # ...
            session.commit()
            logger.info("Data saved successfully.")
            duration = time.time() - start_time
            logger.info(f"SaveData completed in {duration:.2f} seconds.")
            return persistence_pb2.SaveDataResponse()
        except Exception as e:
            logger.error(f"Error during data persistence: {e}")
            session.rollback()
            context.set_details('Failed to save data.')
            context.set_code(grpc.StatusCode.INTERNAL)
            return persistence_pb2.SaveDataResponse()
        finally:
            session.close()

    def _queue_operation(self, transaction_id: str, operation_type: str, 
                        entity_type: str, data: str, sequence: int) -> bool:
        """!
        @brief Internal method to queue an operation closure in a transaction.
        @param transaction_id The ID of the transaction
        @param operation_type Type of operation (CREATE, UPDATE, DELETE)
        @param entity_type Type of entity being operated on
        @param data JSON-formatted operation data
        @param sequence Operation sequence number
        @return bool indicating success or failure
        @note Internal use only - not exposed via gRPC
        """
        def create_closure(operation_type: str, entity_type: str, data: str) -> Callable[[Session], Any]:
            """Creates a closure for the requested database operation"""
            data_dict = json.loads(data)
            
            if entity_type == "TerrainTile":
                if operation_type == "CREATE":
                    def operation(db_session: Session) -> None:
                        tile = TerrainTile(
                            x=data_dict['x'],
                            y=data_dict['y'],
                            terrain_type=data_dict['terrain_type'],
                            terrain_id=data_dict.get('terrain_id', str(uuid.uuid4()))
                        )
                        db_session.add(tile)
                    return operation
                
                elif operation_type == "UPDATE":
                    def operation(db_session: Session) -> None:
                        tile = db_session.query(TerrainTile).filter_by(
                            terrain_id=data_dict['terrain_id'],
                            x=data_dict['x'],
                            y=data_dict['y']
                        ).first()
                        if tile:
                            tile.terrain_type = data_dict['terrain_type']
                    return operation
                
                elif operation_type == "DELETE":
                    def operation(db_session: Session) -> None:
                        db_session.query(TerrainTile).filter_by(
                            terrain_id=data_dict['terrain_id'],
                            x=data_dict['x'],
                            y=data_dict['y']
                        ).delete()
                    return operation
            
            # Add support for other entity types here
            
            raise ValueError(f"Unsupported operation {operation_type} on entity {entity_type}")

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

        port = 50052
        server.add_insecure_port(f"[::]:{port}")
        server.start()
        logger.info(f"Persistence Service started on port {port}")
        server.wait_for_termination()
    except Exception as e:
        logger.error(f"Error starting Persistence Service: {e}")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

if __name__ == '__main__':
    serve()