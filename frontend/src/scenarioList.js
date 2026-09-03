import { map } from "./map.js";
import {
  clearEmergencyContext,
  initEmergencyContext,
} from "./emergencyContext.js";

const SCENARIOS_URL = "/data/scenarios.json";
const DANA_SCENARIO_ID = "dana-valencia-2024";

async function loadScenarios() {
  const response = await fetch(SCENARIOS_URL);

  if (!response.ok) {
    throw new Error(
      `No se pudieron cargar los escenarios (status ${response.status}).`,
    );
  }

  return response.json();
}

function getStatusLabel(scenario) {
  if (scenario.status === "historical") {
    return "Histórico";
  }

  if (scenario.status === "demo") {
    return "Demostración";
  }

  return "Escenario";
}

function setHeaderStatus(text) {
  const headerStatus = document.querySelector("header span");

  if (headerStatus) {
    headerStatus.textContent = text;
  }
}

function setOperationalContentVisible(visible) {
  const sidebar = document.getElementById("sidebar");
  const filters = document.getElementById("aid-filters");
  const associationsList =
    document.getElementById("associations-list");

  const associationsTitle =
    sidebar?.querySelector(":scope > h2");

  for (const element of [
    associationsTitle,
    filters,
    associationsList,
  ]) {
    if (element) {
      element.style.display = visible ? "" : "none";
    }
  }
}

function hideAssociationMarkers() {
  const manager = window.__AyudaMeAidManager;

  manager?.updateVisibility(map, {
    showAll: false,
    categories: [],
  });
}

function restoreAssociationMarkers() {
  window.__AyudaMeRefreshAidVisibility?.();
}

function setScenarioNoticeVisible(visible) {
  const notice = document.getElementById(
    "scenario-data-notice",
  );

  if (notice) {
    notice.style.display = visible ? "" : "none";
  }
}

function removeDemoInfo() {
  document.getElementById("scenario-demo-info")?.remove();
}

function renderDemoInfo(scenario) {
  removeDemoInfo();

  const sidebar = document.getElementById("sidebar");

  if (!sidebar) {
    return;
  }

  const section = document.createElement("section");
  section.id = "scenario-demo-info";

  const eyebrow = document.createElement("p");
  eyebrow.className = "scenario-demo-info__eyebrow";
  eyebrow.textContent = "Escenario de demostración";

  const title = document.createElement("h2");
  title.textContent = scenario.name;

  const location = document.createElement("p");
  location.className = "scenario-demo-info__location";
  location.textContent = scenario.location;

  const description = document.createElement("p");
  description.textContent = scenario.description;

  const notice = document.createElement("p");
  notice.className = "scenario-demo-info__notice";
  notice.textContent =
    "Simulación ficticia: no hay una zona afectada real ni datos operativos de asociaciones cargados para este escenario.";

  section.append(
    eyebrow,
    title,
    location,
    description,
    notice,
  );

  const associationsTitle =
    sidebar.querySelector(":scope > h2");

  if (associationsTitle) {
    sidebar.insertBefore(section, associationsTitle);
  } else {
    sidebar.prepend(section);
  }
}

function setActiveScenarioCard(scenarioId) {
  const cards = document.querySelectorAll(
    ".scenario-card",
  );

  for (const card of cards) {
    const isActive =
      card.dataset.scenarioId === scenarioId;

    card.classList.toggle(
      "scenario-card--active",
      isActive,
    );

    if (isActive) {
      card.setAttribute("aria-current", "true");
    } else {
      card.removeAttribute("aria-current");
    }

    const state = card.querySelector(
      ".scenario-card__state",
    );

    if (state) {
      state.textContent = isActive
        ? "Escenario activo"
        : "Ver escenario";
    }
  }
}

async function activateDanaScenario() {
  removeDemoInfo();
  setScenarioNoticeVisible(true);
  setOperationalContentVisible(true);
  setHeaderStatus("Escenario histórico");

  await initEmergencyContext();

  restoreAssociationMarkers();
}

function activateDemoScenario(scenario) {
  clearEmergencyContext();
  hideAssociationMarkers();
  setOperationalContentVisible(false);
  setScenarioNoticeVisible(false);

  setHeaderStatus("Escenario de demostración");
  renderDemoInfo(scenario);

  const latitude = scenario.map_view?.latitude;
  const longitude = scenario.map_view?.longitude;
  const zoom = scenario.map_view?.zoom;

  if (
    Number.isFinite(latitude) &&
    Number.isFinite(longitude) &&
    Number.isFinite(zoom)
  ) {
    map.setView([latitude, longitude], zoom);
  }
}

async function activateScenario(scenario) {
  window.__AyudaMeActiveScenarioId = scenario.id;
  setActiveScenarioCard(scenario.id);

  if (scenario.id === DANA_SCENARIO_ID) {
    await activateDanaScenario();
    return;
  }

  activateDemoScenario(scenario);
}

function createScenarioCard(scenario, isActive) {
  const card = document.createElement("button");
  card.type = "button";
  card.className = "scenario-card";
  card.dataset.scenarioId = scenario.id;

  if (isActive) {
    card.classList.add("scenario-card--active");
    card.setAttribute("aria-current", "true");
  }

  const name = document.createElement("strong");
  name.textContent = scenario.name;

  const metadata = document.createElement("span");
  metadata.className = "scenario-card__metadata";
  metadata.textContent =
    `${scenario.location} · ${getStatusLabel(scenario)}`;

  const state = document.createElement("span");
  state.className = "scenario-card__state";
  state.textContent = isActive
    ? "Escenario activo"
    : "Ver escenario";

  card.append(name, metadata, state);

  card.addEventListener("click", () => {
    activateScenario(scenario);
  });

  return card;
}

function renderScenarios(scenarios) {
  const navigation = document.getElementById(
    "scenario-navigation",
  );
  const sidebar = document.getElementById("sidebar");

  if (!navigation || !sidebar) {
    return;
  }

  const section = document.createElement("section");
  section.id = "scenario-list";

  const title = document.createElement("h2");
  title.textContent = "Escenarios";

  const cards = document.createElement("div");
  cards.className = "scenario-list__cards";

  for (const scenario of scenarios) {
    const isActive =
      scenario.id === DANA_SCENARIO_ID;

    cards.appendChild(
      createScenarioCard(scenario, isActive),
    );
  }

  section.append(title, cards);
  navigation.replaceChildren(section);

  document.getElementById(
    "scenario-data-notice",
  )?.remove();

  const notice = document.createElement("p");
  notice.id = "scenario-data-notice";
  notice.className = "scenario-list__notice";
  notice.textContent =
    "Contexto y geometría DANA: reales · Datos operativos: demostración.";

  const associationsTitle =
    sidebar.querySelector(":scope > h2");

  if (associationsTitle) {
    sidebar.insertBefore(notice, associationsTitle);
  } else {
    sidebar.prepend(notice);
  }
}

async function initScenarioList() {
  try {
    const scenarios = await loadScenarios();

    if (!Array.isArray(scenarios)) {
      throw new Error(
        "El catálogo de escenarios no tiene un formato válido.",
      );
    }

    window.__AyudaMeActiveScenarioId =
      DANA_SCENARIO_ID;

    renderScenarios(scenarios);
  } catch (error) {
    console.error(
      "No se pudo cargar el listado de escenarios:",
      error,
    );
  }
}

if (document.readyState === "loading") {
  document.addEventListener(
    "DOMContentLoaded",
    initScenarioList,
  );
} else {
  initScenarioList();
}
