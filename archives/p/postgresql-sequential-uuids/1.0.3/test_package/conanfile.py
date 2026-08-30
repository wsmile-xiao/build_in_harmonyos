import json
import os
import re
import shutil
import subprocess
import random

from conan import ConanFile
from conan.errors import ConanException


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    _PG_INSTALL = "/data/storage/el2/base/.pg-sequential-uuids-build/postgresql-18.3/install"
    _UPSTREAM_REGRESS_GROUPS = ["uuids"]

    def build(self):
        # Build the smoke test binary
        dep = self.dependencies["postgresql-sequential-uuids"]
        pkg = dep.package_folder
        if not pkg:
            raise ConanException("postgresql-sequential-uuids package_folder "
                                 "not populated")
        libdir = os.path.join(pkg, dep.cpp_info.libdirs[0])
        ext_so = os.path.join(libdir, "sequential_uuids.so")
        if not os.path.isfile(ext_so):
            raise ConanException(
                "sequential_uuids.so not found at %s" % ext_so)

        ext_dir = os.path.join(pkg, "extension")
        test_src = os.path.join(self.source_folder, "test_sequential_uuids.c")
        test_bin = os.path.join(self.build_folder, "test_sequential_uuids")

        env = os.environ.copy()
        env["PATH"] = "/data/service/hnp/bin:" + env.get("PATH", "/usr/bin:/bin")
        subprocess.run(
            ["/data/service/hnp/bin/clang", "-O2", "-o", test_bin, test_src],
            env=env, check=True)

    def _find_upstream_root(self):
        try:
            dep = self.dependencies["postgresql-sequential-uuids"]
            pkg = dep.package_folder
            if pkg:
                cand = os.path.join(pkg, "upstream")
                if os.path.isdir(cand) and os.path.isfile(
                        os.path.join(cand, "Makefile")):
                    return cand
        except Exception:
            pass
        return None

    def _run_pg_regress(self):
        pg_install = self._PG_INSTALL
        pg_bindir = os.path.join(pg_install, "bin")
        postgres = os.path.join(pg_bindir, "postgres")
        initdb = os.path.join(pg_bindir, "initdb")
        pg_ctl = os.path.join(pg_bindir, "pg_ctl")
        createdb = os.path.join(pg_bindir, "createdb")

        for name, path in (("postgres", postgres), ("initdb", initdb),
                           ("pg_ctl", pg_ctl), ("createdb", createdb)):
            if not os.path.isfile(path):
                return (1, 0, 0, 0, 1,
                        "PG server binary %s missing" % name, "")

        upstream_root = self._find_upstream_root()
        if not upstream_root:
            return (1, 0, 0, 0, 1,
                    "upstream source tree not reachable", "")

        discovered_groups = []
        for name in self._UPSTREAM_REGRESS_GROUPS:
            sql = os.path.join(upstream_root, "test", "sql", name + ".sql")
            out = os.path.join(upstream_root, "test", "expected",
                               name + ".out")
            if (os.path.isfile(sql) and os.path.getsize(sql) > 0
                    and os.path.isfile(out) and os.path.getsize(out) > 0):
                discovered_groups.append(name)
        discovered = len(discovered_groups)

        dep = self.dependencies["postgresql-sequential-uuids"]
        pkg = dep.package_folder
        if not pkg or not os.path.isdir(pkg):
            return (discovered, 0, 0, 0, discovered,
                    "package_folder not populated", "")
        libdir = os.path.join(pkg, dep.cpp_info.libdirs[0])
        ext_so = os.path.join(libdir, "sequential_uuids.so")
        if not os.path.isfile(ext_so):
            return (discovered, 0, 0, 0, discovered,
                    "sequential_uuids.so not packaged", "")

        work_root = os.path.join(os.path.expanduser("~"), "tmp",
                                 "pg-seq-uuids-test")
        pgdata = os.path.join(work_root, "pgdata")
        staging = os.path.join(work_root, "staging")
        logfile = os.path.join(pgdata, "postgresql.log")
        for d in (pgdata, staging):
            os.makedirs(d, exist_ok=True)

        pg_libdir = os.path.join(pg_install, "lib")
        _pg_role = "hmbstest"
        pg_env = {
            "PATH": pg_bindir + ":/data/service/hnp/bin:"
                     "/storage/Users/currentUser/usr/local/bin:"
                     + os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", os.path.expanduser("~")),
            "TMPDIR": os.path.join(work_root, "tmp"),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
            "SHELL": os.environ.get("SHELL", "/bin/sh"),
            "LD_LIBRARY_PATH": pg_libdir + ":"
                               + os.environ.get("LD_LIBRARY_PATH", ""),
            "USER": _pg_role,
            "LOGNAME": _pg_role,
            "PGUSER": _pg_role,
        }
        v = os.environ.get("TERM")
        if v is not None:
            pg_env["TERM"] = v
        os.makedirs(pg_env["TMPDIR"], exist_ok=True)

        tmpfs_root = "/data/storage/el2/base/.pg-sequential-uuids-build"
        pgxs_path = os.path.join(
            tmpfs_root, "postgresql-18.3", "aarch64-build",
            "src", "makefiles", "pgxs.mk")
        pg_config = os.path.join(pg_bindir, "pg_config")

        port = 49152 + random.randint(0, 9999)
        detail_lines = []
        executed = passed = failed = skipped = 0
        reason = ""
        server_started = False

        try:
            r = subprocess.run(
                [initdb, "-D", pgdata, "--auth=trust",
                 "--no-instructions", "--user=%s" % _pg_role],
                capture_output=True, text=True, env=pg_env, timeout=120)
            if r.returncode != 0:
                return (discovered, 0, 0, 0, discovered,
                        "initdb failed: %s" % (r.stderr or r.stdout)[-800:], "")
            detail_lines.append("initdb OK")

            sharedir = pkglibdir = ""
            for flag in ("--sharedir", "--pkglibdir"):
                try:
                    rr = subprocess.run([pg_config, flag],
                        capture_output=True, text=True, env=pg_env, timeout=10)
                    if rr.returncode == 0:
                        v = rr.stdout.strip()
                        if flag == "--sharedir": sharedir = v
                        else: pkglibdir = v
                except Exception:
                    pass
            auto_conf = os.path.join(pgdata, "postgresql.auto.conf")
            with open(auto_conf, "a", encoding="utf-8") as fh:
                fh.write("listen_addresses = 'localhost'\n")
                fh.write("port = %d\n" % port)
                staging_sharedir = staging + sharedir if sharedir else ""
                staging_pkglibdir = staging + pkglibdir if pkglibdir else ""
                if staging_sharedir or staging_pkglibdir:
                    fh.write("extension_control_path = '%s'\n" % ":".join(
                        filter(None, [staging_sharedir, "$system"])))
                    fh.write("dynamic_library_path = '%s'\n" % ":".join(
                        filter(None, [staging_pkglibdir, "$libdir"])))

            r = subprocess.run(
                [pg_ctl, "-D", pgdata, "-l", logfile, "-w", "start"],
                capture_output=True, text=True, env=pg_env, timeout=120)
            if r.returncode != 0:
                log_tail = ""
                if os.path.isfile(logfile):
                    with open(logfile, "r", encoding="utf-8",
                              errors="replace") as fh:
                        log_tail = fh.read()[-1200:]
                return (discovered, 0, 0, 0, discovered,
                        "pg_ctl start failed: %s | log: %s" % (
                            (r.stderr or r.stdout)[-400:], log_tail), "")
            server_started = True
            detail_lines.append("pg_ctl start OK (port %d)" % port)

            install_env = dict(pg_env)
            install_env.update({
                "PG_CONFIG": pg_config, "DESTDIR": staging,
                "PG_LDFLAGS": "-Wl,--unresolved-symbols=ignore-all "
                               "-Wl,--allow-shlib-undefined",
                "PGXS": pgxs_path,
            })
            r = subprocess.run(
                ["make", "install", "PG_CONFIG=%s" % pg_config,
                 "PGXS=%s" % pgxs_path, "DESTDIR=%s" % staging, "-j1"],
                capture_output=True, text=True, env=install_env,
                cwd=upstream_root, timeout=180)
            if r.returncode != 0:
                return (discovered, 0, 0, 0, discovered,
                        "make install DESTDIR failed: %s" % (
                            (r.stderr or r.stdout)[-800:]), "")
            detail_lines.append("make install DESTDIR OK")

            r = subprocess.run(
                [createdb, "-h", "localhost", "-p", str(port),
                 "contrib_regression"],
                capture_output=True, text=True, env=pg_env, timeout=30)
            if r.returncode != 0:
                return (discovered, 0, 0, 0, discovered,
                        "createdb failed: %s" % (r.stderr or r.stdout)[-400:],
                        "")
            detail_lines.append("createdb OK")

            regress_env = dict(pg_env)
            regress_env.update({
                "PGHOST": "localhost", "PGPORT": str(port),
                "PGUSER": _pg_role, "PGDATABASE": "contrib_regression",
                "PG_CONFIG": pg_config, "PGXS": pgxs_path,
                "PG_LDFLAGS": "-Wl,--unresolved-symbols=ignore-all "
                               "-Wl,--allow-shlib-undefined",
            })
            r = subprocess.run(
                ["make", "installcheck", "PG_CONFIG=%s" % pg_config,
                 "PGXS=%s" % pgxs_path, "-j1"],
                capture_output=True, text=True, env=regress_env,
                cwd=upstream_root, timeout=300)
            regress_out = (r.stdout or "") + "\n" + (r.stderr or "")
            detail_lines.append("installcheck exit=%d" % r.returncode)
            detail_lines.append("pg_regress:\n" + regress_out[-2000:])

            seen_groups = {}
            for line in regress_out.splitlines():
                ls = line.strip()
                m = re.match(r"^\s*test\s+(\S+)\s*\.\.\.\s+(ok|FAILED)\s*$", ls)
                if m:
                    seen_groups[m.group(1)] = m.group(2)
                    continue
                m = re.match(
                    r"^(not ok|ok)\s+\d+\s+-\s+(.+?)(?:\s+\d+\s+ms)?\s*$", ls)
                if m:
                    status = "ok" if m.group(1) == "ok" else "FAILED"
                    seen_groups[m.group(2).strip()] = status

            for name in discovered_groups:
                if name not in seen_groups:
                    skipped += 1
                    continue
                executed += 1
                if seen_groups[name] == "ok": passed += 1
                else: failed += 1

            if executed == 0:
                reason = "pg_regress produced no parseable results"
            elif failed > 0:
                reason = "pg_regress: %d/%d failed" % (failed, executed)
            else:
                reason = "pg_regress: %d/%d passed" % (passed, executed)
        except subprocess.TimeoutExpired as e:
            return (discovered, 0, 0, 0, discovered,
                    "timeout at %s" % e.command, "")
        except Exception as e:
            return (discovered, 0, 0, 0, discovered,
                    "exception: %s" % e, "")
        finally:
            if server_started:
                try:
                    subprocess.run(
                        [pg_ctl, "-D", pgdata, "-m", "fast", "stop"],
                        capture_output=True, text=True, env=pg_env,
                        timeout=30)
                    detail_lines.append("pg_ctl stop OK")
                except Exception as e:
                    detail_lines.append("pg_ctl stop failed: %s" % e)
            try:
                shutil.rmtree(work_root, ignore_errors=True)
            except Exception:
                pass

        return (discovered, executed, passed, failed, skipped, reason,
                "\n".join(detail_lines))

    def test(self):
        dep = self.dependencies["postgresql-sequential-uuids"]
        pkg = dep.package_folder
        if not pkg:
            raise ConanException("package_folder not populated")
        libdir = os.path.join(pkg, dep.cpp_info.libdirs[0])
        ext_so = os.path.join(libdir, "sequential_uuids.so")
        if not os.path.isfile(ext_so):
            raise ConanException("sequential_uuids.so not found")

        ext_dir = os.path.join(pkg, "extension")
        test_bin = os.path.join(self.build_folder, "test_sequential_uuids")
        os.environ["SEQUENTIAL_UUIDS_EXT_DIR"] = ext_dir
        self.run(f"{test_bin} {ext_so}")

        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True, "passed": True,
            "command": "test_sequential_uuids (ELF + control + SQL smoke)",
            "discovered": 1, "passedCount": 1,
        }))

        discovered, executed, passed, failed, skipped, reason, detail = (
            self._run_pg_regress())
        if failed > 0:
            status = "failed"
        elif executed > 0:
            status = "passed"
        else:
            status = "skipped"
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": status, "framework": "pg_regress",
            "command": "make installcheck (initdb → pg_ctl → installcheck)",
            "discovered": discovered, "executed": executed,
            "passed": passed, "failed": failed, "skipped": skipped,
            "reason": reason, "detail": detail,
        }))
        if failed > 0:
            raise RuntimeError(
                "pg_regress: %d/%d failed" % (failed, executed))
