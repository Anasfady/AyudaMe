# Datos mock — AyudaMe MVP

Todos los archivos `.mock.json` y `emergency-context.json` en esta carpeta son
**datos sintéticos de demostración**. No representan asociaciones, personas ni
emergencias reales.

## Archivos

- `emergency-context.json` — contexto del escenario de emergencia mostrado en
  el mapa del MVP. `source.type: "mock"` indica que es un dato de demo.
- `associations.mock.json` — array raíz con asociaciones/organizaciones
  sintéticas que ofrecen recursos. Los nombres, IDs y coordenadas son
  ficticios.
- `alertas.json`, `ayudas.json`, `necesidades.json` — reservados para otras
  responsabilidades del equipo (aún vacíos en este branch).

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
