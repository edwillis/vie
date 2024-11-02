import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src/python/terrain_generation_service")))

import grpc
import terrain_generator_pb2
import terrain_generator_pb2_grpc
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')  # or your preferred GUI backend
import numpy as np
from matplotlib.patches import RegularPolygon



def display_terrain(terrain_tiles):
    """
    Display the terrain using matplotlib hexagonal grid visualization.
    
    @param terrain_tiles: List of TerrainTile objects received from the gRPC service.
    """
    terrain_colors = {
        "mountain": "#A9A9A9",
        "hills": "#8B4513",
        "forest": "#228B22",
        "plains": "#9ACD32",
        "desert": "#DAA520",
        "lake": "#1E90FF",
    }

    fig, ax = plt.subplots(1, figsize=(12, 12))
    ax.set_aspect('equal')

    hex_radius = 1
    hex_height = hex_radius * (3 ** 0.5)

    for tile in terrain_tiles:
        x_offset = tile.x * 1.5 * hex_radius
        y_offset = tile.y * hex_height + (tile.x % 2) * hex_height / 2
        color = terrain_colors[tile.terrain_type]

        hexagon = RegularPolygon(
            (x_offset, y_offset), numVertices=6, radius=hex_radius, orientation=np.radians(30), edgecolor='k', facecolor=color
        )
        ax.add_patch(hexagon)
        ax.text(x_offset, y_offset, tile.terrain_type[:3], ha='center', va='center', fontsize=8, color='black')

    ax.set_xlim(-10 * 1.5 * hex_radius, 10 * 1.5 * hex_radius)
    ax.set_ylim(-10 * hex_height, 10 * hex_height)
    plt.axis('off')
    plt.show()


def run():
    """
    Connect to the gRPC service and request terrain generation.
    """
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = terrain_generator_pb2_grpc.TerrainGeneratorServiceStub(channel)
        request = terrain_generator_pb2.TerrainRequest(total_land_hexagons=250)
        response = stub.GenerateTerrain(request)
        display_terrain(response.tiles)


if __name__ == "__main__":
    run()
