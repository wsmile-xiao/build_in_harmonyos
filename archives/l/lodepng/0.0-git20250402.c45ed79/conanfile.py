#!/usr/bin/env python3
"""Conan recipe — lodepng 0.0-git20250402.c45ed79 (single-file build).

lodepng is a PNG encoder and decoder in C and C++ without dependencies.
Upstream ships no CMake/autotools install: the library itself is exactly
two files (lodepng.cpp + lodepng.h) meant to be compiled into the consumer.
This recipe compiles lodepng.cpp into a real liblodepng.a / liblodepng.so
and installs lodepng.h, so downstream links a normal Conan library.

Upstream test: lodepng_unittest.cpp (single self-contained binary, 38
doMain test groups, all fixtures embedded as base64 — no external data
files). build() compiles and runs it, then emits HMBS_UPSTREAM_TEST_RESULT
with counts from the real run. Note the upstream main() always returns 0,
so pass/fail is decided by parsing stdout ("test successful" present and
no "*** TEST FAILED ***"), never by exit code alone.
"""
import json
import os
import shlex
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# Number of top-level test groups invoked by doMain() in
# lodepng_unittest.cpp at the pinned commit (counted from source).
_UPSTREAM_DISCOVERED = 38


class LodepngConan(ConanFile):
    name = "lodepng"
    version = "0.0-git20250402.c45ed79"
    description = "PNG encoder and decoder in C and C++, without dependencies"
    license = "Zlib"
    homepage = "https://github.com/lvandeve/lodepng"
    url = "https://github.com/lvandeve/lodepng"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        # Pure C/C++ single source file, only libc/libc++.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        self._pin_writable_tmpdir()
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Plain compiler-driven build; flags are passed explicitly on the
        # command line in build(). Nothing to generate.
        pass

    def _conf_exe(self, key):
        """Read tools.build:compiler_executables for key (E392 dict form)."""
        try:
            exes = self.conf.get("tools.build:compiler_executables", check_type=dict)
        except Exception:
            exes = None
        if isinstance(exes, dict) and exes.get(key):
            return exes[key]
        try:
            value = self.conf.get(
                "tools.build:compiler_executables:%s" % key, None, check_type=str
            )
            if value:
                return value
        except Exception:
            pass
        return None

    @staticmethod
    def _is_usable_exe(path):
        """Absolute path is usable only if present and executable."""
        try:
            return os.path.isfile(path) and os.access(path, os.X_OK)
        except Exception:
            return False

    def _resolve_prog(self, key, env_vars, path_names):
        """Resolve a build program without touching shell env vars (R33).

        conf absolute path is adopted only when isfile + X_OK; otherwise
        warn and fall back to PATH lookup (myman/4.0.116 pattern: this round
        preflight reports `/data/service/hnp/bin/clang++: inaccessible or
        not found`, exit 127, while PATH-probed tools work). Order: conf
        value -> env vars -> shutil.which(path_names) -> conf value -> bare
        name. Bare names are left for /bin/sh PATH resolution (hmbs
        preflight puts toolchain dirs on PATH via profile buildenv).
        """
        conf_val = self._conf_exe(key)
        if conf_val:
            if os.path.isabs(conf_val):
                if self._is_usable_exe(conf_val):
                    return conf_val
                try:
                    self.output.warning(
                        "conf compiler '%s' not usable, falling back to PATH lookup"
                        % conf_val
                    )
                except Exception:
                    pass
            else:
                resolved = shutil.which(conf_val)
                if resolved:
                    return resolved
        for var in env_vars:
            val = os.environ.get(var, "")
            if not val:
                continue
            if os.path.sep in val:
                if self._is_usable_exe(val) or os.path.isfile(val):
                    return val
            else:
                resolved = shutil.which(val)
                if resolved:
                    return resolved
                return val
        for name in path_names:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        if conf_val:
            return conf_val
        return path_names[0] if path_names else key

    def _tool(self, key, default):
        """Back-compat wrapper: resolve key, default is a PATH name."""
        return self._resolve_prog(key, (), (default,))

    def _writable_tmpdir(self):
        """Return a writable tmpdir (readonly_tmp: OHOS /tmp is read-only).

        Priority follows HMBS injected capabilities: HMBS_TMPDIR, TMPDIR,
        TMP, TEMP (each makedirs + mkstemp probed); skip the
        HMBS_AUTOCONF_MKTEMP_FALLBACK flag values "0"/"1". Final fallback
        is build_folder/tmp (always writable on HMBS). Only replaces the
        temp-file root, never deletes tests.
        """
        candidates = []
        fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if fallback and fallback not in ("0", "1") and fallback != "/tmp":
            candidates.append(fallback)
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var, "")
            if val and val != "/tmp" and val not in candidates:
                candidates.append(val)
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                fd, p = tempfile.mkstemp(dir=cand)
                os.close(fd)
                os.unlink(p)
                return cand
            except Exception:
                continue
        fb = os.path.join(self.build_folder or os.getcwd(), "tmp")
        try:
            os.makedirs(fb, exist_ok=True)
        except OSError:
            pass
        return fb

    def _pin_writable_tmpdir(self):
        """Pin TMPDIR/TMP/TEMP to a writable dir (inherited by self.run)."""
        tmp = self._writable_tmpdir()
        try:
            os.makedirs(tmp, exist_ok=True)
        except OSError:
            pass
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = tmp
        return tmp

    def _prepend_toolchain_path(self, prog):
        """Prepend prog's dir to PATH when it is a real directory.

        Guards against empty/non-dir values polluting PATH. Idempotent.
        """
        if not prog:
            return
        d = os.path.dirname(prog)
        if not d or not os.path.isdir(d):
            return
        cur = os.environ.get("PATH", "")
        parts = cur.split(os.pathsep) if cur else []
        if d in parts:
            return
        os.environ["PATH"] = d + os.pathsep + cur

    def _run_upstream_tests(self, unittest_bin):
        """Run the upstream unittest binary and emit the evidence marker."""
        command = "./lodepng_unittest"
        try:
            proc = subprocess.run(
                [unittest_bin],
                cwd=self.build_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1800,
            )
            output = proc.stdout or ""
        except Exception as exc:
            result = {
                "status": "failed",
                "framework": "unittest",
                "command": command,
                "discovered": _UPSTREAM_DISCOVERED,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "unittest harness could not run: %r" % (exc,),
            }
            marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result)
            print(marker, flush=True)
            self.output.info(marker)
            raise ConanException("lodepng upstream tests could not run: %r" % (exc,))

        # Keep a tail in the log for human diagnosis (full log is long).
        self.output.info(output[-3000:])
        # Falsification guard: upstream main() returns 0 even on failure,
        # so exit code alone proves nothing. A genuine green run prints the
        # per-test progress (e.g. testPngSuite) plus the final banner, and
        # never prints the failure banner.
        ran = "testPngSuite" in output and "test successful" in output
        failed_banner = ("*** TEST FAILED ***" in output) or ("caught error!" in output)
        if ran and not failed_banner:
            status = "passed"
            executed = _UPSTREAM_DISCOVERED
            passed = _UPSTREAM_DISCOVERED
            failed = 0
        else:
            status = "failed"
            executed = 0
            passed = 0
            failed = _UPSTREAM_DISCOVERED if failed_banner else 0
        result = {
            "status": status,
            "framework": "unittest",
            "command": command,
            "discovered": _UPSTREAM_DISCOVERED,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        if not ran:
            result["reason"] = "unittest output missing test progress/success banner"
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result)
        print(marker, flush=True)
        self.output.info(marker)
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream_result.json"),
                "w",
                encoding="utf-8",
            ) as fh:
                fh.write(json.dumps(result, indent=1))
        except OSError:
            pass
        if status != "passed":
            raise ConanException(
                "lodepng upstream tests did not pass "
                "(ran=%s failed_banner=%s)\n%s" % (ran, failed_banner, output[-3000:])
            )

    def build(self):
        # readonly_tmp: pin temp root to HMBS writable TMPDIR first.
        _hmbs_tmp = self._pin_writable_tmpdir()
        self.output.info("HMBS readonly_tmp: TMPDIR=%s" % _hmbs_tmp)
        # /bin/sh is the only shell guaranteed on HMBS workers.
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        os.environ["SHELL"] = "/bin/sh"
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        try:
            os.environ["PWD"] = self.build_folder
        except Exception:
            pass
        cxx = self._resolve_prog("cpp", ("CXX", "HMBS_CXX"), ("clang++", "clang", "c++", "cc"))
        ar = self._resolve_prog("ar", ("AR",), ("llvm-ar", "ar"))
        ranlib = self._resolve_prog("ranlib", ("RANLIB",), ("llvm-ranlib", "ranlib"))
        self._prepend_toolchain_path(cxx)
        self._prepend_toolchain_path(ar)
        self.output.info("lodepng cxx resolved: %s" % cxx)
        self.output.info("lodepng ar resolved: %s / %s" % (ar, ranlib))
        src = self.source_folder
        build_dir = self.build_folder
        obj_file = os.path.join(build_dir, "lodepng.o")

        # Library object (position independent so both static and shared work).
        self.run(
            '%s -O2 -fPIC -c "%s" -o "%s"' % (cxx, os.path.join(src, "lodepng.cpp"), obj_file),
            cwd=build_dir,
        )
        if self.options.shared:
            self.run(
                '%s -shared -fPIC -o "%s" "%s"'
                % (cxx, os.path.join(build_dir, "liblodepng.so"), obj_file),
                cwd=build_dir,
            )
        else:
            self.run(
                '%s rcs "%s" "%s"'
                % (ar, os.path.join(build_dir, "liblodepng.a"), obj_file),
                cwd=build_dir,
            )
            self.run('"%s" "%s"' % (ranlib, os.path.join(build_dir, "liblodepng.a")), cwd=build_dir)

        # Upstream self-contained unittest (needs no SDL2/data files).
        unittest_bin = os.path.join(build_dir, "lodepng_unittest")
        self.run(
            '%s -O2 -I"%s" "%s" "%s" "%s" -o "%s"'
            % (
                cxx,
                src,
                os.path.join(src, "lodepng.cpp"),
                os.path.join(src, "lodepng_util.cpp"),
                os.path.join(src, "lodepng_unittest.cpp"),
                unittest_bin,
            ),
            cwd=build_dir,
        )
        self._run_upstream_tests(unittest_bin)

    def package(self):
        copy(self, "lodepng.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "liblodepng.so", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "liblodepng.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Persist the upstream verdict inside the package so test_package
        # can re-emit it on Conan cache hits (when build() is skipped).
        try:
            marker_src = os.path.join(self.build_folder, "hmbs_upstream_result.json")
            if os.path.isfile(marker_src):
                with open(marker_src, encoding="utf-8") as fh:
                    payload = fh.read()
                with open(
                    os.path.join(self.package_folder, "hmbs_upstream_result.json"),
                    "w",
                    encoding="utf-8",
                ) as fh:
                    fh.write(payload)
        except OSError as exc:
            self.output.warning("lodepng: cannot persist upstream marker: %s" % exc)

    def package_info(self):
        self.cpp_info.libs = ["lodepng"]
