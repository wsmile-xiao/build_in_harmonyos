import os
import shutil
import subprocess
import sys


def find_perl():
    found = shutil.which("perl")
    if found:
        return found
    for candidate in ("/storage/Users/currentUser/usr/local/bin/perl",
                      "/data/service/hnp/bin/perl", "/usr/bin/perl"):
        if os.path.isfile(candidate):
            return candidate
    return None


def main():
    package = sys.argv[1]
    perl5 = os.path.join(package, "lib", "perl5")
    perl = find_perl()
    if not os.path.isdir(perl5) or not perl:
        print("FAIL: packaged modules or OHOS perl runtime is missing",
              file=sys.stderr)
        return 1

    program = (
        "use strict; use Debconf::Priority qw(priority_valid priority_list); "
        "my @got = priority_list(); "
        "die 'priority order mismatch' unless join(',', @got) eq "
        "'low,medium,high,critical'; "
        "die 'low priority rejected' unless priority_valid('low'); "
        "die 'medium priority rejected' unless priority_valid('medium'); "
        "die 'high priority rejected' unless priority_valid('high'); "
        "die 'critical priority rejected' unless priority_valid('critical'); "
        "die 'invalid priority accepted' if priority_valid('urgent'); "
        "print 'Debconf::Priority API OK';"
    )
    result = subprocess.run([perl, f"-I{perl5}", "-e", program],
                            capture_output=True, text=True)
    if result.returncode:
        print(f"FAIL: module API rc={result.returncode}: "
              f"{result.stderr.strip()[:300]}", file=sys.stderr)
        return 1
    print(result.stdout.strip())

    escape = os.path.join(package, "bin", "debconf-escape")
    escaped = subprocess.run([perl, escape, "-e"], input="a\nb",
                             capture_output=True, text=True)
    if escaped.returncode or escaped.stdout != "a\\nb":
        print(f"FAIL: debconf-escape -e output mismatch: "
              f"{escaped.stdout!r}", file=sys.stderr)
        return 1
    unescaped = subprocess.run([perl, escape, "-u"], input=escaped.stdout,
                               capture_output=True, text=True)
    if unescaped.returncode or unescaped.stdout != "a\nb":
        print(f"FAIL: debconf-escape -u output mismatch: "
              f"{unescaped.stdout!r}", file=sys.stderr)
        return 1
    print("debconf-escape -e/-u round-trip OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
