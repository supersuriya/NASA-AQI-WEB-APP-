// Cleaner, Safer Skies - NASA Air Quality Monitor
// Enhanced frontend with real FastAPI backend integration

// ============================================================================
// CONFIGURATION
// ============================================================================
const API_BASE_URL = 'http://localhost:8000';
const USE_REAL_API = true; // Set to false to use mock data for testing

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================
let map;
let currentLocation = null;
let forecastChart = null;
let confidenceChart = null;
let notificationPermission = null;
let availableCities = [];
let currentCity = null;
let currentParameter = 'PM2.5';
let currentHoursAhead = 24;

// Default location (New York City) if geolocation fails
const DEFAULT_LOCATION = {
    lat: 40.7128,
    lng: -74.0060
};

// Air quality categories with colors and icons
const AIR_QUALITY_CATEGORIES = {
    'Good': {
        color: '#10B981',
        bgColor: 'from-green-50 to-emerald-50',
        icon: '🌿',
        description: 'Air quality is satisfactory'
    },
    'Moderate': {
        color: '#F59E0B',
        bgColor: 'from-yellow-50 to-amber-50',
        icon: '😊',
        description: 'Air quality is acceptable'
    },
    'Unhealthy for Sensitive Groups': {
        color: '#F97316',
        bgColor: 'from-orange-50 to-red-50',
        icon: '😷',
        description: 'Sensitive groups may experience health effects'
    },
    'Unhealthy': {
        color: '#EF4444',
        bgColor: 'from-red-50 to-pink-50',
        icon: '🔥',
        description: 'Everyone may experience health effects'
    },
    'Very Unhealthy': {
        color: '#8B5CF6',
        bgColor: 'from-purple-50 to-indigo-50',
        icon: '💀',
        description: 'Health warnings of emergency conditions'
    },
    'Hazardous': {
        color: '#7C2D12',
        bgColor: 'from-red-100 to-red-200',
        icon: '☠️',
        description: 'Health alert: everyone may experience serious health effects'
    }
};

// ============================================================================
// INITIALIZATION
// ============================================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Cleaner, Safer Skies with real API...');
    initializeApp();
});

/**
 * Initialize the application
 */
async function initializeApp() {
    try {
        // Initialize the map
        initializeMap();
        
        // Set up event listeners
        setupEventListeners();
        
        // Request notification permission
        requestNotificationPermission();
        
        // Initialize charts
        initializeCharts();
        
        // Load available cities from API
        await loadAvailableCities();
        
        // Load available parameters for default city
        await loadAvailableParameters();
        
        console.log('App initialized successfully');
    } catch (error) {
        console.error('Error initializing app:', error);
        showError('Failed to initialize application. Please refresh the page.');
    }
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
    // Location button
    const useMyLocationBtn = document.getElementById('useMyLocation');
    if (useMyLocationBtn) {
        useMyLocationBtn.addEventListener('click', handleLocationRequest);
    }
    
    // City selection
    const citySelect = document.getElementById('citySelect');
    if (citySelect) {
        citySelect.addEventListener('change', handleCityChange);
    }
    
    // Parameter selection
    const parameterSelect = document.getElementById('parameterSelect');
    if (parameterSelect) {
        parameterSelect.addEventListener('change', handleParameterChange);
    }
    
    // Hours ahead selection
    const hoursSelect = document.getElementById('hoursSelect');
    if (hoursSelect) {
        hoursSelect.addEventListener('change', handleHoursChange);
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
// API INTEGRATION
// ============================================================================

/**
 * Load available cities from the API
 */
async function loadAvailableCities() {
    try {
        console.log('Loading available cities...');
        const response = await fetch(`${API_BASE_URL}/cities`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        availableCities = data.cities || [];
        
        // Populate city select dropdown
        const citySelect = document.getElementById('citySelect');
        citySelect.innerHTML = '<option value="">Select a city...</option>';
        
        availableCities.forEach(city => {
            const option = document.createElement('option');
            option.value = city;
            option.textContent = city;
            citySelect.appendChild(option);
        });
        
        console.log(`Loaded ${availableCities.length} cities`);
    } catch (error) {
        console.error('Error loading cities:', error);
        showError('Failed to load cities. Using default location.');
    }
}

/**
 * Load available parameters for a city
 */
async function loadAvailableParameters(city = null) {
    if (!city) return;
    
    try {
        console.log(`Loading parameters for ${city}...`);
        const response = await fetch(`${API_BASE_URL}/parameters/${encodeURIComponent(city)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const parameters = data.parameters || ['PM2.5', 'O3', 'NO2'];
        
        // Update parameter select dropdown
        const parameterSelect = document.getElementById('parameterSelect');
        parameterSelect.innerHTML = '';
        
        parameters.forEach(param => {
            const option = document.createElement('option');
            option.value = param;
            option.textContent = param;
            parameterSelect.appendChild(option);
        });
        
        // Set default parameter
        if (parameters.includes('PM2.5')) {
            parameterSelect.value = 'PM2.5';
            currentParameter = 'PM2.5';
        }
        
        console.log(`Loaded parameters for ${city}:`, parameters);
    } catch (error) {
        console.error(`Error loading parameters for ${city}:`, error);
    }
}

/**
 * Get air quality prediction from the API
 */
async function getAirQualityPrediction(city, parameter, hoursAhead) {
    try {
        console.log(`Getting prediction for ${city} - ${parameter} (${hoursAhead}h)`);
        
        const requestBody = {
            city: city,
            parameter: parameter,
            hours_ahead: hoursAhead,
            use_real_data: true
        };
        
        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Prediction data received:', data);
        
        return data;
    } catch (error) {
        console.error('Error getting prediction:', error);
        throw error;
    }
}

/**
 * Get mock data for testing (when API is not available)
 */
async function getMockAirQualityData(city, parameter, hoursAhead) {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Generate mock data
    const seed = Math.abs(city.length + parameter.length) * 1000;
    const random = (Math.sin(seed) + 1) / 2;
    
    const predictions = [];
    const confidenceIntervals = [];
    
    for (let i = 1; i <= hoursAhead; i++) {
        const baseValue = 20 + Math.random() * 30;
        const prediction = baseValue + (Math.random() - 0.5) * 10;
        const confidence = prediction * 0.2; // 20% confidence interval
        
        predictions.push({
            hour: i,
            timestamp: new Date(Date.now() + i * 60 * 60 * 1000).toISOString(),
            predicted_value: Math.round(prediction * 10) / 10
        });
        
        confidenceIntervals.push({
            hour: i,
            lower_bound: Math.round((prediction - confidence) * 10) / 10,
            upper_bound: Math.round((prediction + confidence) * 10) / 10
        });
    }
    
    return {
        city: city,
        parameter: parameter,
        hours_ahead: hoursAhead,
        predictions: predictions,
        confidence_intervals: confidenceIntervals,
        model_metadata: {
            model_type: 'RandomForestRegressor',
            model_accuracy: 0.85,
            real_data_enabled: false
        },
        data_sources: {
            tempo: false,
            openaq: false,
            weather: false
        },
        timestamp: new Date().toISOString()
    };
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
            
            // Find nearest city and get air quality data
            await findNearestCityAndGetData(location);
        }
        
    } catch (error) {
        console.error('Location error:', error);
        statusElement.textContent = 'Location access denied. Please select a city manually.';
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
 * Find nearest city and get air quality data
 */
async function findNearestCityAndGetData(location) {
    // For simplicity, we'll use a basic distance calculation
    // In a real app, you might use a more sophisticated geocoding service
    let nearestCity = 'New York'; // Default
    let minDistance = Infinity;
    
    // Simple distance calculation (not accurate for large distances)
    availableCities.forEach(city => {
        // This is a simplified approach - in reality you'd need city coordinates
        const distance = Math.random() * 1000; // Mock distance
        if (distance < minDistance) {
            minDistance = distance;
            nearestCity = city;
        }
    });
    
    // Set the city in the dropdown
    const citySelect = document.getElementById('citySelect');
    citySelect.value = nearestCity;
    currentCity = nearestCity;
    
    // Load parameters for this city
    await loadAvailableParameters(nearestCity);
    
    // Get air quality data
    await getAirQualityData(nearestCity, currentParameter, currentHoursAhead);
}

/**
 * Handle city selection change
 */
async function handleCityChange(event) {
    const selectedCity = event.target.value;
    if (selectedCity) {
        currentCity = selectedCity;
        await loadAvailableParameters(selectedCity);
        await getAirQualityData(selectedCity, currentParameter, currentHoursAhead);
    }
}

/**
 * Handle parameter selection change
 */
async function handleParameterChange(event) {
    currentParameter = event.target.value;
    if (currentCity) {
        await getAirQualityData(currentCity, currentParameter, currentHoursAhead);
    }
}

/**
 * Handle hours ahead selection change
 */
async function handleHoursChange(event) {
    currentHoursAhead = parseInt(event.target.value);
    if (currentCity) {
        await getAirQualityData(currentCity, currentParameter, currentHoursAhead);
    }
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
 * Get air quality data for given parameters
 */
async function getAirQualityData(city, parameter, hoursAhead) {
    console.log(`Getting air quality data for ${city} - ${parameter} (${hoursAhead}h)`);
    
    // Show loading state
    showLoadingState(true);
    
    try {
        let data;
        
        if (USE_REAL_API) {
            // Use real API
            data = await getAirQualityPrediction(city, parameter, hoursAhead);
        } else {
            // Use mock data
            data = await getMockAirQualityData(city, parameter, hoursAhead);
        }
        
        // Display the results
        displayAirQualityResults(data);
        
        // Update charts with new data
        updateForecastChart(data);
        updateConfidenceChart(data);
        
        // Check for notifications
        checkForNotifications(data);
        
        console.log('Air quality data loaded:', data);
        
    } catch (error) {
        console.error('Error getting air quality data:', error);
        showError(`Failed to get air quality data: ${error.message}`);
    } finally {
        // Hide loading state
        showLoadingState(false);
    }
}

// ============================================================================
// UI UPDATES
// ============================================================================

/**
 * Display air quality results in the UI
 */
function displayAirQualityResults(data) {
    console.log('Displaying air quality results:', data);
    
    // Get current prediction (first hour)
    const currentPrediction = data.predictions[0];
    const currentValue = currentPrediction.value; // Changed from predicted_value to value
    
    // Update current value
    document.getElementById('currentValue').textContent = currentValue.toFixed(1);
    
    // Update parameter display
    const unit = data.parameter === 'PM2.5' ? 'μg/m³' : 'ppb';
    document.getElementById('currentParameter').textContent = `${data.parameter} (${unit})`;
    
    // Determine air quality category
    const category = getAirQualityCategory(data.parameter, currentValue);
    document.getElementById('airQualityCategory').textContent = category;
    
    // Update data sources
    const sources = [];
    // Since we're using sample data, show the data source from model_metadata
    if (data.model_metadata && data.model_metadata.data_source) {
        sources.push(data.model_metadata.data_source);
    } else {
        sources.push('Sample Data');
    }
    
    document.getElementById('dataSources').textContent = sources.join(', ');
    
    // Update model accuracy
    const accuracy = data.model_metadata && data.model_metadata.accuracy;
    if (accuracy && accuracy !== 'N/A - Sample Data') {
        // If accuracy is a number, convert to percentage
        if (typeof accuracy === 'number') {
            document.getElementById('modelAccuracy').textContent = `${(accuracy * 100).toFixed(1)}%`;
        } else {
            document.getElementById('modelAccuracy').textContent = accuracy;
        }
    } else {
        document.getElementById('modelAccuracy').textContent = 'N/A';
    }
    
    // Update category styling
    updateCategoryStyling(category);
    
    // Show the data display panel
    const display = document.getElementById('dataDisplay');
    display.classList.remove('hidden');
    
    // Smooth scroll to results
    display.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Get air quality category based on parameter and value
 */
function getAirQualityCategory(parameter, value) {
    if (parameter === 'PM2.5') {
        if (value <= 12) return 'Good';
        if (value <= 35.4) return 'Moderate';
        if (value <= 55.4) return 'Unhealthy for Sensitive Groups';
        if (value <= 150.4) return 'Unhealthy';
        if (value <= 250.4) return 'Very Unhealthy';
        return 'Hazardous';
    } else if (parameter === 'O3') {
        if (value <= 54) return 'Good';
        if (value <= 70) return 'Moderate';
        if (value <= 85) return 'Unhealthy for Sensitive Groups';
        if (value <= 105) return 'Unhealthy';
        if (value <= 200) return 'Very Unhealthy';
        return 'Hazardous';
    } else if (parameter === 'NO2') {
        if (value <= 53) return 'Good';
        if (value <= 100) return 'Moderate';
        if (value <= 360) return 'Unhealthy for Sensitive Groups';
        if (value <= 649) return 'Unhealthy';
        if (value <= 1249) return 'Very Unhealthy';
        return 'Hazardous';
    }
    return 'Unknown';
}

/**
 * Update category styling based on air quality
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
 */
function showError(message) {
    const statusElement = document.getElementById('locationStatus');
    statusElement.textContent = message;
    statusElement.className = 'mt-4 text-sm text-red-600 text-center';
    
    // Reset after 5 seconds
    setTimeout(() => {
        statusElement.className = 'mt-4 text-sm text-gray-600 text-center';
        statusElement.textContent = 'Click "Use My Location" or select a city to get started';
    }, 5000);
}

// ============================================================================
// CHART FUNCTIONALITY
// ============================================================================

/**
 * Initialize the charts
 */
function initializeCharts() {
    // Initialize forecast chart
    const forecastCtx = document.getElementById('forecastChart').getContext('2d');
    forecastChart = new Chart(forecastCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Predicted Value',
                data: [],
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
                    display: true
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
            }
        }
    });
    
    // Initialize confidence chart
    const confidenceCtx = document.getElementById('confidenceChart').getContext('2d');
    confidenceChart = new Chart(confidenceCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Upper Bound',
                data: [],
                borderColor: '#EF4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                borderWidth: 2,
                fill: false,
                tension: 0.4
            }, {
                label: 'Predicted Value',
                data: [],
                borderColor: '#3B82F6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 3,
                fill: false,
                tension: 0.4,
                pointBackgroundColor: '#3B82F6',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 6
            }, {
                label: 'Lower Bound',
                data: [],
                borderColor: '#10B981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                fill: false,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true
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
            }
        }
    });
}

/**
 * Update forecast chart with new data
 */
function updateForecastChart(data) {
    if (!forecastChart) return;
    
    const labels = data.predictions.map(p => {
        const date = new Date(p.timestamp);
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true 
        });
    });
    
    const values = data.predictions.map(p => p.value);
    
    forecastChart.data.labels = labels;
    forecastChart.data.datasets[0].data = values;
    forecastChart.data.datasets[0].label = `${data.parameter} (${data.parameter === 'PM2.5' ? 'μg/m³' : 'ppb'})`;
    
    forecastChart.update('active');
}

/**
 * Update confidence chart with new data
 */
function updateConfidenceChart(data) {
    if (!confidenceChart) return;
    
    const labels = data.predictions.map(p => {
        const date = new Date(p.timestamp);
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true 
        });
    });
    
    const upperBounds = data.confidence_intervals.map(c => c.upper);
    const lowerBounds = data.confidence_intervals.map(c => c.lower);
    const values = data.predictions.map(p => p.value);
    
    confidenceChart.data.labels = labels;
    confidenceChart.data.datasets[0].data = upperBounds; // Upper bound
    confidenceChart.data.datasets[1].data = values; // Predicted value
    confidenceChart.data.datasets[2].data = lowerBounds; // Lower bound
    
    confidenceChart.update('active');
}

// ============================================================================
// NOTIFICATIONS
// ============================================================================

/**
 * Check for notifications based on air quality
 */
function checkForNotifications(data) {
    const currentValue = data.predictions[0].value;
    const category = getAirQualityCategory(data.parameter, currentValue);
    const unhealthyCategories = ['Unhealthy', 'Very Unhealthy', 'Hazardous'];
    
    if (unhealthyCategories.includes(category) && notificationPermission === 'granted') {
        showAirQualityNotification(data, category, currentValue);
    }
}

/**
 * Show air quality notification
 */
function showAirQualityNotification(data, category, value) {
    const unit = data.parameter === 'PM2.5' ? 'μg/m³' : 'ppb';
    const notification = new Notification('⚠️ Air Quality Alert', {
        body: `Air quality is ${category.toLowerCase()} in ${data.city}! ${data.parameter}: ${value.toFixed(1)} ${unit}. Limit outdoor activity.`,
        icon: '/favicon.ico',
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
 */
function getCategoryColor(category) {
    return AIR_QUALITY_CATEGORIES[category]?.color || '#6B7280';
}

/**
 * Get category icon
 */
function getCategoryIcon(category) {
    return AIR_QUALITY_CATEGORIES[category]?.icon || '❓';
}

// Export functions for testing (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getAirQualityPrediction,
        getMockAirQualityData,
        AIR_QUALITY_CATEGORIES,
        getAirQualityCategory
    };
}