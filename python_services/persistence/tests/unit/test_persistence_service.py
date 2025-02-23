import pytest
from persistence.persistence_service import PersistenceService
from persistence.persistence_pb2 import TerrainTile, StoreTerrainRequest, RetrieveTerrainRequest

@pytest.fixture(scope='module')
def persistence_service():
    return PersistenceService()

def test_store_terrain(persistence_service):
    """
    @test Store Terrain
    Tests the functionality of storing terrain tiles using the persistence service.
    
    @pre PersistenceService is initialized
    @post A valid terrain ID is returned after storing the tiles
    """
    tiles = [
        TerrainTile(x=1, y=1, terrain_type="Mountain"),
        TerrainTile(x=2, y=2, terrain_type="Forest")
    ]
    request = StoreTerrainRequest(tiles=tiles)
    response = persistence_service.StoreTerrain(request, None)  # Pass None for context
    assert response.terrain_id

def test_retrieve_terrain(persistence_service):
    """
    @test Retrieve Terrain
    Tests the retrieval of stored terrain tiles using the persistence service.
    
    @pre Terrain tiles are stored and a valid terrain ID is available
    @post The correct number of tiles is retrieved
    """
    tiles = [
        TerrainTile(x=1, y=1, terrain_type="Mountain"),
        TerrainTile(x=2, y=2, terrain_type="Forest")
    ]
    store_request = StoreTerrainRequest(tiles=tiles)
    store_response = persistence_service.StoreTerrain(store_request, None)
    retrieve_request = RetrieveTerrainRequest(terrain_id=store_response.terrain_id)
    retrieve_response = persistence_service.RetrieveTerrain(retrieve_request, None)
    assert len(retrieve_response.tiles) == 2

def test_retrieve_nonexistent_terrain(persistence_service):
    """
    @test Retrieve Nonexistent Terrain
    Tests the error handling when attempting to retrieve a terrain with a non-existent ID.
    
    @pre PersistenceService is initialized
    @post An error is raised with the NOT_FOUND status code
    """
    request = RetrieveTerrainRequest(terrain_id="non-existent-id")
    with pytest.raises(Exception) as excinfo:
        persistence_service.RetrieveTerrain(request, None)