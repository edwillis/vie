/**
 * @file TerrainMap.js
 * @brief Component that renders the terrain map using SVG polygons.
 */

import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { TerrainGenerationServiceClient } from '../protos/terrain_generation/terrain_generation_grpc_web_pb';

// Import the proto module properly
const terrainProto = require('../protos/terrain_generation/terrain_generation_pb.js');

/**
 * @brief Helper function to generate the points of a hexagon.
 * @param cx X-coordinate of the center.
 * @param cy Y-coordinate of the center.
 * @param size Size of the hexagon.
 * @return String containing the points attribute for the SVG polygon.
 */
const generateHexagonPoints = (cx, cy, size) => {
  const points = [];
  for (let i = 0; i < 6; i++) {
    const angle = ((60 * i - 30) * Math.PI) / 180;
    const x = cx + size * Math.cos(angle);
    const y = cy + size * Math.sin(angle);
    points.push(`${x},${y}`);
  }
  return points.join(' ');
};

/**
 * @brief Helper function to map terrain types to colors.
 * @param terrainType The type of terrain.
 * @return The color corresponding to the terrain type.
 */
const getTerrainColor = (terrainType) => {
  switch (terrainType) {
    case 'lake':
      return '#1f77b4';
    case 'forest':
      return '#2ca02c';
    case 'mountain':
      return '#7f7f7f';
    case 'desert':
      return '#dbb700';
    case 'plains':
      return '#8c564b';
    case 'hills':
      return '#bcbd22';
    default:
      return '#cccccc';
  }
};

/**
 * @brief Component that renders the terrain map using SVG polygons.
 * @param tiles Array of tile objects with x, y coordinates and terrainType.
 * @param width Width of the SVG canvas.
 * @param height Height of the SVG canvas.
 * @return The SVG element containing the rendered terrain map.
 */
const TerrainMap = ({ tiles, width, height }) => {
  const hexSize = 20; ///< Size of each hexagon

  // Calculate pixel positions and find min values for offsets
  let minX = Infinity;
  let minY = Infinity;

  const hexPositions = tiles.map((tile) => {
    const { x, y } = tile;
    const pixelX = hexSize * Math.sqrt(3) * (x + y / 2);
    const pixelY = hexSize * 1.5 * y;

    if (pixelX < minX) minX = pixelX;
    if (pixelY < minY) minY = pixelY;

    return { ...tile, pixelX, pixelY };
  });

  // Offsets to ensure all hexagons are within the SVG bounds
  const offsetX = -minX + hexSize;
  const offsetY = -minY + hexSize;

  return (
    <svg width={width} height={height}>
      {hexPositions.map((tile, index) => {
        const { pixelX, pixelY, terrainType } = tile;
        // Apply offsets to pixel positions
        const adjustedX = pixelX + offsetX;
        const adjustedY = pixelY + offsetY;
        const points = generateHexagonPoints(adjustedX, adjustedY, hexSize);
        const fillColor = getTerrainColor(terrainType);

        return (
          <polygon
            key={index}
            points={points}
            fill={fillColor}
            stroke="black"
          />
        );
      })}
    </svg>
  );
};

TerrainMap.propTypes = {
  tiles: PropTypes.arrayOf(
    PropTypes.shape({
      x: PropTypes.number.isRequired,          ///< X-coordinate of the tile
      y: PropTypes.number.isRequired,          ///< Y-coordinate of the tile
      terrainType: PropTypes.string.isRequired, ///< Type of terrain
    })
  ).isRequired,
  width: PropTypes.number.isRequired, ///< Width of the SVG canvas
  height: PropTypes.number.isRequired, ///< Height of the SVG canvas
};

const TerrainMapContainer = () => {
  const [terrainData, setTerrainData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [hexCount, setHexCount] = useState(50);
  const [error, setError] = useState(null);

  // Create a client with TLS options that skip verification
  const client = new TerrainGenerationServiceClient(
    'https://localhost:3000',
    null,
    {
      "trustCertCollectionFilePath": null,
      "suppressCorsPreflight": false
    }
  );

  // Debug to confirm if the correct endpoint is being used
  console.log("Using terrain service endpoint:", 'https://localhost:3000');

  // Debug section to trace the actual structure
  useEffect(() => {
    console.log("Proto module:", terrainProto);
    console.log("Proto module keys:", Object.keys(terrainProto));
    
    // Look for the TerrainRequest constructor at the root level
    if (terrainProto.TerrainRequest) {
      console.log("Found TerrainRequest at top level");
    } else {
      // Search for any constructor-like properties
      Object.keys(terrainProto).forEach(key => {
        if (typeof terrainProto[key] === 'function' && 
            key.indexOf('Request') > -1) {
          console.log(`Found constructor at key: ${key}`);
        }
      });
    }
  }, []);

  const generateTerrain = () => {
    setLoading(true);
    setError(null);
    
    try {
      // Use the constructor directly from the root level - not under "terrain"
      const request = new terrainProto.TerrainRequest();
      
      // Set properties
      request.setTotalLandHexagons(parseInt(hexCount));
      request.setPersist(true);
      
      console.log("Request created successfully:", request);
      
      console.log("Calling service with method: generateTerrain");
      
      client.generateTerrain(request, {}, (err, response) => {
        setLoading(false);
        
        if (err) {
          console.error('Error generating terrain:', err);
          setError(`Error: ${err.message || 'Unknown error'}`);
          return;
        }
        
        // Process the terrain data
        const tilesList = response.getTilesList();
        const parsedTiles = tilesList.map(tile => ({
          x: tile.getX(),
          y: tile.getY(),
          terrainType: tile.getTerrainType()
        }));
        
        setTerrainData(parsedTiles);
      });
    } catch (e) {
      console.error("Error creating request:", e);
      setError(`Error: ${e.message}`);
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '15px' }}>
        <label htmlFor="hexCount">Number of hexagons: </label>
        <input 
          id="hexCount"
          type="number" 
          value={hexCount} 
          onChange={(e) => setHexCount(e.target.value)} 
          min="10" 
          max="500"
        />
        <button 
          onClick={generateTerrain} 
          disabled={loading}
          style={{ marginLeft: '10px' }}
        >
          {loading ? 'Generating...' : 'Generate Terrain'}
        </button>
      </div>
      
      {error && (
        <div style={{ color: 'red', marginBottom: '10px' }}>
          {error}
        </div>
      )}
      
      {terrainData ? (
        <TerrainMap tiles={terrainData} width={800} height={600} />
      ) : (
        <div>No terrain data. Click "Generate Terrain" to create a map.</div>
      )}
    </div>
  );
};

export default TerrainMapContainer;