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
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import persistence.persistence_pb2 as persistence_pb2
import persistence.persistence_pb2_grpc as persistence_pb2_grpc
from grpc_reflection.v1alpha import reflection
from common.logging_config import setup_logger
import json

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
    @class PersistenceService
    @brief Service for persisting data.
    """

    def __init__(self):
        """
        @brief Initializes the PersistenceService.
        @details Sets up the database engine and session maker, initializes logging, and prepares transaction queues.
        """
        self.engine = create_engine('sqlite:///persistence_service.db')
        self.DbSession = sessionmaker(bind=self.engine)
        logger.info("PersistenceService initialized.")
        self.lock = threading.Lock()
        self.transaction_queues = {}  # Dictionary to store transaction queues

    def StoreTerrain(self, request, context):
        """
        @brief Stores terrain tiles in the database.
        @param request The gRPC request containing terrain tiles to store.
        @param context The gRPC context.
        @return A StoreTerrainResponse containing the terrain ID.
        @exception Sets gRPC context with appropriate HTTP response code on failure.
        """
        start_time = time.time()
        with self.lock:
            session = DbSession()
            terrain_id = str(uuid.uuid4())
            for tile in request.tiles:
                new_tile = TerrainTile(x=tile.x, y=tile.y, terrain_type=tile.terrain_type, terrain_id=terrain_id)
                session.add(new_tile)
            session.commit()
            session.close()
            logger.info(f"Stored terrain with ID: {terrain_id}")
            duration = time.time() - start_time
            logger.info(f"StoreTerrain invocation duration: {duration:.2f} seconds")
            return persistence_pb2.StoreTerrainResponse(terrain_id=terrain_id)

    def RetrieveTerrain(self, request, context):
        """
        @brief Retrieves terrain tiles from the database.
        @param request The gRPC request containing the terrain ID to retrieve.
        @param context The gRPC context.
        @return A RetrieveTerrainResponse containing the requested terrain tiles.
        @exception Sets gRPC context with NOT_FOUND status code if terrain is not found.
        """
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
        @exception Sets gRPC context with appropriate HTTP response code on failure.
        """
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
        @exception Raises KeyError if the transaction ID does not exist.
        """
        if transaction_id not in self.transaction_queues:
            raise KeyError(f"Transaction {transaction_id} not found")

        try:
            # Create the closure for the operation
            operation_closure = self._create_closure(operation_type, entity_type, data)
            
            # Append the operation to the transaction queue
            self.transaction_queues[transaction_id].append((sequence, operation_closure))
            
            # Sort the queue by sequence to ensure correct execution order
            self.transaction_queues[transaction_id].sort(key=lambda x: x[0])
            
            return True
        except Exception as e:
            logger.error(f"Failed to queue operation: {e}")
            return False

    def _create_closure(self, operation_type: str, entity_type: str, data: str) -> Callable[[Session], Any]:
        """
        @brief Creates a closure for the requested database operation.
        @param operation_type The type of operation (CREATE, UPDATE, DELETE).
        @param entity_type The type of entity being operated on.
        @param data JSON-formatted operation data.
        @return A callable closure that performs the operation.
        @exception Raises ValueError for unsupported operations or entities.
        """
        data_dict = json.loads(data)
        
        if entity_type == "TerrainTile":
            if operation_type == "CREATE":
                def operation(db_session: Session) -> None:
                    terrain_id = data_dict.get('terrain_id', str(uuid.uuid4()))
                    tile = TerrainTile(
                        x=data_dict['x'],
                        y=data_dict['y'],
                        terrain_type=data_dict['terrain_type'],
                        terrain_id=terrain_id
                    )
                    db_session.add(tile)
                    logger.debug(f"Created TerrainTile with ID: {terrain_id}")
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

    def begin_transaction(self) -> str:
        """
        @brief Begins a new transaction and returns a transaction ID.
        @return A unique transaction ID.
        """
        transaction_id = str(uuid.uuid4())
        self.transaction_queues[transaction_id] = []
        logger.info(f"Transaction {transaction_id} started.")
        return transaction_id

    def commit_transaction(self, transaction_id: str) -> None:
        """
        @brief Commits all operations in the transaction queue.
        @param transaction_id The ID of the transaction to commit.
        @exception Logs an error if the transaction is not found or fails.
        """
        if transaction_id not in self.transaction_queues:
            logger.error(f"Transaction {transaction_id} not found.")
            return

        session = self.DbSession()
        try:
            for _, operation in self.transaction_queues[transaction_id]:
                operation(session)
            session.commit()
            logger.info(f"Transaction {transaction_id} committed successfully.")
        except Exception as e:
            session.rollback()
            logger.error(f"Transaction {transaction_id} failed: {e}")
        finally:
            session.close()
            del self.transaction_queues[transaction_id]

    def rollback_transaction(self, transaction_id: str) -> None:
        """
        @brief Rolls back all operations in the transaction queue.
        @param transaction_id The ID of the transaction to roll back.
        """
        if transaction_id in self.transaction_queues:
            del self.transaction_queues[transaction_id]
            logger.info(f"Transaction {transaction_id} rolled back.")

LOCK_FILE = "/tmp/persistence_service.lock"

def serve():
    """
    @brief Starts the gRPC server for the PersistenceService.
    @exception Logs an error if the service is already running or fails to start.
    """
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