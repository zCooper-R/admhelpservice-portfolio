import os


SETTINGS_BY_ENVIRONMENT = {
    "PORTFOLIO": "config.settings.portfolio",
    "LOCAL": "config.settings.portfolio",
}


def resolve_settings_module(default="config.settings.portfolio"):
    """Return an explicitly configured settings module or the safe portfolio one."""
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
    if settings_module:
        return settings_module

    execution_environment = os.environ.get("DJANGO_EXECUTION_ENVIRONMENT", "PORTFOLIO")
    return SETTINGS_BY_ENVIRONMENT.get(execution_environment, default)
