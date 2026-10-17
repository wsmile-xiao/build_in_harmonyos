"""Exercise the packaged import and a dependency-injection consumer."""

import os
import sys
from pathlib import Path


def main():
    package = Path(sys.argv[1]).resolve()
    import in_n_out as ino

    imported = Path(ino.__file__).resolve()
    module_root = (package / "lib" / "python").resolve()
    assert os.path.commonpath([str(imported), str(module_root)]) == str(module_root)
    assert (module_root / "in_n_out" / "py.typed").is_file()
    assert ino.__version__ == "0.2.1"
    assert (module_root / "in_n_out-0.2.1.dist-info" / "METADATA").is_file()
    assert (module_root / "in_n_out-0.2.1.dist-info" / "licenses" / "LICENSE").is_file()
    assert (package / "licenses" / "LICENSE").is_file()
    assert not (module_root / "in_n_out" / "tests").exists()

    @ino.inject
    def combine(number: int, label: str) -> str:
        return f"{label}:{number}"

    with ino.register(providers=[(lambda: 7, int), (lambda: "item", str)]):
        assert combine() == "item:7"

    print("PASS packaged import and injection consumer")


if __name__ == "__main__":
    main()
