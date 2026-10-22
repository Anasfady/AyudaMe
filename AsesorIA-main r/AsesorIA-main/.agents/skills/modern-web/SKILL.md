# Modern Web Guidance Skill — AsesorIA

## Propósito
Guía para el coding agent sobre patrones web modernos, usada como referencia NO como dependencia runtime.

## Regla fundamental
Modern Web Guidance NO se convierte en dependencia de la aplicación.
- NO añadir a `requirements.txt`.
- NO añadir a `package.json` de la aplicación.
- NO instalar paquetes de runtime en el proyecto AsesorIA.
- Úsala solo como referencia del coding agent para decisiones de UI/UX.

## 1. Patrones actuales de web
- HTML5 semántico: `<header>`, `<main>`, `<section>`, `<footer>`, `<button>`, `<input>`, `<textarea>`.
- CSS moderno: `clamp()`, `minmax()`, `calc()`, `rem`, `em`, unidades relativas.
- CSS Grid y Flexbox para layout.
- `prefers-color-scheme` para themes light/dark (Chainlit ya inyecta classes `.dark` en `<html>`).
- `prefers-reduced-motion` para animaciones (ver skill accessibility).
- `meta viewport` `<meta name="viewport" content="width=device-width, initial-scale=1">` (Chainlit ya lo inyecta).

## 2. Compatibilidad
- AsesorIA corre sobre Chainlit 2.12, que usa React internamente pero NO debe reescribirse.
- Todo CSS debe usar el prefijo `-ias-` para no colisionar con selectores de Chainlit.
- JS debe ser defensivo: `MutationObserver`, `getElementById` con `id` guards, auto-observación de DOM.
- Evitar APIs experimentales no soportadas universalmente (WebGPU, WebHID, etc.).

## 3. Razonable modernización
Lo que SÍ está permitido y es recomendable:
- Usar `clamp()` para tamaños de fuente fluidas.
- Usar `minmax()` en grids/responsive.
- Usar `rem` en lugar de `px` para dimensiones relativas al root.
- Usar `prefers-color-scheme` para detectar theme del sistema (aunque AsesorIA usa tema fijo light/dark).
- Usar `gap` en lugar de márgenes manuales en Flex/Grid.
- Usar `border-radius: 0.5rem` o variables `--radius`.

## 4. Evitar
- APIs experimentales sin fallback.
- `document.write()`.
- `innerHTML` masivo sin sanitización.
- `document.querySelectorAll` sobre elementos inestables sin guards.
- Transformaciones CSS que afecten layout (solo uso decorativo controlado).
- Agregar librerías completas (React, Vue, Angular) — **estrictamente prohibido**.

## 5. Referencia
Si el coding agent necesita consultar un patrón:
1. Visitar la skill `modern-web` en `.agents/skills/modern-web/SKILL.md`.
2. Buscar en MDN Web Docs.
3. Buscar en la documentación de Chainlit 2.12.
4. Probar en `localhost:8000` y verificar visualmente.

## 6. Nunca hacer lo siguiente
- Convertir AsesorIA a una aplicación SPA de un solo framework.
- Agregar un bundler (webpack, Vite, etc.) — el proyecto ya usaChainlit nativo.
- Migrar `custom.js` o `custom.css` a estar procesados por una build system.
- Instalar `modern-web-guidance` como dependencia del proyecto (ya es skill del agent, no runtime).

## 7. Comprobar después de cambios
- `python -m pytest tests/ -q` debe pasar (0 fallos).
- Visual inspection en `localhost:8000` light y dark.
- No romper la compatibilidad con Chrome/Edge/Firefox últimas versiones (Chainlit 2.12 target).