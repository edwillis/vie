import React, { useEffect } from 'react';
import * as protobuf from 'protobufjs';
import * as terrainMessages from '../protos/terrain_generation/terrain_generation_pb';

const TerrainMapContainer = () => {
  // Load the proto definition directly
  useEffect(() => {
    protobuf.load('/proto/terrain_generation.proto')
      .then(loadedRoot => {
        console.log("Proto loaded successfully");
      })
      .catch(err => {
        console.error("Failed to load proto:", err);
      });
  }, []);

  // Log all properties and methods of the terrainMessages module
  useEffect(() => {
    console.log("All properties of terrainMessages:", 
      Object.getOwnPropertyNames(terrainMessages));
    
    // Check if there are any constructors with "Request" in the name
    for (const key of Object.getOwnPropertyNames(terrainMessages)) {
      if (typeof terrainMessages[key] === 'function' && key.includes('Request')) {
        console.log(`Found request constructor: ${key}`);
      }
    }
  }, []);

};

export default TerrainMapContainer; 