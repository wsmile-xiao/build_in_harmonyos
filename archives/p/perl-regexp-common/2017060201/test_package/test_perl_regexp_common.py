#!/usr/bin/env python3
"""Adapted consumer validation for perl-regexp-common 2017060201.

Static inventory of the packaged Conan artifact: module layout, version
marker, packaged licenses, metadata, and the complete upstream t/ test set.

Usage: python test_perl_regexp_common.py <package_folder>
"""
import glob
import json
import os
import sys

package_folder = sys.argv[1]
perl_root = os.path.join(package_folder, "lib", "perl5")
share = os.path.join(package_folder, "share", "perl-regexp-common")


def installed(pattern):
    hits = glob.glob(os.path.join(perl_root, pattern), recursive=True)
    assert hits, f"missing packaged module: {pattern}"
    return hits[0]


assertions = 0
# Core module + all pattern-family submodules shipped by Regexp-Common 2017060201
# (lib/Regexp/Common/*.pm), plus a sample of the 18 Regexp::Common::URI schemes.
expected = [
    "Regexp/Common.pm",
    "Regexp/Common/balanced.pm",
    "Regexp/Common/CC.pm",
    "Regexp/Common/comment.pm",
    "Regexp/Common/delimited.pm",
    "Regexp/Common/lingua.pm",
    "Regexp/Common/list.pm",
    "Regexp/Common/net.pm",
    "Regexp/Common/number.pm",
    "Regexp/Common/profanity.pm",
    "Regexp/Common/SEN.pm",
    "Regexp/Common/URI.pm",
    "Regexp/Common/whitespace.pm",
    "Regexp/Common/zip.pm",
    "Regexp/Common/_support.pm",
    "Regexp/Common/URI/http.pm",
    "Regexp/Common/URI/ftp.pm",
    "Regexp/Common/URI/telnet.pm",
]
for rel in expected:
    installed("**/" + rel)
    assertions += 1

common_pm = open(installed("**/Regexp/Common.pm"), encoding="utf-8").read()
assert "$VERSION" in common_pm, "Regexp::Common version marker missing"
assertions += 1
assert "2017060201" in common_pm, "Regexp::Common version is not 2017060201"
assertions += 1

for lic in ("LICENSE", "COPYRIGHT", "COPYRIGHT.MIT"):
    assert os.path.isfile(os.path.join(package_folder, "licenses", lic)), \
        f"missing license file: {lic}"
    assertions += 1

# Complete upstream test inventory (73 .t files across t/ and 7 subdirs).
expected_t_top = {
    "Common.pm",
    "test___luhn.t",
    "test_balanced.t",
    "test_bases.t",
    "test_bases_sep.t",
    "test_comments.t",
    "test_curry.t",
    "test_i.t",
    "test_lingua_palindrome.t",
    "test_list.t",
    "test_no_import.t",
    "test_profanity.t",
    "test_sub.t",
    "test_sub_named.t",
    "test_ws.t",
}
observed_top = {
    os.path.basename(p) for p in glob.glob(os.path.join(share, "t", "*"))
    if os.path.isfile(p)
}
assert observed_top == expected_t_top, f"unexpected t/ top-level set: {sorted(observed_top)}"
assertions += 1

expected_subdirs = {
    "comment": 6,
    "delimited": 2,
    "net": 5,
    "number": 11,
    "SEN": 1,
    "URI": 14,
    "zip": 20,
}
total_sub = 0
for sub, count in expected_subdirs.items():
    observed = sorted(os.path.basename(p) for p in glob.glob(os.path.join(share, "t", sub, "*.t")))
    assert len(observed) == count, f"t/{sub}: expected {count} tests, found {len(observed)}"
    assertions += 1
    total_sub += len(observed)
assert total_sub + len([f for f in expected_t_top if f.endswith(".t")]) == 73, \
    "upstream test total is not 73"
assertions += 1

meta = json.load(open(os.path.join(share, "META.json"), encoding="utf-8"))
assert meta["version"] == "2017060201", f"META.json version is {meta['version']}"
assertions += 1
runtime_requires = meta["prereqs"]["runtime"]["requires"]
for module in ("vars", "strict", "warnings", "Config"):
    assert module in runtime_requires, f"META.json missing core runtime prerequisite {module}"
    assertions += 1
test_requires = meta["prereqs"]["test"]["requires"]
assert "Test::More" in test_requires, "META.json missing test prerequisite Test::More"
assertions += 1

print(f"perl-regexp-common packaging inventory OK ({assertions} assertions)")
