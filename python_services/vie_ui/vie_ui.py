import logging
import common.logging_config 
import grpc
import terrain_generation.terrain_generation_pb2 as terrain_generation_pb2
import terrain_generation.terrain_generation_pb2_grpc as terrain_generation_pb2_grpc
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('GTK3Agg')  # or your preferred GUI backend
import numpy as np
from matplotlib.patches import RegularPolygon
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger(__name__)

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
        "lake": "#1E90FF"
    }

    root = tk.Tk()
    root.title("Terrain Visualization")

    style = ttk.Style()
    style.configure("TScrollbar", arrowsize=20, gripcount=0, background="#d9d9d9", darkcolor="#d9d9d9", lightcolor="#d9d9d9", troughcolor="#d9d9d9", bordercolor="#d9d9d9", arrowcolor="#5c5c5c")

    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=1)

    fig, ax = plt.subplots(1, figsize=(12, 12))
    ax.set_aspect('equal')

    hex_radius = 1
    hex_height = hex_radius * (3 ** 0.5)

    x_offsets = []
    y_offsets = []

    for tile in terrain_tiles:
        x_offset = tile.x * 1.5 * hex_radius
        y_offset = tile.y * hex_height + (tile.x % 2) * hex_height / 2
        # log the terrain type and the x and y coordinates
        logger.info(f"Terrain type: {tile.terrain_type}, x: {tile.x}, y: {tile.y}")
        color = terrain_colors[tile.terrain_type]

        hexagon = RegularPolygon(
            (x_offset, y_offset), numVertices=6, radius=hex_radius, orientation=np.radians(30), edgecolor='k', facecolor=color
        )
        ax.add_patch(hexagon)
        ax.text(x_offset, y_offset, tile.terrain_type[:3], ha='center', va='center', fontsize=8, color='black')

        x_offsets.append(x_offset)
        y_offsets.append(y_offset)

    ax.set_xlim(min(x_offsets) - hex_radius, max(x_offsets) + hex_radius)
    ax.set_ylim(min(y_offsets) - hex_height, max(y_offsets) + hex_height)
    plt.axis('off')

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

    scrollbar_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.get_tk_widget().yview, style="TScrollbar")
    scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
    scrollbar_x = ttk.Scrollbar(root, orient=tk.HORIZONTAL, command=canvas.get_tk_widget().xview, style="TScrollbar")
    scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

    canvas.get_tk_widget().config(xscrollcommand=scrollbar_x.set, yscrollcommand=scrollbar_y.set)

    def zoom(event):
        scale_factor = 1.1 if event.delta > 0 else 0.9
        ax.set_xlim([x * scale_factor for x in ax.get_xlim()])
        ax.set_ylim([y * scale_factor for y in ax.get_ylim()])
        canvas.draw()

    canvas.get_tk_widget().bind("<MouseWheel>", zoom)
    canvas.get_tk_widget().bind("<Button-4>", lambda event: zoom(event))  # For Linux systems
    canvas.get_tk_widget().bind("<Button-5>", lambda event: zoom(event))  # For Linux systems

    root.mainloop()

def run():
    """
    Connect to the gRPC service and request terrain generation.
    """
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = terrain_generation_pb2_grpc.TerrainGenerationServiceStub(channel)
        request = terrain_generation_pb2.TerrainRequest(total_land_hexagons=250)
        response = stub.GenerateTerrain(request)
        display_terrain(response.tiles)

if __name__ == "__main__":
    run()
