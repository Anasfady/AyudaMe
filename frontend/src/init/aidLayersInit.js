/**
 * Inicializa las capas de asociaciones y añade toggles en el sidebar.
 *
 * Importante: se asume que map.js ya ha sido ejecutado y exporta `map`.
 * Se asume que associationsDataService.js existe y expone loadAssociations().
 */

import { map } from "../map.js";
import { loadAssociations } from "../services/associationsDataService.js";
import { createAidLayers, setAidLayerVisible } from "../layers/aid.js";

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

  const aidLayers = createAidLayers(associations, { leaflet: globalThis.L });

  // Añadir la capa "all" por defecto
  aidLayers.all.addTo(map);

  const cbAll = document.getElementById("aid-toggle-all");
  const cbWater = document.getElementById("aid-toggle-water");
  const cbFood = document.getElementById("aid-toggle-food");
  const cbBaby = document.getElementById("aid-toggle-baby");

  cbAll.addEventListener("change", (e) => {
    setAidLayerVisible(map, aidLayers.all, e.target.checked);
  });
  cbWater.addEventListener("change", (e) => {
    setAidLayerVisible(map, aidLayers.water, e.target.checked);
  });
  cbFood.addEventListener("change", (e) => {
    setAidLayerVisible(map, aidLayers.non_perishable_food, e.target.checked);
  });
  cbBaby.addEventListener("change", (e) => {
    setAidLayerVisible(map, aidLayers.baby_products, e.target.checked);
  });

  // Exponer para depuración
  window.__AyudaMeAidLayers = aidLayers;
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAidLayers);
} else {
  initAidLayers();
}
