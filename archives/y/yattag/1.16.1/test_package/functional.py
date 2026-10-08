"""Exercise yattag through the Conan package runtime environment."""

import os
import sys
from pathlib import Path


def main():
    package = Path(sys.argv[1]).resolve()
    import yattag
    from yattag import Doc

    imported = Path(yattag.__file__).resolve()
    assert os.path.commonpath([str(imported), str(package)]) == str(package)
    assert yattag.__version__ == "1.16.1"

    doc, tag, text = Doc().tagtext()
    with tag("p", klass="greeting"):
        text("Hello <OpenHarmony> & yattag")
    assert doc.getvalue() == (
        '<p class="greeting">Hello &lt;OpenHarmony&gt; &amp; yattag</p>')
    print("PASS packaged import, version, and HTML escaping")


if __name__ == "__main__":
    main()
