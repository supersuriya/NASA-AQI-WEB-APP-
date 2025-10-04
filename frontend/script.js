// NASA Air Quality Monitor - JavaScript Logic

// Global variables
let map;
let currentLocation = null;
let airQualityMarker = null;

// Default location (New York City) if geolocation fails
const DEFAULT_LOCATION = {
    lat: 40.7128,
    lng: -74.0060
};

// Air quality categories and their corresponding colors
const AIR_QUALITY_CATEGORIES = {
    'Good': {
        color: '#2ecc71',
        markerClass: 'marker-good',
        categoryClass: 'category-good'
    },
    'Moderate': {
        color: '#f39c12',
        markerClass: 'marker-moderate',
        categoryClass: 'category-moderate'
    },
    'Unhealthy for Sensitive Groups': {
        color: '#e67e22',
        markerClass: 'marker-unhealthy-sensitive',
        categoryClass: 'category-unhealthy-sensitive'
    },
    'Unhealthy': {
        color: '#e74c3c',
        markerClass: 'marker-unhealthy',
        categoryClass: 'category-unhealthy'
    }
};

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    console.log('Initializing NASA Air Quality Monitor...');
    
    // Initialize the map
    initializeMap();
    
    // Get user's current location
    getCurrentLocation();
    
    // Set up event listeners
    setupEventListeners();
}

/**
 * Initialize the Leaflet map
 */
function initializeMap() {
    console.log('Initializing map...');
    
    // Create map centered on default location
    map = L.map('map').setView([DEFAULT_LOCATION.lat, DEFAULT_LOCATION.lng], 10);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    console.log('Map initialized successfully');
}

/**
 * Get user's current location using geolocation API
 */
function getCurrentLocation() {
    console.log('Getting user location...');
    updateLocationStatus('Getting your location...');
    
    if (!navigator.geolocation) {
        console.log('Geolocation is not supported by this browser');
        useDefaultLocation();
        return;
    }
    
    navigator.geolocation.getCurrentPosition(
        function(position) {
            // Success callback
            currentLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude
            };
            
            console.log('Location obtained:', currentLocation);
            updateLocationStatus(`Location: ${currentLocation.lat.toFixed(4)}, ${currentLocation.lng.toFixed(4)}`);
            
            // Update map to user's location
            map.setView([currentLocation.lat, currentLocation.lng], 13);
            
            // Add a marker for user's location
            addLocationMarker();
        },
        function(error) {
            // Error callback
            console.log('Geolocation error:', error);
            useDefaultLocation();
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 300000 // 5 minutes
        }
    );
}

/**
 * Use default location when geolocation fails
 */
function useDefaultLocation() {
    console.log('Using default location (New York)');
    currentLocation = DEFAULT_LOCATION;
    updateLocationStatus('Using default location (New York)');
    
    // Add a marker for default location
    addLocationMarker();
}

/**
 * Add a marker for the current location
 */
function addLocationMarker() {
    if (!currentLocation) return;
    
    // Remove existing location marker if any
    if (map.hasLayer && map.hasLayer(airQualityMarker)) {
        map.removeLayer(airQualityMarker);
    }
    
    // Add new location marker
    const locationIcon = L.divIcon({
        className: 'air-quality-marker',
        html: '<div style="width: 20px; height: 20px; background: #3498db; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 10px rgba(0,0,0,0.3);"></div>',
        iconSize: [26, 26],
        iconAnchor: [13, 13]
    });
    
    airQualityMarker = L.marker([currentLocation.lat, currentLocation.lng], {
        icon: locationIcon
    }).addTo(map);
    
    airQualityMarker.bindPopup(`
        <div style="text-align: center;">
            <strong>Your Location</strong><br>
            <small>Lat: ${currentLocation.lat.toFixed(4)}<br>
            Lng: ${currentLocation.lng.toFixed(4)}</small>
        </div>
    `);
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    const checkAirQualityBtn = document.getElementById('checkAirQuality');
    
    if (checkAirQualityBtn) {
        checkAirQualityBtn.addEventListener('click', checkAirQuality);
    }
}

/**
 * Check air quality for current location
 */
async function checkAirQuality() {
    console.log('Checking air quality...');
    
    if (!currentLocation) {
        alert('Location not available. Please try again.');
        return;
    }
    
    const button = document.getElementById('checkAirQuality');
    const originalText = button.innerHTML;
    
    // Show loading state
    button.disabled = true;
    button.innerHTML = '<span class="loading"></span> Checking...';
    
    try {
        // Call the air quality API
        const airQualityData = await fetchAirQualityData(currentLocation.lat, currentLocation.lng);
        
        // Display the results
        displayAirQualityResults(airQualityData);
        
        // Update map marker with air quality data
        updateMapWithAirQuality(airQualityData);
        
        console.log('Air quality check completed:', airQualityData);
        
    } catch (error) {
        console.error('Error checking air quality:', error);
        alert('Failed to get air quality data. Please try again.');
    } finally {
        // Reset button state
        button.disabled = false;
        button.innerHTML = originalText;
    }
}

/**
 * Fetch air quality data from API
 * TODO: Replace this mock URL with the actual backend URL when ready:
 * http://localhost:8000/api/predict?lat={lat}&lon={lon}
 */
async function fetchAirQualityData(lat, lng) {
    console.log(`Fetching air quality data for lat: ${lat}, lng: ${lng}`);
    
    // Mock API endpoint - replace with actual backend when ready
    const mockApiUrl = 'https://jsonplaceholder.typicode.com/posts/1';
    
    // For now, we'll simulate the API response
    // TODO: Replace this with actual API call when backend is ready
    return new Promise((resolve) => {
        setTimeout(() => {
            // Generate mock data based on location
            const mockData = generateMockAirQualityData(lat, lng);
            resolve(mockData);
        }, 1500); // Simulate network delay
    });
    
    /* 
    // Uncomment this when backend is ready:
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
    */
}

/**
 * Generate mock air quality data for testing
 */
function generateMockAirQualityData(lat, lng) {
    // Generate some variation based on coordinates for testing
    const seed = Math.abs(lat + lng) * 1000;
    const random = (Math.sin(seed) + 1) / 2; // Normalize to 0-1
    
    const pm25Values = [15, 22.5, 35, 45, 55, 65];
    const categories = ['Good', 'Moderate', 'Unhealthy for Sensitive Groups', 'Unhealthy'];
    
    const pm25 = pm25Values[Math.floor(random * pm25Values.length)];
    const category = categories[Math.floor(random * categories.length)];
    
    return {
        predicted_pm25: pm25,
        category: category,
        source: 'Mock Data'
    };
}

/**
 * Display air quality results in the UI
 */
function displayAirQualityResults(data) {
    console.log('Displaying air quality results:', data);
    
    // Update the display elements
    document.getElementById('pm25Value').textContent = data.predicted_pm25;
    document.getElementById('dataSource').textContent = data.source;
    
    // Update category with appropriate styling
    const categoryElement = document.getElementById('airQualityCategory');
    categoryElement.textContent = data.category;
    
    // Remove existing category classes
    Object.values(AIR_QUALITY_CATEGORIES).forEach(cat => {
        categoryElement.classList.remove(cat.categoryClass);
    });
    
    // Add new category class
    if (AIR_QUALITY_CATEGORIES[data.category]) {
        categoryElement.classList.add(AIR_QUALITY_CATEGORIES[data.category].categoryClass);
    }
    
    // Show the air quality display
    const display = document.getElementById('airQualityDisplay');
    display.classList.remove('hidden');
    
    // Scroll to results
    display.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Update map with air quality data
 */
function updateMapWithAirQuality(data) {
    if (!currentLocation || !airQualityMarker) return;
    
    console.log('Updating map with air quality data:', data);
    
    // Remove existing marker
    map.removeLayer(airQualityMarker);
    
    // Get category styling
    const categoryInfo = AIR_QUALITY_CATEGORIES[data.category];
    const color = categoryInfo ? categoryInfo.color : '#3498db';
    const markerClass = categoryInfo ? categoryInfo.markerClass : '';
    
    // Create new marker with air quality data
    const airQualityIcon = L.divIcon({
        className: `air-quality-marker ${markerClass}`,
        html: `<div style="width: 24px; height: 24px; background: ${color}; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 10px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 10px;">AQ</div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
    
    airQualityMarker = L.marker([currentLocation.lat, currentLocation.lng], {
        icon: airQualityIcon
    }).addTo(map);
    
    // Create popup content
    const popupContent = `
        <div style="text-align: center; min-width: 150px;">
            <h4 style="margin: 0 0 10px 0; color: #2c3e50;">Air Quality</h4>
            <div style="margin-bottom: 8px;">
                <strong style="color: ${color};">${data.category}</strong>
            </div>
            <div style="margin-bottom: 8px;">
                <span style="font-size: 1.2em; font-weight: bold;">${data.predicted_pm25}</span>
                <span style="color: #7f8c8d; font-size: 0.9em;"> μg/m³</span>
            </div>
            <div style="font-size: 0.8em; color: #7f8c8d;">
                Source: ${data.source}
            </div>
        </div>
    `;
    
    airQualityMarker.bindPopup(popupContent).openPopup();
}

/**
 * Update location status text
 */
function updateLocationStatus(status) {
    const statusElement = document.getElementById('locationStatus');
    if (statusElement) {
        statusElement.textContent = status;
    }
}

// Export functions for testing (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        generateMockAirQualityData,
        AIR_QUALITY_CATEGORIES
    };
}
