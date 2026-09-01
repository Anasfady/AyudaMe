/**
 * Inicializa las capas de asociaciones y añade toggles en el sidebar.
 *
 * Esta versión usa createAidManager() para crear marcadores únicos por
 * asociación y evita crear duplicados cuando se combinan "Mostrar todas"
 * y filtros de categoría. Además, si existen implementaciones externas
 * (markers.js / popups.js) se reutilizan automáticamente.
 */

import { map } from "../map.js";
import { loadAssociations } from "../services/associationsDataService.js";
import { createAidManager } from "../layers/aid.js";

function createControlsHtml() {
  return `
    <section id="aid-layer-controls" class="nexo-aid-controls">
      <h3>Asociaciones y recursos</h3>
      <div class="nexo-aid-controls__item">
        <label><input type="checkbox" id="aid-toggle-all" checked /> Mostrar todas</label>
      </div>
      <div class="nexo-aid-controls__item">
        <label><input type="checkbox" id="aid-toggle-water" /> Agua</label>
      </div>
      <div class="nexo-aid-controls__item">
        <label><input type="checkbox" id="aid-toggle-food" /> Alimentos no perecederos</label>
      </div>
      <div class="nexo-aid-controls__item">
        <label><input type="checkbox" id="aid-toggle-baby" /> Productos de bebé</label>
      </div>
    </section>
  `;
}

async function initAidLayers() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;

  const wrapper = document.createElement("div");
  wrapper.innerHTML = createControlsHtml();
  sidebar.appendChild(wrapper);

  let associations = [];
  try {
    associations = await loadAssociations("/data/associations.mock.json");
  } catch (err) {
    console.warn("No se pudieron cargar asociaciones:", err);
    return;
  }

  const manager = await createAidManager(associations, { leaflet: globalThis.L });

  // Estado inicial de filtros
  let state = {
    showAll: true,
    categories: [],
  };

  // Aplicar visibilidad inicial
  manager.updateVisibility(map, state);

  const cbAll = document.getElementById("aid-toggle-all");
  const cbWater = document.getElementById("aid-toggle-water");
  const cbFood = document.getElementById("aid-toggle-food");
  const cbBaby = document.getElementById("aid-toggle-baby");

  function applyFiltersFromUI() {
    const showAll = cbAll.checked;
    const categories = [];
    if (cbWater.checked) categories.push("water");
    if (cbFood.checked) categories.push("non_perishable_food");
    if (cbBaby.checked) categories.push("baby_products");

    state = { showAll, categories };
    manager.updateVisibility(map, state);
  }

  cbAll.addEventListener("change", applyFiltersFromUI);
  cbWater.addEventListener("change", applyFiltersFromUI);
  cbFood.addEventListener("change", applyFiltersFromUI);
  cbBaby.addEventListener("change", applyFiltersFromUI);

  // Exponer para depuración
  window.__AyudaMeAidManager = manager;
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAidLayers);
} else {
  initAidLayers();
}
