/**
 * Capa de zonas afectadas para el mapa de AyudaMe.
 *
 * Este módulo no inicializa el mapa ni carga datos.
 * Recibe geometrías compatibles con GeoJSON y devuelve
 * una capa Leaflet que puede añadirse o quitarse del mapa.
 */

function getZoneStyle(riskLevel) {
  const level = String(riskLevel ?? "").toLowerCase();

  if (level === "high" || level === "red" || level === "alto") {
    return {
      color: "#b91c1c",
      fillColor: "#dc2626",
      weight: 2,
      fillOpacity: 0.25,
    };
  }

  if (level === "medium" || level === "orange" || level === "medio") {
    return {
      color: "#c2410c",
      fillColor: "#f97316",
      weight: 2,
      fillOpacity: 0.2,
    };
  }

  return {
    color: "#15803d",
    fillColor: "#22c55e",
    weight: 2,
    fillOpacity: 0.15,
  };
}

function getGeometry(item) {
  if (!item) {
    return null;
  }

  if (item.type === "Feature" || item.type === "FeatureCollection") {
    return item;
  }

  if (
    item.type === "Polygon" ||
    item.type === "MultiPolygon"
  ) {
    return item;
  }

  if (item.zone) {
    return item.zone;
  }

  if (item.geometry) {
    return item.geometry;
  }

  return null;
}

/**
 * Crea una capa Leaflet con las zonas afectadas válidas.
 *
 * @param {Array<object>} zones
 * @param {object} options
 * @param {object} [options.leaflet] Instancia de Leaflet para facilitar tests.
 * @returns {object} L.LayerGroup
 */
export function createZonesLayer(zones = [], options = {}) {
  const leaflet = options.leaflet ?? globalThis.L;

  if (!leaflet) {
    throw new Error("Leaflet no está disponible.");
  }

  const layer = leaflet.layerGroup();

  for (const item of zones) {
    const geometry = getGeometry(item);

    if (!geometry) {
      continue;
    }

    const riskLevel =
      item?.risk_level ??
      item?.properties?.risk_level ??
      geometry?.properties?.risk_level;

    try {
      const zoneLayer = leaflet.geoJSON(geometry, {
        style: getZoneStyle(riskLevel),
      });

      zoneLayer.zoneData = item;
      zoneLayer.addTo(layer);
    } catch {
      // Una geometría inválida no debe impedir que se rendericen las demás.
      continue;
    }
  }

  return layer;
}

/**
 * Muestra u oculta la capa de zonas sin depender de cómo se creó el mapa.
 */
export function setZonesLayerVisible(map, layer, visible) {
  if (!map || !layer) {
    return;
  }

  if (visible && !map.hasLayer(layer)) {
    map.addLayer(layer);
  }

  if (!visible && map.hasLayer(layer)) {
    map.removeLayer(layer);
  }
}
