import logging
import grpc
from concurrent import futures
from timeit import default_timer as timer
from persistence.persistence_pb2 import TerrainTile, StoreTerrainRequest
from persistence.persistence_pb2_grpc import PersistenceServiceStub
import terrain_generation.terrain_generation_pb2 as terrain_generation_pb2
import terrain_generation.terrain_generation_pb2_grpc as terrain_generation_pb2_grpc
import random
import math
import noise
import socket
import os
from grpc_reflection.v1alpha import reflection
from common.logging_config import setup_logger

# Configure logging using the common logging configuration
logger = setup_logger("TerrainGeneratorService")


class TerrainGeneratorService(
    terrain_generation_pb2_grpc.TerrainGenerationServiceServicer
):
    """
    @brief Service for generating terrain.
    """

    def __init__(self):
        """
        @brief Initializes the TerrainGeneratorService.
        """
        self.persistence_stub = None
        logger.info("TerrainGeneratorService initialized.")

    def GenerateTerrain(self, request, context):
        """
        @brief Generates terrain based on the provided request.

        @param request The request containing the total number of land hexagons.
        @param context The gRPC context.

        @return A TerrainResponse containing the generated terrain tiles.
        """
        import time

        start_time = time.time()
        logger.debug("GenerateTerrain invocation started.")

        try:
            total_land_hexagons = request.total_land_hexagons
            # generate an error if the total_land_hexagons is less than 1
            if total_land_hexagons < 1:
                raise ValueError("total_land_hexagons must be greater than 0")
            persist = request.persist

            terrain_types = ["mountain", "hills", "forest", "plains", "desert", "lake"]
            terrain_weights = {
                "mountain": {
                    "mountain": 0.4,
                    "hills": 0.3,
                    "forest": 0.1,
                    "plains": 0.1,
                    "desert": 0.1,
                    "lake": 0.0,
                },
                "hills": {
                    "mountain": 0.3,
                    "hills": 0.3,
                    "forest": 0.2,
                    "plains": 0.1,
                    "desert": 0.1,
                    "lake": 0.0,
                },
                "forest": {
                    "mountain": 0.1,
                    "hills": 0.2,
                    "forest": 0.4,
                    "plains": 0.2,
                    "desert": 0.0,
                    "lake": 0.1,
                },
                "plains": {
                    "mountain": 0.1,
                    "hills": 0.1,
                    "forest": 0.2,
                    "plains": 0.4,
                    "desert": 0.1,
                    "lake": 0.1,
                },
                "desert": {
                    "mountain": 0.1,
                    "hills": 0.1,
                    "forest": 0.0,
                    "plains": 0.1,
                    "desert": 0.6,
                    "lake": 0.1,
                },
                "lake": {
                    "mountain": 0.0,
                    "hills": 0.0,
                    "forest": 0.1,
                    "plains": 0.1,
                    "desert": 0.1,
                    "lake": 0.7,
                },
            }

            def choose_terrain_type(neighbors):
                if not neighbors:
                    return random.choice(terrain_types)
                neighbor_types = [tile.terrain_type for tile in neighbors]
                weights = {
                    terrain: sum(
                        terrain_weights[neighbor].get(terrain, 0)
                        for neighbor in neighbor_types
                    )
                    for terrain in terrain_types
                }
                total_weight = sum(weights.values())
                if total_weight == 0:
                    return random.choice(terrain_types)
                return random.choices(
                    list(weights.keys()), weights=list(weights.values()), k=1
                )[0]

            def generate_island():
                tiles = []
                visited = set()
                queue = [(0, 0)]
                while queue and len(tiles) < total_land_hexagons:
                    x, y = queue.pop(0)
                    if (x, y) in visited:
                        continue
                    visited.add((x, y))
                    nx = x * scale
                    ny = y * scale
                    elevation = noise.pnoise2(nx, ny)
                    neighbors = [
                        tile
                        for tile in tiles
                        if (tile.x, tile.y)
                        in [
                            (x + 1, y),
                            (x - 1, y),
                            (x, y + 1),
                            (x, y - 1),
                            (x + 1, y - 1),
                            (x - 1, y + 1),
                        ]
                    ]
                    terrain_type = choose_terrain_type(neighbors)
                    tiles.append(
                        terrain_generation_pb2.TerrainTile(
                            x=x, y=y, terrain_type=terrain_type
                        )
                    )
                    # Add neighboring hexes to the queue
                    neighbors_coords = [
                        (x + 1, y),
                        (x - 1, y),
                        (x, y + 1),
                        (x, y - 1),
                        (x + 1, y - 1),
                        (x - 1, y + 1),
                    ]
                    queue.extend(neighbors_coords)
                return tiles

            # Generate terrain tiles using a flood fill algorithm to ensure contiguity
            radius = math.ceil(math.sqrt(total_land_hexagons / math.pi))
            scale = 0.1
            tiles = generate_island()

            # Retry if not enough tiles are generated
            while len(tiles) < total_land_hexagons:
                logger.warning("Not enough tiles generated, retrying...")
                tiles = generate_island()

            terrain_id = ""
            if persist:
                # Persist the generated terrain
                store_request = StoreTerrainRequest(
                    tiles=[
                        TerrainTile(x=tile.x, y=tile.y, terrain_type=tile.terrain_type)
                        for tile in tiles
                    ]
                )
                store_response = self.persistence_stub.StoreTerrain(store_request)
                terrain_id = store_response.terrain_id
            # log all the generated tiles
            for tile in tiles:
                logger.info(f"Generated tile: {tile.x}, {tile.y}, {tile.terrain_type}")
            response = terrain_generation_pb2.TerrainResponse(
                tiles=tiles, terrain_id=terrain_id
            )
            logger.info("Generated terrain with %d tiles", len(tiles))
            logger.info("Terrain generated successfully.")
            duration = time.time() - start_time
            logger.info(f"GenerateTerrain completed in {duration:.2f} seconds.")
            return response
        except Exception as e:
            logger.error(f"Error during terrain generation: {e}")
            context.set_details("Failed to generate terrain.")
            context.set_code(grpc.StatusCode.INTERNAL)
            return terrain_generation_pb2.TerrainResponse()
        finally:
            duration = timer() - start_time
            logger.info("GenerateTerrain invocation took %f seconds", duration)


LOCK_FILE = "/tmp/terrain_generation_service.lock"


def serve():
    if os.path.exists(LOCK_FILE):
        logger.error("Terrain Generation Service is already running.")
        return

    with open(LOCK_FILE, "w") as lock_file:
        lock_file.write(str(os.getpid()))

    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        terrain_generation_pb2_grpc.add_TerrainGenerationServiceServicer_to_server(
            TerrainGeneratorService(), server
        )

        # Enable reflection
        SERVICE_NAMES = (
            terrain_generation_pb2.DESCRIPTOR.services_by_name[
                "TerrainGenerationService"
            ].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(SERVICE_NAMES, server)

        port = 50051
        server.add_insecure_port(f"[::]:{port}")
        server.start()
        logger.info(f"Terrain Generation Service started on port {port}")
        server.wait_for_termination()
    except Exception as e:
        logger.error(f"Error starting Terrain Generation Service: {e}")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)


if __name__ == "__main__":
    serve()
