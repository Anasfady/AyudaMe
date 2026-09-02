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

// --- FILTER AND SORT CONTROL PANEL ---

const customControls = L.control({ position: "topright" });

customControls.onAdd = function (map) {
  // Create the main container
  const div = L.DomUtil.create("div", "custom-controls-container");

  // Prevent map zooming/dragging when interacting with the UI
  L.DomEvent.disableClickPropagation(div);
  L.DomEvent.disableScrollPropagation(div);

  // Inject HTML for buttons and hidden dropdown panels
  div.innerHTML = `
    <div class="control-buttons-row">
      <button id="btn-filter" class="map-action-btn">Filtros ▼</button>
      <button id="btn-sort" class="map-action-btn">Ordenar ▼</button>
    </div>
    
    <!-- Filter Dropdown Panel -->
    <div id="filter-dropdown" class="dropdown-panel" style="display: none;">
      <div style="font-weight: bold; margin-bottom: 10px; font-family: sans-serif;">Filtros</div>
      <div id="additional-fields-container">
         <p style="font-size: 12px; color: #666; margin: 0; font-family: sans-serif;">Opciones próximamente...</p>
      </div>
    </div>

    <!-- Sort Dropdown Panel -->
    <div id="sort-dropdown" class="dropdown-panel" style="display: none;">
      <div style="font-weight: bold; margin-bottom: 10px; font-family: sans-serif;">Ordenar por</div>
      <select id="sort-select" style="width: 100%; padding: 6px; border-radius: 4px; border: 1px solid #ccc; font-family: sans-serif;">
        <option value="name_asc">Nombre (A-Z)</option>
        <option value="urgency">Mayor urgencia</option>
      </select>
    </div>
  `;

  // Attach click events to toggle the panels
  const btnFilter = div.querySelector("#btn-filter");
  const btnSort = div.querySelector("#btn-sort");
  const filterDropdown = div.querySelector("#filter-dropdown");
  const sortDropdown = div.querySelector("#sort-dropdown");

  btnFilter.addEventListener("click", () => {
    // Toggle filter panel and ensure sort is closed
    const isClosed = filterDropdown.style.display === "none";
    filterDropdown.style.display = isClosed ? "block" : "none";
    sortDropdown.style.display = "none";
  });

  btnSort.addEventListener("click", () => {
    // Toggle sort panel and ensure filter is closed
    const isClosed = sortDropdown.style.display === "none";
    sortDropdown.style.display = isClosed ? "block" : "none";
    filterDropdown.style.display = "none";
  });

  return div;
};

customControls.addTo(map);

export { map };
