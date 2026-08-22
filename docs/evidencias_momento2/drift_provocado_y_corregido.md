# Evidencia: schema drift provocado, detectado y corregido (E3)

**Fecha:** 2026-08-21, ~20:11 (America/Bogota)
**Qué exige el criterio C2:** que la ingesta relacional detecte drift **antes** de
cargar, falle con un mensaje accionable, y que eso se demuestre con un caso real
provocado y corregido. Este es el caso.

## 1. Provocar el drift

Se simuló que el backend agregó una columna en el origen (el mismo escenario que el
equipo ya vivió de verdad en el Momento 1 con `bill.payment_method`, `bill.paid_date`
y la tabla `vehicle`): la extracción de `coverage` trae una columna nueva,
`max_payout_usd`, que la tabla destino en Snowflake no conoce.

## 2. La detección — antes de tocar el stage

```
$ uv run carga/cargar.py --tabla coverage       (exit code: 1)

Schema drift en COVERAGE: la extracción de Neon trae columna(s) que la tabla
destino no tiene: ['MAX_PAYOUT_USD'].
  La carga de esta tabla NO se ejecutó (el resto de tablas continúa).
  Para resolverlo, aplica esto en un Worksheet y vuelve a correr:

ALTER TABLE RAW.COVERAGE ADD COLUMN "MAX_PAYOUT_USD" VARCHAR;

Resumen: 0/1 tablas cargadas.
```

Puntos que el mensaje resuelve:

- **Dice qué columna** apareció — no un genérico "column count mismatch".
- **Entrega el `ALTER TABLE` listo** para pegar en un Worksheet.
- **No tocó nada**: el chequeo corre antes del `PUT` y del `DELETE`, así que el DW
  quedó exactamente como estaba (no hay rollback que explicar).
- El fallo quedó registrado en `CONTROL.BITACORA_CARGA` como `LOAD_FAILED`, con el
  mensaje completo.

## 3. La corrección

Se aplicó el `ALTER TABLE` **exactamente como lo sugirió el script**, y se volvió a
correr:

```
ALTER TABLE RAW.COVERAGE ADD COLUMN "MAX_PAYOUT_USD" VARCHAR;

$ uv run carga/cargar.py --tabla coverage       (exit code: 0)
COPY COVERAGE · 15 filas borradas, 15 cargadas
Resumen: 1/1 tablas cargadas.
```

## Cómo reproducirlo en la sustentación (40 segundos)

1. Agregar una columna cualquiera al header de `data_extraida/coverage.csv` (y un
   valor a cada fila).
2. `uv run carga/cargar.py --tabla coverage` → falla con el mensaje de arriba.
3. Pegar el `ALTER` sugerido en un Worksheet.
4. Volver a correr → carga limpia.

## Por qué el chequeo explícito, si `MATCH_BY_COLUMN_NAME` ya protege

El `COPY INTO` con emparejamiento por nombre también falla ante una columna
desconocida — pero con un error genérico, después del `DELETE` (forzando rollback), y
sin decir qué hacer. La detección previa convierte el mismo problema en un
diagnóstico de 10 segundos. El detalle está comentado en
`momento2/carga/cargar.py` (`verificar_drift`).
