# UML System Architecture Documentation

## Class Diagram

```mermaid
classDiagram
    class User {
        +int id
        +string username
        +datetime created_at
        +List~Project~ projects
        +to_dict() dict
        +find_or_create(username) User
    }

    class Project {
        +int id
        +int user_id
        +string name
        +string description
        +string filters_json
        +datetime created_at
        +datetime updated_at
        +filters property
        +to_dict() dict
        +update_filters(filters) void
    }

    class Building {
        +int id
        +string building_id
        +string address
        +float latitude
        +float longitude
        +string footprint_coords
        +float height
        +int floors
        +string building_type
        +string zoning
        +float assessed_value
        +string land_use
        +int construction_year
        +datetime last_updated
        +footprint property
        +to_dict() dict
        +matches_filter(criteria) bool
    }

    class CalgaryDataFetcher {
        +string base_url
        +Session session
        +fetch_building_footprints(bounds, limit) List~Dict~
        +fetch_property_assessments(limit) List~Dict~
        +fetch_zoning_data(limit) List~Dict~
        -_get_sample_data() List~Dict~
    }

    class BuildingQueryService {
        +string api_key
        +string api_url
        +Session session
        +process_query(query) Dict
        -_query_llm_api(query) Dict
        -_fallback_query_parsing(query) Dict
        -_create_extraction_prompt(query) string
        -_parse_llm_response(response) Dict
        -_validate_filter_criteria(data) bool
    }

    class BuildingProcessor {
        +process_and_store_buildings(data) List~Building~
        +get_buildings_in_bounds(bounds) List~Building~
        +filter_buildings(buildings, criteria) List~Building~
        +get_building_statistics(buildings) Dict
        -_process_single_building(data) Building
        -_update_building_from_data(building, data) void
        -_extract_spatial_data(geometry) Tuple
        -_normalize_building_type(type) string
    }

    User ||--o{ Project : owns
    CalgaryDataFetcher ..> Building : creates
    BuildingProcessor ..> Building : processes
    BuildingQueryService ..> Project : filters
```

## Sequence Diagram - LLM Query Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Flask_API
    participant BuildingQueryService
    participant HuggingFace_API
    participant BuildingProcessor
    participant Database

    User->>Frontend: Enter natural language query
    Frontend->>Flask_API: POST /api/query/process
    Flask_API->>BuildingQueryService: process_query(user_input)
    
    alt Has Hugging Face API Key
        BuildingQueryService->>HuggingFace_API: Send structured prompt
        HuggingFace_API-->>BuildingQueryService: Return JSON filter criteria
        BuildingQueryService->>BuildingQueryService: Parse and validate response
    else No API Key or API Fails
        BuildingQueryService->>BuildingQueryService: Use fallback rule-based parsing
    end
    
    BuildingQueryService-->>Flask_API: Return filter criteria
    Flask_API->>BuildingProcessor: Get buildings from database
    Database-->>BuildingProcessor: Return building records
    BuildingProcessor->>BuildingProcessor: Apply filter criteria
    BuildingProcessor-->>Flask_API: Return filtered buildings
    Flask_API-->>Frontend: JSON response with buildings
    Frontend->>Frontend: Update 3D visualization
    Frontend->>User: Display filtered buildings
```

## Component Architecture Diagram

```mermaid
graph TB
    subgraph "Frontend (React + Three.js)"
        A[App.js] --> B[UserIdentityForm]
        A --> C[BuildingQueryPanel]
        A --> D[CalgaryMap3D]
        A --> E[BuildingDetailsPanel]
        A --> F[SavedProjectsPanel]
        D --> G[Building.js]
        D --> H[Three.js Scene]
        I[dashboardApi.js] --> A
    end

    subgraph "Backend (Flask)"
        J[run.py] --> K[Flask App]
        K --> L[API Routes]
        L --> M[Buildings Routes]
        L --> N[Projects Routes]
        L --> O[LLM Routes]
        L --> P[User Routes]
        
        Q[Services Layer]
        M --> Q
        N --> Q
        O --> Q
        P --> Q
        
        Q --> R[CalgaryDataFetcher]
        Q --> S[BuildingQueryService]
        Q --> T[BuildingProcessor]
        
        U[Database Models]
        Q --> U
        U --> V[User Model]
        U --> W[Project Model]
        U --> X[Building Model]
    end

    subgraph "External APIs"
        Y[Calgary Open Data API]
        Z[Hugging Face API]
    end

    subgraph "Database"
        AA[SQLite Database]
    end

    I -.->|HTTP Requests| L
    R -.->|Fetch Data| Y
    S -.->|LLM Queries| Z
    U -.->|Store/Retrieve| AA
```

## Data Flow Diagram

```mermaid
flowchart TD
    A[User Login] --> B[Load Building Data]
    B --> C{Data in Cache?}
    C -->|Yes| D[Load from Database]
    C -->|No| E[Fetch from Calgary API]
    E --> F[Process & Store Buildings]
    F --> D
    D --> G[Display 3D Buildings]
    
    G --> H[User Enters Query]
    H --> I[LLM Processing]
    I --> J[Generate Filters]
    J --> K[Apply Filters to Buildings]
    K --> L[Update 3D Visualization]
    
    L --> M{User Action}
    M -->|Save Project| N[Save to Database]
    M -->|Load Project| O[Retrieve from Database]
    M -->|New Query| H
    M -->|Click Building| P[Show Building Details]
    
    N --> G
    O --> K
    P --> G
```

## System States Diagram

```mermaid
stateDiagram-v2
    [*] --> NotLoggedIn
    NotLoggedIn --> LoggedIn : User enters username
    
    LoggedIn --> LoadingData : Fetch buildings
    LoadingData --> DataLoaded : Buildings retrieved
    LoadingData --> DataError : API failure
    DataError --> LoadingData : Retry
    
    DataLoaded --> FilteringBuildings : User enters query
    FilteringBuildings --> ProcessingQuery : Send to LLM
    ProcessingQuery --> FilterApplied : Filters generated
    ProcessingQuery --> QueryError : Processing failed
    QueryError --> DataLoaded : Show error, return to base state
    
    FilterApplied --> DataLoaded : Clear filters
    FilterApplied --> SavingProject : Save analysis
    FilterApplied --> LoadingProject : Load saved project
    
    SavingProject --> FilterApplied : Project saved
    LoadingProject --> FilterApplied : Project loaded
    
    DataLoaded --> ShowingBuildingDetails : Click building
    FilterApplied --> ShowingBuildingDetails : Click building
    ShowingBuildingDetails --> DataLoaded : Close popup
    ShowingBuildingDetails --> FilterApplied : Close popup (if filters active)
```

## Database Schema

```mermaid
erDiagram
    users {
        int id PK
        string username UK
        datetime created_at
    }
    
    projects {
        int id PK
        int user_id FK
        string name
        text description
        text filters_json
        datetime created_at
        datetime updated_at
    }
    
    buildings {
        int id PK
        string building_id UK
        string address
        float latitude
        float longitude
        text footprint_coords
        float height
        int floors
        string building_type
        string zoning
        float assessed_value
        string land_use
        int construction_year
        datetime last_updated
    }
    
    users ||--o{ projects : "owns"
```

## API Integration Flow

```mermaid
sequenceDiagram
    participant App as Frontend App
    participant API as Flask API
    participant Calgary as Calgary Open Data
    participant HF as Hugging Face API
    participant DB as SQLite Database

    Note over App,DB: Initial Data Loading
    App->>API: GET /api/buildings/area?bounds=...
    API->>DB: Query existing buildings
    alt No buildings in area
        API->>Calgary: Fetch building footprints
        Calgary-->>API: Return GeoJSON data
        API->>Calgary: Fetch property assessments
        Calgary-->>API: Return assessment data
        API->>API: Process and merge data
        API->>DB: Store processed buildings
    end
    API-->>App: Return building data

    Note over App,DB: Natural Language Query
    App->>API: POST /api/query/process
    API->>HF: Send structured prompt
    alt HF API available
        HF-->>API: Return parsed filters
    else HF API unavailable
        API->>API: Use fallback parsing
    end
    API->>DB: Query buildings with filters
    DB-->>API: Return filtered results
    API-->>App: Return filtered buildings

    Note over App,DB: Project Persistence
    App->>API: POST /api/projects/save
    API->>DB: Store project with filters
    DB-->>API: Confirm save
    API-->>App: Return saved project info
```

This UML documentation provides a comprehensive view of the system architecture, data flow, and component interactions for the Calgary Urban Intelligence Dashboard project.
