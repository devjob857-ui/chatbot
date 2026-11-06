"""Validación de seguridad del SQL generado por el modelo.

Solo se acepta una única consulta de lectura sobre las tablas permitidas.
Se analiza con un parser real (sqlglot); nunca con expresiones regulares.
"""

from collections.abc import Iterable

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

DIALECT = "mysql"

# Funciones que no tienen sentido en una consulta de negocio y pueden usarse para atacar
# (esperas, lectura de archivos, bloqueos, información del servidor).
FORBIDDEN_FUNCTIONS = {
    "sleep",
    "benchmark",
    "load_file",
    "get_lock",
    "release_lock",
    "release_all_locks",
    "is_free_lock",
    "is_used_lock",
    "master_pos_wait",
    "sys_exec",
    "sys_eval",
    "user",
    "current_user",
    "session_user",
    "system_user",
    "database",
    "schema",
    "version",
    "current_version",
    "current_schema",
    "current_database",
    "connection_id",
    "last_insert_id",
    "row_count",
    "found_rows",
}

# Nodos que nunca pueden aparecer en una consulta de solo lectura.
FORBIDDEN_NODES: tuple[type[exp.Expression], ...] = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Merge,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.TruncateTable,
    exp.Command,
    exp.Into,
    exp.Lock,
    exp.Parameter,
    exp.SessionParameter,
    exp.Placeholder,
    exp.Set,
    exp.Use,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
    exp.PropertyEQ,
)


class UnsafeSQLError(ValueError):
    """El SQL no es una consulta de lectura permitida. El mensaje se puede mostrar al modelo."""


def validate_select(sql: str, allowed_tables: Iterable[str], max_rows: int) -> str:
    """Valida el SQL y lo devuelve normalizado, con un LIMIT de como máximo `max_rows`."""
    allowed = {table.lower() for table in allowed_tables}

    try:
        statements = [s for s in sqlglot.parse(sql, read=DIALECT) if s is not None]
    except ParseError as error:
        raise UnsafeSQLError("La consulta no es SQL válido para MariaDB.") from error

    if len(statements) > 1:
        raise UnsafeSQLError("Se permite exactamente una consulta, sin ';' adicionales.")

    if not statements:
        raise UnsafeSQLError("La consulta está vacía.")
    tree = statements[0]
    if not isinstance(tree, exp.Query):
        raise UnsafeSQLError("Solo se permiten consultas SELECT.")

    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            raise UnsafeSQLError(f"La consulta contiene una operación no permitida ({node.key.upper()}).")
        if isinstance(node, exp.Func):
            name = (node.name if isinstance(node, exp.Anonymous) else node.sql_name()).lower()
            if name in FORBIDDEN_FUNCTIONS:
                raise UnsafeSQLError(f"La función {name.upper()} no está permitida.")

    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if table.db or table.catalog:
            raise UnsafeSQLError(f"No se permite indicar el esquema ({table.db}.{table.name}).")
        if name in cte_names:
            continue
        if name not in allowed:
            permitted = ", ".join(sorted(allowed))
            raise UnsafeSQLError(f"La tabla '{table.name}' no está permitida. Tablas disponibles: {permitted}.")

    _enforce_limit(tree, max_rows)
    return tree.sql(dialect=DIALECT, comments=False)


def _enforce_limit(tree: exp.Query, max_rows: int) -> None:
    limit = tree.args.get("limit")
    if limit is not None:
        value = limit.expression
        if isinstance(value, exp.Literal) and value.is_int and int(value.this) <= max_rows:
            return
    tree.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))
