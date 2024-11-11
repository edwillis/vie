import pytest
import grpc
from concurrent import futures
from persistence.persistence_pb2 import TerrainTile, StoreTerrainRequest, RetrieveTerrainRequest
from persistence.persistence_pb2_grpc import PersistenceServiceStub, add_PersistenceServiceServicer_to_server
from persistence.persistence_service import PersistenceService

@pytest.fixture(scope='module')
def grpc_add_to_server():
    return add_PersistenceServiceServicer_to_server

@pytest.fixture(scope='module')
def grpc_servicer():
    return PersistenceService()

@pytest.fixture(scope='module')
def grpc_server(grpc_add_to_server, grpc_servicer):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    grpc_add_to_server(grpc_servicer, server)
    port = server.add_insecure_port('[::]:50052')
    server.start()
    yield server
    server.stop(None)

@pytest.fixture(scope='module')
def grpc_channel(grpc_server):
    channel = grpc.insecure_channel('localhost:50052')
    yield channel
    channel.close()

@pytest.fixture(scope='module')
def grpc_stub_cls(grpc_channel):
    return PersistenceServiceStub(grpc_channel)

def test_store_terrain(grpc_stub_cls):
    tiles = [
        TerrainTile(x=1, y=1, terrain_type="Mountain"),
        TerrainTile(x=2, y=2, terrain_type="Forest")
    ]
    request = StoreTerrainRequest(tiles=tiles)
    response = grpc_stub_cls.StoreTerrain(request)
    assert response.terrain_id

def test_retrieve_terrain(grpc_stub_cls):
    tiles = [
        TerrainTile(x=1, y=1, terrain_type="Mountain"),
        TerrainTile(x=2, y=2, terrain_type="Forest")
    ]
    store_request = StoreTerrainRequest(tiles=tiles)
    store_response = grpc_stub_cls.StoreTerrain(store_request)
    retrieve_request = RetrieveTerrainRequest(terrain_id=store_response.terrain_id)
    retrieve_response = grpc_stub_cls.RetrieveTerrain(retrieve_request)
    assert len(retrieve_response.tiles) == 2

def test_retrieve_nonexistent_terrain(grpc_stub_cls):
    request = RetrieveTerrainRequest(terrain_id="non-existent-id")
    with pytest.raises(grpc.RpcError) as excinfo:
        grpc_stub_cls.RetrieveTerrain(request)
    assert excinfo.value.code() == grpc.StatusCode.NOT_FOUND