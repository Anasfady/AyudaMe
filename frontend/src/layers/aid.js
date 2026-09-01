/**
 * Capa de asociaciones/recursos (aid.js)
 *
 * Exporta:
 * - createAidLayers(associations, options) -> devuelve un objeto con capas:
 *     { all, water, non_perishable_food, baby_products }
 * - setAidLayerVisible(map, layer, visible) -> añade/quita una capa del mapa
 *
 * Usa marcadores SVG mediante L.divIcon para un aspecto consistente.
 * Expectativa de los datos: asociaciones normalizadas según associationsDataService:
 * { id, name, lat, lng, status, needs:[], availableResources:[] }
 */

const CATEGORY_STYLES = {
  water: {
    color: "#0b5cff",
    fillColor: "#60a5fa",
  },
  non_perishable_food: {
    color: "#92400e",
    fillColor: "#f59e0b",
  },
  baby_products: {
    color: "#be185d",
    fillColor: "#fb7185",
  },
  all: {
    color: "#0f766e",
    fillColor: "#34d399",
  },
};

function isActiveAssociation(assoc) {
  const status = String(assoc?.status ?? "").toLowerCase();
  if (!status) return true;
  return status === "active" || status === "activo";
}

function safeJoin(arr) {
  if (!Array.isArray(arr) || arr.length === 0) return "—";
  return arr.join(", ");
}

function createSvgDivIcon(leaflet, color, size = 28) {
  const svg = encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24">
      <g transform="translate(0,0)">
        <circle cx="12" cy="10" r="6" fill="${color}" stroke="#ffffff" stroke-width="1.5"/>
        <path d="M12 22s6-6.5 6-11a6 6 0 1 0-12 0c0 4.5 6 11 6 11z" fill="${color}" opacity="0.95"/>
      </g>
    </svg>
  `);

  const html = `<div style="display:inline-block;line-height:0"><img src="data:image/svg+xml;utf8,${svg}" style="display:block; width:${size}px; height:${size}px" /></div>`;

  return leaflet.divIcon({
    className: "aid-marker-icon",
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  });
}

function createMarker(leaflet, assoc, icon, popupOptions = {}) {
  const marker = leaflet.marker([assoc.lat, assoc.lng], { icon });

  marker.associationData = assoc;
  marker.associationId = assoc.id ?? null;
  marker.availableResources = Array.isArray(assoc.availableResources)
    ? assoc.availableResources
    : [];
  marker.needs = Array.isArray(assoc.needs) ? assoc.needs : [];

  const popupHtml = `
    <div style="min-width:180px">
      <strong>${assoc.name}</strong>
      <div style="margin-top:4px"><small>ID: ${assoc.id}</small></div>
      <hr style="margin:6px 0" />
      <div><strong>Recursos disponibles:</strong><div>${safeJoin(marker.availableResources)}</div></div>
      <div><strong>Necesita:</strong><div>${safeJoin(marker.needs)}</div></div>
      <div style="margin-top:6px"><small>Estado: ${assoc.status ?? "unknown"}</small></div>
    </div>
  `.trim();

  marker.bindPopup(popupHtml, popupOptions);
  return marker;
}

/**
 * associations: lista normalizada (output de associationsDataService)
 * options:
 *  - leaflet: instancia L (por defecto globalThis.L)
 *  - popupOptions: opciones para bindPopup
 *
 * Devuelve { all, water, non_perishable_food, baby_products } (LayerGroup).
 */
export function createAidLayers(associations = [], options = {}) {
  const leaflet = options.leaflet ?? globalThis.L;
  if (!leaflet) throw new Error("Leaflet no está disponible.");

  const layers = {
    all: leaflet.layerGroup(),
    water: leaflet.layerGroup(),
    non_perishable_food: leaflet.layerGroup(),
    baby_products: leaflet.layerGroup(),
  };

  const icons = {
    all: createSvgDivIcon(leaflet, CATEGORY_STYLES.all.fillColor),
    water: createSvgDivIcon(leaflet, CATEGORY_STYLES.water.fillColor),
    non_perishable_food: createSvgDivIcon(leaflet, CATEGORY_STYLES.non_perishable_food.fillColor),
    baby_products: createSvgDivIcon(leaflet, CATEGORY_STYLES.baby_products.fillColor),
  };

  for (const assoc of associations) {
    if (!assoc || typeof assoc !== "object") continue;
    if (!isActiveAssociation(assoc)) continue;
    if (!Number.isFinite(Number(assoc.lat)) || !Number.isFinite(Number(assoc.lng))) continue;

    try {
      const mAll = createMarker(leaflet, assoc, icons.all, options.popupOptions);
      mAll.addTo(layers.all);
    } catch {
      // ignore
    }

    const resources = Array.isArray(assoc.availableResources) ? assoc.availableResources : [];

    for (const res of resources) {
      if (!res || typeof res !== "string") continue;
      const normalized = String(res).trim();
      if (Object.prototype.hasOwnProperty.call(layers, normalized)) {
        try {
          const icon = icons[normalized] ?? icons.all;
          const m = createMarker(leaflet, assoc, icon, options.popupOptions);
          m.addTo(layers[normalized]);
        } catch {
          continue;
        }
      }
    }
  }

  return layers;
}

export function setAidLayerVisible(map, layer, visible) {
  if (!map || !layer) return;
  if (visible && !map.hasLayer(layer)) map.addLayer(layer);
  if (!visible && map.hasLayer(layer)) map.removeLayer(layer);
}
