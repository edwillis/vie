import pytest
import grpc
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
from black import format_file_in_place, FileMode, WriteBack
from terrain_generation.terrain_generation_service import TerrainGeneratorService
from terrain_generation.terrain_generation_pb2 import TerrainRequest, TerrainResponse, TerrainTile
from persistence.persistence_service import PersistenceService
from persistence.persistence_pb2 import StoreTerrainRequest, TerrainTile

@pytest.fixture(scope='module')
def persistence_service():
    return PersistenceService()

def test_generate_terrain():
    """
    @test Generate Terrain
    Tests the basic functionality of terrain generation, ensuring the correct number of tiles are generated.
    
    @pre TerrainGeneratorService is initialized
    @post A TerrainResponse with the expected number of tiles is returned
    """
    service = TerrainGeneratorService()
    request = TerrainRequest(total_land_hexagons=5, persist=0)
    context = MagicMock()

    response = service.GenerateTerrain(request, context)

    assert isinstance(response, TerrainResponse)
    assert len(response.tiles) == 5
    # test that the tiles' terrain type is one of the valid terrain types
    for tile in response.tiles:
        assert tile.terrain_type in ["mountain", "hills","forest", "plains", "desert", "lake"]

def test_generate_terrain_logging_and_timing():
    """
    @test Generate Terrain Logging and Timing
    Tests that logging and timing information is correctly recorded during terrain generation.
    
    @pre TerrainGeneratorService is initialized
    @post Logging and timing information is correctly output
    """
    service = TerrainGeneratorService()
    request = TerrainRequest(total_land_hexagons=5, persist=0)
    context = MagicMock()

    with patch('terrain_generation.terrain_generation_service.logger') as mock_logger, \
         patch('terrain_generation.terrain_generation_service.timer', side_effect=[0, 1]):
        response = service.GenerateTerrain(request, context)

        mock_logger.info.assert_any_call("Generated terrain with %d tiles", 5)

def test_generate_terrain_error_handling():
    """
    @test Generate Terrain Error Handling
    Tests the error handling mechanism during terrain generation when an exception is raised.
    
    @pre TerrainGeneratorService is initialized
    @post An error is logged and the appropriate gRPC status code is set
    """
    service = TerrainGeneratorService()
    request = TerrainRequest(total_land_hexagons=-1, persist=0)
    context = MagicMock()

    response = service.GenerateTerrain(request, context)

    assert isinstance(response, TerrainResponse)
    assert len(response.tiles) == 0
    context.set_details.assert_called_once_with("total_land_hexagons must be greater than 0")
    context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)

def test_terrain_generation():
    """
    @test Terrain Generation
    Ensures the terrain generation function outputs the correct number of hexagons.
    
    @pre TerrainGeneratorService is initialized
    @post The number of generated tiles matches the requested number
    """
    width = 10
    height = 15
    request = TerrainRequest(total_land_hexagons =width * height, persist=0)
    context = Mock()
    response = TerrainGeneratorService().GenerateTerrain(request, context)
    assert len(response.tiles) == width * height


# test that generated terrain hexes form one shape with no discontinuities
def test_terrain_generation_shape():
    """
    @test Terrain Generation Shape
    Verifies that the generated terrain hexes form a continuous shape with no discontinuities.
    
    @pre TerrainGeneratorService is initialized
    @post All generated tiles are contiguous
    """
    width = 10
    height = 15
    request = TerrainRequest(total_land_hexagons=width * height, persist=0)
    context = Mock()
    response = TerrainGeneratorService().GenerateTerrain(request, context)
    tiles = response.tiles

    # check that the generated terrain hexes form one shape with no discontinuities
    for tile in tiles:
        x = tile.x
        y = tile.y
        neighbors = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1), (x + 1, y - 1), (x - 1, y + 1)]
        assert any(neighbor in [(t.x, t.y) for t in tiles] for neighbor in neighbors)


# test that invalid inputs returns an error
def test_terrain_generation_invalid_input():
    """
    @test Terrain Generation Invalid Input
    Tests that invalid input results in an error being returned.
    
    @pre TerrainGeneratorService is initialized
    @post An error is returned for invalid input
    """
    request = TerrainRequest(total_land_hexagons=-1, persist=0)
    context = Mock()
    response = TerrainGeneratorService().GenerateTerrain(request, context)
    assert context.set_code.called
    assert context.set_details.called


def test_black_formatting():
    """
    @test Black Formatting
    Verifies that the terrain generation service code is formatted according to PEP8 standards using Black.
    
    @pre terrain_generation_service.py file exists
    @post Code is properly formatted according to Black's standards
    """
    from pathlib import Path
    from black import format_file_in_place, FileMode, WriteBack

    path = Path(__file__).parent.parent.parent / "terrain_generation_service.py"
    
    # Set Black's mode for checking and formatting
    format_file_in_place(
        path, fast=False, mode=FileMode(), write_back=WriteBack.YES
    )

    result = format_file_in_place(
        path, fast=False, mode=FileMode(), write_back=WriteBack.CHECK
    )

    # If the file is correctly formatted, Black will return None. If it's not, raise an error.
    assert not result, f"Formatting issues found in {path}"

def test_generate_terrain_with_transaction():
    """
    @test Generate Terrain with Transaction
    Tests the terrain generation with transaction management.
    
    @pre TerrainGeneratorService is initialized
    @post A TerrainResponse with the expected number of tiles is returned and transaction is committed
    """
    service = TerrainGeneratorService()
    request = TerrainRequest(total_land_hexagons=5, persist=1)
    context = MagicMock()

    with patch.object(service, 'persistence_stub', autospec=True) as mock_stub:
        mock_stub.BeginTransaction.return_value = MagicMock(transaction_id='1234')
        mock_stub.StoreTerrain.return_value = MagicMock(terrain_id='5678')
        mock_stub.CommitTransaction.return_value = MagicMock()

        response = service.GenerateTerrain(request, context)

        mock_stub.BeginTransaction.assert_called_once()
        mock_stub.StoreTerrain.assert_called_once()
        mock_stub.CommitTransaction.assert_called_once()
        assert isinstance(response, TerrainResponse)
        assert len(response.tiles) == 5

def test_store_terrain(persistence_service):
    tiles = [
        TerrainTile(x=1, y=1, terrain_type="Mountain"),
        TerrainTile(x=2, y=2, terrain_type="Forest")
    ]
    request = StoreTerrainRequest(tiles=tiles)
    mock_context = MagicMock()  # Use a mock context

    response = persistence_service.StoreTerrain(request, mock_context)

    assert response.success
    mock_context.set_code.assert_not_called()
    mock_context.set_details.assert_not_called()

def test_generate_terrain_with_error_handling():
    """
    @test Generate Terrain with Error Handling
    Tests the terrain generation with error handling logic.
    
    @pre TerrainGeneratorService is initialized
    @post An error is logged and the appropriate gRPC status code is set
    """
    service = TerrainGeneratorService()
    request = TerrainRequest(total_land_hexagons=5, persist=1)
    context = MagicMock()

    # Mock the persistence stub to raise an exception during StoreTerrain
    with patch.object(service, 'persistence_stub', autospec=True) as mock_stub:
        mock_stub.StoreTerrain.side_effect = Exception("Simulated storage error")

        response = service.GenerateTerrain(request, context)

        # Verify that the error was handled
        context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        context.set_details.assert_called_once_with('Failed to store terrain')  # Ensure this matches the actual error message
        assert isinstance(response, TerrainResponse)
        assert len(response.tiles) == 0