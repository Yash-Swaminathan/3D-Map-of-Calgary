# Calgary Open Data API Setup Guide

## 🔧 **Required: Get a Calgary Developer Token**

### Step 1: Register for a Calgary Data Account
1. Go to [https://data.calgary.ca](https://data.calgary.ca)
2. Sign up for a free account or sign in
3. Verify your email address

### Step 2: Create a Developer Token
1. Login to your Calgary account
2. Go to [https://data.calgary.ca/profile/edit/developer_settings](https://data.calgary.ca/profile/edit/developer_settings)
3. Create a new developer application token
4. Copy the token (it looks like: `aBcD3FgH1jKlMnOpQrStUvWxYz`)

### Step 3: Configure Your Environment
Create a `.env` file in the `backend/` directory:

```env
# Flask Configuration
FLASK_CONFIG=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///urban_dashboard.db

# Calgary Open Data API Configuration
# REQUIRED: Get your free developer token at https://data.calgary.ca/profile/edit/developer_settings
CALGARY_DEVELOPER_TOKEN=YOUR_ACTUAL_TOKEN_HERE

# LLM Configuration (Optional)
HUGGINGFACE_API_KEY=your-huggingface-api-key-here

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,https://localhost:3000

# Development settings
PORT=5001
DEBUG=true
```

## 📊 **Calgary Dataset Endpoints**

The application uses Calgary's SODA 2.1 API format:

### ✅ **Working Endpoints (with Developer Token):**
```
# Building Footprints (uc4c-6kbd) - Building outlines/polygons
https://data.calgary.ca/resource/uc4c-6kbd.json

# 3D Buildings (cchr-krqg) - Buildings with height data
https://data.calgary.ca/resource/cchr-krqg.json

# Zoning Data (qe6k-p9nh) - Land use districts
https://data.calgary.ca/resource/qe6k-p9nh.json

# Building Permits (c2es-76ed) - Construction permits with addresses
https://data.calgary.ca/resource/c2es-76ed.json

# Property Assessments (4bsw-nn7w) - Property values and details
https://data.calgary.ca/resource/4bsw-nn7w.json
```

## 🧪 **Test Your Setup**

After configuring your developer token, test the APIs:

```bash
# Test with curl (replace YOUR_TOKEN with your actual token)
curl -H "X-App-Token: YOUR_TOKEN" \
  "https://data.calgary.ca/resource/uc4c-6kbd.json?$limit=2"

# Should return JSON data with building footprints
```

## 🔄 **What Changed in the Code**

The application now uses:

1. **Calgary's native developer tokens**: From their developer portal
2. **SODA 2.1 API format**: Standard resource endpoints
3. **Proper authentication headers**: X-App-Token header
4. **Real data prioritization**: No fallback to sample data
5. **Combined data sources**: OSM + Calgary APIs for comprehensive coverage

## 🚀 **API Endpoints Available**

Your application now supports:

```bash
# Get buildings in downtown Calgary area
GET /api/buildings/area?bounds=51.0420,-114.0750,51.0480,-114.0650&limit=100

# Get zoning data for area
GET /api/buildings/zoning?bounds=51.0420,-114.0750,51.0480,-114.0650&limit=100

# Get building permits for area
GET /api/buildings/permits?bounds=51.0420,-114.0750,51.0480,-114.0650&limit=100

# Get 3D buildings with height data
GET /api/buildings/3d?bounds=51.0420,-114.0750,51.0480,-114.0650&limit=100

# Get comprehensive combined data
GET /api/buildings/area?refresh=true&bounds=51.0420,-114.0750,51.0480,-114.0650
```

## 🆘 **Still Having Issues?**

1. **Check your token**: Make sure it's correctly set in `.env` as `CALGARY_DEVELOPER_TOKEN`
2. **Restart the server**: Changes to `.env` require a restart
3. **Check logs**: Look for authentication warnings in the backend logs
4. **Verify token**: Test the curl command above with your token
5. **Check bounds**: Ensure you're using the correct coordinate format (lat_min,lng_min,lat_max,lng_max)

## 📝 **Rate Limits**

With a Calgary developer token, you get:
- **Higher rate limits** than anonymous access
- **Priority in API queue** during peak usage
- **Access to all datasets** without restrictions

## 🗺️ **Downtown Calgary Coordinates**

The application is optimized for downtown Calgary:
- **Latitude range**: 51.0420° to 51.0480°
- **Longitude range**: -114.0750° to -114.0650°
- **Coverage**: Beltline/Centre City district (3-4 blocks)

---

**🎉 This should give you access to real Calgary building data with proper authentication!** 