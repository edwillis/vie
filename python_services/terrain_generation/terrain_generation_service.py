import logging
import grpc
from concurrent import futures
from timeit import default_timer as timer
from persistence.persistence_pb2 import TerrainTile
from persistence.persistence_pb2_grpc import PersistenceServiceStub
import terrain_generation.terrain_generation_pb2 as terrain_generation_pb2
import terrain_generation.terrain_generation_pb2_grpc as terrain_generation_pb2_grpc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    def GenerateTerrain(self, request, context):
        """
        @brief Generates terrain based on the provided request.

        @param request The request containing the total number of land hexagons.
        @param context The gRPC context.

        @return A TerrainResponse containing the generated terrain tiles.
        """
        start_time = timer()
        try:
            total_land_hexagons = request.total_land_hexagons
            # Generate terrain tiles (dummy implementation)
            tiles = [
                terrain_generation_pb2.TerrainTile(x=i, y=i, terrain_type="land")
                for i in range(total_land_hexagons)
            ]
            response = terrain_generation_pb2.TerrainResponse(tiles=tiles)
            logger.info("Generated terrain with %d tiles", total_land_hexagons)
            return response
        except Exception as e:
            logger.error("Error generating terrain: %s", str(e))
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return terrain_generation_pb2.TerrainResponse()
        finally:
            duration = timer() - start_time
            logger.info("GenerateTerrain invocation took %f seconds", duration)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    terrain_generation_pb2_grpc.add_TerrainGenerationServiceServicer_to_server(
        TerrainGeneratorService(), server
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    logger.info("TerrainGeneratorService started, listening on port 50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
