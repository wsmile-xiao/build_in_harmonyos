#!/usr/bin/env python3
"""Conan recipe — crossguid 0.0-git200150803 (custom direct clang++ build)."""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CrossguidConan(ConanFile):
    name = "crossguid"
    version = "0.0-git200150803"
    description = "Lightweight cross platform C++ GUID/UUID library"
    license = "MIT"
    homepage = "https://github.com/graeme-hill/crossguid"
    url = ""
    topics = ("guid", "uuid")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("uuid/2.40.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        # readonly_tmp: conan get() may use /tmp for download/extract;
        # prefer HMBS-injected writable dir, fallback under base_source_folder.
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or os.path.join(self.base_source_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Forward HMBS writable TMPDIR into buildenv so compiler temp files
        # never fall back to read-only /tmp.
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v:
                try:
                    os.makedirs(_v, exist_ok=True)
                except Exception:
                    pass
                self.buildenv_info.define(_k, _v)

    def _resolve_tool(self, *candidates):
        # R33: conf value only when the file exists; otherwise PATH lookup
        # (hmbs prepends real tool dirs to buildenv PATH). No bare $CC/$CXX.
        for _c in candidates:
            if not _c:
                continue
            if os.path.isabs(_c):
                if os.path.isfile(_c):
                    return _c
                _w = shutil.which(os.path.basename(_c))
                if _w:
                    return _w
            else:
                _w = shutil.which(_c)
                if _w:
                    return _w
                if os.path.isfile(_c):
                    return _c
        for _c in candidates:
            if _c:
                return _c
        return "clang++"

    def _toolchain(self):
        # conan 2.30 strictly validates conf keys: the sub-key form
        # "tools.build:compiler_executables:cpp" raises
        # "does not exist in configuration list". Use the dict form.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = self._resolve_tool(
            compilers.get("cpp"), "clang++",
            "aarch64-linux-ohos-clang++", "c++", "g++",
            compilers.get("c"))
        cc = self._resolve_tool(
            compilers.get("c"), "clang",
            "aarch64-linux-ohos-clang", "cc", "gcc")
        ar = self._resolve_tool(
            compilers.get("ar"), "llvm-ar", "ar")
        ranlib = self._resolve_tool(
            compilers.get("ranlib"), "llvm-ranlib", "ranlib")
        return cxx, cc, ar, ranlib

    def _run_noshell(self, args, cwd=None):
        # Shell-free exec: bypass /bin/sh -c so dash never creates
        # /tmp/sh*.tmp on read-only /tmp. List form directly execs.
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        _env = dict(os.environ)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _env[_k] = _tmp
        self.output.info("noshell: %s" % " ".join(args))
        subprocess.run(args, check=True, cwd=cwd or self.build_folder,
                       env=_env)

    def build(self):
        apply_conandata_patches(self)
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        cxx, cc, ar, ranlib = self._toolchain()
        self.output.info("crossguid toolchain: CC=%s CXX=%s AR=%s" % (cc, cxx, ar))

        uuid_pkg = self.dependencies["uuid"].package_folder
        uuid_inc = os.path.join(uuid_pkg, "include")
        uuid_lib = os.path.join(uuid_pkg, "lib")
        uuid_static = os.path.join(uuid_lib, "libuuid.a")

        src = self.source_folder
        bdir = self.build_folder
        obj = os.path.join(bdir, "guid.o")
        self._run_noshell([cxx, "-c", os.path.join(src, "guid.cpp"),
                           "-o", obj, "-std=c++11", "-fPIC",
                           "-DGUID_LIBUUID", "-I%s" % uuid_inc, "-O2"])

        if self.options.shared:
            soname = os.path.join(bdir, "libcrossguid.so")
            self._run_noshell([cxx, "-shared", "-o", soname, obj, uuid_static])
        else:
            libsta = os.path.join(bdir, "libcrossguid.a")
            self._run_noshell([ar, "rcs", libsta, obj])
            self._run_noshell([ranlib, libsta])

        self._run_upstream_tests(cxx, uuid_inc, uuid_static, bdir, src)

    def _run_upstream_tests(self, cxx, uuid_inc, uuid_static, bdir, src):
        # Upstream test (2015 snapshot): test.cpp + testmain.cpp, 6 assertions,
        # prints "All tests passed!" on success (linux.sh parity, GUID_LIBUUID).
        test_bin = os.path.join(bdir, "crossguid_upstream_test")
        self._run_noshell([cxx,
                           os.path.join(src, "test.cpp"),
                           os.path.join(src, "testmain.cpp"),
                           os.path.join(src, "guid.cpp"),
                           "-o", test_bin, "-std=c++11",
                           "-DGUID_LIBUUID",
                           "-I%s" % src, "-I%s" % uuid_inc, uuid_static])
        discovered = 6
        cmd = test_bin
        rc = 1
        out = ""
        try:
            if can_run(self):
                _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                        or os.environ.get("TEMP")
                        or os.path.join(self.build_folder, "tmp"))
                try:
                    os.makedirs(_tmp, exist_ok=True)
                except Exception:
                    pass
                _env = dict(os.environ)
                for _k in ("TMPDIR", "TMP", "TEMP"):
                    _env[_k] = _tmp
                p = subprocess.run([test_bin], capture_output=True, text=True,
                                   timeout=120, env=_env)
                rc = p.returncode
                out = (p.stdout or "") + (p.stderr or "")
            else:
                out = "can_run=False, test binary built but not executed"
                rc = 1
        except Exception as e:
            out = "upstream test exception: %s" % e
            rc = 1
        for line in out.splitlines()[-15:]:
            self.output.info("[crossguid upstream] %s" % line)
        ok = (rc == 0 and "All tests passed!" in out)
        passed = discovered if ok else 0
        failed = 0 if ok else discovered
        result = {
            "status": "passed" if ok else "failed",
            "framework": "custom",
            "command": cmd,
            "discovered": discovered,
            "executed": discovered if can_run(self) else 0,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "reason": "" if ok else out[-500:],
        }
        _line = 'HMBS_UPSTREAM_TEST_RESULT=%s' % json.dumps(result)
        self.output.info(_line)
        print(_line, flush=True)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream_result.json"),
                      "w", encoding="utf-8") as _f:
                json.dump({k: result.get(k) for k in
                           ("status", "framework", "command", "discovered",
                            "executed", "passed", "failed", "skipped")},
                          _f, ensure_ascii=False)
        except Exception:
            pass
        if can_run(self) and not ok:
            raise Exception("crossguid upstream tests failed: %s" % out[-2000:])

    def package(self):
        copy(self, "hmbs_upstream_result.json",
             src=self.build_folder, dst=self.package_folder)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "guid.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "libcrossguid.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "libcrossguid.so*", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["crossguid"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("m")
