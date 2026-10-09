import axios from 'axios';

// Accept either a server origin or an API URL; use CRA's proxy locally.
const configuredUrl = (process.env.REACT_APP_API_URL || '').replace(/\/+$/, '');
const baseURL = configuredUrl.endsWith('/api') ? configuredUrl : `${configuredUrl}/api`;
const client = axios.create({ baseURL, timeout: 180000 });
client.interceptors.response.use(response => response, error => {
  error.message = error.response?.data?.error ||
    (error.code === 'ECONNABORTED' ? 'The data request timed out. Please try again.' :
      error.response ? error.message : 'Cannot reach the dashboard API. Check that the backend is running.');
  return Promise.reject(error);
});

export const apiService = {
  login: username => client.post('/users/login', { username }),
  getBuildingsInArea: (bounds, refresh = false) =>
    client.get('/buildings/area', { params: { bounds: bounds.join(','), refresh } }),
  processQuery: (query, userId, bounds) =>
    client.post('/query/process', { query, user_id: userId, bounds }),
  filterBuildings: (filters, bounds) => client.post('/buildings/filter', { filters, bounds }),
  saveProject: (userId, name, description, filters) =>
    client.post('/projects/save', { user_id: userId, name, description, filters }),
  loadProject: (projectId, withBuildings = false, bounds) =>
    client.post(`/projects/${projectId}/load`, { bounds }, { params: { apply_filters: withBuildings } }),
  getUserProjects: userId => client.get(`/projects/user/${userId}`),
  deleteProject: projectId => client.delete(`/projects/${projectId}`),
  getQuerySuggestions: () => client.get('/query/suggestions'),
};

export default apiService;
