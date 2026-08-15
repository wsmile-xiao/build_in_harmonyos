#!/usr/bin/env python3
"""Run Zabbix upstream cmocka tests without the Perl tests_run.pl harness.

The upstream test harness (tests/tests_run.pl) requires Perl modules YAML::XS,
Path::Tiny and IPC::Run3 which are not available on HarmonyOS. This script
replicates its core logic using PyYAML:

  - recursively scan tests/ for ``*.yaml`` files (excluding ``*.inc.yaml``);
  - each ``<name>.yaml`` maps to a sibling executable ``<name>``;
  - each YAML document is one test case; feed it to the executable via stdin;
  - exit code 0 => passed, non-zero => failed, missing executable => skipped.

It prints a machine-friendly summary and exits non-zero if any test failed.
"""

import argparse
import os
import re
import subprocess
import sys

import yaml


_INT_NO_SEXAGESIMAL = re.compile(
    r"""^(?:[-]?0b[0-1_]+
        |[-]?0[0-7_]+
        |[-]?(?:0|[1-9][0-9_]*)
        |[-]?0x[0-9a-fA-F_]+)$""", re.X)

_FLOAT_NO_SEXAGESIMAL = re.compile(
    r"""^(?:[-]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?
        |\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?
        |[-]?\.(?:inf|Inf|INF)
        |\.(?:nan|NaN|NAN))$""", re.X)


class _NoTimestampLoader(yaml.SafeLoader):
    """SafeLoader matching libyaml's implicit-tag behavior.

    PyYAML resolves ``2010-01-01 12:00:00 +02:00`` to a datetime, ``12:00:00`` to
    a sexagesimal int (43200), ``+1`` to an int, and ``NULL``/``~``/empty to null.
    libyaml (used by the test binaries and by Perl's YAML::XS) keeps all of these
    as plain strings. Match libyaml so the re-dumped YAML is identical, while
    still resolving ordinary ints/bools/floats.
    """


_NoTimestampLoader.yaml_implicit_resolvers = {}
for _key, _mappings in yaml.SafeLoader.yaml_implicit_resolvers.items():
    _new_mappings = []
    for _tag, _regexp in _mappings:
        if _tag == "tag:yaml.org,2002:timestamp":
            continue
        if _tag == "tag:yaml.org,2002:null":
            # libyaml (used by the test binaries and by Perl's YAML::XS) does not
            # apply the null implicit tag to plain scalars; NULL/~/empty stay
            # plain strings. Match that so the re-dumped YAML is identical.
            continue
        if _tag == "tag:yaml.org,2002:int":
            _new_mappings.append((_tag, _INT_NO_SEXAGESIMAL))
            continue
        if _tag == "tag:yaml.org,2002:float":
            _new_mappings.append((_tag, _FLOAT_NO_SEXAGESIMAL))
            continue
        _new_mappings.append((_tag, _regexp))
    _NoTimestampLoader.yaml_implicit_resolvers[_key] = _new_mappings


def load_yaml_docs(yaml_path):
    """Load YAML documents, tolerating quirks YAML::XS accepts but PyYAML rejects:
    a tab inside a comment, and cross-document duplicate anchors (Zabbix test
    data reuses ``&buffer`` across documents; libyaml requires uniqueness within
    the whole stream, YAML::XS scopes anchors per document). Timestamps and
    sexagesimal scalars are kept as strings so the exact test input is preserved.
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        content = f.read()

    docs = []
    for chunk in re.split(r"^---[ \t]*$", content, flags=re.MULTILINE):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            doc = yaml.load(chunk, Loader=_NoTimestampLoader)
        except yaml.YAMLError:
            try:
                doc = yaml.safe_load(chunk)
            except yaml.YAMLError:
                doc = None
        if doc is not None:
            docs.append(doc)
    return docs


def count_cases(yaml_path):
    """Count the number of non-empty YAML documents in a test data file."""
    try:
        return len(load_yaml_docs(yaml_path))
    except Exception:
        return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tests_root", nargs="?", default="tests",
                        help="tests directory (default: tests)")
    parser.add_argument("--verbose", action="store_true",
                        help="print each failed case's output")
    args = parser.parse_args()

    if not os.path.isdir(args.tests_root):
        print("tests directory not found: %s" % args.tests_root)
        return 1

    yaml_files = []
    for dirpath, _dirnames, filenames in os.walk(args.tests_root):
        for fn in filenames:
            if fn.endswith(".yaml") and not fn.endswith(".inc.yaml"):
                yaml_files.append(os.path.join(dirpath, fn))
    yaml_files.sort()

    suites = 0
    total = 0
    passed = 0
    failed = 0
    skipped = 0
    errors = 0
    failures = []

    for yf in yaml_files:
        exe = os.path.splitext(yf)[0]
        if not (os.path.isfile(exe) and os.access(exe, os.X_OK)):
            # Executable not built (e.g. server-only library tests) => skipped.
            skipped += count_cases(yf)
            continue

        suites += 1
        try:
            docs = load_yaml_docs(yf)
        except Exception as exc:  # YAML parse error
            errors += 1
            failures.append((os.path.basename(yf), "YAML error: %s" % exc))
            continue

        for doc in docs:
            total += 1
            case_name = "N/A"
            if isinstance(doc, dict):
                case_name = str(doc.get("test case", "N/A"))
            payload = yaml.safe_dump(doc)

            try:
                proc = subprocess.run(
                    [os.path.join(".", os.path.basename(exe))],
                    input=payload.encode("utf-8"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=300,
                    cwd=os.path.dirname(exe),
                )
            except Exception as exc:
                errors += 1
                failures.append((case_name, "run error: %s" % exc))
                continue

            if proc.returncode == 0:
                passed += 1
            else:
                failed += 1
                out = proc.stdout.decode(errors="replace")[-400:]
                err = proc.stderr.decode(errors="replace")[-400:]
                failures.append((case_name, (out + err).strip() or "exit %d" % proc.returncode))

    rate = (100.0 * passed / total) if total else 0.0
    print("=" * 64)
    print("cmocka test summary")
    print("  suites (compiled): %d" % suites)
    print("  total cases:       %d" % total)
    print("  passed:            %d" % passed)
    print("  failed:            %d" % failed)
    print("  skipped:           %d" % skipped)
    print("  errors:            %d" % errors)
    print("  pass rate:         %.1f%%" % rate)
    print("=" * 64)

    if failures:
        print("\nFailures:")
        for name, detail in failures:
            print("  - %s" % name)
            if args.verbose and detail:
                for line in detail.splitlines():
                    print("      %s" % line)

    return 1 if (failed or errors) else 0


if __name__ == "__main__":
    sys.exit(main())
