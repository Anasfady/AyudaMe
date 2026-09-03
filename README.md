# AyudaMe 🆘

Una plataforma de emergencia interactiva para coordinar y localizar recursos de ayuda en zonas afectadas por desastres naturales. Basada en mapas geográficos y gestión de asociaciones humanitarias.

## 📋 Descripción

**AyudaMe** es una aplicación web que proporciona:

- 🗺️ **Mapa interactivo** en tiempo real con límites geográficos de España
- 🏥 **Localización de asociaciones humanitarias** y puntos de ayuda
- 📊 **Filtrado de recursos** por categoría (agua, alimentos, productos para bebés, etc.)
- 🚨 **Visualización de zonas de emergencia** (DANA Valencia 2024)
- 📍 **Contexto de emergencia** con información de fuentes oficiales (Copernicus EMS)

## 🏗️ Estructura del Proyecto

```
AyudaMe/
├── app/                          # Backend (FastAPI)
│   ├── __init__.py
│   └── main.py                   # Servidor principal
├── frontend/                      # Frontend (HTML/JS/CSS)
│   ├── pages/
│   │   └── mapa.html             # Página principal
│   ├── src/
│   │   ├── map.js                # Inicialización del mapa Leaflet
│   │   ├── emergencyContext.js   # Gestión de contexto de emergencia
│   │   ├── scenarioList.js       # Catálogo de escenarios
│   │   ├── components/           # Componentes reutilizables
│   │   ├── init/                 # Inicializadores
│   │   ├── layers/               # Capas de mapa
│   │   └── services/             # Servicios API
│   └── css/
│       ├── asociaciones.css      # Estilos del panel de asociaciones
│       └── scenarios.css         # Estilos de escenarios
├── data/                          # Datos estáticos
│   ├── emergency-context.json    # Contexto de emergencia
│   ├── dana-horta-sud-copernicus.geojson  # Geometría de zonas afectadas
│   └── associations.mock.json    # Asociaciones simuladas
├── test/                          # Tests
├── requirements.txt               # Dependencias Python
├── Procfile                       # Configuración Heroku
└── README.md
```

## 🚀 Instalación

### Requisitos Previos
- Python 3.8+
- Node.js (opcional, si se modifica el frontend)

### Paso 1: Clonar el repositorio
```bash
git clone https://github.com/Anasfady/AyudaMe.git
cd AyudaMe
```

### Paso 2: Instalar dependencias Python
```bash
pip install -r requirements.txt
```

Las dependencias incluyen:
- `fastapi[standard]` - Framework web asincrónico
- `uvicorn` - Servidor ASGI

### Paso 3: Ejecutar la aplicación

#### Desarrollo local
```bash
uvicorn app.main:app --reload
```

La aplicación estará disponible en `http://localhost:8000`

#### Producción (Heroku)
```bash
heroku create
git push heroku main
```

## 📖 Uso

1. Accede a la aplicación en `http://localhost:8000`
2. Se abrirá automáticamente el mapa interactivo centrado en España
3. **Filtros de asociaciones**: Selecciona las categorías de ayuda que deseas visualizar
   - 💧 Agua
   - 🥫 Alimentos no perecederos
   - 👶 Productos de bebé
4. **Visualización**: El mapa mostrará:
   - Ubicaciones de asociaciones humanitarias
   - Zona afectada por la emergencia (en rojo)
   - Información del contexto de emergencia en la barra lateral

## 🗺️ Módulos Principales

### Backend (FastAPI)

**`app/main.py`**
```python
- GET /              # Redirige a /frontend/pages/mapa.html
- GET /health       # Verificación del estado del servidor
```

Sirve archivos estáticos:
- `/frontend` → Archivos de la interfaz
- `/data` → Datos JSON (contexto de emergencia, etc.)

### Frontend

**`frontend/src/map.js`** - Inicialización del mapa
- Carga Leaflet con tiles de CartoDB Voyager
- Define límites geográficos (España)
- Exporta instancia única del mapa

**`frontend/src/emergencyContext.js`** - Contexto de emergencia
- Carga geometría de zonas afectadas desde `/data/emergency-context.json`
- Dibuja polígonos en el mapa (DANA Valencia 2024)
- Muestra información en la barra lateral

**`frontend/src/scenarioList.js`** - Catálogo de escenarios
- Gestión de escenarios de emergencia
- Carga y cambio de contextos

**`frontend/pages/mapa.html`** - Página principal
- Estructura HTML del mapa
- Panel lateral de asociaciones
- Incluye bibliotecas: Leaflet para mapas

## 📊 Formato de Datos

### emergency-context.json
```json
{
  "name": "DANA Valencia 2024",
  "date": "2024-10-29",
  "geometry_file": "affected-zone.geojson",
  "source": {
    "provider": "Copernicus Emergency Management Service",
    "activation": "EMSR667",
    "area_name": "Valencia, España"
  }
}
```

### Association (associations.mock.json)
```json
[
  {
    "id": "association-001",
    "name": "Nombre de la asociación",
    "latitude": 39.42,
    "longitude": -0.35,
    "status": "active",
    "needs": ["water", "non_perishable_food"],
    "available_resources": ["baby_products"]
  }
]
```

Categorías soportadas: `water`, `non_perishable_food`, `baby_products`

## 🎨 Tecnologías Utilizadas

- **Backend**: FastAPI, Uvicorn
- **Frontend**: Vanilla JavaScript (ES6 modules), HTML5, CSS3
- **Mapas**: Leaflet.js, CartoDB Voyager tiles, GeoJSON
- **Datos**: JSON

## 🔧 Desarrollo

### Estructura de módulos JavaScript
Los módulos se cargan en este orden en `mapa.html`:
1. `map.js` - Instancia base del mapa
2. `init/associationsInit.js` - Inicializa asociaciones
3. `scenarioList.js` - Catálogo de escenarios
4. `emergencyContext.js` - Contexto de emergencia

### Agregar nuevas funcionalidades

1. **Nuevas capas de mapa**: Añade archivos en `frontend/src/layers/`
2. **Nuevos servicios**: Crea módulos en `frontend/src/services/`
3. **Nuevas rutas API**: Expande `app/main.py` con decoradores `@app.get()` o `@app.post()`

### Servicio de Datos de Asociaciones

**`frontend/src/services/associationsDataService.js`**

Funciones principales:
- `loadAssociations(url)` - Carga y valida asociaciones desde JSON
- `normalizeAssociations(rawList)` - Normaliza lista de asociaciones
- `normalizeAssociation(raw)` - Valida un registro individual
- `normalizeCategoryList(categories)` - Filtra categorías reconocidas

El servicio convierte datos brutos a formato normalizado:
- `latitude`/`longitude` → `lat`/`lng` (siempre `Number`)
- `available_resources` → `availableResources`

## 📱 Responsive Design

El diseño es completamente responsive:
- Pantalla completa (100vh × 100vw)
- Panel lateral: 300px de ancho (se adapta en móviles)
- Mapa: ocupa el espacio restante
- Compatible con touch en dispositivos móviles

## 🐛 Troubleshooting

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError: fastapi` | Ejecuta `pip install -r requirements.txt` |
| Mapa no carga | Verifica que Leaflet.js está disponible en CDN |
| Geometría de emergencia no aparece | Comprueba que `/data/emergency-context.json` existe |
| Asociaciones no se muestran | Verifica que `/data/associations.mock.json` está disponible |
| Error CORS en API | Verifica que FastAPI está configurado con middleware CORS |

## 📜 Licencia

Por especificar

## 👥 Contribuciones

Las contribuciones son bienvenidas. Para cambios importantes:
1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/mi-feature`)
3. Commit tus cambios (`git commit -am 'Agrega mi feature'`)
4. Push a la rama (`git push origin feature/mi-feature`)
5. Abre un Pull Request

## 📧 Contacto

Autor: [@Anasfady](https://github.com/Anasfady)

---

**Estado**: Activo 🟢

Última actualización: Septiembre 2026