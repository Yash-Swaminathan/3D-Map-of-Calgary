import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Toaster } from 'react-hot-toast';
import CalgaryMap3D from './components/CalgaryMap3D/CalgaryMap3D';
import BuildingQueryPanel from './components/BuildingQueryPanel/BuildingQueryPanel';
import BuildingDetailsPanel from './components/BuildingDetailsPanel/BuildingDetailsPanel';
import SavedProjectsPanel from './components/SavedProjectsPanel/SavedProjectsPanel';
import UserIdentityForm from './components/UserIdentityForm/UserIdentityForm';
import apiService from './services/dashboardApi';
import './dashboard.css';
import { tilesForBounds, matchesFilters, intersectsView } from './utils/viewport';


export default function App() {
  const [user, setUser] = useState(null);
  const [buildings, setBuildings] = useState([]);
  const [bounds, setBounds] = useState(null);
  const [refreshCounter, setRefreshCounter] = useState(0);
  const [densityCells, setDensityCells] = useState([]);
  const [overviewCount, setOverviewCount] = useState(null);
  const [progress, setProgress] = useState('Waiting for map');
  const refreshCoverage = useRef(false);
  const refreshKeys = useRef(new Set());
  const [queryLoading, setQueryLoading] = useState(false);
  const tileCache = useRef(new Map());
  const onViewportChange = useCallback(next => setBounds(previous => previous?.join(',') === next.join(',') ? previous : next), []);
  const [selectedBuilding, setSelectedBuilding] = useState(null);
  const [activeFilters, setActiveFilters] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showProjects, setShowProjects] = useState(false);
  const [showIdentity, setShowIdentity] = useState(false);
  const [status, setStatus] = useState(null);
  const tiles = useMemo(() => bounds ? tilesForBounds(bounds) : [], [bounds]);
  // Broad views show live geographic density; zoom-in returns to building meshes.
  const overview = tiles.length > 144 || (bounds && (bounds[2] - bounds[0] > 0.12 || bounds[3] - bounds[1] > 0.12));
  const visibleBuildings = useMemo(() => buildings.filter(b => matchesFilters(b, activeFilters)), [buildings, activeFilters]);
  const refresh = () => { tileCache.current.clear(); refreshCoverage.current = overview; refreshKeys.current = new Set(overview ? [] : tiles.map(t => t.join(','))); setRefreshCounter(v => v + 1); };
  useEffect(() => {
    if (!bounds) return;
    const controller = new AbortController();
    let cancelled = false;
    setIsLoading(true); setError(null); setSelectedBuilding(null); setOverviewCount(null);
    setBuildings([]); setDensityCells([]); setStatus(null); setProgress(`Loading ${tiles.length} area tiles`);
    const load = async () => {
      try {
        if (overview) {
          setProgress('Counting live roof records for this view');
          const force = refreshCoverage.current; refreshCoverage.current = false;
          const { data } = await apiService.getCoverage(bounds, controller.signal, force);
          if (!cancelled) { setOverviewCount(data.source_record_count); setDensityCells(data.density_cells || []); setStatus(data); }
          return;
        }
        const records = new Map();
        const warnings = new Set();
        let completed = 0;
        const publish = () => {
          if (!cancelled) {
            setBuildings([...records.values()].filter(b => intersectsView(b, bounds)));
            setProgress(`${completed} / ${tiles.length} area tiles loaded`);
          }
        };
        const pending = [...tiles];
        const worker = async () => {
          while (pending.length && !cancelled) {
            const tile = pending.shift(), key = tile.join(',');
            let result = tileCache.current.get(key);
            if (!result) {
              let offset = 0, version;
              const all = [];
              do {
                const { data } = await apiService.getBuildingsInArea(tile, refreshKeys.current.has(key) && offset === 0, { offset, version, signal: controller.signal });
                if (cancelled) return;
                if (!data.success) throw new Error(data.error || 'Could not load buildings.');
                all.push(...data.buildings);
                offset = data.next_offset; version = data.version;
                result = { ...data, buildings: all };
                for (const building of data.buildings) records.set(building.building_id, building);
                publish();
              } while (offset != null);
              if (cancelled) return;
              tileCache.current.set(key, result);
              refreshKeys.current.delete(key);
              // Keep session memory bounded; evicted tiles remain cached on the server.
              if (tileCache.current.size > 80) tileCache.current.delete(tileCache.current.keys().next().value);
            }
            result.warnings?.forEach(w => warnings.add(w));
            result.buildings.forEach(b => records.set(b.building_id, b));
            completed++; publish();
            if (!cancelled) setStatus({ ...result, warnings: [...warnings] });
          }
        };
        await Promise.all([worker(), worker(), worker(), worker()]);
      } catch (err) {
        if (!cancelled) { setError(err.message); cancelled = true; controller.abort(); setIsLoading(false); }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    load();
    return () => { cancelled = true; controller.abort(); };
  }, [bounds, tiles, overview, refreshCounter]);

  const handleQuery = async query => {
    setQueryLoading(true);
    setError(null);
    try {
      const { data } = await apiService.processQuery(query, user?.id, bounds);
      if (!data.success) throw new Error(data.error || 'Could not interpret the question.');
      setActiveFilters(data.filters);
      setSelectedBuilding(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setQueryLoading(false);
    }
  };

  const clearFilters = () => {
    setActiveFilters(null);
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
    const { data } = await apiService.loadProject(project.id, false, bounds);
    if (!data.success) throw new Error(data.error || 'Could not load the project.');
    setActiveFilters(data.filters);
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
          <span className="area-pill"><i /> Dynamic map area</span>
          <button className="secondary-button" onClick={() => user ? setShowProjects(true) : setShowIdentity(true)}>
            Saved projects{user ? ` | ${user.username}` : ''}
          </button>
          <button className="primary-button" disabled={isLoading || queryLoading} onClick={refresh}>
            {isLoading ? 'Loading area...' : 'Refresh data'}
          </button>
        </nav>
      </header>
      <main className="dashboard-main">
        <aside className="analysis-panel">
          <div className="area-summary">
            <p className="eyebrow">YOUR STUDY AREA</p>
            <h2>Explore Calgary as you move.</h2>
            <p>Pan or zoom to load the visible area. Find buildings by height, use, assessed value, or land-use district.</p>
            <div className="metrics">
              <div><strong>{overview ? overviewCount?.toLocaleString() || '...' : buildings.length.toLocaleString()}</strong><span>{overview ? 'Roof records' : 'Buildings'}</span></div>
              <div><strong>{overview ? '-' : heightCount.toLocaleString()}</strong><span>Known heights</span></div>
              <div><strong>{overview ? '-' : assessedCount.toLocaleString()}</strong><span>Assessments</span></div>
            </div>
            <div className="data-note">
              <span className={`status-dot ${error ? 'error' : ''}`} />
              {isLoading ? progress : error ? 'Data request needs attention' : overview ? 'Live City of Calgary roof-record count' :
                status?.fetched_at ? `${status.cache_status === 'cached' ? 'Cached' : 'Fresh'} open data | ${new Date(status.fetched_at + 'Z').toLocaleDateString()}` : 'Waiting for data'}
            </div>
            {status?.warnings?.length > 0 && <details className="source-warnings"><summary>Data coverage notes</summary>
              {status.warnings.map(warning => <p key={warning}>{warning}</p>)}</details>}
          </div>
          {bounds && <p className="viewport-coordinates">Current view: {bounds[0].toFixed(4)}, {bounds[1].toFixed(4)} to {bounds[2].toFixed(4)}, {bounds[3].toFixed(4)}</p>}
          {overview && <p className="overview-note">{overviewCount == null ? 'City overview' : `${overviewCount.toLocaleString()} roof records in this view`}. The coloured cells show roof density across this view. Click a cell to explore its buildings.</p>}
          <BuildingQueryPanel onQuerySubmit={handleQuery} onClearFilters={clearFilters}
            activeFilters={activeFilters} isLoading={isLoading || queryLoading} disabled={overview} error={error}
            buildingCount={visibleBuildings.length} totalBuildings={buildings.length} />
          {error && <button className="retry-button" disabled={isLoading || queryLoading} onClick={() => setRefreshCounter(v => v + 1)}>Retry loading area</button>}
          <footer className="source-footer">City of Calgary Open Data | Optional OpenStreetMap enrichment<br />
            Unknown values remain unknown. Values describe matched property assessments.</footer>
        </aside>
        <section className="map-panel" aria-label="Interactive 3D building map">
          <CalgaryMap3D buildings={visibleBuildings} selectedBuilding={selectedBuilding}
            onBuildingClick={setSelectedBuilding} isLoading={isLoading} onViewportChange={onViewportChange} densityCells={densityCells} />
          <div className="map-heading"><p className="eyebrow">3D BUILDING EXPLORER</p><h2>{overview ? 'Calgary overview' : 'Current map area'}</h2>
            <span>{overview ? `${overviewCount?.toLocaleString() || 'Counting'} roof records` : `${visibleBuildings.length.toLocaleString()} ${activeFilters ? 'matching' : 'mapped'} buildings`}</span></div>
          {!overview && <div className="map-legend"><span className="legend-title">BUILDING USE</span>
            {['Commercial', 'Residential', 'Industrial', 'Mixed Use', 'Unknown'].map((label, i) =>
              <span key={label}><i style={{ background: ['#528fbc', '#71a995', '#a093bf', '#d8ad66', '#a9b4ba'][i] }} />{label}</span>)}
          </div>}
          {overview && !isLoading && <div className="map-empty overview-prompt" role="status"><strong>City building density</strong><p>Click a coloured cell or zoom in to explore individual buildings.</p></div>}
          {!overview && !isLoading && !visibleBuildings.length && <div className="map-empty" role="status">
            <strong>{error ? 'Building data is unavailable' : activeFilters ? 'No buildings match these filters' : 'No buildings found in this area'}</strong>
            <p>{error ? 'Check the message in the sidebar and retry.' : activeFilters ? 'Clear the filters to explore the full area.' : 'Pan to another area or refresh the open data.'}</p>
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
