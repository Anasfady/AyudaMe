/**
 * ==========================================
 * AYUDAME - MARCADORES DE ASOCIACIONES
 * ==========================================
 *
 * Este módulo se encarga de crear los marcadores visuales de las 
 * asociaciones en el mapa.
 *
 * No carga datos ni inicializa el mapa.
 */

const ASSOCIATION_MARKER_ICONS = {
    water: "💧",
    non_perishable_food: "🥫",
    baby_products: "👶",
};

const ASSOCIATION_MARKER_COLORS = {
    water: "#2563eb",
    non_perishable_food: "#d97706",
    baby_products: "#db2777",
};

/**
 * Obtiene todas las categorías disponibles de una asociación.
 */
function getAssociationCategories(association) {
    const needs = Array.isArray(association?.needs)
        ? association.needs
        : [];

    const resources = Array.isArray(
        association?.availableResources,
    )
        ? association.availableResources
        : [];

    return [...needs, ...resources];
}

/**
 * Obtiene el icono que representará a la asociación.
 *
 * Se utiliza la primera categoría conocida.
 * Si la asociación no tiene necesidades ni recursos,
 * se muestra el icono genérico de asociación.
 */
function getAssociationMarkerIcon(association) {
    const categories =
        getAssociationCategories(association);

    const category = categories.find(
        (item) => ASSOCIATION_MARKER_ICONS[item],
    );

    return (
        ASSOCIATION_MARKER_ICONS[category] ?? "🤝"
    );
}

/**
 * Obtiene el color que representará al marcador.
 *
 * Si no existe ninguna categoría conocida,
 * se utiliza verde como color por defecto.
 */
function getAssociationMarkerColor(association) {
    const categories =
        getAssociationCategories(association);

    const category = categories.find(
        (item) => ASSOCIATION_MARKER_COLORS[item],
    );

    return (
        ASSOCIATION_MARKER_COLORS[category] ??
        "#16a34a"
    );
}

/**
 * Escapa un valor para utilizarlo dentro de atributos HTML.
 */
function escapeHtmlAttribute(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll('"', "&quot;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}

/**
 * Crea el icono Leaflet de una asociación.
 */
export function createAssociationIcon(
    association,
) {
    const leaflet = globalThis.L;

    if (!leaflet) {
        throw new Error(
            "Leaflet no está disponible.",
        );
    }

    const icon =
        getAssociationMarkerIcon(association);

    const color =
        getAssociationMarkerColor(association);

    const name = escapeHtmlAttribute(
        association?.name ?? "Asociación",
    );

    return leaflet.divIcon({
        className: "nexo-marker",

        html: `
      <div
        class="nexo-marker-icon"
        style="background-color: ${color};"
        aria-label="Asociación ${name}"
        title="${name}"
      >
        ${icon}
      </div>
    `,

        iconSize: [42, 42],

        iconAnchor: [21, 21],

        popupAnchor: [0, -21],
    });
}

/**
 * Crea un marcador Leaflet para una asociación.
 *
 * El contenido del popup se recibe desde fuera para mantener
 * separadas las responsabilidades.
 */
export function createAssociationMarker(
    association,
    popupContent = "",
) {
    const leaflet = globalThis.L;

    if (!leaflet) {
        throw new Error(
            "Leaflet no está disponible.",
        );
    }

    if (!association) {
        return null;
    }

    const lat = Number(association.lat);
    const lng = Number(association.lng);

    if (
        !Number.isFinite(lat) ||
        !Number.isFinite(lng)
    ) {
        return null;
    }

    const marker = leaflet.marker(
        [lat, lng],
        {
            icon: createAssociationIcon(
                association,
            ),

            title:
                association.name ??
                "Asociación",
        },
    );

    if (popupContent) {
        marker.bindPopup(popupContent);
    }

    /*
     * Se guardan los datos de la asociación directamente en el
     * marcador para que otros módulos puedan reutilizarlos.
     */
    marker.associationData = association;

    marker.associationId =
        association.id ?? null;

    return marker;
}

/**
 * Crea una capa Leaflet con todas las asociaciones que 
 * tengan coordenadas válidas.
 */
export function createAssociationsLayer(
    associations = [],
    popupBuilder = null,
) {
    const leaflet = globalThis.L;

    if (!leaflet) {
        throw new Error(
            "Leaflet no está disponible.",
        );
    }

    const layer = leaflet.layerGroup();

    if (!Array.isArray(associations)) {
        return layer;
    }

    for (const association of associations) {
        if (!association) {
            continue;
        }

        const lat = Number(association.lat);
        const lng = Number(association.lng);

        if (
            !Number.isFinite(lat) ||
            !Number.isFinite(lng)
        ) {
            continue;
        }

        let popupContent = "";

        if (typeof popupBuilder === "function") {
            popupContent =
                popupBuilder(association);
        }

        const marker =
            createAssociationMarker(
                association,
                popupContent,
            );

        if (marker) {
            marker.addTo(layer);
        }
    }

    return layer;
}