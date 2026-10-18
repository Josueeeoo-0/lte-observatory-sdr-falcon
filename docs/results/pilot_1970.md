# Informe del piloto a 1970 MHz

Este informe describe los resultados agregados publicados para la sesión `pilot_1970`.

| Indicador | Valor |
|---|---|
| Registros válidos | 198 |
| Filas descartadas | 9 |
| Filas con cantidad de campos incorrecta | 1 |
| Lapso entre registros válidos extremos | 120,542 segundos |
| Suma de PRB de las asignaciones observadas | 4042 |
| Identificadores distintos tras el filtro | 45 |
| Ventanas de un segundo con registros | 44 |

El análisis contabilizó 207 líneas en total, sin líneas vacías ni comentarios. El conteo corresponde al archivo procesado por el analizador; puede diferir de `wc -l` si la última línea no termina con un salto de línea. No se ha verificado aquí esa causa en el archivo original.

## Actividad temporal

La [figura de actividad](../../figures/pilot_1970/activity.svg) muestra recursos asignados, cantidad de mensajes e identificadores distintos por ventana. Los espacios sin trazado representan intervalos sin registros y no permiten concluir que la celda estuvo inactiva.

La suma de PRB describe asignaciones decodificadas, no ocupación porcentual ni tráfico entregado. Los 45 identificadores corresponden al filtro que excluye 0 y valores desde 65524; no equivalen a 45 personas ni a todos los equipos conectados.

## Distribución de MCS

La [distribución MCS](../../figures/pilot_1970/mcs.svg) cuenta qué índices aparecen en registros de subida y bajada. Permite comparar las asignaciones observadas, pero no determina por sí sola la calidad del canal.

## Sensibilidad a registros faltantes

La [figura del experimento](../../figures/pilot_1970/synthetic_record_removal.svg) compara el total de PRB conservados al eliminar registros con probabilidades del 0 %, 10 %, 30 % y 50 %, usando semilla fija.

Es una prueba sintética sobre registros ya decodificados. No reproduce pérdidas reales de subtramas ni errores RF. Una única semilla ofrece una realización reproducible, no una estimación de precisión del sistema.

## Calidad de la adquisición

No se obtuvo un resumen reconocible de subtramas omitidas a partir de la consola suministrada al análisis. No se publica un porcentaje de omisión para esta sesión. El lapso de 120,542 segundos entre registros extremos tampoco demuestra recepción continua.

## Datos consultables

- [Resumen de sesión](../../data/processed/pilot_1970/summary.json).
- [Actividad por ventana](../../data/processed/pilot_1970/activity.csv).
- [Conteos MCS](../../data/processed/pilot_1970/mcs_distribution.csv).
- [Escenarios de eliminación](../../data/processed/pilot_1970/synthetic_record_removal.csv).
