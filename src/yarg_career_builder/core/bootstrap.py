"""Application bootstrap: seed data files and load consistent state."""

from .config import load_settings, load_sources, save_settings
from .career_io import seed_template, load_template, apply_startup_rule


def load_app_state(apply_startup=True):
    """Seed data files and return (settings, sources).

    With ``apply_startup=True`` (GUI), the career structure is resolved from the
    last-loaded career or the default template. With ``apply_startup=False``
    (CLI), career/tiers are only back-filled from the template if missing, so a
    fresh checkout still builds without manual setup.
    """
    settings = load_settings()
    sources = load_sources()
    seed_template()

    if apply_startup:
        settings = apply_startup_rule(settings)
        save_settings(settings)
    elif not settings.get("tiers"):
        result = load_template()
        settings["career"] = result["career"]
        settings["tiers"] = result["tiers"]
        save_settings(settings)

    return settings, sources
