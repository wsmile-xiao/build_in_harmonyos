"""Exercise a packaged yattag document through the OHOS filesystem."""

import os
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.current = None
        self.heading = ""
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "li"):
            self.current = tag

    def handle_data(self, data):
        if self.current == "h1":
            self.heading += data
        elif self.current == "li":
            self.items.append(data)

    def handle_endtag(self, tag):
        if tag == self.current:
            self.current = None


def main():
    package = Path(sys.argv[1]).resolve()
    workspace = Path(sys.argv[2]).resolve()
    import yattag
    from yattag import Doc

    imported = Path(yattag.__file__).resolve()
    if os.path.commonpath([str(imported), str(package)]) != str(package):
        raise AssertionError("consumer did not import the Conan package")

    names = ["yattag", "演示 & 安全"]
    doc, tag, text = Doc().tagtext()
    with tag("html", lang="zh-CN"):
        with tag("body"):
            with tag("h1"):
                text("鸿蒙 PC 软件状态")
            with tag("ul", id="packages"):
                for name in names:
                    with tag("li"):
                        text(name)
    markup = doc.getvalue()

    with tempfile.TemporaryDirectory(prefix="yattag-ohos-", dir=workspace) as directory:
        output = Path(directory) / "status.html"
        output.write_text(markup, encoding="utf-8")
        persisted = output.read_text(encoding="utf-8")

    if persisted != markup:
        raise AssertionError("generated page did not round-trip through the filesystem")
    if '<html lang="zh-CN">' not in persisted or "演示 &amp; 安全" not in persisted:
        raise AssertionError("HTML language or escaping is wrong")

    parser = PageParser()
    parser.feed(persisted)
    if parser.heading != "鸿蒙 PC 软件状态" or parser.items != names:
        raise AssertionError("saved page does not contain the expected content")
    print("PASS packaged HTML generation, UTF-8 file round-trip, and parsed content")


if __name__ == "__main__":
    main()
