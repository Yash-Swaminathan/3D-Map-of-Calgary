import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Toaster } from 'react-hot-toast';
import CalgaryMap3D from './components/CalgaryMap3D/CalgaryMap3D';
import BuildingQueryPanel from './components/BuildingQueryPanel/BuildingQueryPanel';
import BuildingDetailsPanel from './components/BuildingDetailsPanel/BuildingDetailsPanel';
import SavedProjectsPanel from './components/SavedProjectsPanel/SavedProjectsPanel';
import UserIdentityForm from './components/UserIdentityForm/UserIdentityForm';
import apiService from './services/dashboardApi';
import './dashboard.css';

const BOUNDS = [51.042, -114.075, 51.048, -114.065];

export default function App() {
  const [user, setUser] = useState(null);
  const [buildings, setBuildings] = useState([]);
  const [visibleBuildings, setVisibleBuildings] = useState([]);
  const [selectedBuilding, setSelectedBuilding] = useState(null);
  const [activeFilters, setActiveFilters] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showProjects, setShowProjects] = useState(false);
  const [showIdentity, setShowIdentity] = useState(false);
  const [status, setStatus] = useState(null);
  const initialized = useRef(false);

  const loadBuildingData = useCallback(async (refresh = false, filters = null) => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await apiService.getBuildingsInArea(BOUNDS, refresh);
      if (!data.success) throw new Error(data.error || 'Could not load buildings.');
      setBuildings(data.buildings);
      setStatus(data);
      if (filters) {
        const result = await apiService.filterBuildings(filters, BOUNDS);
        setVisibleBuildings(result.data.buildings);
      } else {
        setVisibleBuildings(data.buildings);
      }
      setSelectedBuilding(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true;
      loadBuildingData();
    }
  }, [loadBuildingData]);

  const handleQuery = async query => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await apiService.processQuery(query, user?.id, BOUNDS);
      if (!data.success) throw new Error(data.error || 'Could not interpret the question.');
      setVisibleBuildings(data.buildings);
      setActiveFilters(data.filters);
      setSelectedBuilding(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const clearFilters = () => {
    setActiveFilters(null);
    setVisibleBuildings(buildings);
    setSelectedBuilding(null);
    setError(null);
  };

  const saveProject = async ({ name, description }) => {
    if (!user || !activeFilters) throw new Error('Choose a name and apply filters before saving.');
    const { data } = await apiService.saveProject(user.id, name, description, activeFilters);
    if (!data.success) throw new Error(data.error || 'Could not save the project.');
    return data.project;
  };

  const loadProject = async project => {
    const { data } = await apiService.loadProject(project.id, true, BOUNDS);
    if (!data.success) throw new Error(data.error || 'Could not load the project.');
    setActiveFilters(data.filters);
    setVisibleBuildings(data.buildings || []);
    setSelectedBuilding(null);
    setShowProjects(false);
  };

  const assessedCount = buildings.filter(b => b.assessed_value != null).length;
  const heightCount = buildings.filter(b => b.height != null).length;

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">C<span>U</span></span>
          <div><p className="eyebrow">CITY DATA / SPATIAL EXPLORER</p>
            <h1>Calgary Urban Intelligence</h1></div>
        </div>
        <nav className="header-actions" aria-label="Dashboard controls">
          <span className="area-pill"><i /> Downtown Calgary</span>
          <button className="secondary-button" onClick={() => user ? setShowProjects(true) : setShowIdentity(true)}>
            Saved projects{user ? ` | ${user.username}` : ''}
          </button>
          <button className="primary-button" disabled={isLoading} onClick={() => loadBuildingData(true, activeFilters)}>
            {isLoading ? 'Loading area...' : 'Refresh data'}
          </button>
        </nav>
      </header>
      <main className="dashboard-main">
        <aside className="analysis-panel">
          <div className="area-summary">
            <p className="eyebrow">YOUR STUDY AREA</p>
            <h2>Explore the downtown core.</h2>
            <p>Find buildings by height, use, assessed value, or land-use district.</p>
            <div className="metrics">
              <div><strong>{buildings.length.toLocaleString()}</strong><span>Buildings</span></div>
              <div><strong>{heightCount.toLocaleString()}</strong><span>Known heights</span></div>
              <div><strong>{assessedCount.toLocaleString()}</strong><span>Assessments</span></div>
            </div>
            <div className="data-note">
              <span className={`status-dot ${error ? 'error' : ''}`} />
              {isLoading ? 'Loading a bounded area...' : error ? 'Data request needs attention' :
                status ? `${status.cache_status === 'cached' ? 'Cached' : 'Fresh'} open data | ${new Date(status.fetched_at + 'Z').toLocaleDateString()}` : 'Waiting for data'}
            </div>
            {status?.warnings?.length > 0 && <details className="source-warnings"><summary>Data coverage notes</summary>
              {status.warnings.map(warning => <p key={warning}>{warning}</p>)}</details>}
          </div>
          <BuildingQueryPanel onQuerySubmit={handleQuery} onClearFilters={clearFilters}
            activeFilters={activeFilters} isLoading={isLoading} error={error}
            buildingCount={visibleBuildings.length} totalBuildings={buildings.length} />
          {error && <button className="retry-button" disabled={isLoading} onClick={() => loadBuildingData(false, activeFilters)}>Retry loading area</button>}
          <footer className="source-footer">City of Calgary Open Data | OpenStreetMap contributors<br />
            Unknown values remain unknown. Values describe matched property assessments.</footer>
        </aside>
        <section className="map-panel" aria-label="Interactive 3D building map">
          <CalgaryMap3D buildings={visibleBuildings} selectedBuilding={selectedBuilding}
            onBuildingClick={setSelectedBuilding} isLoading={isLoading} bounds={BOUNDS} />
          <div className="map-heading"><p className="eyebrow">3D BUILDING EXPLORER</p><h2>Downtown Calgary</h2>
            <span>{visibleBuildings.length.toLocaleString()} {activeFilters ? 'matching' : 'mapped'} buildings</span></div>
          <div className="map-legend"><span className="legend-title">BUILDING USE</span>
            {['Commercial', 'Residential', 'Industrial', 'Mixed Use', 'Unknown'].map((label, i) =>
              <span key={label}><i style={{ background: ['#528fbc', '#71a995', '#a093bf', '#d8ad66', '#a9b4ba'][i] }} />{label}</span>)}
          </div>
          {!isLoading && !visibleBuildings.length && <div className="map-empty" role="status">
            <strong>{error ? 'Building data is unavailable' : activeFilters ? 'No buildings match these filters' : 'No buildings found in this area'}</strong>
            <p>{error ? 'Check the message in the sidebar and retry.' : activeFilters ? 'Clear the filters to explore the full area.' : 'Try refreshing the open data.'}</p>
          </div>}
        </section>
        {selectedBuilding && <BuildingDetailsPanel building={selectedBuilding} onClose={() => setSelectedBuilding(null)} />}
        {showProjects && user && <SavedProjectsPanel user={user} activeFilters={activeFilters}
          onClose={() => setShowProjects(false)} onSaveProject={saveProject} onLoadProject={loadProject} />}
        {showIdentity && <div className="identity-overlay" role="dialog" aria-modal="true" aria-label="Choose a project identity">
          <button className="identity-close" aria-label="Close identity form" onClick={() => setShowIdentity(false)}>&times;</button>
          <UserIdentityForm onLogin={identity => { setUser(identity); setShowIdentity(false); setShowProjects(true); }} />
        </div>}
      </main>
      <Toaster position="bottom-right" />
    </div>
  );
}
