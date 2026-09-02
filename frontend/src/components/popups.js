/**
 * ==========================================
 * AYUDAME - POPUPS DE ASOCIACIONES
 * ==========================================
 *
 * Genera el contenido visual de los popups asociados a los
 * marcadores de asociaciones.
 */

const CATEGORY_LABELS = {
    water: "Agua",
    non_perishable_food:
        "Alimentos no perecederos",
    baby_products: "Productos para bebés",
};

/**
 * Convierte una categoría interna del modelo en un texto 
 * comprensible para el usuario.
 */
export function getCategoryLabel(category) {
    return (
        CATEGORY_LABELS[category] ??
        category
    );
}

/**
 * Escapa contenido procedente de los datos antes de 
 * introducirlo en HTML.
 */
function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

/**
 * Normaliza una lista de categorías.
 *
 * Si el valor no es un array, devuelve una lista vacía 
 * para evitar errores.
 */
function normalizeCategories(
    categories,
) {
    if (!Array.isArray(categories)) {
        return [];
    }

    return categories.filter(
        (category) =>
            typeof category === "string" &&
            category.trim().length > 0,
    );
}

/**
 * Genera los badges HTML de una lista de necesidades o recursos.
 */
function createCategoryBadges(
    categories,
    type,
) {
    const normalized =
        normalizeCategories(categories);

    if (normalized.length === 0) {
        return `
      <span
        class="nexo-badge nexo-badge-empty"
      >
        Ninguno
      </span>
    `;
    }

    return normalized
        .map(
            (category) => `
        <span
          class="nexo-badge nexo-badge-${type}"
        >
          ${escapeHtml(
                getCategoryLabel(category),
            )}
        </span>
      `,
        )
        .join("");
}

/**
 * Genera el popup completo de una asociación.
 *
 * El popup muestra:
 * - Nombre
 * - Municipio
 * - Necesidades
 * - Recursos disponibles
 */
export function createAssociationPopup(
    association,
) {
    if (!association) {
        return `
      <div class="nexo-popup">
        <p>
          Información de asociación
          no disponible.
        </p>
      </div>
    `;
    }

    const needs = normalizeCategories(
        association.needs,
    );

    const resources =
        normalizeCategories(
            association.availableResources,
        );

    const name = escapeHtml(
        association.name ||
        "Asociación",
    );

    const municipality = escapeHtml(
        association.municipality ||
        association.municipio ||
        "Municipio no disponible",
    );

    return `
    <div class="nexo-popup">

      <div class="nexo-popup-header">

        <span
          class="nexo-popup-icon"
          aria-hidden="true"
        >
          🤝
        </span>

        <h3>
          ${name}
        </h3>

      </div>

      <p class="nexo-popup-location">
        📍 ${municipality}
      </p>

      <div class="nexo-popup-section">

        <strong>
          Necesidades
        </strong>

        <div class="nexo-badge-list">
          ${createCategoryBadges(
        needs,
        "need",
    )}
        </div>

      </div>

      <div class="nexo-popup-section">

        <strong>
          Recursos disponibles
        </strong>

        <div class="nexo-badge-list">
          ${createCategoryBadges(
        resources,
        "resource",
    )}
        </div>

      </div>

    </div>
  `;
}