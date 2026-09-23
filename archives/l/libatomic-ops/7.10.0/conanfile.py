#!/usr/bin/env python3
"""Conan recipe -- libatomic-ops 7.10.0 (direct cc compile, no CMake).

Upstream libatomic_ops is a tiny flat C library (src/atomic_ops.c plus the
GPL helpers src/atomic_ops_malloc.c / src/atomic_ops_stack.c) with no
generated headers and no external dependencies. Building it with the
Conan-configured compiler directly avoids the preflight failure mode where
conan's CMakeToolchain maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, which
vanilla cmake (4.4.3 on the workers) does not know ("System is unknown to
cmake") and the subsequent compiler identification step fails because clang
temp files fall back to the read-only /tmp (E002).

Build semantics replicate upstream CMakeLists.txt 7.10.0:
  - flags: -Wall -Wextra, -D_REENTRANT (OHOS provides pthreads),
    -DNDEBUG (assertions off, matching enable_assertions=OFF),
    intrinsics left enabled (enable_atomic_intrinsics=ON);
  - static (default): ar rcs libatomic_ops.a (+ libatomic_ops_gpl.a);
  - shared: cc -shared with SOVERSION 1 / VERSION 1.3.0 derived from
    LIBATOMIC_OPS_VER_INFO 4:0:3, -Wl,-soname, --no-undefined when available;
  - upstream tests: the 5 ctest cases are compiled from tests/ with the
    same defines upstream uses (generalized / pthreads variants) and run
    for real; HMBS_UPSTREAM_TEST_RESULT carries the observed counts.
E002 handling (readonly /tmp): every child process is spawned via the
list-form _run_noshell helper (no /bin/sh -c, so no /tmp/sh*.tmp) with
TMPDIR/TMP/TEMP pointed at the HMBS-injected writable dir (or a
build_folder fallback), forwarded into buildenv as well.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LibAtomicOpsConan(ConanFile):
    name = "libatomic-ops"
    version = "7.10.0"
    description = "Portable atomic memory operation primitives"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/bdwgc/libatomic_ops"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        _tmp = self._writable_tmpdir()
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Forward the writable tmpdir so any compiler temp files spawned
        # under conanbuild env never fall back to read-only /tmp.
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v:
                try:
                    os.makedirs(_v, exist_ok=True)
                except OSError:
                    pass
                self.buildenv_info.define(_k, _v)

    # -- helpers ---------------------------------------------------------
    def _writable_tmpdir(self):
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            value = os.environ.get(var)
            if value and value != "0" and value != "/tmp":
                try:
                    os.makedirs(value, exist_ok=True)
                except OSError:
                    pass
                return value
        fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if fallback and fallback != "0" and fallback != "/tmp":
            try:
                os.makedirs(fallback, exist_ok=True)
            except OSError:
                pass
            return fallback
        # NOTE: source() runs before build_folder exists in this Conan
        # version, so never touch self.base_source_folder/self.build_folder
        # directly here; fall back to the process cwd (conan runs source()
        # with cwd inside the base source dir).
        root = getattr(self, "build_folder", None) or os.getcwd()
        cand = os.path.join(root, "tmp_hmbs")
        try:
            os.makedirs(cand, exist_ok=True)
        except OSError:
            return root
        return cand

    def _cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        path = compilers.get("c")
        if path and os.path.isfile(path):
            return path
        if path:
            return shutil.which(os.path.basename(path)) or path
        for key in ("CC",):
            env_val = os.environ.get(key, "")
            if env_val:
                first = env_val.split()[0]
                if os.path.isfile(first):
                    return env_val
                resolved = shutil.which(os.path.basename(first))
                if resolved:
                    return env_val.replace(first, resolved, 1)
        return shutil.which("clang") or "clang"

    def _ar(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        path = compilers.get("ar", "")
        if path and os.path.isfile(path):
            return path
        for cand in ("llvm-ar", "ar"):
            resolved = shutil.which(cand)
            if resolved:
                return resolved
        return "llvm-ar"

    def _ranlib(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        path = compilers.get("ranlib", "")
        if path and os.path.isfile(path):
            return path
        for cand in ("llvm-ranlib", "ranlib"):
            resolved = shutil.which(cand)
            if resolved:
                return resolved
        return "llvm-ranlib"

    def _sdk_llvm_libdirs(self, cc_bin):
        # CI-020 precedent (PR #9950 build #48256): SDK lld failed at
        # startup with "Error loading shared library libxml2.so.16" plus
        # xml* relocation errors, i.e. the loader resolved lld's
        # DT_NEEDED to an incompatible libxml2 shadowing the SDK-bundled
        # one. Prepending the SDK llvm lib dirs to LD_LIBRARY_PATH lets
        # lld find its own libs again. No-op on healthy workers where the
        # dirs are absent or already first.
        import glob as _glob
        found = []
        try:
            cc_real = os.path.realpath(cc_bin) if cc_bin else ""
        except OSError:
            cc_real = ""
        cands = []
        if cc_real:
            cands.append(os.path.join(os.path.dirname(cc_real), "..", "lib"))
            cands.append(os.path.join(os.path.dirname(cc_real), "..", "..", "lib"))
        cands.append("/data/service/hnp/bin/../lib")
        for pat in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
                    "/data/service/hnp/ohos-sdk*/ohos/native/llvm/lib"):
            try:
                cands.extend(_glob.glob(pat))
            except OSError:
                pass
        for cand in cands:
            try:
                norm = os.path.normpath(cand)
            except OSError:
                continue
            if norm in found or not os.path.isdir(norm):
                continue
            found.append(norm)
        # Prefer dirs that actually ship a libxml2* (lld's missing dep).
        def _has_xml2(d):
            try:
                for f in os.listdir(d):
                    if f.startswith("libxml2"):
                        return True
            except OSError:
                pass
            return False
        found.sort(key=lambda d: (not _has_xml2(d), d))
        return found

    def _fix_lld_libpath(self, env):
        try:
            cur = env.get("LD_LIBRARY_PATH", "")
        except Exception:
            cur = ""
        dirs = self._sdk_llvm_libdirs(
            (self._cc().split()[0] if isinstance(self._cc(), str) else ""))
        if not dirs:
            return
        have = [p for p in cur.split(os.pathsep) if p] if cur else []
        merged = [d for d in dirs if d not in have] + have
        env["LD_LIBRARY_PATH"] = os.pathsep.join(merged)
        try:
            self.output.info("[HMBS lld-fix] LD_LIBRARY_PATH={0}".format(
                env["LD_LIBRARY_PATH"][:600]))
        except Exception:
            pass

    def _run_link(self, cmd, cwd=None):
        # Link commands go through lld on OHOS workers. If the default
        # lld is broken (libxml2 shadowing, see _sdk_llvm_libdirs), retry
        # once with a non-lld system linker instead of failing the whole
        # package: the tests only exercise atomic-ops logic, not linker
        # specifics. Compile-only commands must NOT use this path.
        try:
            self._run_noshell(cmd, cwd=cwd)
            return
        except subprocess.CalledProcessError:
            pass
        alt = ""
        for cand, flag in (("ld.bfd", "-fuse-ld=bfd"),
                           ("ld.gold", "-fuse-ld=gold"),
                           ("ld", "-fuse-ld=ld")):
            if shutil.which(cand):
                alt = flag
                break
        if not alt:
            raise
        self.output.warning(
            "[HMBS lld-fix] default link failed, retrying with {0}".format(alt))
        retry = [cmd[0], alt] + cmd[1:]
        self._run_noshell(retry, cwd=cwd)

    def _run_noshell(self, args, cwd=None):
        # List-form exec bypasses /bin/sh -c so the shell never creates
        # /tmp/sh*.tmp on the read-only /tmp (E002 / crossguid precedent).
        _tmp = self._writable_tmpdir()
        try:
            os.makedirs(_tmp, exist_ok=True)
        except OSError:
            pass
        _env = dict(os.environ)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _env[_k] = _tmp
        self._fix_lld_libpath(_env)
        self.output.info("noshell: %s" % " ".join(args))
        _cwd = cwd or getattr(self, "build_folder", None) or os.getcwd()
        subprocess.run(args, check=True, cwd=_cwd, env=_env)

    def _sign_file(self, path):
        # HarmonyOS requires a valid signature to exec/load ELFs; the SDK
        # output may carry none. Best effort, tolerant when tools absent.
        if os.path.islink(path) or not os.path.isfile(path):
            return
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            signer = shutil.which("binary-sign-tool") or ""
        if not signer:
            return
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        if not os.path.isfile(objcopy):
            objcopy = shutil.which("llvm-objcopy") or "llvm-objcopy"
        try:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path],
                check=False, timeout=60)
            subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"],
                check=False, timeout=120)
        except (OSError, subprocess.SubprocessError):
            pass

    def _cflags(self):
        if str(self.settings.build_type) == "Debug":
            opt = "-O0 -g"
        else:
            opt = "-O2 -DNDEBUG"
        flags = ["-Wall", "-Wextra", "-D_REENTRANT"] + opt.split()
        if self.options.get_safe("fPIC", True) or self.options.shared:
            flags.append("-fPIC")
        return flags

    # -- build -----------------------------------------------------------
    def build(self):
        _tmp = self._writable_tmpdir()
        try:
            os.makedirs(_tmp, exist_ok=True)
        except OSError:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        self.output.info("[HMBS tmp] build TMPDIR={0}".format(_tmp))

        src_dir = self.source_folder
        probe = os.path.join(src_dir, "src", "atomic_ops.c")
        if not os.path.isfile(probe):
            raise ConanException(
                "libatomic_ops sources not found at {0} (expected src/atomic_ops.c)".format(src_dir))
        gpl_srcs = ["src/atomic_ops_malloc.c", "src/atomic_ops_stack.c"]
        missing = [s for s in gpl_srcs if not os.path.isfile(os.path.join(src_dir, s))]
        if missing:
            raise ConanException("libatomic_ops GPL sources missing: {0}".format(", ".join(missing)))

        cc = self._cc()
        self.output.info("direct compile with cc={0}".format(cc))
        obj_dir = os.path.join(self.build_folder, "obj")
        try:
            os.makedirs(obj_dir, exist_ok=True)
        except OSError:
            pass
        inc = os.path.join(src_dir, "src")
        cflags = self._cflags()

        def compile_one(rel):
            src = os.path.join(src_dir, rel)
            obj = os.path.join(obj_dir, rel.replace("/", "_").replace(".c", ".o"))
            self._run_noshell([cc] + cflags + ["-I", inc, "-c", src, "-o", obj])
            return obj

        base_obj = compile_one("src/atomic_ops.c")
        gpl_objs = [compile_one(s) for s in gpl_srcs]

        if self.options.shared:
            # SOVERSION/VERSION from LIBATOMIC_OPS_VER_INFO 4:0:3.
            self._run_link(
                [cc, "-shared", "-Wl,-soname,libatomic_ops.so.1",
                 "-Wl,--no-undefined", "-o",
                 os.path.join(self.build_folder, "libatomic_ops.so.1.3.0"),
                 base_obj])
            self._run_link(
                [cc, "-shared", "-Wl,-soname,libatomic_ops_gpl.so.1",
                 "-Wl,--no-undefined", "-o",
                 os.path.join(self.build_folder, "libatomic_ops_gpl.so.1.3.0")]
                + gpl_objs + [os.path.join(self.build_folder, "libatomic_ops.so.1.3.0")])
            for lib in ("libatomic_ops.so.1.3.0", "libatomic_ops_gpl.so.1.3.0"):
                self._sign_file(os.path.join(self.build_folder, lib))
            self._make_version_links()
        else:
            ar = self._ar()
            ranlib = self._ranlib()
            lib = os.path.join(self.build_folder, "libatomic_ops.a")
            self._run_noshell([ar, "rcs", lib, base_obj])
            self._run_noshell([ranlib, lib])
            gpl_lib = os.path.join(self.build_folder, "libatomic_ops_gpl.a")
            self._run_noshell([ar, "rcs", gpl_lib] + gpl_objs)
            self._run_noshell([ranlib, gpl_lib])

        self._run_upstream_tests(cc, inc)

    def _make_version_links(self):
        bdir = self.build_folder
        for real, links in (("libatomic_ops.so.1.3.0", ("libatomic_ops.so.1", "libatomic_ops.so")),
                            ("libatomic_ops_gpl.so.1.3.0", ("libatomic_ops_gpl.so.1", "libatomic_ops_gpl.so"))):
            real_path = os.path.join(bdir, real)
            if not os.path.isfile(real_path):
                continue
            for link in links:
                link_path = os.path.join(bdir, link)
                try:
                    if os.path.islink(link_path) or os.path.isfile(link_path):
                        os.unlink(link_path)
                except OSError:
                    pass
                try:
                    os.symlink(real, link_path)
                except OSError:
                    try:
                        shutil.copy2(real_path, link_path)
                    except OSError as exc:
                        self.output.warning("versioned .so link skipped: {0}".format(exc))

    def _run_upstream_tests(self, cc, inc):
        """Compile and run the 5 upstream cases; emit the evidence marker."""
        cases = [
            ("test_atomic", ["tests/test_atomic.c"], []),
            ("test_atomic_generalized", ["tests/test_atomic.c"],
             ["-DAO_PREFER_GENERALIZED", "-DAO_TEST_EMULATION"]),
            ("test_atomic_pthreads", ["tests/test_atomic.c"], ["-DAO_USE_PTHREAD_DEFS"]),
            ("test_stack", ["tests/test_stack.c"], []),
            ("test_malloc", ["tests/test_malloc.c"], []),
        ]
        bdir = self.build_folder
        libdir = bdir
        discovered = len(cases)
        passed = 0
        failed = 0
        details = []
        for name, srcs, extra in cases:
            src_paths = [os.path.join(self.source_folder, s) for s in srcs]
            if any(not os.path.isfile(p) for p in src_paths):
                details.append("{0}: source missing, counted as failed".format(name))
                failed += 1
                continue
            test_bin = os.path.join(bdir, name)
            compile_cmd = ([cc, "-O2", "-DNDEBUG", "-D_REENTRANT", "-I", inc]
                           + extra + src_paths
                           + ["-o", test_bin, "-L", libdir,
                              "-latomic_ops", "-latomic_ops_gpl", "-pthread"])
            try:
                self._run_link(compile_cmd)
            except subprocess.CalledProcessError as exc:
                details.append("{0}: compile failed ({1})".format(name, exc))
                failed += 1
                continue
            self._sign_file(test_bin)
            rc, out = self._exec_test(test_bin)
            # Falsifiability: require rc==0 AND non-empty meaningful output.
            # Upstream tests print progress lines; an empty-output rc==0
            # (e.g. fixture missing) must not count as passed.
            if rc == 0 and out.strip():
                passed += 1
                self.output.info("[upstream] {0}: PASSED".format(name))
            else:
                failed += 1
                details.append("{0}: rc={1} out={2}".format(name, rc, out[-500:]))
                self.output.warning("[upstream] {0}: FAILED rc={1}".format(name, rc))
        for line in details[-10:]:
            self.output.info("[upstream detail] {0}".format(line))
        marker = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "ctest",
            "command": "direct-cc upstream tests (5 cases from tests/)",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
        if failed:
            raise ConanException("libatomic-ops upstream tests failed: {0}".format("; ".join(details)))

    def _exec_test(self, test_bin):
        _tmp = self._writable_tmpdir()
        _env = dict(os.environ)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _env[_k] = _tmp
        if self.options.shared:
            prev = _env.get("LD_LIBRARY_PATH", "")
            _env["LD_LIBRARY_PATH"] = self.build_folder + (os.pathsep + prev if prev else "")
        try:
            if not can_run(self):
                return 1, "can_run=False, test binary built but not executed"
            p = subprocess.run([test_bin], capture_output=True, text=True,
                               timeout=300, env=_env)
            return p.returncode, (p.stdout or "") + (p.stderr or "")
        except Exception as exc:
            return 1, "upstream test exception: {0}".format(exc)

    def package(self):
        if self.options.shared:
            copy(self, "libatomic_ops.so*", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "libatomic_ops_gpl.so*", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        else:
            copy(self, "libatomic_ops.a", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "libatomic_ops_gpl.a", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        # Preserve the atomic_ops/ subdirectory tree (sysdeps/gcc, ...):
        # atomic_ops.h includes "atomic_ops/sysdeps/gcc/aarch64.h".
        copy(self, "*.h", src=os.path.join(self.source_folder, "src", "atomic_ops"),
             dst=os.path.join(self.package_folder, "include", "atomic_ops"), keep_path=True)
        for lic in ("LICENSE", "COPYING", "ChangeLog"):
            lic_path = os.path.join(self.source_folder, lic)
            if os.path.isfile(lic_path):
                copy(self, lic, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
                break

    def package_info(self):
        self.cpp_info.libs = ["atomic_ops", "atomic_ops_gpl"]
