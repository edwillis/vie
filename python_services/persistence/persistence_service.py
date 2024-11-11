import logging
import threading
import time
import uuid
import grpc
import socket
import os
from concurrent import futures
from sqlalchemy import create_engine, Column, Integer, String, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import persistence.persistence_pb2 as persistence_pb2
import persistence.persistence_pb2_grpc as persistence_pb2_grpc
from grpc_reflection.v1alpha import reflection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine('sqlite:///persistence_service.db')
Session = sessionmaker(bind=engine)

class TerrainTile(Base):
    __tablename__ = 'terrain_tiles'
    id = Column(Integer, Sequence('tile_id_seq'), primary_key=True)
    x = Column(Integer)
    y = Column(Integer)
    terrain_type = Column(String(50))
    terrain_id = Column(String(50))

Base.metadata.create_all(engine)

class PersistenceService(persistence_pb2_grpc.PersistenceServiceServicer):
    def __init__(self):
        self.lock = threading.Lock()

    def StoreTerrain(self, request, context):
        start_time = time.time()
        with self.lock:
            session = Session()
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
        start_time = time.time()
        with self.lock:
            session = Session()
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