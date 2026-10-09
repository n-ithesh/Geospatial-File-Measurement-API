<div align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Inter&weight=700&size=36&pause=1000&color=3B82F6&center=true&vCenter=true&width=800&height=80&lines=Geospatial+File+Measurement;Automated+UTM+Projection;FastAPI+%2B+Next.js+Fullstack" alt="Animated Header" />
  
  <p align="center">
    <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=FastAPI&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js" />
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
  </p>
</div>

---

## What is this project?
The Geospatial File Measurement System is a full-stack application designed to process geospatial files (zipped Shapefiles and KML files). It extracts geographical features from these files, automatically calculates highly accurate metric measurements (area and length) by projecting the data into UTM (Universal Transverse Mercator), and provides an interactive web interface for users to upload files, view processing status, and visualize the features and measurements on a map.

The system is composed of two main parts:
- **Backend**: A production-quality REST API built with FastAPI (Python) and SQLite/PostgreSQL.
- **Frontend**: A modern web interface built with Next.js (React) and React Leaflet.

## Why was this project developed?
Calculating accurate measurements (like the area of a polygon or length of a line) from geographic coordinates (longitude/latitude) is complex because the Earth is not flat. Standard GIS tools require users to manually understand and select the correct projected coordinate reference systems (CRS) to get accurate metric results. 

This project was developed to automate this process. It removes the need for manual GIS software intervention by automatically determining the correct UTM zone for each feature, reprojecting it on the fly, and computing accurate measurements. It provides a simple, accessible web UI for non-technical users to process geospatial data effortlessly.

## How does this project work?
1. **Upload**: A user uploads a `.zip` (containing a Shapefile) or `.kml` file via the web frontend or directly to the API.
2. **Processing**: 
   - The FastAPI backend validates the file and extracts all contained geometric features using `geopandas` and `pyogrio`.
   - For each feature, the backend determines the appropriate UTM zone based on its geographic location.
   - The geometry is transformed from its source CRS (e.g., EPSG:4326) into the specific UTM zone.
   - Accurate area (in square meters) or length (in meters) is calculated using Shapely.
3. **Storage**: The original geometries, their properties, and the calculated measurements are stored in a database.
4. **Visualization**: The Next.js frontend queries the API for the processed features, displaying them in a data table and overlaying them on an interactive map using React Leaflet.

## What is needed? (Prerequisites)

### General
- Git (optional, for cloning)

### Backend Prerequisites
- Python 3.11+
- `pip` (Python package manager)
- (Optional) Docker for containerized deployment

### Frontend Prerequisites
- Node.js (v18 or higher recommended)
- `npm` (Node package manager)

## Setup and Installation

### 1. Backend Setup
Navigate to the `backend/` directory:
```bash
cd backend/
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
Run the backend server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*Interactive API docs will be available at http://localhost:8000/docs*

### 2. Frontend Setup
Navigate to the `frontend/` directory:
```bash
cd frontend/
cp .env.local.example .env.local
npm install
```
Run the frontend development server:
```bash
npm run dev
```
*The web interface will be available at http://localhost:3000*

## Architecture Overview
- **Backend API**: FastAPI, GeoPandas, Shapely, SQLAlchemy, SQLite (default)
- **Frontend App**: Next.js 14 (App Router), React Query, Tailwind CSS, React Leaflet

For more detailed information, please refer to the specific README files in the `backend/` and `frontend/` directories.
