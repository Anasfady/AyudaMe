# Accessibility Skill — AsesorIA

## Propósito
Procedimiento reusable para evaluar accesibilidad en el frontend de AsesorIA usando Playwright, @axe-core/playwright y buenas prácticas WCAG.

## Herramientas
- Playwright (`npx playwright test`).
- @axe-core/playwright (`await page.evaluate(() => new Axe({page}).getScannen())`).
- Lighthouse (`await page.evaluate(() => ChromeLighthouse(...))`).

## 1. Procedimiento general
1. Levantar la app: `cd ui && chainlit run app.py`.
2. Ejecutar tests de Playwright contra `localhost:8000`.
3. Ejecutar axe-core en los elementos críticos.
4. Revisar informe de Lighthouse (modo incógnito si hay variables de entorno).
5. Priorizar problemas reales sobre puntuaciones artificiales.

## 2. Contraste
- Verificar contraste de razón >= 4.5:1 para texto normal y >= 3:1 para grande (WCAG AA).
- Comprobar `--background`, `--foreground`, `--card`, `--muted-foreground` en light y dark.
- Probar estados hover, focus, disabled.
- Usar `contrast-ratio.com` o herramientas similares si es necesario.
- Si el contraste falla, hacer ajustes mínimos a `theme.json` o `custom.css`.

## 3. Nombres accesibles
- Todo botón debe tener `aria-label` o texto interno significativo.
- Los `cl.Action` deben tener `name` y `label` claros.
- Los chips `cl.Text(display="side")` deben tener `name` descriptivo.
- Evitar textos genéricos como "Hacer" o "Más" sin contexto.
- Verificar que el screen reader lea el contenido esperado.

## 4. Botones
- `cl.Action` deben tener `label` y `tooltip` descriptivos.
- `cl.Button` (si existe) deben tener texto claro.
- Estados: `hover`, `focus`, `disabled` deben ser visual y accesiblemente distintos.
- Usar `:-webkit-focus-ring` o `outline` coherente con `custom.css`.
- Verificar que Enter y Space activan el botón.

## 5. Inputs y focus
- `textarea` (campo de pregunta) debe tener `aria-label` o placeholder significativo.
- `focus-visible` debe estar definido en `custom.css` (actualmente: `outline: 2px solid hsl(var(--ring, 152 45% 34%))`).
- El focus no debe quedar oculto ni superpuesto.
- Tab order debe ser lógico: botón upload → textarea → enviar (Enter).

## 6. Errores
- Los mensajes de error deben ser visibles y asociados al elemento correspondiente.
- `format_error()` y `format_file_error()` deben mostrar texto en español natural, sin stack traces ni detalles internos.
- Los errores de validación de archivos (tipo, tamaño, vacío) deben ser anunciados por screen reader.
- Nunca mostrar `undefined`, `null` o nombres de excepción al usuario.

## 7. Estados de carga
- `cl.Step(name="Consultando la documentación")` debe tener `type="retrieval"`.
- El output `🔎 Consultando la documentación...` debe ser legible.
- Durante loading, el botón de enviar o el textarea deben permanecer accesibles o estar en estado disabled con mensaje claro.
- Nunca dejar el composer en estado "Stop" (bug conocido, documentado en `ui/README.md`).

## 8. Responsive
- Probar desktop (~1400px): jerarquía visible, tarjetas no se apilan de forma extraña, FAB accesible.
- Probar 420px: todo el contenido cabrá sin overflow horizontal, tarjetas se apilan verticalmente, FAB y panel lateral siguen accesibles.
- Texto truncado debe tener `text-overflow: ellipsis` y ancho contenido.
- No debe haber elementos superpuestos en ningún viewport.

## 9. Reduced motion
- Verificar que no hay animaciones que sean incomodas.
- Si hay transiciones (hover, focus), estas deben ser breves y no causar mareos.
- Respetar la preferencia del usuario por `reduce-motion` si está configurada (aunque Chainlit no expone esta meta fácilmente, verificar que no hay animaciones infinitas o aceleradas).

## 10. Dark / Light
- Verificar paleta en light y dark (`theme.json`).
- Contraste adecuado en ambos themes.
- No hay "artefactos" visuales al cambiar de tema.
- Los componentes `-ias-*` deben verse coherentes en light y dark.

## 11. Informar
- Documentar cada problema encontrado con:
  - Página/elemento.
  - Descripción del problema WCAG.
  - Nivel (A/AA/AAA).
  - Recomendación de corrección.
- Si un problema requiere backend, marcarlo como dependencia externa.
- Ejecutar `pytest tests/ -q` después de cambios para asegurar 0 fallos.