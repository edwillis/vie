import React, { useState, useEffect } from 'react';
import * as protobuf from 'protobufjs';
import { TerrainGenerationServiceClient } from '../protos/terrain_generation/terrain_generation_grpc_web_pb';

// Import the generated proto modules
// Note: These imports may vary based on how your proto files are packaged
import * as terrainMessages from '../protos/terrain_generation/terrain_generation_pb';

const TerrainMapContainer = () => {
  const [hexCount] = useState(50);
  const [root, setRoot] = useState(null);
  
  // Load the proto definition directly
  useEffect(() => {
    protobuf.load('/proto/terrain_generation.proto')
      .then(loadedRoot => {
        setRoot(loadedRoot);
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

  // Create a client connecting to the terrain generation service
  const client = new TerrainGenerationServiceClient('https://localhost:3000', null, null);

  // If generateTerrain is not used, remove it
  // const generateTerrain = () => {
  //   if (!root) {
  //     console.error("Proto definition not loaded yet");
  //     return;
  //   }
    
  //   try {
  //     // Get the message type from the loaded root
  //     const TerrainRequest = root.lookupType('terrain.GenerateTerrainRequest');
      
  //     // Create a message
  //     const message = TerrainRequest.create({
  //       totalLandHexagons: parseInt(hexCount),
  //       persist: true
  //     });
      
  //     // Convert to binary format for gRPC
  //     const buffer = TerrainRequest.encode(message).finish();
      
  //     // Now use the binary format with your gRPC client
  //     client.generateTerrain(buffer, {}, (err, response) => {
  //       // Process response...
  //     });
  //   } catch (e) {
  //     console.error("Failed to create request:", e);
  //   }
  // };

  // Rest of component...
};

export default TerrainMapContainer; 