/**
 * @file App.js
 * @brief Main application component for the React client.
 */

import React, { useEffect, useState } from 'react';
import logo from './logo.svg';
import './App.css';
// Import the gRPC client for the TerrainGenerationService
import { TerrainGenerationServiceClient } from './protos/terrain_generation/terrain_generation_grpc_web_pb';
// Import the request message class for terrain generation
import { TerrainRequest } from './protos/terrain_generation/terrain_generation_pb';
// Import the TerrainMap component which will display the terrain
import TerrainMap from './components/TerrainMap';

/**
 * @class App
 * @brief Main application component that fetches terrain data and renders the terrain map.
 */
const App = () => {
  // Declare state variable 'terrainTiles' to hold the terrain data
  const [terrainTiles, setTerrainTiles] = useState([]);

  // useEffect hook to run side effects (fetching data) after the component mounts
  useEffect(() => {
    console.info('Initializing TerrainGenerationServiceClient...');
    // Create a new client instance for the TerrainGenerationService
    const client = new TerrainGenerationServiceClient('https://localhost:3000');

    // Create a new TerrainRequest message
    const request = new TerrainRequest();

    // Set the number of total land hexagons to generate
    request.setTotalLandHexagons(250);
    request.setPersist(false);

    console.info('Sending GenerateTerrain request:', request.toObject());

    // Invoke the GenerateTerrain method
    client.generateTerrain(request, {}, (err, response) => {
      if (err) {
        console.error('Error generating terrain:', err.message);
      } else {
        const tiles = response.getTilesList().map(tile => ({
          x: tile.getX(),
          y: tile.getY(),
          terrainType: tile.getTerrainType(),
        }));
        console.info('Received terrain tiles:', tiles);
        setTerrainTiles(tiles);
        console.info('Terrain generated successfully.');
      }
    });
  }, []);

  // Return the JSX to render the component
  return (
    <div>
      <h1>Terrain Generation</h1>
      {/* Pass width and height props to TerrainMap */}
      <TerrainMap tiles={terrainTiles} width={600} height={400} />
    </div>
  );
};

// Export the App component as the default export
export default App;
