#!/usr/bin/env python3
"""Consumer test for the installed platformdirs package."""

import os
import tempfile


def main() -> None:
    import platformdirs

    assert platformdirs.__version__ == "4.3.8"
    result = platformdirs.PlatformDirs(
        appname="AtomCodeTest", appauthor=False, version="1", ensure_exists=True
    )
    assert result.user_data_dir.endswith(os.path.join("AtomCodeTest", "1"))
    assert os.path.isdir(result.user_data_dir)
    assert str(result.user_config_path) == result.user_config_dir
    assert result.user_config_path.name == "1"
    with tempfile.TemporaryDirectory() as temporary:
        old_xdg_cache = os.environ.get("XDG_CACHE_HOME")
        os.environ["XDG_CACHE_HOME"] = temporary
        try:
            directory = platformdirs.user_cache_dir("platformdirs-test", appauthor=False)
            assert directory == os.path.join(temporary, "platformdirs-test")
        finally:
            if old_xdg_cache is None:
                os.environ.pop("XDG_CACHE_HOME", None)
            else:
                os.environ["XDG_CACHE_HOME"] = old_xdg_cache

    print("OK: platformdirs 4.3.8 API and ensure_exists behavior")


if __name__ == "__main__":
    main()
