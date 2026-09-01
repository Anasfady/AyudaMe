# Datos — AyudaMe MVP

Los datos del MVP distinguen entre el contexto histórico de emergencia y los
datos simulados utilizados para demostrar la operativa de asociaciones.

## Archivos

- `emergency-context.json` — contexto histórico de referencia basado en la
  DANA de Valencia de 2024. Incluye la fecha de referencia del escenario y
  metadatos de la fuente geográfica utilizada.
- `dana-horta-sud-copernicus.geojson` — geometría de inundación observada en
  Horta Sud procedente de Copernicus Emergency Management Service, activación
  EMSR773, AOI03, producto de delineación `observedEventA`. Representa la zona
  cartografiada dentro de esa área de interés, no toda la extensión de la DANA.
- `associations.mock.json` — asociaciones, necesidades y recursos sintéticos
  utilizados exclusivamente para validar la funcionalidad del MVP. Los nombres,
  IDs y coordenadas de estas asociaciones son ficticios.
- `alertas.json`, `ayudas.json`, `necesidades.json` — archivos reservados para
  otras responsabilidades del equipo.

## Contrato `Association` (dato bruto en `associations.mock.json`)

`associations.mock.json` es un array raíz de objetos `Association`:

```json
[
  {
    "id": "association-001",
    "name": "string no vacío",
    "latitude": -90..90,
    "longitude": -180..180,
    "status": "active | inactive",
    "needs": ["water | non_perishable_food | baby_products", "..."],
    "available_resources": ["water | non_perishable_food | baby_products", "..."]
  }
]
```

`latitude`/`longitude` pueden venir como número o como string numérico
(`"39.42"`); cualquier otro valor (`"hola"`, `null`, `undefined`, `NaN`, fuera
de rango) hace que el registro completo se descarte.

`needs` y `available_resources` son arrays de categorías: qué le falta a la
asociación (`needs`) y qué tiene disponible para repartir
(`available_resources`). Ambos deben ser arrays; cualquier categoría no
reconocida dentro de ellos se descarta sin invalidar el resto del registro.

Categorías permitidas (únicas soportadas en este MVP):
`water`, `non_perishable_food`, `baby_products`.

## `associationsDataService.js`

Ubicación: `frontend/src/services/associationsDataService.js`.

Responsabilidad: cargar, validar y normalizar asociaciones. No contiene
lógica de Leaflet, no crea marcadores y no toca el DOM — solo trabaja con
datos.

Funciones principales:

- `normalizeCategoryList(categories)` — filtra una lista dejando solo
  categorías reconocidas; devuelve `null` si el valor no es un array.
- `normalizeAssociation(raw)` — valida y normaliza una asociación completa
  (incluye `needs` y `available_resources`).
- `normalizeAssociations(rawList)` — normaliza una lista; descarta cualquier
  registro inválido sin interrumpir el procesamiento de los demás.
- `loadAssociations(url)` — hace `fetch` de `associations.mock.json` y
  devuelve el resultado ya normalizado. Comprueba `response.ok` y que el
  JSON recibido sea un array.

### Dato bruto vs. dato normalizado

| Dato bruto (`associations.mock.json`)         | Dato normalizado (salida del servicio) |
| ---------------------------------------------- | --------------------------------------- |
| `latitude`, `longitude` (número o string)      | `lat`, `lng` (siempre `Number`)         |
| `available_resources`                          | `availableResources`                    |
| Puede incluir registros o categorías inválidas | Solo contiene registros/categorías válidas |

El dato normalizado es el que debe consumir la capa de recursos/asociaciones
(fuera del alcance de este trabajo).

### Ejecución local

Para que `loadAssociations()` pueda acceder a `/data/associations.mock.json`,
el servidor HTTP debe iniciarse desde la raíz del repositorio.

```bash
python3 -m http.server 8000
```
