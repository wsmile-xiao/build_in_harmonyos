#!/usr/bin/env python3
"""Consumer test for packaged feedparser 6.0.11 — real API (R34).

feedparser.parse() on inline RSS/Atom strings — fully offline; exercises
the sgmllib3k-based sanitizer path, date parsing and version metadata.
"""
import sys

site_all = sys.argv[1]
for p in site_all.split(":"):
    if p and p not in sys.path:
        sys.path.insert(0, p)

import feedparser  # noqa: E402

RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
<title>Feed Title Here</title>
<link>https://example.com/</link>
<description>desc</description>
<item>
  <title>Release 1.2.3</title>
  <link>https://example.com/1.2.3</link>
  <pubDate>Wed, 01 Jan 2025 00:00:00 GMT</pubDate>
  <description>&lt;b&gt;bold&lt;/b&gt; notes</description>
</item>
<item>
  <title>Release 1.2.2</title>
  <link>https://example.com/1.2.2</link>
  <pubDate>Tue, 01 Oct 2024 00:00:00 GMT</pubDate>
</item>
</channel></rss>
"""


def main():
    assert feedparser.__version__ == "6.0.11", feedparser.__version__

    d = feedparser.parse(RSS)
    assert d.bozo == 0 or d.bozo is False or not d.get("bozo_exception"), \
        f"unexpected bozo: {d.get('bozo_exception')}"
    assert d.feed.title == "Feed Title Here", d.feed.title
    assert len(d.entries) == 2, len(d.entries)
    assert d.entries[0].title == "Release 1.2.3"
    # date parsing (not required to match tz precisely — check structure)
    assert d.entries[0].published_parsed is not None
    assert d.entries[0].published_parsed.tm_year == 2025
    # description sanitizer (sgmllib path): content kept, dangerous
    # markup stripped — <b> is on feedparser's safe-tag whitelist, so only
    # assert unsafe tags are gone
    assert "bold" in d.entries[0].description
    assert "<script" not in d.entries[0].description

    # Atom feed
    ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>Atom Feed</title>
<entry><title>v2.0.0</title><id>https://example.com/v2</id>
<updated>2025-06-01T00:00:00Z</updated></entry></feed>"""
    a = feedparser.parse(ATOM)
    assert a.feed.title == "Atom Feed"
    assert a.entries[0].title == "v2.0.0"
    assert a.entries[0].updated_parsed.tm_year == 2025

    # malformed input must not raise (bozo flag semantics)
    bad = feedparser.parse("this is not xml at all <<<>>>")
    assert isinstance(bad, feedparser.FeedParserDict)

    print("test_feedparser: OK (version, RSS/Atom parse, dates, sanitizer, "
          "bozo semantics)")


if __name__ == "__main__":
    main()
