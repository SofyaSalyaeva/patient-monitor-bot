import os


def pytest_configure(config):
    """Set dummy env vars before any app code is imported."""
    defaults = {
        "BOT_TOKEN": "123:FAKE_TOKEN",
        "YANDEX_CLOUD_FOLDER": "fake_folder",
        "YANDEX_CLOUD_API_KEY": "fake_key",
    }
    for k, v in defaults.items():
        os.environ.setdefault(k, v)
