import pytest
from unittest.mock import MagicMock
from persistence.persistence_service import PersistenceService
from persistence.persistence_pb2 import (
    TerrainTile,
    StoreTerrainRequest,
    RetrieveTerrainRequest,
    BeginTransactionRequest,
    CommitTransactionRequest,
    RollbackTransactionRequest,
)
import grpc

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

def test_begin_transaction(persistence_service):
    """
    @test Begin Transaction
    Tests starting a new transaction.
    
    @pre PersistenceService is initialized
    @post A valid transaction ID is returned
    """
    request = BeginTransactionRequest()
    response = persistence_service.BeginTransaction(request, None)
    assert response.transaction_id

def test_commit_transaction(persistence_service):
    """
    @test Commit Transaction
    Tests committing a transaction.
    
    @pre A transaction is started
    @post The transaction is committed successfully
    """
    begin_response = persistence_service.BeginTransaction(BeginTransactionRequest(), None)
    transaction_id = begin_response.transaction_id

    # Store terrain within the transaction
    tiles = [
        TerrainTile(x=1, y=1, terrain_type="Mountain"),
        TerrainTile(x=2, y=2, terrain_type="Forest")
    ]
    store_request = StoreTerrainRequest(tiles=tiles, transaction_id=transaction_id)
    persistence_service.StoreTerrain(store_request, None)

    # Commit the transaction
    commit_request = CommitTransactionRequest(transaction_id=transaction_id)
    commit_response = persistence_service.CommitTransaction(commit_request, None)
    assert commit_response is not None

def test_rollback_transaction(persistence_service):
    """
    @test Rollback Transaction
    Tests rolling back a transaction.
    
    @pre A transaction is started
    @post The transaction is rolled back successfully
    """
    begin_response = persistence_service.BeginTransaction(BeginTransactionRequest(), None)
    transaction_id = begin_response.transaction_id

    # Store terrain within the transaction
    tiles = [
        TerrainTile(x=1, y=1, terrain_type="Mountain"),
        TerrainTile(x=2, y=2, terrain_type="Forest")
    ]
    store_request = StoreTerrainRequest(tiles=tiles, transaction_id=transaction_id)
    persistence_service.StoreTerrain(store_request, None)

    # Rollback the transaction
    rollback_request = RollbackTransactionRequest(transaction_id=transaction_id)
    rollback_response = persistence_service.RollbackTransaction(rollback_request, None)
    assert rollback_response is not None

    # Attempt to retrieve the terrain, which should not exist
    retrieve_request = RetrieveTerrainRequest(terrain_id="non-existent-id")
    mock_context = MagicMock()
    response = persistence_service.RetrieveTerrain(retrieve_request, mock_context)
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)

def test_transaction_commit_after_rollback(persistence_service):
    """
    @test Transaction Commit After Rollback
    Tests that a transaction cannot be committed after it has been rolled back.
    
    @pre A transaction is started and rolled back
    @post Committing the transaction results in an error
    """
    begin_response = persistence_service.BeginTransaction(BeginTransactionRequest(), None)
    transaction_id = begin_response.transaction_id

    # Rollback the transaction
    rollback_request = RollbackTransactionRequest(transaction_id=transaction_id)
    persistence_service.RollbackTransaction(rollback_request, None)

    # Attempt to commit the transaction
    commit_request = CommitTransactionRequest(transaction_id=transaction_id)
    mock_context = MagicMock()
    persistence_service.CommitTransaction(commit_request, mock_context)
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)

def test_transaction_rollback_after_commit(persistence_service):
    """
    @test Transaction Rollback After Commit
    Tests that a transaction cannot be rolled back after it has been committed.
    
    @pre A transaction is started and committed
    @post Rolling back the transaction results in an error
    """
    begin_response = persistence_service.BeginTransaction(BeginTransactionRequest(), None)
    transaction_id = begin_response.transaction_id

    # Commit the transaction
    commit_request = CommitTransactionRequest(transaction_id=transaction_id)
    persistence_service.CommitTransaction(commit_request, None)

    # Attempt to rollback the transaction
    rollback_request = RollbackTransactionRequest(transaction_id=transaction_id)
    mock_context = MagicMock()
    persistence_service.RollbackTransaction(rollback_request, mock_context)
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)

def test_create_update_commit_transaction(persistence_service):
    """
    @test Create, Update, and Commit Transaction
    Tests creating a terrain, updating it, and committing the transaction.
    
    @pre A transaction is started
    @post The terrain is updated and committed successfully, and the updated value is retrieved
    """
    # Start a transaction
    begin_response = persistence_service.BeginTransaction(BeginTransactionRequest(), None)
    transaction_id = begin_response.transaction_id

    # Create terrain within the transaction
    initial_tiles = [
        TerrainTile(x=1, y=1, terrain_type="Mountain"),
        TerrainTile(x=2, y=2, terrain_type="Forest")
    ]
    store_request = StoreTerrainRequest(tiles=initial_tiles, transaction_id=transaction_id)
    store_response = persistence_service.StoreTerrain(store_request, None)
    terrain_id = store_response.terrain_id
    tile_ids = store_response.tile_ids

    # Update terrain within the transaction using tile IDs
    updated_tiles = [
        TerrainTile(id=tile_ids[0], x=1, y=1, terrain_type="Desert"),  # Change terrain type
        TerrainTile(id=tile_ids[1], x=2, y=2, terrain_type="Forest")
    ]
    update_request = StoreTerrainRequest(tiles=updated_tiles, transaction_id=transaction_id)
    persistence_service.StoreTerrain(update_request, None)

    # Commit the transaction
    commit_request = CommitTransactionRequest(transaction_id=transaction_id)
    persistence_service.CommitTransaction(commit_request, None)

    # Retrieve and verify the updated terrain
    retrieve_request = RetrieveTerrainRequest(terrain_id=terrain_id)
    retrieve_response = persistence_service.RetrieveTerrain(retrieve_request, None)
    assert len(retrieve_response.tiles) == 2
    assert any(tile.terrain_type == "Desert" for tile in retrieve_response.tiles)
    assert any(tile.terrain_type == "Forest" for tile in retrieve_response.tiles)