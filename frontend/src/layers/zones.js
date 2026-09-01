/**
 * Capa de zonas afectadas para el mapa de AyudaMe.
 *
 * Este módulo no inicializa el mapa ni carga datos.
 * Recibe alertas con una propiedad `zone` y crea polígonos Leaflet.
 */

function isActiveAlert(alert) {
  const status = String(alert?.status ?? "").toLowerCase();

  if (!status) {
    return true;
  }

  return status === "active" || status === "activa";
}

function getZoneStyle(riskLevel) {
  const level = String(riskLevel ?? "").toLowerCase();

  if (level === "high" || level === "red" || level === "alto") {
    return {
      color: "#b91c1c",
      fillColor: "#dc2626",
      weight: 3,
      fillOpacity: 0.35,
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

function isCoordinatePair(value) {
  return (
    Array.isArray(value) &&
    value.length >= 2 &&
    Number.isFinite(Number(value[0])) &&
    Number.isFinite(Number(value[1]))
  );
}

function convertGeoJsonCoordinates(value) {
  if (isCoordinatePair(value)) {
    /*
     * GeoJSON: [longitude, latitude]
     * Leaflet: [latitude, longitude]
     */
    return [Number(value[1]), Number(value[0])];
  }

  if (!Array.isArray(value)) {
    return null;
  }

  const converted = value
    .map(convertGeoJsonCoordinates)
    .filter((item) => item !== null);

  return converted.length > 0 ? converted : null;
}

function getLeafletCoordinates(zone) {
  if (!zone) {
    return null;
  }

  /*
   * Permite utilizar directamente arrays Leaflet:
   * [[lat, lng], [lat, lng], ...]
   */
  if (Array.isArray(zone)) {
    return zone;
  }

  if (zone.type === "Feature") {
    return getLeafletCoordinates(zone.geometry);
  }

  if (zone.type === "Polygon" || zone.type === "MultiPolygon") {
    return convertGeoJsonCoordinates(zone.coordinates);
  }

  if (zone.geometry) {
    return getLeafletCoordinates(zone.geometry);
  }

  return null;
}

/**
 * Crea una capa con las zonas de las alertas activas.
 *
 * Cada polígono conserva la referencia a su alerta para facilitar
 * popups, interacción e integración con otros módulos.
 */
export function createZonesLayer(alerts = [], options = {}) {
  const leaflet = options.leaflet ?? globalThis.L;

  if (!leaflet) {
    throw new Error("Leaflet no está disponible.");
  }

  const layer = leaflet.layerGroup();

  for (const alert of alerts) {
    if (!isActiveAlert(alert)) {
      continue;
    }

    const coordinates = getLeafletCoordinates(
      alert?.zone ?? alert?.geometry,
    );

    if (!coordinates) {
      continue;
    }

    try {
      const zoneLayer = leaflet.polygon(
        coordinates,
        getZoneStyle(alert.risk_level),
      );

      zoneLayer.alertId = alert.id ?? null;
      zoneLayer.alertData = alert;
      zoneLayer.zoneData = alert.zone ?? alert.geometry ?? null;
      zoneLayer.riskLevel = alert.risk_level ?? null;

      zoneLayer.addTo(layer);
    } catch {
      /*
       * Una zona inválida no debe impedir que se representen
       * correctamente las demás alertas.
       */
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
