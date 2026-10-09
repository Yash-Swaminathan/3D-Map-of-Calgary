import axios from 'axios';
import toast from 'react-hot-toast';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const apiService = {
  getBuildingsInArea: (bounds, refresh = false) =>
    axios.get(`${API_BASE_URL}/api/buildings/area`, {
      params: { bounds: bounds.join(','), refresh }
    }),
  processQuery: (query, userId, bounds) =>
    axios.post(`${API_BASE_URL}/api/llm/process`, { query, user_id: userId, bounds }),
  saveProject: (userId, name, description, filters) =>
    axios.post(`${API_BASE_URL}/api/projects/save`, { user_id: userId, name, description, filters }),
  loadProject: (projectId, withBuildings = false) =>
    axios.post(`${API_BASE_URL}/api/projects/${projectId}/load`, { with_buildings: withBuildings }),
  getQuerySuggestions: () =>
    axios.get(`${API_BASE_URL}/api/llm/suggestions`),
};

export default apiService; 