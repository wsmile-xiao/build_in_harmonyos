#!/usr/bin/env python3
"""Test script for lxml 6.1.1 — verifies core XML functionality.

This test exercises the lxml C extension by:
1. Importing lxml.etree (loads the compiled C extension)
2. Parsing an XML document
3. Serializing back to string
4. Evaluating XPath expressions
5. Testing XSLT transformation
"""
import sys

def test_lxml():
    # Test 1: Import and version check
    from lxml import etree
    print(f"lxml version: {etree.LXML_VERSION}")
    print(f"libxml2 version: {etree.LIBXML_VERSION}")
    print(f"libxslt version: {etree.LIBXSLT_VERSION}")

    # Test 2: Parse XML
    xml = "<root><child id='1'>hello</child><child id='2'>world</child></root>"
    doc = etree.fromstring(xml.encode())
    assert doc.tag == "root"

    # Test 3: Serialize back
    result = etree.tostring(doc, encoding="unicode")
    assert "root" in result and "child" in result

    # Test 4: XPath evaluation
    texts = doc.xpath("//child/text()")
    assert texts == ["hello", "world"], f"XPath result mismatch: {texts}"

    # Test 5: XPath with attribute
    ids = doc.xpath("//child/@id")
    assert ids == ["1", "2"], f"XPath attr result mismatch: {ids}"

    # Test 6: XSLT transformation
    xslt = etree.XSLT(etree.fromstring(
        b'<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">'
        b'<xsl:template match="/"><count><xsl:value-of select="count(//child)"/></count></xsl:template>'
        b'</xsl:stylesheet>'
    ))
    transformed = xslt(doc)
    assert str(transformed).strip() == '<?xml version="1.0"?>\n<count>2</count>'

    # Test 7: Element creation
    root = etree.Element("newroot")
    child = etree.SubElement(root, "item")
    child.text = "test data"
    assert root[0].text == "test data"

    print("All tests passed!")
    return True


if __name__ == "__main__":
    success = test_lxml()
    if success:
        print("PASS: lxml test_package")
        sys.exit(0)
    else:
        print("FAIL: lxml test_package")
        sys.exit(1)
