import pytest
from unittest.mock import MagicMock
from persistence.persistence_service import PersistenceService
from persistence.persistence_pb2 import TerrainTile, StoreTerrainRequest, RetrieveTerrainRequest, SaveDataRequest
import grpc
import json

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
    @post The gRPC context is set with NOT_FOUND status code and appropriate details
    """
    request = RetrieveTerrainRequest(terrain_id="non-existent-id")
    mock_context = MagicMock()
    response = persistence_service.RetrieveTerrain(request, mock_context)
    
    # Check that the context was set with the correct status code and details
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)
    mock_context.set_details.assert_called_once_with('Terrain not found')
    assert response is not None

def test_save_data_with_transaction(persistence_service):
    """
    @test Save Data with Transaction
    Tests the SaveData method and the queuing of operations in a transaction.
    
    @pre PersistenceService is initialized
    @post Data is saved successfully and operations are queued and committed
    """
    mock_context = MagicMock()
    
    # Begin a new transaction to get a valid transaction ID
    transaction_id = persistence_service.begin_transaction()
    
    operation_data = json.dumps({
        "x": 3,
        "y": 3,
        "terrain_type": "Desert"
    })
    
    # Queue a CREATE operation
    success = persistence_service._queue_operation(
        transaction_id=transaction_id,
        operation_type="CREATE",
        entity_type="TerrainTile",
        data=operation_data,
        sequence=1
    )
    assert success, "Failed to queue operation"

    # Simulate SaveData call
    save_request = SaveDataRequest(transaction_id=transaction_id)
    response = persistence_service.SaveData(save_request, mock_context)
    
    # Verify that the data was saved successfully
    assert response is not None
    mock_context.set_code.assert_not_called()
    mock_context.set_details.assert_not_called()

def test_queue_operation_with_nonexistent_transaction(persistence_service):
    """
    @test Queue Operation with Nonexistent Transaction
    Tests that an exception is raised when attempting to queue an operation with a non-existent transaction ID.
    
    @pre PersistenceService is initialized
    @post An exception is raised indicating the transaction ID does not exist
    """
    transaction_id = "non-existent-transaction-id"
    operation_data = json.dumps({
        "x": 3,
        "y": 3,
        "terrain_type": "Desert"
    })
    
    with pytest.raises(KeyError, match=f"Transaction {transaction_id} not found"):
        persistence_service._queue_operation(
            transaction_id=transaction_id,
            operation_type="CREATE",
            entity_type="TerrainTile",
            data=operation_data,
            sequence=1
        )

def test_transaction_commit_and_retrieve(persistence_service):
    """
    @test Transaction Commit and Retrieve
    Tests committing a transaction and verifying the data is saved by retrieving it.
    
    @pre PersistenceService is initialized
    @post Data is saved and can be retrieved successfully
    """
    mock_context = MagicMock()
    
    # Begin a new transaction to get a valid transaction ID
    transaction_id = persistence_service.begin_transaction()
    
    operation_data = TerrainTile(x=4, y=4, terrain_type="Plains")
    
    # Queue a CREATE operation and capture the terrain ID
    store_request = StoreTerrainRequest(
        tiles=[operation_data],
        transaction_id=transaction_id
    )
    store_response = persistence_service.StoreTerrain(store_request, mock_context)
    assert store_response.terrain_id, "Failed to store terrain"

    # Commit the transaction
    persistence_service.commit_transaction(transaction_id)

    # Retrieve the data to verify it was saved
    retrieve_request = RetrieveTerrainRequest(terrain_id=store_response.terrain_id)
    retrieve_response = persistence_service.RetrieveTerrain(retrieve_request, mock_context)
    
    # Verify that the retrieved data matches the saved data
    assert len(retrieve_response.tiles) == 1
    assert retrieve_response.tiles[0].x == 4
    assert retrieve_response.tiles[0].y == 4
    assert retrieve_response.tiles[0].terrain_type == "Plains"