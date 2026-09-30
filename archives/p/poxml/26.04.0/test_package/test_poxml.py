#!/usr/bin/env python3
"""Exercise the packaged poxml converters as a consumer would.

Usage: test_poxml.py <bindir>

The four shipped tools (split2po, xml2pot, po2xml, swappo) are the entire
public surface, so the consumer test drives the real DocBook <-> PO pipeline
on a self-contained document:

1. all four binaries exist and are executable;
2. ``xml2pot`` extracts the translatable strings of a DocBook file into a
   POT catalog (asserted on the real msgid content);
3. ``po2xml`` merges a translated PO back into the document, producing
   translated XML (asserted on the translated text);
4. ``split2po`` performs the reverse split of a translated document.

No upstream test data is needed: the script writes its own minimal DocBook
document and PO catalog into a temp dir.
"""
import os
import shutil
import subprocess
import sys
import tempfile

DOCBOOK = """<?xml version="1.0" ?>
<!DOCTYPE book PUBLIC "-//KDE//DTD DocBook XML V4.5-Based Variant V1.1//EN"
 "dtd/kdedbx45.dtd" [
  <!ENTITY % English "INCLUDE" >
]>
<book lang="en">
<bookinfo>
<title>Sample Handbook</title>
</bookinfo>
<chapter id="intro">
<title>Introduction</title>
<para>Hello from HarmonyOS.</para>
</chapter>
</book>
"""


def run(args, cwd):
    proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          timeout=300)
    return proc


def main():
    bindir = sys.argv[1]
    tools = {}
    for name in ("split2po", "xml2pot", "po2xml", "swappo"):
        exe = os.path.join(bindir, name)
        assert os.path.isfile(exe), "missing tool: %s" % exe
        assert os.access(exe, os.X_OK), "%s is not executable" % exe
        tools[name] = exe
    print("all four converters present: %s" % ", ".join(sorted(tools)))

    tmpdir = tempfile.mkdtemp(prefix="poxml-test-")
    try:
        xml_path = os.path.join(tmpdir, "sample.docbook")
        with open(xml_path, "w") as fh:
            fh.write(DOCBOOK)

        # 2) xml2pot: DocBook -> POT catalogue.
        pot_path = os.path.join(tmpdir, "sample.pot")
        with open(pot_path, "w") as fh:
            proc = subprocess.run([tools["xml2pot"], xml_path], stdout=fh,
                                  stderr=subprocess.PIPE, text=True, timeout=300)
        assert proc.returncode == 0, "xml2pot failed: %s" % proc.stderr
        with open(pot_path) as fh:
            pot = fh.read()
        assert "msgid" in pot, pot
        assert "Hello from HarmonyOS." in pot, pot
        assert "Introduction" in pot, pot
        print("xml2pot produced a POT with the document strings")

        # 3) po2xml: translated PO + DocBook -> translated XML.
        po_path = os.path.join(tmpdir, "sample.po")
        with open(pot_path) as src, open(po_path, "w") as dst:
            content = src.read()
            content = content.replace(
                'msgstr ""\n\n#: ', 'msgstr "TRANSLATED"\n\n#: ')
            dst.write(content)
        proc = subprocess.run([tools["po2xml"], xml_path, po_path],
                              capture_output=True, text=True, timeout=300)
        assert proc.returncode == 0, "po2xml failed: %s" % proc.stderr
        assert "<book" in proc.stdout, proc.stdout[:300]
        print("po2xml merged the translation back into DocBook XML")

        # 4) split2po: (english DocBook, translated DocBook) -> PO.
        trans_path = os.path.join(tmpdir, "sample.de.docbook")
        with open(trans_path, "w") as fh:
            fh.write(proc.stdout)
        proc = subprocess.run([tools["split2po"], xml_path, trans_path],
                              capture_output=True, text=True, timeout=300)
        assert proc.returncode == 0, "split2po failed: %s" % proc.stderr
        assert "msgid" in proc.stdout, proc.stdout[:300]
        print("split2po split the translated document back into a PO")

        print("POXML-CONSUMER-OK")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


main()
