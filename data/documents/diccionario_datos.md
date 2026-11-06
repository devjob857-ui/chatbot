# Diccionario de datos de Medicalidad

Este documento describe las tablas de MariaDB que el asistente puede consultar. Se envía completo
al modelo que escribe el SQL, así que **todo lo que esté aquí influye en la calidad de las respuestas**.

Reglas para mantenerlo:
- Cada tabla va en una sección `## Tabla: <nombre>`. Solo las tablas listadas así se pueden consultar.
- Las descripciones marcadas *(confirmar)* se dedujeron del nombre de la columna: revisarlas.
- Los puntos marcados **POR COMPLETAR** necesitan información del equipo de negocio.
- Las columnas sin descripción existen, pero el modelo no sabrá para qué sirven: conviene describir
  las que los usuarios vayan a preguntar.

## Conceptos del negocio

- **IPS / proveedor**: institución prestadora de salud que envía las facturas. Se identifica por `nit` y `proveedor` (nombre).
- **Factura**: se identifica por prefijo (`PrefijoFact`) + número (`NroFact`), por ejemplo `FE-1234` = prefijo `FE`, número `1234`.
  El mismo prefijo y número puede repetirse entre proveedores distintos: siempre mostrar el proveedor.
- **Radicación**: fecha en que la factura se recibió formalmente (`FechaRad`).
- **Glosa**: valor objetado de una factura durante la auditoría. Puede ser parcial o total.
- **Valor glosado total** de una factura = `IFNULL(glosaparcial, 0) + IFNULL(glosatotal, 0)`.
- **Auditoría**: revisión de la factura por un auditor (`auditor`, `fechaauditoria`).

## Tabla: cabezafactura

Encabezado de cada factura: una fila por factura.

| Columna | Descripción |
|---|---|
| idcf | Identificador interno de la factura (clave primaria). |
| Tipofact | Tipo de factura. **POR COMPLETAR**: valores posibles. |
| FechaRad | Fecha de radicación de la factura. |
| Sucursal | Sucursal *(confirmar)*. |
| Radicacion | Número de radicación *(confirmar)*. |
| PrefijoFact | Prefijo de la factura (p. ej. `FE`). |
| NroFact | Número de la factura, sin el prefijo. |
| Subtotal | Subtotal de la factura antes de impuestos y descuentos *(confirmar)*. |
| coutamoderad | Cuota moderadora *(confirmar)*. |
| iva | Valor del IVA. |
| descuento | Valor del descuento. |
| totalfactura | Valor total facturado. |
| usuario | Usuario que registró la factura *(confirmar)*. |
| fechadigitacion | Fecha de digitación de la factura. |
| estadofact | Estado de la factura. **POR COMPLETAR**: qué valores existen y qué significa cada uno (p. ej. cuál indica "pendiente por auditar"). |
| nit | NIT del proveedor (IPS). |
| proveedor | Nombre del proveedor (IPS). |
| codhabilita | Código de habilitación de la IPS *(confirmar)*. |
| numlote | Número de lote de carga *(confirmar)*. |
| digitador | Persona que digitó la factura. |
| fechaasignadig | Fecha de asignación al digitador. |
| fechadigita | Fecha de digitación. |
| auditor | Auditor asignado a la factura. |
| fechaasignaaudit | Fecha de asignación al auditor. |
| fechaauditoria | Fecha en que se auditó la factura. Vacía (NULL) si aún no se audita *(confirmar)*. |
| quiencontestaglo | Quién contestó la glosa. |
| fechacontestaglosa | Fecha de respuesta a la glosa. |
| glosaparcial | Valor glosado parcialmente. |
| glosatotal | Valor glosado totalmente. |
| valorapagar | Valor a pagar después de glosas *(confirmar)*. |
| fecharecibedyg | Fecha de recepción en DyG *(confirmar)*. |
| cuentacobro | Número de cuenta de cobro *(confirmar)*. |
| copago | Valor del copago. |
| contratofact | Contrato asociado a la factura *(confirmar)*. |
| quienconcilia | Quién realizó la conciliación. |
| fechaconcilia | Fecha de conciliación. |
| origenservicio | Origen del servicio. **POR COMPLETAR**: valores posibles. |

Otras columnas sin describir: sucursalx, debito, credito, anticipo, corte, idlotecabeza, notacabezafact,
notead, noteenf, notemed, notaimagen, quienrecibe, unidadliderc, unidadlsatelitec, consecutivcarga, idtscf,
notacontestg1, notacontestg2, notaaudglosa1, notaaudglosa2, fechacontestglosa1, quiencontestaglosa2,
correoenivado, contratof, envianotifica, envianotifica2, notaconcilia, fechaudrespglosa1, fechaudrespglosa2, covid19.

## Tabla: detallefact

Detalle de la factura: una fila por cada servicio facturado.

| Columna | Descripción |
|---|---|
| iddf | Identificador interno del detalle (clave primaria). |
| idcabezafact | Factura a la que pertenece. Se relaciona con `cabezafactura.idcf`. |
| numdocumento | Número de documento del paciente *(confirmar)*. |
| codiservicio | Código del servicio prestado. |
| nombreservicio | Nombre del servicio prestado. |
| fechaprestacionserv | Fecha en que se prestó el servicio. |
| valorunitariod | Valor unitario del servicio. |
| cantidadd | Cantidad. |
| totald | Valor total del servicio (unitario × cantidad) *(confirmar)*. |
| estadfact | Estado del detalle. **POR COMPLETAR**: valores posibles. |
| glosaparciald | Valor glosado parcialmente en este servicio. |
| glosatotald | Valor glosado totalmente en este servicio. |
| totalapagard | Valor a pagar por este servicio. |
| auditord | Auditor del servicio. |
| fechaauditord | Fecha de auditoría del servicio. |
| copagod | Copago del servicio. |
| coddx | Código del diagnóstico (CIE-10) *(confirmar)*. |
| descridx | Descripción del diagnóstico. |
| tiposerviciod | Tipo de servicio. **POR COMPLETAR**: valores posibles. |

Otras columnas sin describir: fechaactual, idpland, napd, usuariodigita, fechadigita, issd, tarifad,
coberturad, controlcarguedig, ivad, creditod, debitod, anticipod, descuentod, inicio, fin, derivacohorte,
nvoiddx, nvodescripdx, observacohorte, estadosalidas, mapiisdetfact, nopobsdetfact, NoFormula,
FechaFormula, CantidadFormula, FechaEntrega.

## Relaciones

- `detallefact.idcabezafact` → `cabezafactura.idcf` (una factura tiene muchos servicios).

## Ejemplos de preguntas y su SQL

Pregunta: ¿Cuál fue el valor glosado total de la factura FE-1234?
```sql
SELECT proveedor, nit, PrefijoFact, NroFact,
       IFNULL(glosaparcial, 0) + IFNULL(glosatotal, 0) AS valor_glosado
FROM cabezafactura
WHERE PrefijoFact = 'FE' AND NroFact = '1234'
```

Pregunta: ¿Cuántas facturas se radicaron en octubre de 2026?
```sql
SELECT COUNT(*) AS facturas
FROM cabezafactura
WHERE FechaRad >= '2026-10-01' AND FechaRad < '2026-11-01'
```

Pregunta: ¿Cuál es el total facturado por mes este año?
```sql
SELECT DATE_FORMAT(FechaRad, '%Y-%m') AS mes, SUM(totalfactura) AS total_facturado
FROM cabezafactura
WHERE YEAR(FechaRad) = YEAR(CURDATE())
GROUP BY mes
ORDER BY mes
```

Pregunta: ¿Qué proveedores tienen más valor glosado?
```sql
SELECT proveedor, nit, SUM(IFNULL(glosaparcial, 0) + IFNULL(glosatotal, 0)) AS valor_glosado
FROM cabezafactura
GROUP BY proveedor, nit
ORDER BY valor_glosado DESC
LIMIT 10
```

Pregunta: ¿Qué servicios tiene la factura FE-1234?
```sql
SELECT d.codiservicio, d.nombreservicio, d.cantidadd, d.totald
FROM detallefact d
JOIN cabezafactura c ON d.idcabezafact = c.idcf
WHERE c.PrefijoFact = 'FE' AND c.NroFact = '1234'
```

Pregunta: ¿Cuántas facturas tiene la Clínica San Rafael sin auditar?
```sql
SELECT COUNT(*) AS facturas_sin_auditar
FROM cabezafactura
WHERE proveedor LIKE '%San Rafael%' AND fechaauditoria IS NULL
```

Pregunta: ¿Qué auditor tiene más facturas asignadas?
```sql
SELECT auditor, COUNT(*) AS facturas
FROM cabezafactura
WHERE auditor IS NOT NULL AND auditor <> ''
GROUP BY auditor
ORDER BY facturas DESC
LIMIT 10
```
