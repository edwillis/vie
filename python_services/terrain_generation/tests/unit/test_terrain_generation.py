import pytest
import grpc
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
from black import format_file_in_place, FileMode, WriteBack
from terrain_generation.terrain_generation_service import TerrainGeneratorService
from terrain_generation.terrain_generation_pb2 import TerrainRequest, TerrainResponse, TerrainTile

# @TODO add tests for negative hex requests, small requests and large requests and fix the lake on edge

def test_generate_terrain():
    service = TerrainGeneratorService()
    request = TerrainRequest(total_land_hexagons=5, persist=0)
    context = MagicMock()

    response = service.GenerateTerrain(request, context)

    assert isinstance(response, TerrainResponse)
    assert len(response.tiles) == 5
    for i, tile in enumerate(response.tiles):
        assert tile.x == i
        assert tile.y == i
        assert tile.terrain_type == "land"

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
    request = TerrainRequest(total_land_hexagons=5)
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
    request = TerrainRequest(total_land_hexagons=width * height)
    context = Mock()
    response = TerrainGeneratorService().GenerateTerrain(request, context)
    assert len(response.tiles) == width * height


def is_on_perimeter(x, y, width, height):
    """
    Check if the hex at coordinates (x, y) is on the perimeter of the grid.
    
    A hex is considered on the perimeter if it is on the edge of the grid.
    
    @param x: X-coordinate of the hex
    @param y: Y-coordinate of the hex
    @param width: Width of the grid
    @param height: Height of the grid
    @return: True if the hex is on the perimeter, False otherwise
    """
    return x == 0 or y == 0 or x == width - 1 or y == height - 1


def test_no_lake_on_perimeter():
    """
    Test that the generated terrain does not have lake hexes on the perimeter.
    """
    width = 10
    height = 15
    request = TerrainRequest(total_land_hexagons=width * height)
    context = Mock()
    response = TerrainGeneratorService().GenerateTerrain(request, context)
    
    # Convert response tiles to a dictionary for easier checking
    terrain = {(tile.x, tile.y): tile.terrain_type for tile in response.tiles}
    
    # Iterate over all hexes in the generated terrain
    for (x, y), terrain_type in terrain.items():
        if is_on_perimeter(x, y, width, height):
            assert terrain_type != "Lake", f"Lake found on the perimeter at ({x}, {y})"


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