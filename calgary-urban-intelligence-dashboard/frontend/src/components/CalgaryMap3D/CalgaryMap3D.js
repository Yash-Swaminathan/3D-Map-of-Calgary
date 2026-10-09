import React, { Suspense, useMemo, useRef } from 'react';
import { Canvas, useFrame, extend, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import styled from 'styled-components';
import BuildingMesh from './BuildingMesh';

// Extend with OrbitControls
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
extend({ OrbitControls });

const MapContainer = styled.div`
  position: relative;
  width: 100%;
  height: 100%;
  background: linear-gradient(to bottom, #87CEEB 0%, #98FB98 50%, #90EE90 100%);
`;

const LocationInfo = styled.div`
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.4;
  z-index: 100;
  
  h4 {
    margin: 0 0 8px 0;
    font-size: 14px;
    color: #4A90E2;
  }
  
  p {
    margin: 4px 0;
  }
`;

const LoadingOverlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  color: white;
  font-size: 18px;
  gap: 20px;
`;

const Spinner = styled.div`
  width: 50px;
  height: 50px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top: 3px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const ControlsInfo = styled.div`
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.4;
  z-index: 100;
`;

// Controls component
function Controls() {
  const { camera, gl } = useThree();
  const controlsRef = useRef();
  
  useFrame(() => {
    if (controlsRef.current) {
      controlsRef.current.update();
    }
  });
  
  return (
    <orbitControls
      ref={controlsRef}
      args={[camera, gl.domElement]}
      enablePan={true}
      enableZoom={true}
      enableRotate={true}
      minDistance={80}
      maxDistance={800}
      minPolarAngle={0}
      maxPolarAngle={Math.PI / 2}
    />
  );
}

// Basic lighting setup
function Lighting() {
  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight
        position={[100, 100, 100]}
        intensity={1}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
        shadow-camera-far={200}
        shadow-camera-left={-100}
        shadow-camera-right={100}
        shadow-camera-top={100}
        shadow-camera-bottom={-100}
      />
      <directionalLight position={[-100, 50, -100]} intensity={0.3} />
    </>
  );
}

// Ground plane
function Ground({ bounds }) {
  const groundRef = useRef();
  
  const groundSize = useMemo(() => {
    // Create a much larger ground plane that covers the entire building area
    const baseSize = 1000; // Larger base size
    if (!bounds || bounds.length !== 4) return [baseSize, baseSize];
    
    // Make ground proportional to the spread of buildings but ensure it's always large enough
    const [latMin, lonMin, latMax, lonMax] = bounds;
    const latRange = Math.abs(latMax - latMin);
    const lonRange = Math.abs(lonMax - lonMin);
    
    // Scale based on coordinate range but with reasonable limits
    const width = Math.max(lonRange * 15000, baseSize);
    const height = Math.max(latRange * 15000, baseSize);
    
    return [width, height];
  }, [bounds]);
  
  return (
    <>
      {/* Main ground plane */}
      <mesh ref={groundRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
        <planeGeometry args={groundSize} />
        <meshLambertMaterial color="#4A7C59" />
      </mesh>
      
      {/* Grid lines for better depth perception */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.1, 0]}>
        <planeGeometry args={[groundSize[0] * 0.9, groundSize[1] * 0.9]} />
        <meshBasicMaterial 
          color="#3A6B47" 
          transparent 
          opacity={0.2}
          wireframe
        />
      </mesh>
      
      {/* Center reference point */}
      <mesh position={[0, 1, 0]}>
        <cylinderGeometry args={[2, 2, 2, 8]} />
        <meshBasicMaterial color="#FF6B6B" transparent opacity={0.7} />
      </mesh>
    </>
  );
}

// Buildings container
function BuildingsContainer({ buildings, selectedBuilding, onBuildingClick, bounds }) {
  const buildingsData = useMemo(() => {
    if (!buildings || buildings.length === 0) return [];
    
    // Separate buildings with coordinates from those without
    const validBuildings = buildings.filter(b => b.latitude && b.longitude);
    const invalidBuildings = buildings.filter(b => !b.latitude || !b.longitude);
    
    if (validBuildings.length === 0) {
      // If no valid coordinates, use grid layout for all buildings
      return buildings.map((building, index) => {
        const gridSize = Math.ceil(Math.sqrt(buildings.length));
        const row = Math.floor(index / gridSize);
        const col = index % gridSize;
        const spacing = 25;
        
        return {
          ...building,
          position: [
            (col - gridSize / 2) * spacing,
            0,
            (row - gridSize / 2) * spacing
          ]
        };
      });
    }
    
    // Find the actual center of the buildings
    const avgLat = validBuildings.reduce((sum, b) => sum + b.latitude, 0) / validBuildings.length;
    const avgLng = validBuildings.reduce((sum, b) => sum + b.longitude, 0) / validBuildings.length;
    
    // Calculate appropriate scale based on the spread of buildings
    const latRange = Math.max(...validBuildings.map(b => b.latitude)) - Math.min(...validBuildings.map(b => b.latitude));
    const lngRange = Math.max(...validBuildings.map(b => b.longitude)) - Math.min(...validBuildings.map(b => b.longitude));
    
    // Use a more conservative scale to spread buildings out better
    const targetSpread = 600; // Increased spread for better distribution
    const maxRange = Math.max(latRange, lngRange);
    let scale = maxRange > 0 ? targetSpread / maxRange : 100000;
    
    // Ensure minimum spacing between buildings
    const minBuildingSpacing = 15; // Minimum distance between building centers
    
    console.log(`Positioning ${validBuildings.length} buildings. Center: ${avgLat.toFixed(6)}, ${avgLng.toFixed(6)}. Scale: ${scale.toFixed(0)}`);
    
    // Track used positions to prevent overlapping
    const usedPositions = new Set();
    
    const result = [];
    
    // Process buildings with valid coordinates
    validBuildings.forEach((building, index) => {
      // Calculate base position
      let x = (building.longitude - avgLng) * scale;
      let z = -(building.latitude - avgLat) * scale; // Negative for proper orientation
      
      // Round to grid to help with spacing
      x = Math.round(x / minBuildingSpacing) * minBuildingSpacing;
      z = Math.round(z / minBuildingSpacing) * minBuildingSpacing;
      
      // Check for collisions and adjust position if needed
      let attempts = 0;
      const maxAttempts = 20;
      const posKey = `${x},${z}`;
      
      while (usedPositions.has(posKey) && attempts < maxAttempts) {
        // Spiral outward to find a free position
        const angle = attempts * 0.618 * 2 * Math.PI; // Golden angle for even distribution
        const radius = minBuildingSpacing * (1 + attempts * 0.3);
        x = Math.round(x + Math.cos(angle) * radius);
        z = Math.round(z + Math.sin(angle) * radius);
        attempts++;
      }
      
      usedPositions.add(`${x},${z}`);
      
      const position = [x, 0, z]; // Buildings sit on ground (y=0)
      
      // Debug log for first few buildings
      if (index < 5) {
        console.log(`Building ${index}: ${building.address?.substring(0, 30)} at (${building.latitude.toFixed(6)}, ${building.longitude.toFixed(6)}) -> 3D position (${x.toFixed(1)}, 0, ${z.toFixed(1)})`);
      }
      
      result.push({
        ...building,
        position: position
      });
    });
    
    // Add buildings without coordinates to empty areas
    if (invalidBuildings.length > 0) {
      console.log(`Adding ${invalidBuildings.length} buildings without coordinates to grid positions`);
      
      invalidBuildings.forEach((building, index) => {
        // Find an empty spot in a grid pattern around the edge of the main area
        let found = false;
        let spiralRadius = targetSpread * 0.6; // Start outside the main cluster
        
        for (let attempt = 0; attempt < 50 && !found; attempt++) {
          const angle = (index + attempt) * 0.618 * 2 * Math.PI; // Golden angle
          const x = Math.round(Math.cos(angle) * spiralRadius / minBuildingSpacing) * minBuildingSpacing;
          const z = Math.round(Math.sin(angle) * spiralRadius / minBuildingSpacing) * minBuildingSpacing;
          const posKey = `${x},${z}`;
          
          if (!usedPositions.has(posKey)) {
            usedPositions.add(posKey);
            result.push({
              ...building,
              position: [x, 0, z]
            });
            found = true;
          } else {
            spiralRadius += minBuildingSpacing;
          }
        }
        
        if (!found) {
          // Fallback: place far away
          const fallbackX = (targetSpread + index * minBuildingSpacing);
          const fallbackZ = 0;
          result.push({
            ...building,
            position: [fallbackX, 0, fallbackZ]
          });
        }
      });
    }
    
    console.log(`Final positioning: ${result.length} total buildings positioned`);
    return result;
  }, [buildings, bounds]);
  
  return (
    <group>
      {buildingsData.map((building, index) => (
        <BuildingMesh
          key={building.building_id || `building-${index}`}
          building={building}
          position={building.position}
          isSelected={selectedBuilding?.building_id === building.building_id}
          onClick={() => onBuildingClick(building)}
        />
      ))}
    </group>
  );
}

// Camera setup
function CameraSetup({ bounds }) {
  const { camera } = useThree();
  
  React.useEffect(() => {
    if (bounds && bounds.length === 4) {
      const [latMin, lonMin, latMax, lonMax] = bounds;
      const range = Math.max(latMax - latMin, lonMax - lonMin);
      
      // Position camera based on the building spread (now using larger target spread)
      const cameraDistance = 400; // Fixed distance for consistent view
      camera.position.set(cameraDistance * 0.6, cameraDistance * 0.8, cameraDistance * 0.6);
      camera.lookAt(0, 0, 0);
    } else {
      // Default camera position for sample/fallback data
      camera.position.set(150, 200, 150);
      camera.lookAt(0, 0, 0);
    }
  }, [camera, bounds]);
  
  return null;
}

// Loading fallback
function LoadingFallback() {
  return (
    <mesh>
      <boxGeometry args={[1, 1, 1]} />
      <meshBasicMaterial color="gray" />
    </mesh>
  );
}

// Title text (simple mesh text replacement)
function TitleText() {
  return (
    <mesh position={[0, 200, -200]}>
      <boxGeometry args={[100, 20, 5]} />
      <meshBasicMaterial color="white" transparent opacity={0.8} />
    </mesh>
  );
}

function CalgaryMap3D({ buildings, selectedBuilding, onBuildingClick, isLoading, bounds }) {
  const validBuildings = useMemo(() => {
    return buildings.filter(building => 
      building.latitude && 
      building.longitude && 
      typeof building.latitude === 'number' && 
      typeof building.longitude === 'number'
    );
  }, [buildings]);

  return (
    <MapContainer>
      {isLoading && (
        <LoadingOverlay>
          <Spinner />
          <span>Loading building data...</span>
        </LoadingOverlay>
      )}
      <Canvas 
        camera={{ position: [240, 320, 240], fov: 60, near: 1, far: 3000 }} 
        shadows 
        style={{ background: 'transparent' }}
      >
        <Suspense fallback={<LoadingFallback />}>
          <Lighting />
          <Ground bounds={bounds} />
          <BuildingsContainer 
            buildings={validBuildings} 
            selectedBuilding={selectedBuilding} 
            onBuildingClick={onBuildingClick} 
            bounds={bounds} 
          />
          <CameraSetup bounds={bounds} />
          <TitleText />
          <Controls />
        </Suspense>
      </Canvas>
      <ControlsInfo>
        <strong>Controls:</strong><br />
        • Drag to rotate view<br />
        • Scroll to zoom<br />
        • Right-click + drag to pan<br />
        • Click buildings for details
      </ControlsInfo>
      <LocationInfo>
        <h4>📍 Calgary Location</h4>
        {bounds && bounds.length === 4 ? (
          <>
            <p><strong>Area:</strong> Downtown Calgary</p>
            <p><strong>District:</strong> Beltline/Centre City</p>
            <p><strong>Approx. Coverage:</strong> 3-4 blocks</p>
            <p style={{fontSize: '10px', opacity: 0.8, marginTop: '8px'}}>
              Lat: {bounds[0].toFixed(4)}° - {bounds[2].toFixed(4)}°<br/>
              Lng: {bounds[1].toFixed(4)}° - {bounds[3].toFixed(4)}°
            </p>
          </>
        ) : (
          <>
            <p><strong>Area:</strong> Calgary Sample Data</p>
            <p><strong>District:</strong> Downtown Core</p>
          </>
        )}
      </LocationInfo>
    </MapContainer>
  );
}

export default CalgaryMap3D;
