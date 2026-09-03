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

function filterAssociations(
  associations,
  { showAll, categories },
) {
  if (showAll) {
    return associations;
  }

  return associations.filter((association) => {
    const resources = Array.isArray(
      association?.availableResources,
    )
      ? association.availableResources
      : [];

    return resources.some((resource) =>
      categories.includes(resource),
    );
  });
}

function wireFilterControls(manager, associations, container) {
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
      const filterState = getFilterState();

      manager.updateVisibility(map, filterState);

      const filteredAssociations = filterAssociations(
        associations,
        filterState,
      );

      renderAssociationCards(
        filteredAssociations,
        container,
      );
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

    const filterState = getFilterState();

    manager.updateVisibility(map, filterState);

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


    renderAssociationCards(
      filterAssociations(
        associations,
        filterState,
      ),
      container,
    );

    wireFilterControls(
      manager,
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
          No se pudieron cargar las asociaciones:
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
