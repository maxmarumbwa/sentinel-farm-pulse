/**
 * Simple Farm Digitizer
 * Handles map drawing and form submission
 */

let map, drawnItems, currentPolygon;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    setupForm();
    
    // If editing existing farm, load it
    if (window.existingFarm && window.existingFarm.geometry) {
        loadExistingFarm();
    }
});

function initMap() {
    // Create map
    map = L.map('map').setView([-15.0, 28.0], 6);
    
    // Add OpenStreetMap basemap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap'
    }).addTo(map);
    
    // Add satellite layer
    const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: '© Esri'
    });
    
    // Add layer control
    const baseLayers = {
        'Street Map': L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19
        }),
        'Satellite': satellite
    };
    L.control.layers(baseLayers).addTo(map);
    
    // Create a group for drawn items
    drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);
    
    // Add draw controls
    const drawControl = new L.Control.Draw({
        draw: {
            polygon: {
                allowIntersection: false,
                showArea: true,
                shapeOptions: {
                    color: '#28a745',
                    weight: 3
                }
            },
            rectangle: false,
            circle: false,
            marker: false,
            polyline: false
        },
        edit: {
            featureGroup: drawnItems,
            remove: true
        }
    });
    map.addControl(drawControl);
    
    // Handle draw events
    map.on('draw:created', function(e) {
        handleDrawCreated(e);
    });
    
    map.on('draw:edited', function(e) {
        handleDrawEdited(e);
    });
    
    map.on('draw:deleted', function(e) {
        handleDrawDeleted(e);
    });
}

function handleDrawCreated(e) {
    const layer = e.layer;
    drawnItems.clearLayers();
    drawnItems.addLayer(layer);
    currentPolygon = layer;
    updateArea(layer);
    updateGeometry(layer);
}

function handleDrawEdited(e) {
    const layers = e.layers;
    layers.eachLayer(function(layer) {
        currentPolygon = layer;
        updateArea(layer);
        updateGeometry(layer);
    });
}

function handleDrawDeleted(e) {
    currentPolygon = null;
    document.getElementById('areaDisplay').value = '0.00';
    document.getElementById('geometryData').value = '';
}

function updateArea(layer) {
    if (!layer) return;
    // Calculate area in hectares
    const area = L.GeometryUtil.geodesicArea(layer.getLatLngs()[0]);
    const hectares = area / 10000;
    document.getElementById('areaDisplay').value = hectares.toFixed(2);
}

function updateGeometry(layer) {
    if (!layer) return;
    const geojson = layer.toGeoJSON();
    document.getElementById('geometryData').value = JSON.stringify(geojson.geometry);
}

function loadExistingFarm() {
    const farm = window.existingFarm;
    if (!farm.geometry) return;
    
    // Load geometry
    const geojson = farm.geometry;
    const layer = L.geoJSON(geojson, {
        style: {
            color: '#28a745',
            weight: 3,
            fillOpacity: 0.2
        }
    });
    
    drawnItems.addLayer(layer);
    currentPolygon = layer;
    
    // Fit map to polygon
    map.fitBounds(layer.getBounds());
    
    // Update area
    updateArea(layer);
    updateGeometry(layer);
}

function setupForm() {
    document.getElementById('farmForm').addEventListener('submit', function(e) {
        const geometry = document.getElementById('geometryData').value;
        if (!geometry) {
            e.preventDefault();
            alert('Please draw a polygon on the map first!');
            return;
        }
        // Form will submit normally
    });
}