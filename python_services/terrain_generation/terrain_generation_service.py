import logging
import grpc
from concurrent import futures
from timeit import default_timer as timer
from persistence.persistence_pb2 import (
    TerrainTile,
    StoreTerrainRequest,
    CommitTransactionRequest,
    RollbackTransactionRequest,
    BeginTransactionRequest,
)
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
from persistence.persistence_pb2 import BeginTransactionRequest
import ssl
from pathlib import Path

# Configure logging using the common logging configuration
logger = setup_logger("TerrainGeneratorService")

# Define the path to the certificates
project_root = Path(__file__).parent.parent.parent  # Navigate up to the project root
cert_path = project_root / "certs" / "localhost.pem"
key_path = project_root / "certs" / "localhost-key.pem"

# Load the TLS credentials
with open(cert_path, "rb") as f:
    cert_data = f.read()
with open(key_path, "rb") as f:
    key_data = f.read()

server_credentials = grpc.ssl_server_credentials(
    [(key_data, cert_data)], root_certificates=None, require_client_auth=False
)


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
        # Create channel options to disable SSL verification (for testing only)
        channel_options = [
            ("grpc.ssl_target_name_override", "localhost"),
            ("grpc.default_authority", "localhost"),
        ]

        # Use SSL but with verification disabled
        credentials = grpc.ssl_channel_credentials(root_certificates=cert_data)

        # Connect with secure but unverified channel
        self.persistence_stub = PersistenceServiceStub(
            grpc.secure_channel("localhost:50052", credentials, options=channel_options)
        )
        logger.info("TerrainGeneratorService initialized with secure channel.")

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
            self._validate_request(total_land_hexagons)

            tiles = self._generate_terrain_tiles(total_land_hexagons)

            terrain_id = ""
            if request.persist:
                terrain_id = self._persist_terrain(tiles)

            self._log_generated_tiles(tiles)
            response = self._create_response(tiles, terrain_id)

            duration = time.time() - start_time
            logger.info(f"GenerateTerrain completed in {duration:.2f} seconds.")
            return response
        except ValueError as e:
            logger.error(f"Error during terrain generation: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return terrain_generation_pb2.TerrainResponse()
        except Exception as e:
            logger.error(f"Error during terrain generation: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Failed to store terrain")
            return terrain_generation_pb2.TerrainResponse()

    def _validate_request(self, total_land_hexagons):
        """
        @brief Validates the request parameters.

        @param total_land_hexagons The total number of land hexagons requested.

        @exception ValueError If total_land_hexagons is less than 1.
        """
        if total_land_hexagons < 1:
            raise ValueError("total_land_hexagons must be greater than 0")

    def _generate_terrain_tiles(self, total_land_hexagons):
        """
        @brief Generates terrain tiles using a flood fill algorithm.

        @param total_land_hexagons The total number of land hexagons to generate.

        @return A list of generated TerrainTile objects.
        """
        terrain_types = ["mountain", "hills", "forest", "plains", "desert", "lake"]
        terrain_weights = self._get_terrain_weights()

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

        return tiles

    def _persist_terrain(self, tiles):
        """
        @brief Persists the generated terrain tiles.

        @param tiles The list of generated TerrainTile objects.

        @return The ID of the persisted terrain.
        """
        transaction_id = None  # Initialize transaction_id

        try:
            # Begin a transaction
            begin_response = self.persistence_stub.BeginTransaction(
                BeginTransactionRequest()
            )
            transaction_id = begin_response.transaction_id

            # Persist the generated terrain
            store_request = StoreTerrainRequest(
                tiles=[
                    TerrainTile(x=tile.x, y=tile.y, terrain_type=tile.terrain_type)
                    for tile in tiles
                ],
                transaction_id=transaction_id,
            )
            store_response = self.persistence_stub.StoreTerrain(store_request)
            terrain_id = store_response.terrain_id

            # Commit the transaction
            self.persistence_stub.CommitTransaction(
                CommitTransactionRequest(transaction_id=transaction_id)
            )

            return terrain_id
        except Exception as e:
            logger.error(f"Error during terrain persistence: {e}")
            if transaction_id:
                # Rollback the transaction in case of error
                self.persistence_stub.RollbackTransaction(
                    RollbackTransactionRequest(transaction_id=transaction_id)
                )
            return ""

    def _log_generated_tiles(self, tiles):
        """
        @brief Logs each generated terrain tile.

        @param tiles The list of generated TerrainTile objects.
        """
        for tile in tiles:
            logger.info(f"Generated tile: {tile.x}, {tile.y}, {tile.terrain_type}")

    def _create_response(self, tiles, terrain_id):
        """
        @brief Creates a TerrainResponse object.

        @param tiles The list of generated TerrainTile objects.
        @param terrain_id The ID of the persisted terrain.

        @return A TerrainResponse object containing the tiles and terrain ID.
        """
        logger.info("Generated terrain with %d tiles", len(tiles))
        logger.info("Terrain generated successfully.")
        return terrain_generation_pb2.TerrainResponse(
            tiles=tiles, terrain_id=terrain_id
        )

    def _get_terrain_weights(self):
        """
        @brief Returns the terrain weights for generating terrain types.

        @return A dictionary of terrain weights.
        """
        return {
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

        # Revert to using TLS
        server.add_secure_port("[::]:50051", server_credentials)

        server.start()
        logger.info("Terrain Generation Service started on port 50051")
        server.wait_for_termination()
    except Exception as e:
        logger.error(f"Error starting Terrain Generation Service: {e}")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)


if __name__ == "__main__":
    serve()
