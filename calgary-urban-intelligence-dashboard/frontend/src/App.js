import React, { useState, useEffect, useCallback } from 'react';
import styled from 'styled-components';
import { Toaster, toast } from 'react-hot-toast';

// Components
import CalgaryMap3D from './components/CalgaryMap3D/CalgaryMap3D';
import BuildingQueryPanel from './components/BuildingQueryPanel/BuildingQueryPanel';
import BuildingDetailsPanel from './components/BuildingDetailsPanel/BuildingDetailsPanel';
import SavedProjectsPanel from './components/SavedProjectsPanel/SavedProjectsPanel';
import UserIdentityForm from './components/UserIdentityForm/UserIdentityForm';

// Services
import apiService from './services/dashboardApi';

// Styled Components
const AppContainer = styled.div`
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  overflow: hidden;
`;

const Header = styled.header`
  height: 80px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 30px;
  z-index: 1000;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
`;

const Title = styled.h1`
  color: white;
  margin: 0;
  font-size: 24px;
  font-weight: 600;
`;

const HeaderControls = styled.div`
  display: flex;
  align-items: center;
  gap: 15px;
`;

const StatusBadge = styled.div`
  background: ${props => props.$success ? 'rgba(46, 204, 113, 0.8)' : 'rgba(231, 76, 60, 0.8)'};
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
`;

const MainContent = styled.div`
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
`;

const SidePanel = styled.div`
  width: 400px;
  height: 100%;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
  z-index: 100;
  box-shadow: 2px 0 20px rgba(0, 0, 0, 0.1);
  overflow: hidden;
`;

const DataSourceInfo = styled.div`
  padding: 15px;
  background: rgba(0, 0, 0, 0.05);
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  font-size: 12px;
  line-height: 1.4;
  flex-shrink: 0;
  
  h4 {
    margin: 0 0 8px 0;
    color: #333;
  }
  
  p {
    margin: 0;
    color: #666;
  }
`;

const MapContainer = styled.div`
  flex: 1;
  position: relative;
`;

const ControlButton = styled.button`
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  
  &:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }
  
  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.3);
  }
`;

function App() {
    // State management
    const [user, setUser] = useState(null);
    const [buildings, setBuildings] = useState([]);
    const [selectedBuilding, setSelectedBuilding] = useState(null);
    const [filteredBuildings, setFilteredBuildings] = useState([]);
    const [activeFilters, setActiveFilters] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [showSavedProjects, setShowSavedProjects] = useState(false);
    const [dataStatus, setDataStatus] = useState(null);

    // Calgary downtown bounds (approximately 3-4 blocks)
    const defaultBounds = [51.042, -114.075, 51.048, -114.065];

    // Load initial building data
    useEffect(() => {
        if (user) {
            loadBuildingData();
        }
    }, [user]);

    const loadBuildingData = async (refresh = false) => {
        setIsLoading(true);
        setError(null);

        try {
            // Always use intelligent combined data source
            const response = await apiService.getBuildingsInArea(defaultBounds, refresh);

            if (response.data.success) {
                setBuildings(response.data.buildings);
                setFilteredBuildings(response.data.buildings);
                setDataStatus({
                    success: true,
                    source: response.data.data_source,
                    cacheStatus: response.data.cache_status,
                    count: response.data.buildings.length
                });
                
                // Show success message with data info
                toast.success(`Loaded ${response.data.buildings.length} buildings from real Calgary data`);
            } else {
                throw new Error(response.data.error || 'Failed to load building data');
            }
        } catch (err) {
            setError(err.message);
            setDataStatus({ success: false, error: err.message });
            console.error('Error loading building data:', err);
            toast.error('Failed to load building data');
        } finally {
            setIsLoading(false);
        }
    };

    const handleUserIdentity = (userData) => {
        setUser(userData);
    };

    const handleQuerySubmit = async (query) => {
        if (!query.trim()) return;

        setIsLoading(true);
        setError(null);

        try {
            const response = await apiService.processQuery(query, user?.id, defaultBounds);

            if (response.data.success) {
                setFilteredBuildings(response.data.buildings);
                setActiveFilters(response.data.filters);
                setSelectedBuilding(null); // Clear any selected building
            } else {
                setError(response.data.error || 'Failed to process query');
            }
        } catch (err) {
            setError(err.message);
            console.error('Error processing query:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleBuildingClick = useCallback((building) => {
        setSelectedBuilding(building);
    }, []);

    const handleCloseBuildingDetails = () => {
        setSelectedBuilding(null);
    };

    const handleClearFilters = () => {
        setActiveFilters(null);
        setFilteredBuildings(buildings);
        setSelectedBuilding(null);
    };

    const handleSaveProject = async (projectData) => {
        if (!user || !activeFilters) {
            setError('Please log in and apply filters before saving a project');
            return;
        }

        try {
            const response = await apiService.saveProject(user.id, projectData.name, projectData.description, activeFilters);

            if (response.data.success) {
                return response.data.project;
            } else {
                throw new Error(response.data.error || 'Failed to save project');
            }
        } catch (err) {
            setError(err.message);
            throw err;
        }
    };

    const handleLoadProject = async (project) => {
        try {
            const response = await apiService.loadProject(project.id, true);

            if (response.data.success) {
                setActiveFilters(response.data.filters);
                if (response.data.buildings) {
                    setFilteredBuildings(response.data.buildings);
                }
                setSelectedBuilding(null);
                setShowSavedProjects(false);
            } else {
                throw new Error(response.data.error || 'Failed to load project');
            }
        } catch (err) {
            setError(err.message);
            console.error('Error loading project:', err);
        }
    };

    const debugCalgaryAPIs = async () => {
        setIsLoading(true);
        try {
            const response = await fetch('/api/buildings/debug/calgary-fields');
            const data = await response.json();
            
            console.log('🔍 CALGARY API DEBUG RESULTS:');
            console.log('================================');
            
            if (data.success) {
                Object.entries(data.debug_info).forEach(([apiName, info]) => {
                    console.log(`\n📋 ${apiName.toUpperCase()}:`);
                    console.log(`Status: ${info.status}`);
                    
                    if (info.available_fields) {
                        console.log(`Available fields: ${info.available_fields.join(', ')}`);
                        console.log('Sample record:', info.sample_record);
                    } else if (info.error) {
                        console.log(`Error: ${info.error}`);
                    }
                });
                
                console.log('\n🎯 Fields we are looking for:');
                console.log('Zoning:', data.analysis?.zoning_fields_to_check?.join(', ') || 'None');
                console.log('Construction:', data.analysis?.construction_fields_to_check?.join(', ') || 'None');
                console.log('Value:', data.analysis?.value_fields_to_check?.join(', ') || 'None');
                
                toast.success('Debug info logged to console (F12 Developer Tools)');
            } else {
                console.error('Debug failed:', data.error);
                toast.error('Debug failed: ' + data.error);
            }
        } catch (err) {
            console.error('Debug error:', err);
            toast.error('Debug failed: ' + err.message);
        } finally {
            setIsLoading(false);
        }
    };

    // Show login screen if no user
    if (!user) {
        return (
            <AppContainer>
                <UserIdentityForm onLogin={handleUserIdentity} />
                <Toaster position="top-right" />
            </AppContainer>
        );
    }

    return (
        <AppContainer>
            <Header>
                <Title>Calgary Urban Intelligence Dashboard</Title>
                <HeaderControls>
                    {dataStatus && (
                        <StatusBadge $success={dataStatus.success}>
                            {dataStatus.success 
                                ? `${dataStatus.count} real buildings loaded` 
                                : 'Data Error'
                            }
                        </StatusBadge>
                    )}
                    
                    <span style={{ color: 'white', fontSize: '14px' }}>Welcome, {user.username}</span>
                    
                    <ControlButton
                        onClick={() => setShowSavedProjects(!showSavedProjects)}
                    >
                        Projects
                    </ControlButton>
                    
                    <ControlButton
                        onClick={() => loadBuildingData(true)}
                        disabled={isLoading}
                    >
                        {isLoading ? 'Loading...' : 'Refresh Data'}
                    </ControlButton>
                    
                    <ControlButton
                        onClick={debugCalgaryAPIs}
                        disabled={isLoading}
                        style={{ fontSize: '11px', padding: '6px 12px' }}
                    >
                        Debug APIs
                    </ControlButton>
                </HeaderControls>
            </Header>

            <MainContent>
                <SidePanel>
                    <DataSourceInfo>
                        <h4>Real Calgary Building Data</h4>
                        <p>
                            <strong>Buildings:</strong> {filteredBuildings.length} of {buildings.length}<br/>
                            <strong>Area:</strong> Downtown Calgary (3-4 blocks)<br/>
                            <strong>Data Sources:</strong> OpenStreetMap + Calgary Open Data
                        </p>
                        <p style={{ marginTop: '8px', fontStyle: 'italic' }}>
                            Intelligently combines real building data from OpenStreetMap community mapping 
                            and Calgary's official Open Data portal for the most comprehensive coverage.
                        </p>
                    </DataSourceInfo>
                    
                    <BuildingQueryPanel
                        onQuerySubmit={handleQuerySubmit}
                        onClearFilters={handleClearFilters}
                        activeFilters={activeFilters}
                        isLoading={isLoading}
                        error={error}
                        buildingCount={filteredBuildings.length}
                        totalBuildings={buildings.length}
                    />
                </SidePanel>

                <MapContainer>
                    <CalgaryMap3D
                        buildings={filteredBuildings}
                        selectedBuilding={selectedBuilding}
                        onBuildingClick={handleBuildingClick}
                        isLoading={isLoading}
                        bounds={defaultBounds}
                    />
                </MapContainer>

                {selectedBuilding && (
                    <BuildingDetailsPanel
                        building={selectedBuilding}
                        onClose={handleCloseBuildingDetails}
                    />
                )}

                {showSavedProjects && (
                    <SavedProjectsPanel
                        user={user}
                        activeFilters={activeFilters}
                        onClose={() => setShowSavedProjects(false)}
                        onSaveProject={handleSaveProject}
                        onLoadProject={handleLoadProject}
                    />
                )}
            </MainContent>

            <Toaster position="top-right" />
        </AppContainer>
    );
}

export default App; 