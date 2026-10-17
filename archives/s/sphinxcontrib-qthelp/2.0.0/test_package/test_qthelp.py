import sys
import tempfile
from pathlib import Path

from sphinx.application import Sphinx
import sphinxcontrib.qthelp as qthelp


def main():
    package_folder = Path(sys.argv[1]).resolve()
    python_root = (package_folder / "lib" / "python").resolve()
    module_path = Path(qthelp.__file__).resolve()

    assert module_path.is_relative_to(python_root), module_path
    assert qthelp.__version__ == "2.0.0"

    with tempfile.TemporaryDirectory(prefix="qthelp-test-") as temp_dir:
        root = Path(temp_dir)
        source = root / "source"
        output = root / "output"
        doctrees = root / "doctrees"
        source.mkdir()
        (source / "conf.py").write_text(
            "\n".join(
                (
                    "project = 'OHPCD'",
                    "version = '2.0'",
                    "extensions = ['sphinxcontrib.qthelp']",
                    "qthelp_basename = 'OHPCD'",
                    "qthelp_namespace = 'Org..Bad Space!'",
                    "master_doc = 'index'",
                )
            ),
            encoding="utf-8",
        )
        (source / "index.rst").write_text(
            "OHPCD QtHelp\n============\n\nPackaged extension test.\n",
            encoding="utf-8",
        )

        app = Sphinx(
            srcdir=source,
            confdir=source,
            outdir=output,
            doctreedir=doctrees,
            buildername="qthelp",
            freshenv=True,
            warningiserror=False,
        )
        app.build()

        qhp_path = output / "OHPCD.qhp"
        qhcp_path = output / "OHPCD.qhcp"
        assert app.statuscode == 0
        assert qhp_path.is_file()
        assert qhcp_path.is_file()

        qhp = qhp_path.read_text(encoding="utf-8")
        qhcp = qhcp_path.read_text(encoding="utf-8")
        assert "<namespace>org.badspace</namespace>" in qhp
        assert 'ref="index.html"' in qhp
        assert "qthelp://org.badspace/doc/index.html" in qhcp

    print("PASS: packaged QtHelp module, document build, and namespace sanitization")
    return 0


if __name__ == "__main__":
    sys.exit(main())
