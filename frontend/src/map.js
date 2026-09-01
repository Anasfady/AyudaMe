/**
 * AyudaMe Emergency Map - Base Map Module (Persona 1: @Anas28)
 * Initializes the single shared Leaflet map instance.
 */

// 1. Define the geographical limits for Spain (including Canary & Balearic Islands)
const spainBounds = L.latLngBounds(
  [27.4, -18.5], // Southwest corner (Canary Islands)
  [44.0, 4.4], // Northeast corner (Catalonia/Menorca)
);

// 2. Initialize Leaflet map with boundaries and zoom limits
const map = L.map("map", {
  center: [40.4168, -3.7038], // Centered on Madrid
  zoom: 6, // Zoomed out slightly to show the country
  minZoom: 5, // Prevent zooming out to the whole world
  maxBounds: spainBounds, // Lock panning to Spain
  maxBoundsViscosity: 1.0, // Make the boundaries solid (no elastic bouncing)
  zoomControl: true,
});

// 3. Configure CartoDB.Voyager tile layer
const CartoDB_Voyager = L.tileLayer(
  "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
  {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 20,
  },
);

// 4. Add tiles to the shared map
CartoDB_Voyager.addTo(map);

// 5. Export single shared instance for downstream layers
export { map };
