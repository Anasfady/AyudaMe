/**
 * Capa de alertas para el mapa de AyudaMe.
 *
 * Este módulo no inicializa el mapa ni carga datos.
 * Recibe alertas ya disponibles y devuelve una capa Leaflet
 * que puede añadirse o quitarse del mapa.
 */

function isActiveAlert(alert) {
  const status = String(alert?.status ?? "").toLowerCase();

  if (!status) {
    return true;
  }

  return status === "active" || status === "activa";
}

function getZoneCoordinates(zone) {
  if (!zone) {
    return null;
  }

  if (Array.isArray(zone)) {
    return zone;
  }

  if (zone.type === "Feature") {
    return zone.geometry?.coordinates ?? null;
  }

  if (zone.type === "Polygon" || zone.type === "MultiPolygon") {
    return zone.coordinates ?? null;
  }

  return null;
}

function getFirstCoordinate(value) {
  if (!Array.isArray(value) || value.length === 0) {
    return null;
  }

  if (
    value.length >= 2 &&
    Number.isFinite(Number(value[0])) &&
    Number.isFinite(Number(value[1]))
  ) {
    return value;
  }

  for (const item of value) {
    const coordinate = getFirstCoordinate(item);

    if (coordinate) {
      return coordinate;
    }
  }

  return null;
}

function getCoordinates(alert) {
  const latitude =
    alert?.latitude ??
    alert?.lat ??
    alert?.location?.latitude ??
    alert?.location?.lat;

  const longitude =
    alert?.longitude ??
    alert?.lng ??
    alert?.location?.longitude ??
    alert?.location?.lng;

  const lat = Number(latitude);
  const lng = Number(longitude);

  if (Number.isFinite(lat) && Number.isFinite(lng)) {
    return [lat, lng];
  }

  const zoneCoordinates = getZoneCoordinates(alert?.zone);
  const firstCoordinate = getFirstCoordinate(zoneCoordinates);

  if (!firstCoordinate) {
    return null;
  }

  /*
   * GeoJSON utiliza [longitude, latitude].
   * Leaflet utiliza [latitude, longitude].
   */
  return [
    Number(firstCoordinate[1]),
    Number(firstCoordinate[0]),
  ];
}

function getAlertStyle(riskLevel) {
  const level = String(riskLevel ?? "").toLowerCase();

  if (level === "high" || level === "red" || level === "alto") {
    return {
      radius: 9,
      color: "#b91c1c",
      fillColor: "#dc2626",
      weight: 2,
      fillOpacity: 0.8,
    };
  }

  if (level === "medium" || level === "orange" || level === "medio") {
    return {
      radius: 7,
      color: "#c2410c",
      fillColor: "#f97316",
      weight: 2,
      fillOpacity: 0.7,
    };
  }

  return {
    radius: 6,
    color: "#15803d",
    fillColor: "#22c55e",
    weight: 2,
    fillOpacity: 0.6,
  };
}

export function createAlertsLayer(alerts = [], options = {}) {
  const leaflet = options.leaflet ?? globalThis.L;

  if (!leaflet) {
    throw new Error("Leaflet no está disponible.");
  }

  const layer = leaflet.layerGroup();

  for (const alert of alerts) {
    if (!isActiveAlert(alert)) {
      continue;
    }

    const coordinates = getCoordinates(alert);

    if (!coordinates) {
      continue;
    }

    const marker = leaflet.circleMarker(
      coordinates,
      getAlertStyle(alert.risk_level),
    );

    /*
     * Se conserva la referencia a la alerta para que otros módulos
     * (por ejemplo popups) puedan utilizarla sin duplicar lógica.
     */
    marker.alertData = alert;
    marker.alertId = alert.id ?? null;
    marker.zoneData = alert.zone ?? null;

    marker.addTo(layer);
  }

  return layer;
}

export function setAlertsLayerVisible(map, layer, visible) {
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
