import React from 'react';
import styled from 'styled-components';

const PopupOverlay = styled.div`
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

const PopupContent = styled.div`
  background: white;
  border-radius: 15px;
  padding: 30px;
  max-width: 500px;
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

const BuildingTitle = styled.h2`
  margin: 0 30px 20px 0;
  color: #333;
  font-size: 24px;
  font-weight: 600;
`;

const InfoGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;

  @media (max-width: 480px) {
    grid-template-columns: 1fr;
  }
`;

const InfoItem = styled.div`
  display: flex;
  flex-direction: column;
`;

const InfoLabel = styled.span`
  font-size: 12px;
  color: #666;
  text-transform: uppercase;
  font-weight: 600;
  margin-bottom: 4px;
  letter-spacing: 0.5px;
`;

const InfoValue = styled.span`
  font-size: 16px;
  color: #333;
  font-weight: 500;
`;

const FullWidthInfo = styled.div`
  margin-bottom: 15px;
`;

const TypeBadge = styled.span`
  display: inline-block;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: ${props => {
    switch (props.$type?.toLowerCase()) {
      case 'commercial': return '#4A90E2';
      case 'residential': return '#7ED321';
      case 'industrial': return '#BD10E0';
      case 'mixed use': return '#F5A623';
      default: return '#888888';
    }
  }};
  color: white;
`;

const CoordinatesContainer = styled.div`
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  margin-top: 20px;
`;

const CoordinatesTitle = styled.h4`
  margin: 0 0 10px 0;
  color: #333;
  font-size: 14px;
  font-weight: 600;
`;

const CoordinateText = styled.div`
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #666;
  line-height: 1.4;
`;

function BuildingDetailsPanel({ building, onClose }) {
    const formatCurrency = (value) => {
        if (!value || value === 0) return 'Assessment data not available';
        return new Intl.NumberFormat('en-CA', {
            style: 'currency',
            currency: 'CAD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value);
    };

    const formatNumber = (value) => {
        if (!value || value === 0) return 'Not specified';
        return new Intl.NumberFormat('en-CA').format(value);
    };

    const formatHeight = (height) => {
        if (!height || height === 0) return 'Height data not available';
        return `${height} ${height > 50 ? 'm' : 'ft'}`;
    };

    const formatZoning = (zoning) => {
        if (!zoning) return 'Zoning data not available';
        
        // Calgary zoning code explanations
        const zoningExplanations = {
            'CC-X': 'Centre City - Mixed use downtown core',
            'RC-G': 'Residential - Contextual One/Two Dwelling District',
            'M-CG': 'Mixed Use - Commercial/Residential',
            'C-C1': 'Commercial - Community Commercial',
            'C-O': 'Commercial - Office',
            'I-G': 'Industrial - General Industrial',
            'R-C1': 'Residential - Contextual One Dwelling',
            'R-C2': 'Residential - Contextual One/Two Dwelling',
            'M-C1': 'Mixed Use - Commercial',
            'M-H1': 'Mixed Use - High Density',
            'DC': 'Direct Control District'
        };
        
        const explanation = zoningExplanations[zoning];
        return explanation ? `${zoning} (${explanation})` : zoning;
    };

    const formatLandUse = (landUse) => {
        if (!landUse) return 'Land use data not available';
        return landUse;
    };

  const formatCoordinates = (lat, lng) => {
    if (!lat || !lng) return 'N/A';
    return `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <PopupOverlay onClick={handleOverlayClick}>
      <PopupContent>
        <CloseButton onClick={onClose}>×</CloseButton>
        
        <BuildingTitle>
          {building.address || `Building ${building.building_id}`}
        </BuildingTitle>

        <FullWidthInfo>
          <InfoLabel>Building Type</InfoLabel>
          <div>
            <TypeBadge $type={building.building_type}>
              {building.building_type || 'Unknown'}
            </TypeBadge>
          </div>
        </FullWidthInfo>

        <InfoGrid>
          <InfoItem>
            <InfoLabel>Height</InfoLabel>
            <InfoValue>{formatHeight(building.height)}</InfoValue>
          </InfoItem>

          <InfoItem>
            <InfoLabel>Floors</InfoLabel>
            <InfoValue>{formatNumber(building.floors)}</InfoValue>
          </InfoItem>

          <InfoItem>
            <InfoLabel>Assessed Value</InfoLabel>
            <InfoValue>{formatCurrency(building.assessed_value)}</InfoValue>
          </InfoItem>

          <InfoItem>
            <InfoLabel>Zoning</InfoLabel>
            <InfoValue>{formatZoning(building.zoning)}</InfoValue>
          </InfoItem>

          <InfoItem>
            <InfoLabel>Land Use</InfoLabel>
            <InfoValue>{formatLandUse(building.land_use)}</InfoValue>
          </InfoItem>

          {building.property_type && (
            <InfoItem>
              <InfoLabel>Property Type</InfoLabel>
              <InfoValue>{building.property_type}</InfoValue>
            </InfoItem>
          )}

          {building.year_of_construction && (
            <InfoItem>
              <InfoLabel>Year Built</InfoLabel>
              <InfoValue>{building.year_of_construction}</InfoValue>
            </InfoItem>
          )}
        </InfoGrid>

        {(building.assessment_class || building.land_use_designation || building.comm_name) && (
          <FullWidthInfo>
            <InfoLabel>Assessment Details</InfoLabel>
            <InfoValue style={{fontSize: '12px', lineHeight: '1.4'}}>
              {building.assessment_class_description && (
                <div><strong>Class:</strong> {building.assessment_class_description}</div>
              )}
              {building.land_use_designation && (
                <div><strong>Land Use:</strong> {building.land_use_designation}</div>
              )}
              {building.comm_name && (
                <div><strong>Community:</strong> {building.comm_name}</div>
              )}
              {building.roll_number && (
                <div style={{color: '#888', fontSize: '11px', marginTop: '4px'}}>
                  Roll Number: {building.roll_number}
                </div>
              )}
            </InfoValue>
          </FullWidthInfo>
        )}

        <FullWidthInfo>
          <InfoLabel>Data Source</InfoLabel>
          <InfoValue style={{fontSize: '12px', color: '#666'}}>
            {building.data_source === 'sample' 
              ? 'Sample data with realistic Calgary building characteristics'
              : 'Live data from Calgary Open Data + OpenStreetMap'
            }
          </InfoValue>
        </FullWidthInfo>

        <FullWidthInfo>
          <InfoLabel>Building ID</InfoLabel>
          <InfoValue style={{fontSize: '11px', color: '#888'}}>
            {building.building_id || building.id}
          </InfoValue>
        </FullWidthInfo>

        <CoordinatesContainer>
          <CoordinatesTitle>Location Details</CoordinatesTitle>
          <CoordinateText>
            <strong>Coordinates:</strong> {formatCoordinates(building.latitude, building.longitude)}<br />
            {building.footprint && building.footprint.length > 0 && (
              <>
                <strong>Footprint:</strong> {building.footprint.length} coordinate points<br />
              </>
            )}
            {building.last_updated && (
              <>
                <strong>Last Updated:</strong> {new Date(building.last_updated).toLocaleDateString()}
              </>
            )}
          </CoordinateText>
        </CoordinatesContainer>
      </PopupContent>
    </PopupOverlay>
  );
}

export default BuildingDetailsPanel;
