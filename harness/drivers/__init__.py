from ..profile import GameProfile


def create(profile: GameProfile):
    """Return (eyes, hands, extras) for the profile's driver. extras may be None."""
    if profile.driver == "mgba":
        from .mgba import MGBADriver

        d = MGBADriver(**profile.driver_opts)
        return d, d, d
    raise ValueError(f"unknown driver {profile.driver!r}")
