/**
 * Associations data service for AyudaMe (Persona 5).
 *
 * Loads, validates and normalizes association records. It does not
 * initialize Leaflet, create markers, or touch the DOM.
 */

const ALLOWED_CATEGORIES = ["water", "non_perishable_food", "baby_products"];
const ALLOWED_STATUSES = ["active", "inactive"];

// Accepts numbers or numeric strings ("39.42") but rejects anything that
// doesn't resolve to a finite number inside [min, max] — including other
// types Number() would silently coerce, like booleans or arrays.
export function isValidCoordinate(value, min, max) {
  if (typeof value !== "number" && typeof value !== "string") {
    return false;
  }

  if (typeof value === "string" && value.trim() === "") {
    return false;
  }

  const number = Number(value);

  return Number.isFinite(number) && number >= min && number <= max;
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

// Keeps only known categories from a list, dropping anything else
// instead of invalidating the whole association.
export function normalizeCategoryList(categories) {
  if (!Array.isArray(categories)) {
    return null;
  }

  return categories.filter((category) => ALLOWED_CATEGORIES.includes(category));
}

// Validates a raw association and converts it to the normalized shape:
// latitude/longitude -> lat/lng as Number, available_resources -> availableResources.
// Returns null when the record is invalid.
export function normalizeAssociation(raw) {
  if (!raw || typeof raw !== "object") {
    return null;
  }

  if (!isNonEmptyString(raw.id) || !isNonEmptyString(raw.name)) {
    return null;
  }

  if (!isValidCoordinate(raw.latitude, -90, 90)) {
    return null;
  }

  if (!isValidCoordinate(raw.longitude, -180, 180)) {
    return null;
  }

  if (!ALLOWED_STATUSES.includes(raw.status)) {
    return null;
  }

  const needs = normalizeCategoryList(raw.needs);
  const availableResources = normalizeCategoryList(raw.available_resources);

  if (needs === null || availableResources === null) {
    return null;
  }

  return {
    id: raw.id,
    name: raw.name,
    municipality: raw.municipality ?? raw.municipio ?? null,
    lat: Number(raw.latitude),
    lng: Number(raw.longitude),
    status: raw.status,
    needs,
    availableResources,
  };
}

/**
 * Normalizes a list of associations. Invalid records are dropped
 * (normalizeAssociation returns null) without affecting the rest.
 */
export function normalizeAssociations(rawAssociations) {
  if (!Array.isArray(rawAssociations)) {
    return [];
  }

  return rawAssociations.map(normalizeAssociation).filter(Boolean);
}

/**
 * Fetches associations.mock.json and returns the normalized list.
 */
export async function loadAssociations(
  url = "/data/associations.mock.json",
  options = {},
) {
  // Allows tests to inject a fake fetch instead of relying on the global.
  const fetchImpl = options.fetch ?? globalThis.fetch;
  const response = await fetchImpl(url);

  if (!response.ok) {
    throw new Error(`Respuesta no válida al cargar asociaciones (status ${response.status}).`);
  }

  const data = await response.json();

  if (!Array.isArray(data)) {
    throw new Error("El contenido de asociaciones no es un array.");
  }

  return normalizeAssociations(data);
}
