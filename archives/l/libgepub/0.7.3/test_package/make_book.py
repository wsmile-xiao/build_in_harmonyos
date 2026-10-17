#!/usr/bin/env python3
"""Generate a minimal standard EPUB2 fixture for the libgepub consumer test.

Stdlib only (zipfile), fully offline. Layout:
  mimetype (stored, first entry, per EPUB spec)
  META-INF/container.xml -> OEBPS/content.opf
  OEBPS/content.opf (dc:title HMBS Test Book, dc:creator HMBS Team, 1 spine item)
  OEBPS/ch1.xhtml (one chapter containing the marker paragraph)
  OEBPS/toc.ncx (one navPoint labelled "Chapter 1")
Usage: python3 make_book.py <output.epub>
"""
import sys
import zipfile

TITLE = "HMBS Test Book"
AUTHOR = "HMBS Team"
PARAGRAPH = "Hello OHOS EPUB world."

CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

CONTENT_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package version="2.0" unique-identifier="bookid" xmlns="http://www.idpf.org/2007/opf">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="bookid">hmbs-test-001</dc:identifier>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="ch1"/>
  </spine>
</package>
""".format(title=TITLE, author=AUTHOR)

CH1_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title></head>
<body><h1>Chapter 1</h1><p>{para}</p></body>
</html>
""".format(para=PARAGRAPH)

TOC_NCX = """<?xml version="1.0" encoding="UTF-8"?>
<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
  <head><meta name="dtb:uid" content="hmbs-test-001"/></head>
  <docTitle><text>{title}</text></docTitle>
  <navMap>
    <navPoint id="ch1" playOrder="1">
      <navLabel><text>Chapter 1</text></navLabel>
      <content src="ch1.xhtml"/>
    </navPoint>
  </navMap>
</ncx>
""".format(title=TITLE)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "book.epub"
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", CONTAINER_XML, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/content.opf", CONTENT_OPF, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/ch1.xhtml", CH1_XHTML, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/toc.ncx", TOC_NCX, compress_type=zipfile.ZIP_DEFLATED)
    print("wrote %s (5 entries)" % out)


if __name__ == "__main__":
    main()
