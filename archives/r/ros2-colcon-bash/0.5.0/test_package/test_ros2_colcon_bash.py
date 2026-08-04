import importlib.metadata
import importlib.resources
import py_compile
import sys
from pathlib import Path

import colcon_bash


package_folder = Path(sys.argv[1])
share = package_folder / "share" / "ros2-colcon-bash"
upstream_test = share / "test"

dist = importlib.metadata.distribution("colcon-bash")
assert dist.version == "0.5.0", dist.version

templates = importlib.resources.files(colcon_bash).joinpath("shell", "template")
for name in [
    "hook_set_value.bash.em",
    "package.bash.em",
    "prefix.bash.em",
    "prefix_chain.bash.em",
]:
    path = templates.joinpath(name)
    assert path.is_file(), name

for name in [
    "test_copyright_license.py",
    "test_flake8.py",
    "test_spell_check.py",
    "spell_check.words",
]:
    path = upstream_test / name
    assert path.is_file(), name

setup_cfg = share / "setup.cfg"
setup_text = setup_cfg.read_text(encoding="utf-8")
for token in ("flake8>=3.6.0", "pytest", "scspell3k>=2.2", "colcon-core>=0.12.0"):
    assert token in setup_text, token


def check_copyright_license(paths):
    missing = []
    for path in paths:
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if child.name.startswith("."):
                    continue
                if child.name.endswith(".py") or child.is_dir():
                    missing.extend(check_copyright_license([child]))
        elif path.is_file():
            content = path.read_text(encoding="utf-8")
            if not content:
                continue
            lines = content.splitlines()
            has_copyright = any(line.startswith("# Copyright") for line in lines)
            has_license = "# Licensed under the Apache License, Version 2.0" in lines
            if not has_copyright or not has_license:
                missing.append(path)
    return missing


site_packages = package_folder / "lib" / "python3" / "site-packages"
copyright_missing = check_copyright_license([
    site_packages / "colcon_bash",
    upstream_test / "test_copyright_license.py",
    upstream_test / "test_flake8.py",
    upstream_test / "test_spell_check.py",
])
assert not copyright_missing, [str(path) for path in copyright_missing]

python_files = list((site_packages / "colcon_bash").glob("**/*.py")) + list(upstream_test.glob("test_*.py"))
for py_file in python_files:
    py_compile.compile(str(py_file), doraise=True)

known_words = (upstream_test / "spell_check.words").read_text(encoding="utf-8").splitlines()
assert known_words == sorted(known_words), "upstream spell_check.words must be ordered"
assert len(known_words) == len(set(known_words)), "upstream spell_check.words must not contain duplicates"

spell_check_text = (upstream_test / "test_spell_check.py").read_text(encoding="utf-8")
for token in ("Report", "spell_check", "unknown_words", "found_known_words"):
    assert token in spell_check_text, token

flake8_text = (upstream_test / "test_flake8.py").read_text(encoding="utf-8")
for token in ("get_style_guide", "extend_ignore", "report.total_errors"):
    assert token in flake8_text, token

print("ros2-colcon-bash upstream tests and packaged resources verified")
