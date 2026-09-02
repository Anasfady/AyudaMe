/**
 * AyudaMe Emergency Map - Base Map Module (Persona 1)
 */

const spainBounds = L.latLngBounds([27.4, -18.5], [44.0, 4.4]);

const map = L.map("map", {
  center: [40.4168, -3.7038], // Madrid coordinates
  zoom: 6,
  minZoom: 5,
  maxBounds: spainBounds,
  maxBoundsViscosity: 1.0,
  zoomControl: true,
});

// Use standard OpenStreetMap tiles (Free, no API key required)
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);

// Add the Search Bar (Geocoder)
const geocoder = L.Control.geocoder({
  defaultMarkGeocoder: false,
  placeholder: "Buscar calle, municipio, C.P...",
  geocoder: L.Control.Geocoder.nominatim({
    geocodingQueryParams: {
      countrycodes: "es", // Restricts search to Spain
    },
  }),
}).addTo(map);

// A variable to keep track of the current search marker
let currentSearchMarker = null;

// Zoom to location and place a pin when a user searches
geocoder.on("markgeocode", function (e) {
  // 1. SIMPLIFIED BOUNDS: e.geocode.bbox is already a Leaflet bounds object!
  map.fitBounds(e.geocode.bbox);

  // 2. CLEAR PREVIOUS MARKER: Remove the old pin if a new search is made
  if (currentSearchMarker) {
    map.removeLayer(currentSearchMarker);
  }

  // 3. ADD VISUAL PIN: Show the user exactly what they searched for
  currentSearchMarker = L.marker(e.geocode.center)
    .addTo(map)
    .bindPopup(e.geocode.name)
    .openPopup();
});

customControls.addTo(map);

export { map };
