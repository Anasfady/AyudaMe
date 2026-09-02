import { map } from "../map.js";
import { loadAssociations } from "../services/associationsDataService.js";
import { createAssociationsLayer } from "../components/markers.js";
import { createAssociationPopup } from "../components/popups.js";
import { renderAssociationCards } from "../components/associationCard.js";

async function initAssociations() {
  const container = document.getElementById("associations-list");

  if (!container) {
    return;
  }

  try {
    const associations = await loadAssociations("/data/associations.mock.json");

    const layer = createAssociationsLayer(associations, createAssociationPopup);

    layer.addTo(map);

    renderAssociationCards(associations, container);
  } catch (error) {
    console.error("No se pudieron cargar las asociaciones:", error);

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
  document.addEventListener("DOMContentLoaded", initAssociations);
} else {
  initAssociations();
}
