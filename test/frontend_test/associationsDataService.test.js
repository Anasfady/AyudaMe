import test from "node:test";
import assert from "node:assert/strict";

import {
  normalizeAssociation,
  normalizeAssociations,
  normalizeCategoryList,
  isValidCoordinate,
} from "../../frontend/src/services/associationsDataService.js";

// Baseline fixture reused (and tweaked) across tests below.
const validAssociation = {
  id: "association-001",
  name: "Asociación Demo",
  latitude: 39.42,
  longitude: -0.38,
  status: "active",
  needs: ["baby_products"],
  available_resources: ["water"],
};

test("TEST 1 - registro válido se normaliza correctamente", () => {
  const result = normalizeAssociation(validAssociation);

  assert.deepEqual(result, {
    id: "association-001",
    name: "Asociación Demo",
    municipality: null,
    lat: 39.42,
    lng: -0.38,
    status: "active",
    needs: ["baby_products"],
    availableResources: ["water"],
  });
});

test("TEST 2 - latitude/longitude string numéricos se convierten a number", () => {
  const result = normalizeAssociation({
    ...validAssociation,
    latitude: "39.42",
    longitude: "-0.38",
  });

  assert.equal(typeof result.lat, "number");
  assert.equal(typeof result.lng, "number");
  assert.equal(result.lat, 39.42);
  assert.equal(result.lng, -0.38);
});

test("TEST 3 - coordenadas inválidas provocan que el registro se descarte", () => {
  // Non-numeric string, null, undefined, NaN and out-of-range values must
  // all be rejected.
  assert.equal(
    normalizeAssociation({ ...validAssociation, latitude: "hola" }),
    null,
  );
  assert.equal(normalizeAssociation({ ...validAssociation, latitude: null }), null);
  assert.equal(
    normalizeAssociation({ ...validAssociation, longitude: undefined }),
    null,
  );
  assert.equal(normalizeAssociation({ ...validAssociation, latitude: NaN }), null);
  assert.equal(normalizeAssociation({ ...validAssociation, latitude: 200 }), null);
});

test("TEST 4 - categoría desconocida se rechaza", () => {
  assert.deepEqual(normalizeCategoryList(["clothing", "water"]), ["water"]);

  // An unknown category should only be dropped from the list,
  // not invalidate the whole association.
  const result = normalizeAssociation({
    ...validAssociation,
    needs: ["medication"],
    available_resources: ["water", "medication"],
  });

  assert.deepEqual(result.needs, []);
  assert.deepEqual(result.availableResources, ["water"]);
});

test("TEST 5 - un registro inválido no impide procesar otros registros válidos", () => {
  const rawAssociations = [
    validAssociation,
    { ...validAssociation, id: "association-002" },
    { ...validAssociation, id: "association-003" },
    { ...validAssociation, id: "association-004" },
    { ...validAssociation, id: "association-005" },
    // Corrupt record: empty id and non-numeric latitude.
    { ...validAssociation, id: "", latitude: "hola" },
  ];

  const result = normalizeAssociations(rawAssociations);

  // 5 valid + 1 discarded, without breaking the batch.
  assert.equal(result.length, 5);
});

test("TEST 6 - solo se aceptan water, non_perishable_food y baby_products", () => {
  assert.deepEqual(
    normalizeCategoryList(["water", "non_perishable_food", "baby_products"]),
    ["water", "non_perishable_food", "baby_products"],
  );
  assert.deepEqual(normalizeCategoryList(["shelter", "hygiene"]), []);
  assert.equal(normalizeCategoryList("not-an-array"), null);
});

test("isValidCoordinate valida rangos de latitud y longitud", () => {
  assert.equal(isValidCoordinate(39.4, -90, 90), true);
  assert.equal(isValidCoordinate("39.4", -90, 90), true);
  assert.equal(isValidCoordinate(100, -90, 90), false);
  assert.equal(isValidCoordinate("hola", -90, 90), false);
  assert.equal(isValidCoordinate(null, -90, 90), false);
  assert.equal(isValidCoordinate(undefined, -180, 180), false);
  assert.equal(isValidCoordinate(true, -90, 90), false);
  assert.equal(isValidCoordinate([], -90, 90), false);
  assert.equal(isValidCoordinate("   ", -90, 90), false);
});
