# Pure-python shim for the `gi` (PyGObject) package.
# Only purpose: let build-aux/gen_locations_variant.py from
# gweather-locations run on hosts where PyGObject is not installed.
# Implements exactly the GLib.Variant API surface used by that script.
from . import repository  # noqa: F401  (make 'gi.repository' importable)
