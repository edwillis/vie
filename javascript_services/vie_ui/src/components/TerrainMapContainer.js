import React, { useState, useEffect } from 'react';
import * as protobuf from 'protobufjs';
import { TerrainGenerationServiceClient } from '../protos/terrain_generation/terrain_generation_grpc_web_pb';

// Import the generated proto modules
// Note: These imports may vary based on how your proto files are packaged
import * as terrainMessages from '../protos/terrain_generation/terrain_generation_pb';

const TerrainMapContainer = () => {
  // Removed unused variables
  // const [hexCount] = useState(50);
  // const [root, setRoot] = useState(null);
  
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