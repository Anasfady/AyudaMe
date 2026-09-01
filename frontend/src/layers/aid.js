/**
 * Manager de asociaciones/recursos (aid.js)
 *
 * Esta versión intenta reutilizar las implementaciones de marcadores y popups
 * si están disponibles (por ejemplo la implementación propuesta en el PR #7
 * de @Isabela-Tellez). Si no están presentes, usa un fallback interno.
 *
 * Se ha mejorado la detección de módulos externos y la adaptación de nombres
 * de funciones para ser compatible con los exports de PR #7 (createAssociationMarker,
 * createAssociationPopup).
 *
 * API principal:
 *   - createAidManager(associations, options) -> Promise<manager>
 *     manager:
 *       - markers: Array<Marker>
 *       - markersLayer: LayerGroup (no agregado por defecto al mapa)
 *       - updateVisibility(map, { showAll, categories }) -> void
 *
 * Expectativa de los datos: asociaciones normalizadas según
 * associationsDataService: { id, name, lat, lng, status, needs:[], availableResources:[], municipality }
 */

const DEFAULT_CATEGORIES = ["water", "non_perishable_food", "baby_products"];

function safeJoin(arr) {
  if (!Array.isArray(arr) || arr.length === 0) return "—";
  return arr.map(String).join(", ");
}

function createSvgDivIcon(leaflet, color, size = 28) {
  const svg = encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24">
      <g transform="translate(0,0)">
        <circle cx="12" cy="10" r="6" fill="${color}" stroke="#ffffff" stroke-width="1.5"/>
        <path d="M12 22s6-6.5 6-11a6 6 0 1 0-12 0c0 4.5 6 11 6 11z" fill="${color}" opacity="0.95"/>
      </g>
    </svg>
  `);

  const html = `<div style="display:inline-block;line-height:0"><img src="data:image/svg+xml;utf8,${svg}" style="display:block; width:${size}px; height:${size}px" /></div>`;

  return leaflet.divIcon({
    className: "aid-marker-icon",
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  });
}

/**
 * Intentamos importar implementaciones externas desde posibles ubicaciones
 * y adaptamos las firmas para proporcionar una API uniforme:
 *  - createMarker(leaflet, assoc, options) -> marker
 *  - createPopup(assoc) -> html
 */
async function tryLoadExternal(leaflet) {
  const candidates = [
    "../components/markers.js",
    "../components/popups.js",
    // en caso de cargas desde otra ruta (según bundling) probar variantes relativas
    "./../components/markers.js",
    "./../components/popups.js",
  ];

  let markersMod = null;
  let popupsMod = null;

  // Intentar cargar módulos de marcadores y popups por separado
  for (const path of ["../components/markers.js", "./../components/markers.js"]) {
    try {
      markersMod = await import(path);
      if (markersMod) break;
    } catch (err) {
      // continuar a siguiente candidato
    }
  }

  for (const path of ["../components/popups.js", "./../components/popups.js"]) {
    try {
      popupsMod = await import(path);
      if (popupsMod) break;
    } catch (err) {
      // continuar
    }
  }

  if (!markersMod && !popupsMod) {
    return null;
  }

  // Adaptadores: crear funciones createMarker/createPopup compatibles
  const adapted = {};

  // Popup adapter: soporta createAssociationPopup(export) o default
  if (popupsMod) {
    const popupFactory = popupsMod.createAssociationPopup || popupsMod.createPopup || popupsMod.default || null;

    if (typeof popupFactory === "function") {
      adapted.createPopup = (assoc) => {
        try {
          return popupFactory(assoc);
        } catch (err) {
          return null;
        }
      };
    }
  }

  // Marker adapter: soporta createAssociationMarker(association, popupHtml)
  if (markersMod) {
    const markerFactory = markersMod.createAssociationMarker || markersMod.createMarker || markersMod.default || null;

    if (typeof markerFactory === "function") {
      adapted.createMarker = (leafletInst, assoc, opts = {}) => {
        try {
          // algunos factories esperan popup HTML como segundo argumento
          const popupHtml = adapted.createPopup ? adapted.createPopup(assoc) : "";

          // createAssociationMarker en PR #7 acepta (association, popupContent)
          const marker = markerFactory(assoc, popupHtml);

          // Si la implementación externa no setea associationData, lo hacemos aquí
          if (marker && typeof marker === "object") {
            marker.associationData = assoc;
            marker.categories = Array.isArray(assoc.availableResources) ? assoc.availableResources : [];
          }

          return marker;
        } catch (err) {
          return null;
        }
      };
    }
  }

  return adapted;
}

function buildPopupHtml(assoc) {
  return `
    <div style="min-width:180px">
      <strong>${assoc.name}</strong>
      <div style="margin-top:4px"><small>ID: ${assoc.id}</small></div>
      <hr style="margin:6px 0" />
      <div><strong>Recursos disponibles:</strong><div>${safeJoin(assoc.availableResources)}</div></div>
      <div><strong>Necesita:</strong><div>${safeJoin(assoc.needs)}</div></div>
      <div style="margin-top:6px"><small>Estado: ${assoc.status ?? "unknown"}</small></div>
    </div>
  `.trim();
}

export async function createAidManager(associations = [], options = {}) {
  const leaflet = options.leaflet ?? globalThis.L;
  if (!leaflet) throw new Error("Leaflet no está disponible.");

  const external = await tryLoadExternal(leaflet);

  // Precrear iconos por categoría (fallback visual)
  const icons = {
    all: createSvgDivIcon(leaflet, "#34d399"),
    water: createSvgDivIcon(leaflet, "#60a5fa"),
    non_perishable_food: createSvgDivIcon(leaflet, "#f59e0b"),
    baby_products: createSvgDivIcon(leaflet, "#fb7185"),
  };

  const markers = [];
  const markersLayer = leaflet.layerGroup(); // útil si se quiere agrupar todos

  for (const assoc of associations) {
    if (!assoc || typeof assoc !== "object") continue;
    if (!Number.isFinite(Number(assoc.lat)) || !Number.isFinite(Number(assoc.lng))) continue;

    let marker = null;

    // Si hay adaptadores externos, intentar usarlos
    if (external && typeof external.createMarker === "function") {
      try {
        marker = external.createMarker(leaflet, assoc, { icons });
      } catch (err) {
        marker = null;
      }
    }

    if (!marker) {
      // fallback simple marker con svg icon y popup
      const categoryIcon = icons.all;
      marker = leaflet.marker([assoc.lat, assoc.lng], { icon: categoryIcon });

      const popupHtml = buildPopupHtml(assoc);
      marker.bindPopup(popupHtml, options.popupOptions ?? {});

      marker.associationData = assoc;
      marker.categories = Array.isArray(assoc.availableResources) ? assoc.availableResources : [];
    }

    // No añadimos el marker al mapa aquí — la visibilidad la gestionará updateVisibility
    markers.push(marker);
    markersLayer.addLayer(marker);
  }

  function updateVisibility(map, { showAll = true, categories = [] } = {}) {
    if (!map) return;

    for (const marker of markers) {
      const hasCategory = marker.categories && marker.categories.some((c) => categories.includes(c));
      const shouldShow = Boolean(showAll || hasCategory);

      if (shouldShow && !map.hasLayer(marker)) {
        marker.addTo(map);
      }

      if (!shouldShow && map.hasLayer(marker)) {
        try {
          map.removeLayer(marker);
        } catch (e) {
          // ignore
        }
      }
    }
  }

  return {
    markers,
    markersLayer,
    updateVisibility,
  };
}
