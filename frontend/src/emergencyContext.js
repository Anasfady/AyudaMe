import { map } from "./map.js";

const EMERGENCY_CONTEXT_URL = "/data/emergency-context.json";

const AFFECTED_ZONE_STYLE = {
  color: "#b91c1c",
  fillColor: "#dc2626",
  weight: 2,
  fillOpacity: 0.3,
};

async function loadJson(url) {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(
      `No se pudo cargar ${url} (status ${response.status}).`,
    );
  }

  return response.json();
}

function formatDate(date) {
  const [year, month, day] = String(date ?? "").split("-");

  if (!year || !month || !day) {
    return "Fecha no disponible";
  }

  return `${day}/${month}/${year}`;
}

function renderEmergencyContextInfo(context) {
  const sidebar = document.getElementById("sidebar");

  if (!sidebar) {
    return;
  }

  const section = document.createElement("section");
  section.id = "emergency-context-info";

  const title = document.createElement("h3");
  title.textContent = "Contexto de emergencia";

  const name = document.createElement("strong");
  name.textContent = context.name ?? "Escenario de emergencia";

  const status = document.createElement("p");
  status.textContent =
    `Escenario histórico · ${formatDate(context.date)}`;

  const source = document.createElement("p");
  source.textContent =
    `Fuente: ${context.source?.provider ?? "No disponible"} ` +
    `${context.source?.activation ?? ""}`.trim();

  const area = document.createElement("p");
  area.textContent =
    `Zona cartografiada: ${context.source?.area_name ?? "No disponible"}`;

  section.append(title, name, status, source, area);
  sidebar.appendChild(section);

  const headerStatus = document.querySelector("header span");

  if (headerStatus) {
    headerStatus.textContent = "Escenario histórico";
  }
}

async function initEmergencyContext() {
  const leaflet = globalThis.L;

  if (!leaflet) {
    throw new Error("Leaflet no está disponible.");
  }

  try {
    const context = await loadJson(
      EMERGENCY_CONTEXT_URL,
    );

    if (!context?.geometry_file) {
      throw new Error(
        "El contexto de emergencia no define geometry_file.",
      );
    }

    const geojson = await loadJson(
      `/data/${context.geometry_file}`,
    );

    if (geojson?.type !== "FeatureCollection") {
      throw new Error(
        "La geometría de la zona afectada no es una FeatureCollection válida.",
      );
    }

    const affectedZoneLayer = leaflet.geoJSON(
      geojson,
      {
        style: AFFECTED_ZONE_STYLE,
      },
    );

    affectedZoneLayer.addTo(map);

    const bounds = affectedZoneLayer.getBounds();

    if (bounds.isValid()) {
      map.fitBounds(bounds, {
        padding: [20, 20],
      });
    }

    renderEmergencyContextInfo(context);

    window.__AyudaMeEmergencyLayer =
      affectedZoneLayer;
  } catch (error) {
    console.error(
      "No se pudo cargar el contexto de emergencia:",
      error,
    );
  }
}

initEmergencyContext();
