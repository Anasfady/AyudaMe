/**
 * ==========================================
 * AYUDAME - TARJETAS DE ASOCIACIONES
 * ==========================================
 *
 * Genera las tarjetas que aparecen en el panel lateral del mapa.
 *
 * No crea una página de detalle.
 * La tarjeta forma parte del flujo:
 *
 * marcador → popup → tarjeta
 */

import {
    getCategoryLabel,
} from "./popups.js";

const CATEGORY_ICONS = {
    water: "💧",
    non_perishable_food: "🥫",
    baby_products: "👶",
};

/**
 * Escapa valores procedentes de los datos antes de introducirlos en HTML.
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
 * Normaliza listas de necesidades y recursos.
 */
function normalizeList(value) {
    if (!Array.isArray(value)) {
        return [];
    }

    return value.filter(
        (item) =>
            typeof item === "string" &&
            item.trim().length > 0,
    );
}

/**
 * Genera los badges de necesidades o recursos.
 */
function renderBadges(
    categories,
    type,
) {
    const normalized =
        normalizeList(categories);

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
        .map((category) => {
            const icon =
                CATEGORY_ICONS[category] ??
                "📦";

            return `
        <span
          class="nexo-badge nexo-badge-${type}"
        >
          ${icon}
          ${escapeHtml(
                getCategoryLabel(category),
            )}
        </span>
      `;
        })
        .join("");
}

/**
 * Crea una tarjeta completa de asociación.
 */
export function createAssociationCard(
    association,
) {
    if (!association) {
        return `
      <article
        class="nexo-card nexo-card-empty"
      >
        <p>
          Información no disponible.
        </p>
      </article>
    `;
    }

    const needs = normalizeList(
        association.needs,
    );

    const resources =
        normalizeList(
            association.availableResources,
        );

    const name = escapeHtml(
        association.name ||
        "Asociación sin nombre",
    );

    const municipality = escapeHtml(
        association.municipality ||
        association.municipio ||
        "Municipio no disponible",
    );

    const status =
        association.status === "inactive"
            ? "Inactiva"
            : "Activa";

    const statusClass =
        association.status === "inactive"
            ? "nexo-status-inactive"
            : "nexo-status-active";

    const associationId =
        escapeHtml(
            association.id ?? "",
        );

    return `
    <article
      class="nexo-card association-card"
      data-association-id="${associationId}"
    >

      <div class="nexo-card-header">

        <div>

          <h3 class="nexo-card-title">
            ${name}
          </h3>

          <p class="nexo-card-location">
            📍 ${municipality}
          </p>

        </div>

        <span
          class="nexo-status ${statusClass}"
        >
          ${status}
        </span>

      </div>

      <div class="nexo-card-section">

        <h4>
          Necesidades
        </h4>

        <div class="nexo-badge-list">
          ${renderBadges(
        needs,
        "need",
    )}
        </div>

      </div>

      <div class="nexo-card-section">

        <h4>
          Recursos disponibles
        </h4>

        <div class="nexo-badge-list">
          ${renderBadges(
        resources,
        "resource",
    )}
        </div>

      </div>

    </article>
  `;
}

/**
 * Renderiza todas las asociaciones dentro del panel lateral.
 */
export function renderAssociationCards(
    associations = [],
    container,
) {
    if (!container) {
        return;
    }

    if (
        !Array.isArray(associations) ||
        associations.length === 0
    ) {
        container.innerHTML = `
      <div class="nexo-empty-state">
        <p>
          No hay asociaciones disponibles.
        </p>
      </div>
    `;

        return;
    }

    container.innerHTML =
        associations
            .map(createAssociationCard)
            .join("");
}

/**
 * Añade una única asociación al panel.
 */
export function appendAssociationCard(
    association,
    container,
) {
    if (!container || !association) {
        return;
    }

    container.insertAdjacentHTML(
        "beforeend",
        createAssociationCard(association),
    );
}

/**
 * Busca una tarjeta concreta utilizando el ID de la asociación.
 */
export function getAssociationCard(
    associationId,
    container,
) {
    if (
        !container ||
        associationId === null ||
        associationId === undefined
    ) {
        return null;
    }

    const cards =
        container.querySelectorAll(
            ".association-card",
        );

    return (
        Array.from(cards).find(
            (card) =>
                card.dataset.associationId ===
                String(associationId),
        ) ?? null
    );
}

/**
 * Selecciona visualmente una asociación dentro del panel lateral.
 */
export function selectAssociationCard(
    associationId,
    container,
) {
    if (!container) {
        return;
    }

    const cards =
        container.querySelectorAll(
            ".association-card",
        );

    cards.forEach((card) => {
        card.classList.remove(
            "nexo-card-selected",
        );
    });

    const selected =
        getAssociationCard(
            associationId,
            container,
        );

    if (!selected) {
        return;
    }

    selected.classList.add(
        "nexo-card-selected",
    );

    selected.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
    });
}