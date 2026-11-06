import pytest

from app.security.sql_validator import UnsafeSQLError, validate_select

TABLES = ["cabezafactura", "detallefact"]


def validate(sql: str, max_rows: int = 100) -> str:
    return validate_select(sql, TABLES, max_rows)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT proveedor FROM cabezafactura WHERE PrefijoFact = 'FE' AND NroFact = '1234'",
        "SELECT COUNT(*), SUM(IFNULL(glosaparcial, 0)) FROM cabezafactura c "
        "JOIN detallefact d ON d.idcabezafact = c.idcf WHERE c.FechaRad >= '2026-10-01'",
        "SELECT DATE_FORMAT(FechaRad, '%Y-%m') AS mes, SUM(totalfactura) FROM cabezafactura GROUP BY mes",
        "WITH c AS (SELECT idcf FROM cabezafactura) SELECT * FROM c",
        "SELECT idcf FROM cabezafactura UNION SELECT idcabezafact FROM detallefact",
        "SELECT * FROM cabezafactura WHERE idcf IN (SELECT idcabezafact FROM detallefact)",
        "SELECT * FROM CabezaFactura",
    ],
)
def test_accepts_read_only_queries_on_allowed_tables(sql: str) -> None:
    assert validate(sql).upper().startswith(("SELECT", "WITH"))


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO cabezafactura (idcf) VALUES (1)",
        "UPDATE cabezafactura SET totalfactura = 0",
        "DELETE FROM cabezafactura",
        "DROP TABLE cabezafactura",
        "TRUNCATE TABLE cabezafactura",
        "ALTER TABLE cabezafactura ADD x INT",
        "CREATE TABLE x (a INT)",
        "SELECT 1; DROP TABLE cabezafactura",
        "SELECT * FROM cabezafactura; SELECT * FROM detallefact",
        "SET @a = 1",
        "SHOW TABLES",
        "CALL procedimiento()",
        "EXPLAIN SELECT * FROM cabezafactura",
        "SELECT * FROM cabezafactura INTO OUTFILE '/tmp/x'",
        "SELECT * FROM cabezafactura FOR UPDATE",
        "SELECT * FROM cabezafactura LOCK IN SHARE MODE",
        "SELECT @x",
        "SELECT @x := 1",
        "SELECT SLEEP(5)",
        "SELECT BENCHMARK(1000000, MD5('x'))",
        "SELECT LOAD_FILE('/etc/passwd')",
        "SELECT USER()",
        "SELECT VERSION()",
        "SELECT * FROM usuarios",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM mysql.user",
        "SELECT * FROM otra_base.cabezafactura",
        "SELECT * FROM cabezafactura WHERE idcf IN (SELECT id FROM secreta)",
        "",
        "esto no es sql",
    ],
)
def test_rejects_unsafe_or_unknown_queries(sql: str) -> None:
    with pytest.raises(UnsafeSQLError):
        validate(sql)


def test_comments_are_removed() -> None:
    assert validate("SELECT idcf FROM cabezafactura /* x */ -- y") == "SELECT idcf FROM cabezafactura LIMIT 100"


def test_adds_limit_when_missing() -> None:
    assert validate("SELECT idcf FROM cabezafactura", max_rows=50).endswith("LIMIT 50")


def test_keeps_smaller_limit() -> None:
    assert validate("SELECT idcf FROM cabezafactura LIMIT 5").endswith("LIMIT 5")


def test_caps_larger_limit() -> None:
    assert validate("SELECT idcf FROM cabezafactura LIMIT 5000").endswith("LIMIT 100")


def test_error_message_lists_available_tables() -> None:
    with pytest.raises(UnsafeSQLError, match="cabezafactura, detallefact"):
        validate("SELECT * FROM usuarios")
