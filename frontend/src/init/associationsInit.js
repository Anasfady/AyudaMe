import { map } from "../map.js";
import { loadAssociations } from "../services/associationsDataService.js";
import {
  createAidManager,
  AID_CATEGORIES,
} from "../layers/aid.js";
import {
  renderAssociationCards,
} from "../components/associationCard.js";

function getFilterState() {
  const showAll =
    document.getElementById("aid-filter-all")?.checked ?? true;

  const categories = AID_CATEGORIES.filter(
    (category) =>
      document.getElementById(`aid-filter-${category}`)?.checked,
  );

  return { showAll, categories };
}

function wireFilterControls(manager) {
  const checkboxIds = [
    "aid-filter-all",
    ...AID_CATEGORIES.map((category) => `aid-filter-${category}`),
  ];

  for (const id of checkboxIds) {
    const checkbox = document.getElementById(id);

    if (!checkbox) {
      continue;
    }

    checkbox.addEventListener("change", () => {
      manager.updateVisibility(map, getFilterState());
    });
  }
}

async function initAssociations() {
  const container = document.getElementById(
    "associations-list",
  );

  if (!container) {
    return;
  }

  try {
    const associations =
      await loadAssociations(
        "/data/associations.mock.json",
      );

    const manager = createAidManager(associations);
    window.__AyudaMeAidManager = manager;
    window.__AyudaMeRefreshAidVisibility = () =>
      manager.updateVisibility(map, getFilterState());

    manager.updateVisibility(map, getFilterState());

    if (
      window.__AyudaMeActiveScenarioId &&
      window.__AyudaMeActiveScenarioId !==
        "dana-valencia-2024"
    ) {
      manager.updateVisibility(map, {
        showAll: false,
        categories: [],
      });
    }

    wireFilterControls(manager);

    renderAssociationCards(
      associations,
      container,
    );
  } catch (error) {
    console.error(
      "No se pudieron cargar las asociaciones:",
      error,
    );

    container.innerHTML = `
      <div class="nexo-empty-state">
        <p>
          No se pudieron cargar las asociaciones.
        </p>
      </div>
    `;
  }
}

if (document.readyState === "loading") {
  document.addEventListener(
    "DOMContentLoaded",
    initAssociations,
  );
} else {
  initAssociations();
}
