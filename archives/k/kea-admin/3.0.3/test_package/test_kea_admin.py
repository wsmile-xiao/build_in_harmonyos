#!/usr/bin/env python3
"""Consumer test for the kea-admin 3.0.3 Conan package (HarmonyOS PC).

Runs against the packaged tree only: ``<package>/bin/kea-admin`` is started
through ``sh`` (the HarmonyOS PC kernel refuses execve() of shebang scripts),
the relocation of ``<package>/share/kea/scripts`` is exercised end to end, and
the mysql/pgsql paths are driven with a compiled silent stand-in for the
database clients (the platform ships no mysql/psql binaries).

Usage: python3 test_kea_admin.py <package_folder>

Every check prints one TEST PASS/TEST FAIL line; the script exits 1 if any
check failed.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

PACKAGE = None
PASSED = 0
FAILED = 0
FAILURES = []

# The HarmonyOS PC libc resolves executables by absolute path only: a bare
# "sh" passed to subprocess.run() fails with ENOENT no matter what PATH says
# (posix_spawn does not search PATH on this platform).  Resolve the
# interpreter once, up front; absolute paths work on the device and on CI.
SH = shutil.which("sh") or "/bin/sh"

MOCK_SOURCE = r"""
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    const char *log = getenv("KEA_ADMIN_MOCK_LOG");
    if (log) {
        FILE *f = fopen(log, "a");
        if (f) {
            int i;
            long total = 0;
            char buf[4096];
            size_t n;
            for (i = 1; i < argc; i++) {
                fprintf(f, "ARG %s\n", argv[i]);
            }
            while ((n = fread(buf, 1, sizeof(buf), stdin)) > 0) {
                total += (long) n;
            }
            fprintf(f, "STDIN_BYTES %ld\n", total);
            fclose(f);
        }
    }
    return 0;
}
"""


def check(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print("TEST PASS: %s" % name)
    else:
        FAILED += 1
        FAILURES.append(name)
        print("TEST FAIL: %s%s" % (name, (": " + detail) if detail else ""))


def run(args, env=None, timeout=60, stdin=None):
    """Run a command with stdin always closed unless data is given.

    The CI worker's inherited stdin is a pipe that never reaches EOF; leaving
    it inherited once hung the kea-shell consumer test.
    """
    kw = {}
    if stdin is None:
        kw["stdin"] = subprocess.DEVNULL
    else:
        kw["input"] = stdin
    return subprocess.run(args, capture_output=True, text=True, env=env,
                          timeout=timeout, **kw)


def kea_admin(args, env=None, timeout=60):
    """<sh> <package>/bin/kea-admin ... -- the only supported invocation form."""
    return run([SH, os.path.join(PACKAGE, "bin", "kea-admin")] + args,
               env=env, timeout=timeout)


def count_lines(text, needle):
    return sum(1 for line in text.splitlines() if needle in line)


def test_inventory():
    bin_ka = os.path.join(PACKAGE, "bin", "kea-admin")
    check("inventory/bin_kea_admin_exists", os.path.isfile(bin_ka))
    if os.path.isfile(bin_ka):
        with open(bin_ka, "rb") as f:
            first = f.read(2)
        check("inventory/bin_kea_admin_shebang", first == b"#!",
              "first bytes: %r" % first)
        check("inventory/bin_kea_admin_execbit", os.access(bin_ka, os.X_OK))
    utils = os.path.join(PACKAGE, "share", "kea", "scripts", "admin-utils.sh")
    check("inventory/admin_utils_sh", os.path.isfile(utils))
    mysql_dir = os.path.join(PACKAGE, "share", "kea", "scripts", "mysql")
    pgsql_dir = os.path.join(PACKAGE, "share", "kea", "scripts", "pgsql")
    if os.path.isdir(mysql_dir):
        ups = [n for n in os.listdir(mysql_dir)
               if n.startswith("upgrade_") and n.endswith(".sh")]
        check("inventory/mysql_upgrade_count", len(ups) == 40,
              "expected 40, found %d" % len(ups))
        base = all(os.path.isfile(os.path.join(mysql_dir, n)) for n in
                   ("dhcpdb_create.mysql", "dhcpdb_drop.mysql", "wipe_data.sh"))
        check("inventory/mysql_base_scripts", base)
    else:
        check("inventory/mysql_upgrade_count", False, "mysql dir missing")
    if os.path.isdir(pgsql_dir):
        ups = [n for n in os.listdir(pgsql_dir)
               if n.startswith("upgrade_") and n.endswith(".sh")]
        check("inventory/pgsql_upgrade_count", len(ups) == 34,
              "expected 34, found %d" % len(ups))
        base = all(os.path.isfile(os.path.join(pgsql_dir, n)) for n in
                   ("dhcpdb_create.pgsql", "dhcpdb_drop.pgsql", "wipe_data.sh"))
        check("inventory/pgsql_base_scripts", base)
    else:
        check("inventory/pgsql_upgrade_count", False, "pgsql dir missing")
    copying = os.path.join(PACKAGE, "licenses", "COPYING")
    check("inventory/copying", os.path.isfile(copying) and os.path.getsize(copying) > 0)


def test_relocation():
    with open(os.path.join(PACKAGE, "bin", "kea-admin"), "r", errors="replace") as f:
        text = f.read()
    check("relocation/no_unexpanded_datarootdir", "@datarootdir@" not in text)
    # A baked configure-time prefix would read admin_utils="/share/kea/..."
    # (quoted, absolute); the relocated form resolves <root> at run time.
    check("relocation/no_absolute_share_kea",
          re.search(r"""["']/share/kea""", text) is None)
    check("relocation/package_root_self_location",
          'admin_utils="${package_root}/share/kea/scripts/admin-utils.sh"' in text)
    check("relocation/sh_wrapped_upgrade_calls",
          'sh "${script}" -N -B' in text and
          'sh "${script}" --set ON_ERROR_STOP=1' in text)
    utils = os.path.join(PACKAGE, "share", "kea", "scripts", "admin-utils.sh")
    r = run([SH, "-c", '. "%s"; printf "%%s" "${db_user}"' % utils])
    check("relocation/admin_utils_sourceable",
          r.returncode == 0 and r.stdout == "keatest",
          "rc=%d out=%r err=%r" % (r.returncode, r.stdout[:80], r.stderr[:80]))


def test_version_and_usage():
    r = kea_admin(["-v"])
    check("version/short", r.returncode == 0 and r.stdout == "3.0.3\n",
          "rc=%d out=%r" % (r.returncode, r.stdout))
    r = kea_admin(["--version"])
    check("version/long", r.returncode == 0 and r.stdout == "3.0.3\n",
          "rc=%d out=%r" % (r.returncode, r.stdout))
    r = kea_admin(["-V"])
    check("version/extended",
          r.returncode == 0 and r.stdout.startswith("3.0.3") and "@" not in r.stdout,
          "rc=%d out=%r" % (r.returncode, r.stdout))
    r = kea_admin(["--help"])
    out = r.stdout
    check("usage/help_ok",
          r.returncode == 0 and "Usage: kea-admin COMMAND BACKEND [parameters]" in out
          and "kea-admin 3.0.3" in out,
          "rc=%d" % r.returncode)
    # The usage text prints the resolved default scripts directory: it must be
    # the packaged one, not an absolute /share/kea path.
    check("usage/help_default_dir",
          str(os.path.join(PACKAGE, "share", "kea", "scripts")) in out)


def test_errors():
    cases = [
        ("errors/missing_command", [], "ERROR/kea-admin: missing command"),
        ("errors/invalid_command", ["bogus"], "ERROR/kea-admin: invalid command: bogus"),
        ("errors/missing_backend", ["db-init"], "ERROR/kea-admin: missing backend"),
        ("errors/invalid_backend", ["db-init", "bogus"],
         "ERROR/kea-admin: invalid backend: bogus"),
        ("errors/memfile_init", ["db-init", "memfile"], "ERROR/kea-admin: NOT IMPLEMENTED"),
        ("errors/memfile_version", ["db-version", "memfile"],
         "ERROR/kea-admin: NOT IMPLEMENTED"),
        ("errors/memfile_upgrade", ["db-upgrade", "memfile"],
         "ERROR/kea-admin: NOT IMPLEMENTED"),
        ("errors/lease_dump_memfile", ["lease-dump", "memfile"],
         "ERROR/kea-admin: lease-dump is not supported for memfile"),
        ("errors/lease_upload_memfile", ["lease-upload", "memfile"],
         "ERROR/kea-admin: lease-upload is not supported for memfile"),
        ("errors/param_user", ["db-init", "mysql", "-u"],
         "ERROR/kea-admin: -u or --user requires a parameter"),
    ]
    for name, args, message in cases:
        r = kea_admin(args)
        check(name, r.returncode != 0 and message in r.stdout,
              "rc=%d out=%r" % (r.returncode, r.stdout[:120]))
    # A success path that needs no database: memfile statistics are simply
    # reported as not kept.
    r = kea_admin(["stats-recount", "memfile"])
    check("info/stats_recount_memfile",
          r.returncode == 0 and
          "INFO/kea-admin: memfile does not keep lease statistics" in r.stdout,
          "rc=%d out=%r" % (r.returncode, r.stdout[:120]))


def build_mock(mock_dir):
    """Compile the silent database-client stand-in; return True on success."""
    for compiler in (os.environ.get("CC"), "cc", "clang", "gcc"):
        if not compiler:
            continue
        path = shutil.which(compiler)
        if not path:
            continue
        src = os.path.join(mock_dir, "mockdb.c")
        out = os.path.join(mock_dir, "mysql")
        with open(src, "w") as f:
            f.write(MOCK_SOURCE)
        r = run([path, src, "-o", out], timeout=120)
        if r.returncode != 0:
            check("mock/stub_builds", False, "%s failed: %s" % (compiler, r.stderr[:200]))
            return False
        shutil.copy2(out, os.path.join(mock_dir, "psql"))
        r = run([out])
        check("mock/stub_builds", r.returncode == 0,
              "stub exit %d" % r.returncode)
        return r.returncode == 0
    check("mock/stub_builds", False, "no C compiler found on PATH")
    return False


def mock_env(mock_dir, log_path):
    env = dict(os.environ)
    env["PATH"] = mock_dir + os.pathsep + env.get("PATH", "")
    env["KEA_ADMIN_MOCK_LOG"] = log_path
    return env


def main():
    global PACKAGE
    if len(sys.argv) != 2:
        print("usage: test_kea_admin.py <package_folder>")
        return 2
    PACKAGE = os.path.abspath(sys.argv[1])
    print("kea-admin consumer test; package folder: %s" % PACKAGE)

    test_inventory()
    test_relocation()
    test_version_and_usage()
    test_errors()

    tmp = tempfile.mkdtemp(prefix="kea-admin-test-")
    try:
        mock_dir = os.path.join(tmp, "mockbin")
        os.makedirs(mock_dir)
        have_mock = build_mock(mock_dir)

        if have_mock:
            log = os.path.join(tmp, "mock.log")
            env = mock_env(mock_dir, log)

            # --- mysql db-init end to end -------------------------------
            open(log, "w").close()
            r = kea_admin(["db-init", "mysql", "-u", "root", "-p", "secret",
                           "-h", "127.0.0.1", "-n", "keatest"], env=env, timeout=120)
            out = r.stdout
            check("e2e/mysql_db_init_rc", r.returncode == 0,
                  "rc=%d out=%r err=%r" % (r.returncode, out[:200], r.stderr[:200]))
            check("e2e/mysql_db_init_banner",
                  "Checking if there is a database initialized already..." in out and
                  "Verifying create permissions for root" in out)
            schema = os.path.join(PACKAGE, "share", "kea", "scripts", "mysql",
                                  "dhcpdb_create.mysql")
            check("e2e/mysql_db_init_script",
                  "Initializing database using script %s" % schema in out)
            check("e2e/mysql_db_init_version_line",
                  "Schema version reported after initialization:" in out)
            with open(log, "r") as f:
                log_text = f.read()
            args_ok = all(("ARG " + a) in log_text for a in
                          ("--host=127.0.0.1", "--database=keatest",
                           "--user=root", "--password=secret"))
            check("e2e/mysql_db_init_argv", args_ok)
            # The schema file content must actually reach the client: the
            # stand-in logs the number of bytes it read from stdin.
            schema_size = os.path.getsize(schema)
            check("e2e/mysql_db_init_schema_bytes",
                  ("STDIN_BYTES %d" % schema_size) in log_text,
                  "no STDIN_BYTES %d in mock log" % schema_size)

            # --- mysql db-upgrade end to end ----------------------------
            open(log, "w").close()
            r = kea_admin(["db-upgrade", "mysql", "-u", "root", "-p", "secret",
                           "-h", "127.0.0.1", "-n", "keatest"], env=env, timeout=300)
            out = r.stdout
            check("e2e/mysql_db_upgrade_rc", r.returncode == 0,
                  "rc=%d out=%r err=%r" % (r.returncode, out[:200], r.stderr[:200]))
            check("e2e/mysql_db_upgrade_banner",
                  "Schema version reported before upgrade:" in out and
                  "Schema version reported after upgrade:" in out)
            processed = count_lines(out, "Processing ")
            check("e2e/mysql_db_upgrade_processed_40", processed == 40,
                  "expected 40 'Processing' lines, found %d" % processed)
            with open(log, "r") as f:
                log_text = f.read()
            queries = log_text.count("SELECT CONCAT_WS('.', version, minor) FROM schema_version")
            check("e2e/mysql_db_upgrade_query_flow", queries >= 40,
                  "expected >= 40 schema-version queries, found %d" % queries)

            # --- mysql db-version end to end ----------------------------
            open(log, "w").close()
            r = kea_admin(["db-version", "mysql", "-u", "root", "-p", "secret",
                           "-h", "127.0.0.1", "-n", "keatest"], env=env, timeout=60)
            check("e2e/mysql_db_version_rc",
                  r.returncode == 0 and r.stdout.strip() == "",
                  "rc=%d out=%r" % (r.returncode, r.stdout[:120]))

            # --- pgsql db-init end to end -------------------------------
            open(log, "w").close()
            r = kea_admin(["db-init", "pgsql", "-u", "root", "-p", "secret",
                           "-h", "127.0.0.1", "-n", "keatest"], env=env, timeout=120)
            out = r.stdout
            schema = os.path.join(PACKAGE, "share", "kea", "scripts", "pgsql",
                                  "dhcpdb_create.pgsql")
            check("e2e/pgsql_db_init",
                  r.returncode == 0 and
                  "Initializing database using script %s" % schema in out and
                  "Schema version reported after initialization:" in out,
                  "rc=%d out=%r err=%r" % (r.returncode, out[:200], r.stderr[:200]))

            # --- negative control: relocation breaks without admin-utils -
            copy_root = os.path.join(tmp, "pkgcopy")
            shutil.copytree(PACKAGE, copy_root, symlinks=True)
            copied_bin = os.path.join(copy_root, "bin", "kea-admin")
            copied_utils = os.path.join(copy_root, "share", "kea", "scripts",
                                        "admin-utils.sh")
            os.remove(copied_utils)
            r = run([SH, copied_bin, "-v"])
            check("neg/missing_admin_utils",
                  r.returncode != 0 and "admin-utils" in (r.stdout + r.stderr),
                  "rc=%d out=%r err=%r" % (r.returncode, r.stdout[:120], r.stderr[:120]))

            # --- negative control: init fails when the schema file is gone
            shutil.copy2(os.path.join(PACKAGE, "share", "kea", "scripts",
                                      "admin-utils.sh"), copied_utils)
            os.remove(os.path.join(copy_root, "share", "kea", "scripts", "mysql",
                                   "dhcpdb_create.mysql"))
            open(log, "w").close()
            r = run([SH, copied_bin, "db-init", "mysql", "-u", "root",
                     "-p", "secret", "-h", "127.0.0.1", "-n", "keatest"],
                    env=env, timeout=120)
            check("neg/missing_schema_script",
                  r.returncode == 1 and "Database initialization failed" in r.stdout,
                  "rc=%d out=%r" % (r.returncode, r.stdout[:200]))
        else:
            print("TEST SKIP-precondition: mock cases not run (no C compiler)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    total = PASSED + FAILED
    print("TEST SUMMARY: %d passed, %d failed, %d total" % (PASSED, FAILED, total))
    if FAILED:
        print("TEST FAILED: %s" % ", ".join(FAILURES))
        return 1
    print("TEST RESULT: SUCCESS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
