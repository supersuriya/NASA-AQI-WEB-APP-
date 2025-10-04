// Cleaner, Safer Skies - NASA Air Quality Monitor
// Complete frontend with mock data and easy backend integration

// ============================================================================
// CONFIGURATION - Easy toggle for mock/real API
// ============================================================================
const useMock = true; // Set to false when backend is ready

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================
let map;
let currentLocation = null;
let airQualityChart = null;
let notificationPermission = null;

// Default location (New York City) if geolocation fails
const DEFAULT_LOCATION = {
    lat: 40.7128,
    lng: -74.0060
};

// Air quality categories with colors and icons
const AIR_QUALITY_CATEGORIES = {
    'Good': {
        color: '#10B981', // green-500
        bgColor: 'from-green-50 to-emerald-50',
        icon: '🌿',
        description: 'Air quality is satisfactory'
    },
    'Moderate': {
        color: '#F59E0B', // yellow-500
        bgColor: 'from-yellow-50 to-amber-50',
        icon: '😊',
        description: 'Air quality is acceptable'
    },
    'Unhealthy for Sensitive Groups': {
        color: '#F97316', // orange-500
        bgColor: 'from-orange-50 to-red-50',
        icon: '😷',
        description: 'Sensitive groups may experience health effects'
    },
    'Unhealthy': {
        color: '#EF4444', // red-500
        bgColor: 'from-red-50 to-pink-50',
        icon: '🔥',
        description: 'Everyone may experience health effects'
    },
    'Very Unhealthy': {
        color: '#8B5CF6', // purple-500
        bgColor: 'from-purple-50 to-indigo-50',
        icon: '💀',
        description: 'Health warnings of emergency conditions'
    },
    'Hazardous': {
        color: '#7C2D12', // red-900
        bgColor: 'from-red-100 to-red-200',
        icon: '☠️',
        description: 'Health alert: everyone may experience serious health effects'
    }
};

// ============================================================================
// INITIALIZATION
// ============================================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Cleaner, Safer Skies...');
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    // Initialize the map
    initializeMap();
    
    // Set up event listeners
    setupEventListeners();
    
    // Request notification permission
    requestNotificationPermission();
    
    // Initialize chart with empty data
    initializeChart();
    
    console.log('App initialized successfully');
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
 * Set up event listeners
 */
function setupEventListeners() {
    const useMyLocationBtn = document.getElementById('useMyLocation');
    
    if (useMyLocationBtn) {
        useMyLocationBtn.addEventListener('click', handleLocationRequest);
    }
}

/**
 * Request notification permission
 */
async function requestNotificationPermission() {
    if ('Notification' in window) {
        try {
            notificationPermission = await Notification.requestPermission();
            console.log('Notification permission:', notificationPermission);
        } catch (error) {
            console.log('Notification permission error:', error);
        }
    }
}

// ============================================================================
// LOCATION HANDLING
// ============================================================================

/**
 * Handle location request button click
 */
async function handleLocationRequest() {
    console.log('Location request initiated...');
    
    const button = document.getElementById('useMyLocation');
    const statusElement = document.getElementById('locationStatus');
    
    // Update UI
    button.disabled = true;
    button.innerHTML = '<span class="animate-spin">⏳</span> Getting Location...';
    statusElement.textContent = 'Getting your location...';
    
    try {
        // Get user's current location
        const location = await getCurrentLocation();
        
        if (location) {
            currentLocation = location;
            statusElement.textContent = `Location: ${location.lat.toFixed(4)}, ${location.lng.toFixed(4)}`;
            
            // Update map to user's location
            map.setView([location.lat, location.lng], 13);
            
            // Add location marker
            addLocationMarker();
            
            // Get air quality data
            await getAirQualityData(location.lat, location.lng);
        }
        
    } catch (error) {
        console.error('Location error:', error);
        statusElement.textContent = 'Location access denied. Using default location.';
        useDefaultLocation();
    } finally {
        // Reset button
        button.disabled = false;
        button.innerHTML = '<span class="text-xl">📍</span> Use My Location';
    }
}

/**
 * Get user's current location using geolocation API
 */
function getCurrentLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation is not supported by this browser'));
            return;
        }
        
        navigator.geolocation.getCurrentPosition(
            function(position) {
                resolve({
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                });
            },
            function(error) {
                reject(error);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000 // 5 minutes
            }
        );
    });
}

/**
 * Use default location when geolocation fails
 */
function useDefaultLocation() {
    console.log('Using default location (New York)');
    currentLocation = DEFAULT_LOCATION;
    
    // Update map to default location
    map.setView([DEFAULT_LOCATION.lat, DEFAULT_LOCATION.lng], 10);
    
    // Add location marker
    addLocationMarker();
    
    // Get air quality data for default location
    getAirQualityData(DEFAULT_LOCATION.lat, DEFAULT_LOCATION.lng);
}

/**
 * Add a marker for the current location
 */
function addLocationMarker() {
    if (!currentLocation) return;
    
    // Clear existing markers
    map.eachLayer(function(layer) {
        if (layer instanceof L.Marker) {
            map.removeLayer(layer);
        }
    });
    
    // Add new location marker
    const locationIcon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="width: 24px; height: 24px; background: #3B82F6; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 10px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 12px;">📍</div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
    
    const marker = L.marker([currentLocation.lat, currentLocation.lng], {
        icon: locationIcon
    }).addTo(map);
    
    marker.bindPopup(`
        <div style="text-align: center; min-width: 150px;">
            <strong>Your Location</strong><br>
            <small>Lat: ${currentLocation.lat.toFixed(4)}<br>
            Lng: ${currentLocation.lng.toFixed(4)}</small>
        </div>
    `);
}

// ============================================================================
// AIR QUALITY DATA FETCHING
// ============================================================================

/**
 * Get air quality data for given coordinates
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @param {boolean} useMock - Whether to use mock data or real API
 */
async function getAirQualityData(lat, lng, useMockData = useMock) {
    console.log(`Getting air quality data for lat: ${lat}, lng: ${lng}, useMock: ${useMockData}`);
    
    // Show loading state
    showLoadingState(true);
    
    try {
        let data;
        
        if (useMockData) {
            // Use mock data
            data = await getMockAirQualityData(lat, lng);
        } else {
            // Use real API
            data = await getRealAirQualityData(lat, lng);
        }
        
        // Display the results
        displayAirQualityResults(data);
        
        // Update chart with new data
        updateChart(data);
        
        // Check for notifications
        checkForNotifications(data);
        
        console.log('Air quality data loaded:', data);
        
    } catch (error) {
        console.error('Error getting air quality data:', error);
        showError('Failed to get air quality data. Please try again.');
    } finally {
        // Hide loading state
        showLoadingState(false);
    }
}

/**
 * Get mock air quality data
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 */
async function getMockAirQualityData(lat, lng) {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Generate mock data based on coordinates for variety
    const seed = Math.abs(lat + lng) * 1000;
    const random = (Math.sin(seed) + 1) / 2; // Normalize to 0-1
    
    const pm25Values = [8, 15, 22.5, 35, 45, 55, 65, 85];
    const categories = Object.keys(AIR_QUALITY_CATEGORIES);
    
    const pm25 = pm25Values[Math.floor(random * pm25Values.length)];
    const category = categories[Math.floor(random * categories.length)];
    
    return {
        predicted_pm25: pm25,
        category: category,
        source: 'Mock Data'
    };
}

/**
 * Get real air quality data from API
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 */
async function getRealAirQualityData(lat, lng) {
    const apiUrl = `http://localhost:8000/api/predict?lat=${lat}&lon=${lng}`;
    
    try {
        const response = await fetch(apiUrl);
        
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

// ============================================================================
// UI UPDATES
// ============================================================================

/**
 * Display air quality results in the UI
 * @param {Object} data - Air quality data
 */
function displayAirQualityResults(data) {
    console.log('Displaying air quality results:', data);
    
    // Update PM2.5 value
    document.getElementById('pm25Value').textContent = data.predicted_pm25;
    
    // Update category
    document.getElementById('airQualityCategory').textContent = data.category;
    
    // Update data source
    document.getElementById('dataSource').textContent = data.source;
    
    // Update category styling
    updateCategoryStyling(data.category);
    
    // Show the data display panel
    const display = document.getElementById('dataDisplay');
    display.classList.remove('hidden');
    
    // Smooth scroll to results
    display.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Update category styling based on air quality
 * @param {string} category - Air quality category
 */
function updateCategoryStyling(category) {
    const categoryCard = document.getElementById('categoryCard');
    const categoryIcon = document.getElementById('categoryIcon');
    
    const categoryInfo = AIR_QUALITY_CATEGORIES[category];
    
    if (categoryInfo) {
        // Update background color
        categoryCard.className = `text-center p-4 bg-gradient-to-br ${categoryInfo.bgColor} rounded-xl`;
        
        // Update icon
        categoryIcon.textContent = categoryInfo.icon;
    }
}

/**
 * Show/hide loading state
 * @param {boolean} show - Whether to show loading state
 */
function showLoadingState(show) {
    const spinner = document.getElementById('loadingSpinner');
    
    if (show) {
        spinner.classList.remove('hidden');
    } else {
        spinner.classList.add('hidden');
    }
}

/**
 * Show error message
 * @param {string} message - Error message to display
 */
function showError(message) {
    const statusElement = document.getElementById('locationStatus');
    statusElement.textContent = message;
    statusElement.className = 'text-sm text-red-600';
    
    // Reset after 5 seconds
    setTimeout(() => {
        statusElement.className = 'text-sm text-gray-600';
        statusElement.textContent = 'Click to get your location';
    }, 5000);
}

// ============================================================================
// CHART FUNCTIONALITY
// ============================================================================

/**
 * Initialize the air quality chart
 */
function initializeChart() {
    const ctx = document.getElementById('airQualityChart').getContext('2d');
    
    airQualityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: generateTimeLabels(),
            datasets: [{
                label: 'PM2.5 (μg/m³)',
                data: generateMockHistoricalData(),
                borderColor: '#3B82F6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#3B82F6',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        color: '#6B7280'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        color: '#6B7280'
                    }
                }
            },
            elements: {
                point: {
                    hoverRadius: 8
                }
            }
        }
    });
}

/**
 * Generate time labels for the last 6 hours
 */
function generateTimeLabels() {
    const labels = [];
    const now = new Date();
    
    for (let i = 5; i >= 0; i--) {
        const time = new Date(now.getTime() - (i * 60 * 60 * 1000));
        labels.push(time.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true 
        }));
    }
    
    return labels;
}

/**
 * Generate mock historical data for the last 6 hours
 */
function generateMockHistoricalData() {
    const data = [];
    const baseValue = 20 + Math.random() * 30; // Base value between 20-50
    
    for (let i = 0; i < 6; i++) {
        // Add some variation to make it look realistic
        const variation = (Math.random() - 0.5) * 10;
        const value = Math.max(5, baseValue + variation);
        data.push(Math.round(value * 10) / 10);
    }
    
    return data;
}

/**
 * Update chart with new data
 * @param {Object} data - New air quality data
 */
function updateChart(data) {
    if (!airQualityChart) return;
    
    // Add new data point
    const newData = [...airQualityChart.data.datasets[0].data];
    newData.shift(); // Remove oldest point
    newData.push(data.predicted_pm25); // Add new point
    
    // Update chart
    airQualityChart.data.datasets[0].data = newData;
    airQualityChart.update('active');
}

// ============================================================================
// NOTIFICATIONS
// ============================================================================

/**
 * Check for notifications based on air quality
 * @param {Object} data - Air quality data
 */
function checkForNotifications(data) {
    const unhealthyCategories = ['Unhealthy', 'Very Unhealthy', 'Hazardous'];
    
    if (unhealthyCategories.includes(data.category) && notificationPermission === 'granted') {
        showAirQualityNotification(data);
    }
}

/**
 * Show air quality notification
 * @param {Object} data - Air quality data
 */
function showAirQualityNotification(data) {
    const notification = new Notification('⚠️ Air Quality Alert', {
        body: `Air quality is ${data.category.toLowerCase()} in your area! PM2.5: ${data.predicted_pm25} μg/m³. Limit outdoor activity.`,
        icon: '/favicon.ico', // You can add a custom icon
        tag: 'air-quality-alert'
    });
    
    // Auto-close after 10 seconds
    setTimeout(() => {
        notification.close();
    }, 10000);
    
    // Handle click
    notification.onclick = function() {
        window.focus();
        notification.close();
    };
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get category color
 * @param {string} category - Air quality category
 * @returns {string} Color hex code
 */
function getCategoryColor(category) {
    return AIR_QUALITY_CATEGORIES[category]?.color || '#6B7280';
}

/**
 * Get category icon
 * @param {string} category - Air quality category
 * @returns {string} Emoji icon
 */
function getCategoryIcon(category) {
    return AIR_QUALITY_CATEGORIES[category]?.icon || '❓';
}

// Export functions for testing (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getMockAirQualityData,
        AIR_QUALITY_CATEGORIES,
        generateMockHistoricalData
    };
}