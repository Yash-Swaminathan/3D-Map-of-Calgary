import React, { useRef, useState, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

function BuildingMesh({ building, position, isSelected, onClick }) {
    const meshRef = useRef();
    const [hovered, setHovered] = useState(false);

    // Create building geometry based on footprint and height
    const geometry = useMemo(() => {
        // Use height from data, with better scaling for Calgary buildings
        const rawHeight = building.height || (building.floors ? building.floors * 3.5 : 30);
        const height = Math.max(rawHeight * 0.3, 5); // Better scale and ensure minimum height

        // Handle different geometry sources
        let footprintCoords = null;
        
        if (building.geometry && building.geometry.coordinates) {
            // Handle GeoJSON geometry
            const coords = building.geometry.coordinates;
            if (building.geometry.type === 'Polygon' && coords.length > 0) {
                footprintCoords = coords[0]; // Take outer ring
            }
        } else if (building.footprint && Array.isArray(building.footprint)) {
            // Handle direct footprint coordinates
            if (building.footprint.length > 0 && Array.isArray(building.footprint[0])) {
                footprintCoords = building.footprint;
            }
        }

        if (footprintCoords && footprintCoords.length > 2) {
            try {
                // Create shape from footprint coordinates
                const shape = new THREE.Shape();
                
                // Calculate bounds for scaling
                const minX = Math.min(...footprintCoords.map(p => p[0]));
                const maxX = Math.max(...footprintCoords.map(p => p[0]));
                const minY = Math.min(...footprintCoords.map(p => p[1]));
                const maxY = Math.max(...footprintCoords.map(p => p[1]));
                
                const centerX = (minX + maxX) / 2;
                const centerY = (minY + maxY) / 2;
                
                // Much smaller scale factor for reasonable building sizes
                const scale = 5000;

                footprintCoords.forEach((point, index) => {
                    if (point && point.length >= 2) {
                        // Center and scale the coordinates
                        const x = (point[0] - centerX) * scale;
                        const y = (point[1] - centerY) * scale;

                        if (index === 0) {
                            shape.moveTo(x, y);
                        } else {
                            shape.lineTo(x, y);
                        }
                    }
                });

                // Close the shape
                if (footprintCoords.length > 0) {
                    const firstPoint = footprintCoords[0];
                    if (firstPoint && firstPoint.length >= 2) {
                        const x = (firstPoint[0] - centerX) * scale;
                        const y = (firstPoint[1] - centerY) * scale;
                        shape.lineTo(x, y);
                    }
                }

                // Extrude the shape to create 3D building
                const extrudeSettings = {
                    depth: height,
                    bevelEnabled: false,
                    bevelThickness: 0,
                    bevelSize: 0,
                    bevelOffset: 0,
                    bevelSegments: 1
                };

                const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
                // Translate geometry so the bottom sits on the ground
                geometry.translate(0, 0, height / 2);
                return geometry;
            } catch (error) {
                console.warn('Error creating building geometry from footprint:', error);
                // Fall back to box geometry
            }
        }

        // Fallback to box geometry if no footprint available or if footprint processing failed
        const width = 8 + Math.random() * 6; // Random width between 8-14
        const depth = 6 + Math.random() * 6; // Random depth between 6-12
        const geometry = new THREE.BoxGeometry(width, height, depth);
        // Translate geometry so the bottom sits on the ground (box geometry is centered by default)
        geometry.translate(0, height / 2, 0);
        return geometry;
    }, [building.footprint, building.geometry, building.height, building.floors]);

    // Enhanced color system based on multiple factors
    const material = useMemo(() => {
        let baseColor = '#888888'; // Default gray
        let colorMode = 'type'; // Default to building type coloring

        // Check if we have assessed value for value-based coloring
        if (building.assessed_value && building.assessed_value > 0) {
            colorMode = 'value';
            const value = building.assessed_value;
            
            // Log assessed value for debugging (first few buildings only)
            if (Math.random() < 0.1) { // Log ~10% of buildings to avoid spam
                console.log(`BuildingMesh assessed value: $${value.toLocaleString()} at ${building.address}`);
            }
            
            // Color scale based on realistic Calgary assessed value ranges
            if (value > 10000000) {
                baseColor = '#8B0000'; // Dark red for extremely high value (>10M) - likely commercial towers
            } else if (value > 5000000) {
                baseColor = '#FF0000'; // Red for very high value (5-10M) - high-end commercial/residential
            } else if (value > 2000000) {
                baseColor = '#FF4500'; // Orange-red for high value (2-5M) - premium properties
            } else if (value > 1000000) {
                baseColor = '#FFA500'; // Orange for medium-high value (1-2M) - typical condos/houses
            } else if (value > 500000) {
                baseColor = '#FFD700'; // Gold for medium value (500k-1M) - average properties
            } else if (value > 200000) {
                baseColor = '#ADFF2F'; // Green-yellow for lower-medium value (200k-500k) 
            } else if (value > 50000) {
                baseColor = '#32CD32'; // Green for lower value (50k-200k) - older/smaller properties
            } else {
                baseColor = '#4169E1'; // Blue for very low value (<50k) - land value only?
            }
        } else {
            // Color by building type
            switch (building.building_type?.toLowerCase()) {
                case 'commercial':
                    baseColor = '#4A90E2'; // Blue
                    break;
                case 'residential':
                    baseColor = '#7ED321'; // Green
                    break;
                case 'industrial':
                    baseColor = '#BD10E0'; // Purple
                    break;
                case 'mixed use':
                case 'mixed':
                    baseColor = '#F5A623'; // Orange
                    break;
                default:
                    // Color by zoning if available
                    if (building.zoning) {
                        const zoning = building.zoning.toLowerCase();
                        if (zoning.includes('residential') || zoning.includes('r-')) {
                            baseColor = '#7ED321'; // Green for residential
                        } else if (zoning.includes('commercial') || zoning.includes('c-')) {
                            baseColor = '#4A90E2'; // Blue for commercial
                        } else if (zoning.includes('industrial') || zoning.includes('i-')) {
                            baseColor = '#BD10E0'; // Purple for industrial
                        } else {
                            baseColor = '#888888'; // Gray for unknown
                        }
                    } else {
                        baseColor = '#888888'; // Gray for unknown
                    }
            }
        }

        // Adjust color for selection/hover state
        let color = baseColor;
        let opacity = 0.8;
        
        if (isSelected) {
            color = '#FF6B6B'; // Red for selected
            opacity = 1.0;
        } else if (hovered) {
            color = '#FFD93D'; // Yellow for hovered
            opacity = 0.9;
        }

        return new THREE.MeshLambertMaterial({
            color: color,
            transparent: true,
            opacity: opacity
        });
    }, [building.building_type, building.assessed_value, building.zoning, isSelected, hovered]);

    // Remove the rotation animation to stop the weird spinning behavior
    // Animation for selected buildings - REMOVED
    // useFrame(() => {
    //     if (meshRef.current && isSelected) {
    //         meshRef.current.rotation.y += 0.01; // Slow rotation
    //     }
    // });

    const handleClick = (event) => {
        event.stopPropagation();
        onClick();
    };

    const handlePointerOver = () => {
        setHovered(true);
        document.body.style.cursor = 'pointer';
    };

    const handlePointerOut = () => {
        setHovered(false);
        document.body.style.cursor = 'default';
    };

    return (
        <mesh
            ref={meshRef}
            position={position}
            geometry={geometry}
            material={material}
            onClick={handleClick}
            onPointerOver={handlePointerOver}
            onPointerOut={handlePointerOut}
            castShadow
            receiveShadow
        />
    );
}

export default BuildingMesh;
