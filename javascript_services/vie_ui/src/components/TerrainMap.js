/**
 * @file TerrainMap.js
 * @brief Component that renders the terrain map using SVG polygons.
 */

import React from 'react';
import PropTypes from 'prop-types';

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

export default TerrainMap;