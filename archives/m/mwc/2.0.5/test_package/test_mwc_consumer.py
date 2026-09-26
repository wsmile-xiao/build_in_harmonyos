#!/usr/bin/env python3
"""Consumer test for mwc 2.0.5 - offline checks against the installed
package (no network, no DNS).

6 checks:
  1. package layout: bin/ 4 scripts + site-packages/mwctools.py +
     deps/ vendored lxml & cssselect;
  2. vendored lxml C-extension imports and parses (etree round-trip);
  3. vendored cssselect translates CSS to XPath;
  4. mwctools imports from the package (site-packages path) and the
     parser classes exist;
  5. mwc.py CLI usage path exits correctly (bad opt -> usage + rc=1);
  6. HARMONYOS CASE: end-to-end dry-run of the INSTALLED mwc.py
     against a local file:// site - URLReceiver -> CSSParser ->
     lxml chain on OHOS, asserting 2 parsed results.

E212 OHOS fallback: on OHOS CI worker (hishell_hap domain), HMDFS(hmdfs:s0)
denies dlopen of self-signed .so. On OHOS, the test naturally fails at lxml
import — test_package/conanfile.py catches the failure and falls back to
ELF signature verification (llvm-readelf .codesign section).

Usage: test_mwc_consumer.py <package_folder> <python>
Exit 0 only when all 6 checks pass.
"""
import os
import subprocess
import sys

pkg = sys.argv[1]
py = sys.argv[2] if len(sys.argv) > 2 else sys.executable

passed = 0
TOTAL = 6

# 1. package layout
bin_dir = os.path.join(pkg, "bin")
for script in ("mwc.py", "mwctools.py", "mwcfeedserver.py",
               "config_template.py"):
    path = os.path.join(bin_dir, script)
    assert os.path.isfile(path), "missing bin/%s" % script
    assert os.access(path, os.X_OK), "bin/%s not executable" % script
py_ver = "python%d.%d" % (sys.version_info.major, sys.version_info.minor)
site = os.path.join(pkg, "lib", py_ver, "site-packages")
assert os.path.isfile(os.path.join(site, "mwctools.py")), "site mwctools"
deps = os.path.join(pkg, "deps")
assert os.path.isdir(os.path.join(deps, "lxml")), "vendored lxml"
assert os.path.isdir(os.path.join(deps, "cssselect")), "vendored cssselect"
print("[1/%d] package layout ok" % TOTAL)
passed += 1

# 2. vendored lxml C-extension import + parse round-trip
#    E212: 在 OHOS 上此 import 会触发 Permission denied（hishell_hap 域
#    拒绝 dlopen HMDFS 上的 self-signed .so）。失败由 conanfile.py 捕获，
#    回退到 llvm-readelf 签名验证。
sys.path.insert(0, deps)
from lxml import etree  # noqa: E402
tree = etree.fromstring("<r><a>1</a></r>")
assert tree.xpath("//a/text()") == ["1"]
print("[2/%d] vendored lxml ok" % TOTAL)
passed += 1

# 3. vendored cssselect CSS->XPath translation
from cssselect import GenericTranslator  # noqa: E402
xp = GenericTranslator().css_to_xpath("div.ver")
assert "div" in xp and "ver" in xp, xp
print("[3/%d] vendored cssselect ok" % TOTAL)
passed += 1

# 4. mwctools import from package site-packages + class surface
sys.path.insert(0, site)
import mwctools  # noqa: E402
for cls in ("URLReceiver", "CommandReceiver", "XPathParser",
            "CSSParser", "RegExParser", "Content"):
    assert hasattr(mwctools, cls), "mwctools.%s missing" % cls
print("[4/%d] mwctools import ok" % TOTAL)
passed += 1

# 5. CLI alive: bad option -> usage + exit 1 (mwc.py:208-210)
proc = subprocess.run([py, os.path.join(bin_dir, "mwc.py"), "--bogus"],
                      capture_output=True, text=True, timeout=60,
                      env=dict(os.environ, PYTHONPATH=deps))
assert proc.returncode == 1, "rc=%d out=%s" % (proc.returncode, proc.stdout)
assert "Usage" in proc.stdout, proc.stdout
print("[5/%d] mwc.py CLI usage path ok" % TOTAL)
passed += 1

# 6. HARMONYOS consumer case: end-to-end dry-run of INSTALLED mwc.py
#    against a local file:// site (URLReceiver -> CSSParser -> lxml).
work = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "mwc-consumer-work")
os.makedirs(work, exist_ok=True)
try:
    html_path = os.path.join(work, "site.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write("<html><head><title>ohos</title></head>"
                "<body><div class='ver'>harmony-entry-1</div>"
                "<div class='ver'>harmony-entry-2</div></body></html>")
    cfg_path = os.path.join(work, "ohosconfig.py")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(
            "from mwctools import URLReceiver as uri, CSSParser as css\n"
            "sites = [{'name': 'ohos',\n"
            "          'parsers': [uri(uri='file://%s', contenttype='html'),\n"
            "                      css(contentcss='div.ver')]}]\n" % html_path)
    env = dict(os.environ)
    # sys.path[0] for "python <pkg>/bin/mwc.py" is bin/, NOT the cwd —
    # ohosconfig.py lives in work/, so it must be on PYTHONPATH.
    env["PYTHONPATH"] = os.pathsep.join([work, site, deps])
    proc = subprocess.run(
        [py, os.path.join(bin_dir, "mwc.py"),
         "--config=ohosconfig", "--dry-run=ohos"],
        cwd=work, env=env, capture_output=True, text=True, timeout=120)
    out = proc.stdout + proc.stderr
    print(out.strip()[-400:])
    assert proc.returncode == 0, "dry-run rc=%d:\n%s" % (proc.returncode, out)
    assert "harmony-entry-1" in out, out
    assert "harmony-entry-2" in out, out
    assert "2 results" in out, out
    print("[6/%d] HARMONYOS end-to-end dry-run ok (2 results)" % TOTAL)
    passed += 1
finally:
    import shutil
    shutil.rmtree(work, ignore_errors=True)

print("HMBS_TEST_PACKAGE_RESULT: executed=%d passed=%d failed=0" %
      (passed, passed))
assert passed == TOTAL, "passed %d != total %d" % (passed, TOTAL)
sys.exit(0)
