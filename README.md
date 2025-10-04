# NASA Air Quality Monitor

A web application for monitoring air quality predictions powered by NASA data, built for the NASA Space Apps Challenge.

## Features

- 🌍 Interactive map using Leaflet.js
- 📍 Automatic geolocation detection
- 🔍 Air quality prediction with PM2.5 values
- 📱 Mobile-friendly responsive design
- 🎨 Color-coded air quality categories
- 🚀 Ready for backend integration

## Air Quality Categories

- **Good** (Green): PM2.5 < 12 μg/m³
- **Moderate** (Yellow): PM2.5 12-35 μg/m³
- **Unhealthy for Sensitive Groups** (Orange): PM2.5 35-55 μg/m³
- **Unhealthy** (Red): PM2.5 > 55 μg/m³

## Quick Start

### Option 1: Using Python (Recommended - No npm required)

1. Navigate to the project directory:
   ```bash
   cd "C:\Users\surap\OneDrive\Documents\hackathon\NASA-AQI-WEB-APP-"
   ```

2. Start a simple HTTP server:
   ```bash
   # Using Python 3
   python -m http.server 3000
   
   # Or using Python 2
   python -m SimpleHTTPServer 3000
   ```

3. Open your browser and go to: `http://localhost:3000/frontend/`

### Option 2: Using Node.js (if you have npm installed)

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm start
   ```

3. The app will automatically open in your browser at `http://localhost:3000`

### Option 3: Direct File Opening

Simply open `frontend/index.html` directly in your web browser. Note that some features (like geolocation) may not work properly when opening files directly.

## Project Structure

```
NASA-AQI-WEB-APP-/
├── frontend/
│   ├── index.html          # Main HTML file
│   ├── style.css           # Custom styles
│   └── script.js           # JavaScript logic
├── package.json            # Node.js dependencies
└── README.md              # This file
```

## How It Works

1. **Location Detection**: The app automatically detects your current location using the browser's geolocation API
2. **Map Display**: Shows an interactive map centered on your location (or New York as default)
3. **Air Quality Check**: Click the "Check Air Quality" button to get predictions
4. **Mock Data**: Currently uses mock data for testing (see backend integration below)
5. **Visual Feedback**: Displays results with color-coded categories and map markers

## Backend Integration

The app is ready to connect to your backend API. To integrate:

1. Open `frontend/script.js`
2. Find the `fetchAirQualityData` function (around line 150)
3. Replace the mock implementation with:

```javascript
async function fetchAirQualityData(lat, lng) {
    try {
        const response = await fetch(`http://localhost:8000/api/predict?lat=${lat}&lon=${lng}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}
```

4. Remove or comment out the mock data generation code

## API Response Format

The app expects the backend to return JSON in this format:

```json
{
    "predicted_pm25": 22.5,
    "category": "Moderate",
    "source": "NASA Data"
}
```

## Browser Compatibility

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- Mobile browsers: Full support

## Technologies Used

- **HTML5**: Semantic markup and structure
- **CSS3**: Modern styling with gradients and animations
- **JavaScript (ES6+)**: Modern JavaScript features
- **Leaflet.js**: Interactive maps
- **Geolocation API**: Location detection
- **Fetch API**: HTTP requests

## Development

The app is built with vanilla JavaScript, HTML, and CSS - no build process required. Simply edit the files in the `frontend/` directory and refresh your browser.

## Troubleshooting

### Geolocation not working
- Make sure you're using HTTPS or localhost
- Check browser permissions for location access
- The app will fall back to New York coordinates if geolocation fails

### Map not loading
- Check your internet connection (Leaflet loads tiles from OpenStreetMap)
- Try refreshing the page

### Styling issues
- Clear your browser cache
- Make sure all CSS files are loading properly

## License

MIT License - Feel free to use this code for your NASA Space Apps project!

## Contributing

This is a NASA Space Apps Challenge project. Feel free to fork and improve!
