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
