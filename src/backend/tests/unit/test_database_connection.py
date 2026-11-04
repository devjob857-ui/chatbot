from app.core.config import Settings
from app.database.connection import build_engine


def test_motor_se_conecta_a_mariadb_con_los_datos_de_configuracion() -> None:
    settings = Settings(
        _env_file=None,
        db_host="mariadb.interno",
        db_port=3307,
        db_name="medicalidad",
        db_user="lectura",
        db_password="secreto-de-prueba",
    )

    engine = build_engine(settings)

    assert engine.url.render_as_string(hide_password=False) == (
        "mysql+pymysql://lectura:secreto-de-prueba@mariadb.interno:3307/medicalidad"
    )
    engine.dispose()
