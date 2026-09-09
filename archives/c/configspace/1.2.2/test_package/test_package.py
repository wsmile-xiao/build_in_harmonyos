import os
from pathlib import Path


EXPECTED_EXTERNAL_MODULES = {
    "more_itertools",
    "numpy",
    "pyparsing",
    "scipy",
    "typing_extensions",
}

expected_site = Path(os.environ["CONFIGSPACE_EXPECTED_SITE"]).resolve()
assert (expected_site / ".configspace-conan-package").is_file()

try:
    import scipy.stats._distn_infrastructure as _distn
except ModuleNotFoundError as exc:
    if exc.name not in EXPECTED_EXTERNAL_MODULES:
        raise
    print(f"SKIP ConfigSpace API smoke: missing runtime dependency {exc.name}")
    raise SystemExit(0)
else:
    # Older SciPy releases omit this alias although ConfigSpace uses it only
    # for annotations in the distribution module.
    if not hasattr(_distn, "rv_continuous_frozen"):
        _distn.rv_continuous_frozen = object

try:
    import ConfigSpace as CS
except ModuleNotFoundError as exc:
    if exc.name not in EXPECTED_EXTERNAL_MODULES:
        raise
    print(f"SKIP ConfigSpace API smoke: missing runtime dependency {exc.name}")
    raise SystemExit(0)

assert Path(CS.__file__).resolve().is_relative_to(expected_site)
space = CS.ConfigurationSpace()
assert len(space.get_hyperparameters()) == 0
print("ConfigSpace API smoke test passed")
