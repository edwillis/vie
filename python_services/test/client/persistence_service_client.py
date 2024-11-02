import grpc
import persistence_service_pb2
import persistence_service_pb2_grpc

# Test functions
def test_store_terrain(stub):
    print("Running test_store_terrain...")
    # Define some tiles with the correct field names
    tiles = [
        persistence_service_pb2.TerrainTile(x=1, y=1, terrain_type="Mountain"),
        persistence_service_pb2.TerrainTile(x=2, y=2, terrain_type="Forest")
    ]
    
    # Prepare request
    request = persistence_service_pb2.StoreTerrainRequest(tiles=tiles)
    
    # Call the gRPC method
    response = stub.StoreTerrain(request)
    assert response.terrain_id, "Expected a non-empty terrain ID"
    print("test_store_terrain passed with terrain ID:", response.terrain_id)
    return response.terrain_id

def test_retrieve_terrain(stub, terrain_id):
    print("Running test_retrieve_terrain...")
    # Prepare the request
    request = persistence_service_pb2.RetrieveTerrainRequest(terrain_id=terrain_id)
    
    # Call the gRPC method
    response = stub.RetrieveTerrain(request)
    assert len(response.tiles) > 0, "Expected to retrieve at least one tile"
    print(f"test_retrieve_terrain passed. Retrieved {len(response.tiles)} tiles.")

def test_retrieve_nonexistent_terrain(stub):
    print("Running test_retrieve_nonexistent_terrain...")
    # Prepare the request with a non-existent terrain ID
    request = persistence_service_pb2.RetrieveTerrainRequest(terrain_id="non-existent-id")
    
    # Call the gRPC method and expect an error
    try:
        stub.RetrieveTerrain(request)
        print("test_retrieve_nonexistent_terrain failed: expected an error for non-existent terrain ID")
    except grpc.RpcError as e:
        assert e.code() == grpc.StatusCode.NOT_FOUND, f"Expected NOT_FOUND error, got {e.code()}"
        print("test_retrieve_nonexistent_terrain passed.")

def run_tests():
    # Connect to the server
    with grpc.insecure_channel('localhost:50052') as channel:
        stub = persistence_service_pb2_grpc.PersistenceServiceStub(channel)
        
        # Run tests
        terrain_id = test_store_terrain(stub)
        test_retrieve_terrain(stub, terrain_id)
        test_retrieve_nonexistent_terrain(stub)

if __name__ == "__main__":
    run_tests()
