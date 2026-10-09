import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///urban_dashboard.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    

    
    # Calgary Open Data API Configuration (Calgary's Native API)
    # Get your developer token from: https://data.calgary.ca/profile/edit/developer_settings
    CALGARY_OPEN_DATA_BASE_URL = 'https://data.calgary.ca/resource'
    CALGARY_DEVELOPER_TOKEN = os.environ.get('CALGARY_DEVELOPER_TOKEN')  # Calgary's native developer token
    
    # CORS Configuration
    CORS_ORIGINS = ['http://localhost:3000', 'https://localhost:3000']

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    DEVELOPMENT = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    DEVELOPMENT = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 