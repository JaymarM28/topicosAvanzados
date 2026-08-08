        boolean is_policy_coverage
        boolean is_vehicle_coverage
    }
    POLICY_COVERAGE {
        int id PK
        int policy_id FK
        int coverage_id FK
        boolean active
    }
    VEHICLE {
        int id PK
        text vin
        text make
        text model
        smallint model_year
        text plate
    }
    VEHICLE_COVERAGE {
        int id PK
        int vehicle_id FK
        int coverage_id FK
        boolean active
    }
```

## Tablas

| Tabla | Descripción | Llave | Relación |
|---|---|---|---|
| `coverage` | Catálogo de tipos de cobertura, con flags de si aplica a nivel póliza y/o vehículo | `id` | — |
| `policy` | Pólizas de seguro vehicular | `id` | — |
| `policy_edit_log` | Auditoría de cambios sobre una póliza | `id` | `policy_id` → `policy.id` |
| `bill` | Facturación periódica de una póliza | `id` | `policy_id` → `policy.id` |
| `policy_coverage` | Coberturas contratadas a nivel póliza | `id` | `policy_id` → `policy.id`, `coverage_id` → `coverage.id` |
| `vehicle` | Vehículos asegurados (agregada en `V202608081500`, no está en el baseline) | `id` | — |
| `vehicle_coverage` | Coberturas contratadas a nivel vehículo | `id` | `vehicle_id` → `vehicle.id`, `coverage_id` → `coverage.id` |

## Origen

Inspirado en el ERD de referencia `Vehicle-coverage-ERD-Example-Graphic-2.png`. Los datos
son sintéticos, generados para fines didácticos.
