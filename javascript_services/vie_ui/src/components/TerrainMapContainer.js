import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import * as protobuf from 'protobufjs';
import { TerrainGenerationServiceClient } from '../protos/terrain_generation/terrain_generation_grpc_web_pb';

// Import the generated proto modules
// Note: These imports may vary based on how your proto files are packaged
import * as terrainMessages from '../protos/terrain_generation/terrain_generation_pb';

// Add this at the top of your component or in a useEffect
useEffect(() => {
  // Log all properties and methods of the terrainMessages module
  console.log("All properties of terrainMessages:", 
    Object.getOwnPropertyNames(terrainMessages));
  
  // Check if there are any constructors with "Request" in the name
  for (const key of Object.getOwnPropertyNames(terrainMessages)) {
    if (typeof terrainMessages[key] === 'function' && key.includes('Request')) {
      console.log(`Found request constructor: ${key}`);
    }
  }
}, []); 

const TerrainMapContainer = () => {
  const [terrainData, setTerrainData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [hexCount, setHexCount] = useState(50);
  const [error, setError] = useState(null);
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
        setError(`Failed to load proto: ${err.message}`);
      });
  }, []);

  // Create a client connecting to the terrain generation service
  const client = new TerrainGenerationServiceClient('https://localhost:3000', null, null);

  const generateTerrain = () => {
    if (!root) {
      setError("Proto definition not loaded yet");
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Get the message type from the loaded root
      const TerrainRequest = root.lookupType('terrain.GenerateTerrainRequest');
      
      // Create a message
      const message = TerrainRequest.create({
        totalLandHexagons: parseInt(hexCount),
        persist: true
      });
      
      // Convert to binary format for gRPC
      const buffer = TerrainRequest.encode(message).finish();
      
      // Now use the binary format with your gRPC client
      client.generateTerrain(buffer, {}, (err, response) => {
        // Process response...
      });
    } catch (e) {
      console.error("Failed to create request:", e);
      setError(`Error creating request: ${e.message}`);
      setLoading(false);
    }
  };

  // Rest of component...
}; 