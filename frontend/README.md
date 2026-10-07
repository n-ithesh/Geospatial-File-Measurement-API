# Geospatial File Measurement Frontend

This is the Next.js frontend for the Geospatial File Measurement API.
It allows users to upload zipped Shapefiles and KML files, view their processing status, and explore their extracted features on a map along with their area/length measurements.

## Tech Stack
- Next.js 14+ (App Router)
- React Query (Data fetching, caching, polling)
- React Dropzone (File uploads)
- React Leaflet (Map visualization)
- Tailwind CSS (Styling)

## Setup

1. Copy the example env file:
   ```bash
   cp .env.local.example .env.local
   ```
   Ensure `NEXT_PUBLIC_API_URL` points to your backend instance.

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Backend CORS
Ensure your backend (FastAPI) is configured to allow CORS requests from `http://localhost:3000`. By default, the `CORS_ORIGINS` environment variable in the backend handles this.

## Build for Production

```bash
npm run build
npm start
```
