import bearing_monitor
from bearing_monitor import config


def test_package_exposes_version():
    assert bearing_monitor.__version__ == "0.1.0"


def test_project_root_points_at_repository():
    assert (config.PROJECT_ROOT / "pyproject.toml").is_file()


def test_data_and_model_dirs_live_inside_project():
    for path in (config.RAW_DATA_DIR, config.PROCESSED_DATA_DIR, config.MODELS_DIR):
        assert path.is_relative_to(config.PROJECT_ROOT)
