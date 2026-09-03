/**
 * ==========================================
 * AYUDAME - CAPA DE ASOCIACIONES/RECURSOS
 * ==========================================
 *
 * Gestiona la visibilidad filtrable (por categoría) de los marcadores
 * de asociaciones en el mapa.
 *
 * Reutiliza directamente los marcadores y popups de
 * components/markers.js y components/popups.js: no crea una
 * implementación paralela.
 *
 * Cada asociación tiene un único marcador. Si varios filtros
 * coinciden a la vez, el marcador no se duplica.
 */

import { createAssociationMarker } from "../components/markers.js";
import { createAssociationPopup } from "../components/popups.js";

export const AID_CATEGORIES = [
  "water",
  "non_perishable_food",
  "baby_products",
];

function getAssociationCategories(association) {
  return Array.isArray(association?.availableResources)
    ? association.availableResources
    : [];
}

/**
 * Crea un manager de marcadores de asociaciones con soporte de
 * filtrado por categoría.
 *
 * manager:
 *   - markers: Array<Marker>
 *   - updateVisibility(map, { showAll, categories }) -> void
 */
export function createAidManager(associations = [], options = {}) {
  const leaflet = options.leaflet ?? globalThis.L;

  if (!leaflet) {
    throw new Error("Leaflet no está disponible.");
  }

  const entries = [];

  for (const association of associations) {
    if (!association) {
      continue;
    }

    const popupContent = createAssociationPopup(association);
    const marker = createAssociationMarker(association, popupContent);

    if (!marker) {
      continue;
    }

    entries.push({
      marker,
      categories: getAssociationCategories(association),
    });
  }

  /**
   * Muestra u oculta cada marcador según el estado de los filtros.
   *
   * - showAll: si es true, todos los marcadores se muestran.
   * - categories: lista de categorías activas; un marcador se
   *   muestra si tiene al menos una categoría en común.
   */
  function updateVisibility(
    map,
    { showAll = true, categories = [] } = {},
  ) {
    if (!map) {
      return;
    }

    for (const {
      marker,
      categories: markerCategories,
    } of entries) {
      const matchesCategory = markerCategories.some((category) =>
        categories.includes(category),
      );

      const shouldShow = showAll || matchesCategory;

      if (shouldShow && !map.hasLayer(marker)) {
        marker.addTo(map);
      }

      if (!shouldShow && map.hasLayer(marker)) {
        map.removeLayer(marker);
      }
    }
  }

  return {
    markers: entries.map((entry) => entry.marker),
    updateVisibility,
  };
}