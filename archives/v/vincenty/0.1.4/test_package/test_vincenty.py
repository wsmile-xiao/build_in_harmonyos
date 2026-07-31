#!/usr/bin/env python3
"""Deterministic consumer checks for the packaged vincenty public API."""

import math
from pathlib import Path

import vincenty as vincenty_module
from vincenty import vincenty, vincenty_inverse


checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


module_path = Path(vincenty_module.__file__).resolve().as_posix()
check(
    module_path.endswith("/lib/python/site-packages/vincenty/__init__.py"),
    f"module was not loaded from the packaged artifact: {module_path}",
)
check(vincenty is vincenty_inverse, "public alias mismatch")
check(vincenty((0.0, 0.0), (0.0, 0.0)) == 0.0, "coincident points failed")
check(
    vincenty((0.0, 0.0), (0.0, 1.0)) == 111.319491,
    "equatorial longitude distance mismatch",
)
check(
    vincenty((0.0, 0.0), (1.0, 0.0)) == 110.574389,
    "meridional latitude distance mismatch",
)
check(
    vincenty((0.0, 0.0), (0.5, 179.5)) == 19936.288579,
    "slow-convergence result mismatch",
)
check(
    vincenty((0.0, 0.0), (0.5, 179.7)) is None,
    "non-convergent case should return None",
)

boston = (42.3541165, -71.0693514)
new_york = (40.7791472, -73.9680804)
kilometres = vincenty(boston, new_york)
miles = vincenty(boston, new_york, miles=True)

check(kilometres == 298.396057, "Boston-New York kilometre result mismatch")
check(miles == 185.414657, "Boston-New York mile result mismatch")
check(
    vincenty(new_york, boston) == kilometres,
    "inverse distance should be symmetric",
)
check(
    math.isclose(
        miles,
        kilometres * vincenty_module.MILES_PER_KILOMETER,
        abs_tol=1e-6,
    ),
    "mile conversion mismatch",
)
check(
    vincenty_module.MILES_PER_KILOMETER == 0.621371,
    "mile conversion constant mismatch",
)
check(vincenty_module.MAX_ITERATIONS == 200, "iteration limit mismatch")
check(
    vincenty_module.CONVERGENCE_THRESHOLD == 1e-12,
    "convergence threshold mismatch",
)

print(
    f"PASS: vincenty packaged API consumer test "
    f"({checks}/14 assertions, module={module_path})"
)
