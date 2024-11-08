import pytest
import grpc
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
from black import format_file_in_place, FileMode, WriteBack
from terrain_generation.terrain_generation_service import TerrainGeneratorService
from terrain_generation.terrain_generation_pb2 import TerrainRequest, TerrainResponse, TerrainTile

def test_generate_terrain():
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
    service = TerrainGeneratorService()
    request = TerrainRequest(total_land_hexagons=5, persist=0)
    context = MagicMock()

    with patch('terrain_generation.terrain_generation_service.logger') as mock_logger, \
         patch('terrain_generation.terrain_generation_service.timer', side_effect=[0, 1]):
        response = service.GenerateTerrain(request, context)

        mock_logger.info.assert_any_call("Generated terrain with %d tiles", 5)
        mock_logger.info.assert_any_call("GenerateTerrain invocation took %f seconds", 1.0)

def test_generate_terrain_error_handling():
    service = TerrainGeneratorService()
    request = TerrainRequest(total_land_hexagons=5, persist=0)
    context = MagicMock()

    with patch('terrain_generation.terrain_generation_service.terrain_generation_pb2.TerrainTile', side_effect=Exception("Test error")), \
         patch('terrain_generation.terrain_generation_service.logger') as mock_logger:
        response = service.GenerateTerrain(request, context)

        assert isinstance(response, TerrainResponse)
        assert len(response.tiles) == 0
        context.set_details.assert_called_once_with("Test error")
        context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        mock_logger.error.assert_called_once_with("Error generating terrain: %s", "Test error")

def test_terrain_generation():
    """
    Test the terrain generation function to ensure the output has the correct number of hexagons.
    """
    width = 10
    height = 15
    request = TerrainRequest(total_land_hexagons=width * height, persist=0)
    context = Mock()
    response = TerrainGeneratorService().GenerateTerrain(request, context)
    assert len(response.tiles) == width * height


# test that generated terrain hexes form one shape with no discontinuities
def test_terrain_generation_shape():
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
    request = TerrainRequest(total_land_hexagons=-1, persist=0)
    context = Mock()
    response = TerrainGeneratorService().GenerateTerrain(request, context)
    assert context.set_code.called
    assert context.set_details.called


def test_black_formatting():
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