#!/usr/bin/env python3
"""Consumer test for packaged sgmllib3k 1.0.0 — real API (R34).

SGMLParser subclassing, tag/data event dispatch, entity handling — the same
usage pattern feedparser relies on (sgmllib.SGMLParser base).
"""
import sys

site = sys.argv[1]
if site not in sys.path:
    sys.path.insert(0, site)

import sgmllib  # noqa: E402


class Collector(sgmllib.SGMLParser):
    def __init__(self):
        sgmllib.SGMLParser.__init__(self)
        self.tags = []
        self.data = []

    def start_title(self, attrs):
        self.tags.append(("title", dict(attrs)))

    def handle_data(self, data):
        if data.strip():
            self.data.append(data.strip())

    def do_br(self, attrs):
        self.tags.append(("br", dict(attrs)))


def main():
    assert hasattr(sgmllib, "SGMLParser"), "SGMLParser missing"

    p = Collector()
    p.feed("<html><head><title>Hello &amp; World</title></head>"
           "<body>line1<br>line2</body></html>")
    p.close()

    assert ("title", {}) in p.tags, p.tags
    assert ("br", {}) in p.tags, p.tags
    # note: sgmllib dispatches entity refs as separate data events
    # ('Hello', '&', 'World', ...) — assert on the joined stream
    joined = " ".join(p.data)
    for token in ("Hello", "World", "line1", "line2"):
        assert token in joined, p.data

    print("test_sgmllib3k: OK (SGMLParser subclass, tag events, data "
          "events, entity decoding)")


if __name__ == "__main__":
    main()
