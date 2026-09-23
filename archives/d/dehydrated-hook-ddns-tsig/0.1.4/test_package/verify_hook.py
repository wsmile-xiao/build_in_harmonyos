#!/usr/bin/env python3
"""verify_hook.py — L1 consumer-side test for the dehydrated-hook-ddns-tsig
package.

Validates:
  1. installed layout: bin/ entry script (executable, python3 shebang),
     vendored dnspython site-packages, sample conf
  2. the vendored dnspython wins over any system copy and the full API
     chain used by the hook imports on the device Python
  3. offline API behaviour the hook relies on: rcode value comparison,
     TSIG keyring + update message build, Resolver.nameservers assignment
  4. entry-script smoke: `--help` and a no-op hook callback (offline)

Usage: python3 verify_hook.py <package_folder>
Exit 0 on success, non-zero on failure.
"""
import os
import subprocess
import sys


def run_cmd(cmd):
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = proc.stdout.decode("utf-8", "replace")
    return proc.returncode, out


def main() -> int:
    if len(sys.argv) != 2:
        print("[FAIL] usage: verify_hook.py <package_folder>", file=sys.stderr)
        return 1

    pkg = os.path.abspath(sys.argv[1])
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    script = os.path.join(pkg, "bin", "dehydrated-hook-ddns-tsig")
    conf = os.path.join(
        pkg, "share", "doc", "dehydrated-hook-ddns-tsig",
        "dehydrated-hook-ddns-tsig.conf")

    failures = []

    # ── 1. installed layout ──────────────────────────────────────────────
    if not (os.path.isfile(script) and os.access(script, os.X_OK)):
        failures.append(f"entry script missing or not executable: {script}")
    if not os.path.isfile(os.path.join(site, "dns", "__init__.py")):
        failures.append(f"vendored dnspython not found under {site}")
    if not os.path.isfile(conf):
        failures.append(f"sample conf not installed: {conf}")
    if not failures:
        with open(script, "r", encoding="utf-8") as f:
            first_line = f.readline().rstrip("\n")
        if first_line != "#!/usr/bin/env python3":
            failures.append(f"unexpected shebang: {first_line!r}")

    # ── 2. vendored dnspython import chain ───────────────────────────────
    if not failures:
        sys.path.insert(0, site)
        import dns  # noqa: E402

        dns_file = os.path.abspath(dns.__file__)
        if not dns_file.startswith(site + os.sep):
            failures.append(
                f"dns imported from OUTSIDE the package under test: {dns_file}")
        if dns.version.version != "2.8.0":
            failures.append(
                f"unexpected vendored dnspython version: {dns.version.version}")
        try:
            import dns.exception  # noqa: F401,E402
            import dns.query  # noqa: F401,E402
            import dns.rcode  # noqa: F401,E402
            import dns.rdata  # noqa: F401,E402
            import dns.rdatatype  # noqa: F401,E402
            import dns.resolver  # noqa: F401,E402
            import dns.tsig  # noqa: F401,E402
            import dns.tsigkeyring  # noqa: F401,E402
            import dns.update  # noqa: F401,E402
        except Exception as exc:
            failures.append(f"dnspython import chain failed: {exc}")

        # ── 3. offline API behaviour ─────────────────────────────────────
        if not failures:
            # patch 0003: rcode must be compared by value; by design the
            # identity comparison against the IntEnum member does NOT hold
            # (response.rcode() returns a plain int).
            response_rcode = 0
            if response_rcode != dns.rcode.NOERROR:
                failures.append("rcode value comparison failed (== semantics)")
            if response_rcode is dns.rcode.NOERROR:
                failures.append("identity comparison unexpectedly passed")
            try:
                keyring = dns.tsigkeyring.from_text(
                    {"ci-test-key.": "c2VjcmV0"})
                update = dns.update.Update("example.com", keyring=keyring)
                update.add("_acme-challenge.example.com.", 300, "TXT", "token")
                wire = update.to_wire()
                if not wire or b"token" not in wire:
                    failures.append("TSIG-signed update message malformed")
            except Exception as exc:
                failures.append(f"TSIG keyring/update build failed: {exc}")
            try:
                resolver = dns.resolver.Resolver(configure=False)
                resolver.nameservers = ["127.0.0.1"]
            except Exception as exc:
                failures.append(
                    f"Resolver.nameservers list assignment failed: {exc}")

    # ── 4. entry-script smoke (offline) ──────────────────────────────────
    rc, out = run_cmd([sys.executable, script, "--help"])
    if rc != 0:
        failures.append(f"--help exited {rc}: {out[:200]}")
    # invalid_challenge is a no-op callback that takes a domain argument:
    # it exercises argparse -> configparser -> dispatch -> exit 0 with no
    # network (unlike deploy_challenge) and no upstream KeyError bug
    # (unlike request_failure/startup_hook/exit_hook).
    rc, out = run_cmd(
        [sys.executable, script, "invalid_challenge", "example.com",
         "dns-error-details"])
    if rc != 0:
        failures.append(f"invalid_challenge hook exited {rc}: {out[:200]}")

    if failures:
        for msg in failures:
            print(f"[FAIL] {msg}", file=sys.stderr)
        return 1

    print("[PASS] dehydrated-hook-ddns-tsig: layout + vendored dnspython "
          "import chain + offline API + hook smoke all OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
