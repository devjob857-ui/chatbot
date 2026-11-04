from pathlib import Path

import pytest

from app.core.config import Settings

# tests/unit/test_config.py -> unit, tests, backend, src, raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_settings_read_env_file_from_project_root_regardless_of_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    env_file = Path(Settings.model_config["env_file"])

    assert env_file.is_absolute()
    assert env_file == PROJECT_ROOT / ".env"


def test_settings_leen_datos_de_conexion_desde_el_entorno(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DB_HOST", "mariadb.interno")
    monkeypatch.setenv("DB_PORT", "3307")
    monkeypatch.setenv("DB_NAME", "medicalidad")
    monkeypatch.setenv("DB_USER", "lectura")
    monkeypatch.setenv("DB_PASSWORD", "secreto-de-prueba")

    settings = Settings(_env_file=None)

    assert settings.db_host == "mariadb.interno"
    assert settings.db_port == 3307
    assert settings.db_name == "medicalidad"
    assert settings.db_user == "lectura"
    assert settings.db_password.get_secret_value() == "secreto-de-prueba"


def test_settings_default_to_local_ollama_and_llama32(monkeypatch: pytest.MonkeyPatch) -> None:
    # Sin .env ni variables de entorno: solo los valores por defecto.
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.llm_model == "llama3.2:3b"
