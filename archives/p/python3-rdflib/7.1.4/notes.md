# python3-rdflib 7.1.4

## Source and build

The upstream release is a pure Python package. The recipe stages the rdflib
package into Conan's Python site-packages directory and bundles the exact
runtime versions required by its imports: `isodate/0.7.2` and
`pyparsing/3.2.3`.

The package is a Conan build requirement for `libzeitgeist/1.0.4`; it provides
the `rdflib` import used by Zeitgeist's `data/ontology2code` generator and
does not provide C/C++ headers or libraries.

## Consumer test

The Conan consumer check (`test_package/test_rdflib.py`) imports `rdflib`,
constructs a `Graph`, exercises a `Namespace` URI, and asserts the triple
count. It runs with `sys.executable` so it works wherever Conan's Python is
installed, and validates the packaged module plus its bundled runtime deps.

## Upstream suite on a HarmonyOS PC (2026-09-02)

The upstream pytest suite was executed on-device against the **packaged
artifact** (the Conan package's site-packages on `PYTHONPATH`, not the source
tree):

```
PYTHONPATH=<pkg>/lib/python3.12/site-packages \
python3 -m pytest test -m "not network" -q --basetemp=$HOME/tmp/... \
  --ignore=test/test_sparql/test_service.py \
  --deselect test/test_examples.py::test_example \
  --deselect test/test_graph/test_graph.py::test_guess_format_for_parse_http_text_plain
```

Result: **7488 passed, 0 failed**, 61 skipped (optional deps such as
berkeleydb), 330 xfailed, 36 xpassed, 23 deselected in 157 s.

Environment findings (all environment-level, no upstream code changes):

- The cmd-pkgs Python ships no system CA roots, so HTTPS fixtures fail with
  `CERTIFICATE_VERIFY_FAILED` until `SSL_CERT_FILE` points at a certifi
  bundle; this alone fixed 9 jsonld/infixowl cases.
- pip 24.3 forces PEP 517 isolated builds for the setup.py-only test plugins
  while `test_plugins` installs them with `--no-index`, which cannot fetch
  setuptools; pinning pip 24.0 (+ setuptools/wheel) restores the legacy
  build path and fixes the last 2 cases.
- pytest needs `pytest-cov` (for the `no_cover` fixture) and, on HMDFS, an
  explicit `--basetemp`: `/tmp` is read-only and the `pytest-of-<user>`
  ownership check does not hold on HMDFS stat results.
- The 23 deselected cases require external network endpoints (DBpedia SPARQL
  service, raw.githubusercontent.com, examples that run online); they pass in
  upstream CI with internet access.

The suite is not wired into the Conan build because the package intentionally
ships only the pure-Python runtime for a configure-time generator; the on-device
run above is recorded as the upstream-test evidence for this PR.
