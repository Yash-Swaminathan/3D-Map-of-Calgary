import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import toast from 'react-hot-toast';
import { apiService } from '../../services/dashboardApi';

const ManagerOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(5px);
`;

const ManagerContent = styled.div`
  background: white;
  border-radius: 15px;
  padding: 30px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  position: relative;
  
  /* Custom scrollbar styles */
  &::-webkit-scrollbar {
    width: 8px;
  }
  
  &::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 4px;
  }
  
  &::-webkit-scrollbar-thumb:hover {
    background: #a8a8a8;
  }
`;

const CloseButton = styled.button`
  position: absolute;
  top: 15px;
  right: 15px;
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.3s ease;

  &:hover {
    background: rgba(0, 0, 0, 0.1);
    color: #333;
  }
`;

const Title = styled.h2`
  margin: 0 30px 30px 0;
  color: #333;
  font-size: 24px;
  font-weight: 600;
`;

const TabContainer = styled.div`
  display: flex;
  margin-bottom: 30px;
  border-bottom: 1px solid #e1e1e1;
`;

const Tab = styled.button`
  padding: 12px 24px;
  background: none;
  border: none;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  color: ${props => props.active ? '#667eea' : '#666'};
  border-bottom: 2px solid ${props => props.active ? '#667eea' : 'transparent'};
  transition: all 0.3s ease;

  &:hover {
    color: #667eea;
  }
`;

const TabContent = styled.div`
  display: ${props => props.active ? 'block' : 'none'};
`;

const SaveForm = styled.form`
  display: flex;
  flex-direction: column;
  gap: 20px;
`;

const InputGroup = styled.div`
  display: flex;
  flex-direction: column;
`;

const Label = styled.label`
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
`;

const Input = styled.input`
  padding: 12px;
  border: 2px solid #e1e1e1;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.3s ease;

  &:focus {
    outline: none;
    border-color: #667eea;
  }

  &:disabled {
    background: #f5f5f5;
    cursor: not-allowed;
  }
`;

const TextArea = styled.textarea`
  padding: 12px;
  border: 2px solid #e1e1e1;
  border-radius: 8px;
  font-size: 16px;
  min-height: 80px;
  resize: vertical;
  font-family: inherit;
  transition: border-color 0.3s ease;

  &:focus {
    outline: none;
    border-color: #667eea;
  }

  &:disabled {
    background: #f5f5f5;
    cursor: not-allowed;
  }
`;

const Button = styled.button`
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

const SaveButton = styled(Button)`
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
  }
`;

const ProjectsList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 15px;
`;

const ProjectCard = styled.div`
  border: 1px solid #e1e1e1;
  border-radius: 10px;
  padding: 20px;
  transition: all 0.3s ease;
  cursor: pointer;

  &:hover {
    border-color: #667eea;
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.1);
  }
`;

const ProjectHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
`;

const ProjectName = styled.h3`
  margin: 0;
  color: #333;
  font-size: 18px;
  font-weight: 600;
`;

const ProjectActions = styled.div`
  display: flex;
  gap: 8px;
`;

const ActionButton = styled.button`
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
`;

const LoadButton = styled(ActionButton)`
  background: #28a745;
  color: white;

  &:hover {
    background: #218838;
  }
`;

const DeleteButton = styled(ActionButton)`
  background: #dc3545;
  color: white;

  &:hover {
    background: #c82333;
  }
`;

const ProjectDescription = styled.p`
  margin: 10px 0;
  color: #666;
  font-size: 14px;
  line-height: 1.5;
`;

const ProjectMeta = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #999;
  margin-top: 15px;
`;

const FilterPreview = styled.div`
  background: #f8f9fa;
  padding: 10px;
  border-radius: 6px;
  margin-top: 10px;
  font-size: 13px;
  color: #666;
`;

const NoProjects = styled.div`
  text-align: center;
  padding: 40px 20px;
  color: #666;
  font-size: 16px;
`;

const StatusMessage = styled.div`
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
  background: ${props => props.$type === 'error' ? '#dc3545' : '#28a745'};
  color: white;
`;

function SavedProjectsPanel({ user, activeFilters, onClose, onSaveProject, onLoadProject }) {
  const [activeTab, setActiveTab] = useState('load');
  const [projects, setProjects] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [saveForm, setSaveForm] = useState({
    name: '',
    description: ''
  });

  useEffect(() => {
    if (user) {
      loadUserProjects();
    }
  }, [user]);

  const loadUserProjects = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await apiService.getUserProjects(user.id);
      if (response.data.success) {
        setProjects(response.data.projects);
      } else {
        throw new Error(response.data.error || 'Failed to load projects');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveSubmit = async (e) => {
    e.preventDefault();
    
    if (!saveForm.name.trim()) {
      toast.error('Project name is required');
      return;
    }

    if (!activeFilters) {
      toast.error('No active filters to save');
      return;
    }

    setIsLoading(true);
    
    try {
      const project = await onSaveProject({
        name: saveForm.name.trim(),
        description: saveForm.description.trim()
      });

      toast.success('Project saved successfully!');
      setSaveForm({ name: '', description: '' });
      setActiveTab('load');
      await loadUserProjects(); // Refresh the projects list
    } catch (err) {
      // Error handling is done in the parent component
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadProject = async (project) => {
    setIsLoading(true);
    
    try {
      await onLoadProject(project);
      toast.success(`Project "${project.name}" loaded successfully!`);
    } catch (err) {
      toast.error(`Failed to load project: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteProject = async (projectId, projectName) => {
    if (!window.confirm(`Are you sure you want to delete "${projectName}"?`)) {
      return;
    }

    setIsLoading(true);
    
    try {
      await apiService.deleteProject(projectId);
      toast.success(`Project "${projectName}" deleted successfully!`);
      await loadUserProjects(); // Refresh the projects list
    } catch (err) {
      toast.error(`Failed to delete project: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-CA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatFilterPreview = (filters) => {
    if (!filters) return 'No filters';
    const { attribute, operator, value } = filters;
    return `${attribute} ${operator} ${value}`;
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <ManagerOverlay onClick={handleOverlayClick}>
      <ManagerContent>
        <CloseButton onClick={onClose}>×</CloseButton>
        
        <Title>Project Manager</Title>

        <TabContainer>
          <Tab 
            active={activeTab === 'load'} 
            onClick={() => setActiveTab('load')}
          >
            Load Projects
          </Tab>
          <Tab 
            active={activeTab === 'save'} 
            onClick={() => setActiveTab('save')}
          >
            Save Current Analysis
          </Tab>
        </TabContainer>

        {error && (
          <StatusMessage $type="error">
            Error: {error}
          </StatusMessage>
        )}

        <TabContent active={activeTab === 'load'}>
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>
              Loading projects...
            </div>
          ) : projects.length === 0 ? (
            <NoProjects>
              No saved projects yet.<br />
              Apply some filters and save your first analysis!
            </NoProjects>
          ) : (
            <ProjectsList>
              {projects.map(project => (
                <ProjectCard key={project.id}>
                  <ProjectHeader>
                    <ProjectName>{project.name}</ProjectName>
                    <ProjectActions>
                      <LoadButton 
                        onClick={(e) => {
                          e.stopPropagation();
                          handleLoadProject(project);
                        }}
                        disabled={isLoading}
                      >
                        Load
                      </LoadButton>
                      <DeleteButton 
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteProject(project.id, project.name);
                        }}
                        disabled={isLoading}
                      >
                        Delete
                      </DeleteButton>
                    </ProjectActions>
                  </ProjectHeader>
                  
                  {project.description && (
                    <ProjectDescription>{project.description}</ProjectDescription>
                  )}
                  
                  <FilterPreview>
                    <strong>Filters:</strong> {formatFilterPreview(project.filters)}
                  </FilterPreview>
                  
                  <ProjectMeta>
                    <span>Created: {formatDate(project.created_at)}</span>
                    <span>Updated: {formatDate(project.updated_at)}</span>
                  </ProjectMeta>
                </ProjectCard>
              ))}
            </ProjectsList>
          )}
        </TabContent>

        <TabContent active={activeTab === 'save'}>
          {!activeFilters ? (
            <StatusMessage $type="error">
              No active filters to save. Please apply some filters first using the query interface.
            </StatusMessage>
          ) : (
            <>
              <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
                <strong>Current Filters:</strong><br />
                <small>{formatFilterPreview(activeFilters)}</small>
              </div>
              
              <SaveForm onSubmit={handleSaveSubmit}>
                <InputGroup>
                  <Label htmlFor="projectName">Project Name *</Label>
                  <Input
                    id="projectName"
                    type="text"
                    value={saveForm.name}
                    onChange={(e) => setSaveForm({ ...saveForm, name: e.target.value })}
                    placeholder="e.g., Commercial Buildings Analysis"
                    disabled={isLoading}
                    required
                  />
                </InputGroup>
                
                <InputGroup>
                  <Label htmlFor="projectDescription">Description (optional)</Label>
                  <TextArea
                    id="projectDescription"
                    value={saveForm.description}
                    onChange={(e) => setSaveForm({ ...saveForm, description: e.target.value })}
                    placeholder="Describe what this analysis shows..."
                    disabled={isLoading}
                  />
                </InputGroup>
                
                <SaveButton type="submit" disabled={isLoading || !saveForm.name.trim()}>
                  {isLoading ? 'Saving...' : 'Save Project'}
                </SaveButton>
              </SaveForm>
            </>
          )}
        </TabContent>
      </ManagerContent>
    </ManagerOverlay>
  );
}

export default SavedProjectsPanel;
