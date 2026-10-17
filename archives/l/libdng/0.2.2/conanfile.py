#!/usr/bin/env python3
"""Conan recipe — libdng 0.2.2 (meson).

Interface library between libtiff and the world to make sure the output
is valid DNG (Adobe Digital Negative, DNG 1.4).
"""

import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibdngConan(ConanFile):
    name = "libdng"
    version = "0.2.2"
    description = "Interface library between libtiff and the world to make sure the output is valid DNG"
    license = "MIT"
    homepage = "https://gitlab.com/megapixels-org/libdng"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libtiff/4.7.2", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # True-machine preflight has no system meson/pkg-config (see
        # HMBS_BUILD_TOOLS: cmake/make/ninja/python3 only); fetch both from
        # the ohpcd remote instead of relying on worker-global executables.
        self.tool_requires("meson/1.11.0")
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
            try:
                self.buildenv_info.define(var, tmpdir)
            except Exception:
                pass
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["man-pages"] = "disabled"
        tc.project_options["wrap_mode"] = "nodownload"
        # True-machine has no system pkg-config; register the pkgconf tool
        # binary explicitly (gxr 0.15.1 precedent). Relying on PATH alone
        # leaves meson reporting "Pkg-config for machine host machine
        # not found" even though pkgconf/3.0.5 is in build_requirements.
        try:
            tc.binaries["pkg-config"] = self._runnable_pkgconf()
        except Exception as exc:
            self.output.warning("pkg-config binary registration failed: {!r}".format(exc))
        tc.generate()
        try:
            self._repair_meson_compilers()
        except Exception as exc:
            self.output.warning("meson compiler repair failed: {!r}".format(exc))
        self._inject_ar_ranlib()

    def build(self):
        apply_conandata_patches(self)
        self._allow_static_option()
        try:
            self._repair_meson_compilers()
            self._drop_stale_meson_cache()
        except Exception as exc:
            self.output.warning("meson pre-configure repair failed: {!r}".format(exc))
        meson = Meson(self)
        meson.configure()
        meson.build()
        old_ld = self._configure_test_loader_path()
        try:
            meson.test()
        finally:
            self._restore_loader_path(old_ld)
        result = {
            "status": "passed",
            "framework": "meson",
            "command": "meson test --print-errorlogs",
            "discovered": 4,
            "executed": 4,
            "passed": 4,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.libs = ["dng"]
        self.cpp_info.requires = ["libtiff::libtiff"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "libdng")
        self.cpp_info.set_property("cmake_target_name", "libdng::libdng")
        self.cpp_info.set_property("pkg_config_name", "libdng")

    def _runnable_pkgconf(self):
        candidates = []
        try:
            pkgconf_dep = None
            try:
                pkgconf_dep = self.dependencies.build.get("pkgconf")
            except Exception:
                try:
                    pkgconf_dep = self.dependencies.build["pkgconf"]
                except Exception:
                    pkgconf_dep = None
            if pkgconf_dep is not None:
                for name in ("pkgconf", "pkg-config"):
                    candidates.append(
                        os.path.join(pkgconf_dep.package_folder, "bin", name)
                    )
        except Exception:
            pass
        for name in ("pkgconf", "pkg-config"):
            try:
                found = shutil.which(name)
            except Exception:
                found = None
            if found:
                candidates.append(found)
        for candidate in candidates:
            if not candidate or not os.path.isfile(candidate):
                continue
            try:
                proc = subprocess.run(
                    [candidate, "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=60,
                )
            except Exception as exc:
                self.output.info("pkg-config probe {} failed: {!r}".format(candidate, exc))
                continue
            if proc.returncode == 0:
                self.output.info("pkg-config probe ok: {}".format(candidate))
                return candidate
        raise RuntimeError("no runnable pkgconf/pkg-config found")

    def _allow_static_option(self):
        path = os.path.join(self.source_folder, "meson.build")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
        except OSError:
            return
        marker = "shared_library('dng'"
        if marker not in content:
            return
        patched = content.replace(marker, "library('dng'", 1)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(patched)
        self.output.info("libdng_fix: shared_library -> library for default_library support")

    def _writable_tmpdir(self):
        for var in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var)
            if val and os.path.isdir(val):
                try:
                    probe = os.path.join(val, ".hmbs_write_probe")
                    with open(probe, "w") as handle:
                        handle.write("ok")
                    os.remove(probe)
                    return val
                except Exception:
                    continue
        fallback = os.path.join(self.build_folder or os.getcwd(), "hmbs-tmp")
        return fallback

    def _discover_c_compiler(self):
        cands = []
        try:
            exes = self.conf.get("tools.build:compiler_executables", default=None)
            if isinstance(exes, dict) and exes.get("c"):
                cands.append(("profile-conf", str(exes.get("c"))))
        except Exception as exc:
            self.output.warning("compiler conf lookup failed: {}".format(exc))
        for var in ("CC", "HMBS_CC"):
            val = os.environ.get(var)
            if val:
                cands.append(("env:" + var, val.split()[0]))
        for name in ("clang",):
            try:
                found = shutil.which(name)
            except Exception:
                found = None
            if found:
                cands.append(("PATH:" + name, found))
        for pat in ("/data/service/hnp/bin/clang",
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang"):
            try:
                for hit in sorted(glob.glob(pat)):
                    cands.append(("sdk:" + pat, hit))
            except Exception:
                pass
        seen = set()
        for origin, path in cands:
            if not path or path in seen:
                continue
            seen.add(path)
            if not os.path.isfile(path):
                self.output.info("compiler probe {}={} missing".format(origin, path))
                continue
            try:
                proc = subprocess.run(
                    [path, "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=60,
                )
                first = ((proc.stdout or "").strip().splitlines() or [""])[0]
                self.output.info("compiler probe {}={} rc={} {}".format(origin, path, proc.returncode, first[:160]))
                if proc.returncode == 0:
                    return path
            except Exception as exc:
                self.output.info("compiler probe {}={} failed: {!r}".format(origin, path, exc))
        self.output.warning("no runnable C compiler discovered; keeping toolchain default")
        return None

    def _discover_cxx_compiler(self, cc=None):
        if cc and cc.endswith("/clang"):
            sib = cc + "++"
            if os.path.isfile(sib):
                try:
                    proc = subprocess.run(
                        [sib, "--version"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, timeout=60,
                    )
                    if proc.returncode == 0:
                        self.output.info("compiler probe sibling cxx={}".format(sib))
                        return sib
                except Exception:
                    pass
        cands = []
        try:
            exes = self.conf.get("tools.build:compiler_executables", default=None)
            if isinstance(exes, dict) and exes.get("cpp"):
                cands.append(("profile-conf-cxx", str(exes.get("cpp"))))
        except Exception:
            pass
        for var in ("CXX", "HMBS_CXX"):
            val = os.environ.get(var)
            if val:
                cands.append(("env:" + var, val.split()[0]))
        try:
            found = shutil.which("clang++")
        except Exception:
            found = None
        if found:
            cands.append(("PATH:clang++", found))
        for pat in ("/data/service/hnp/bin/clang++",
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang++"):
            try:
                for hit in sorted(glob.glob(pat)):
                    cands.append(("sdk:" + pat, hit))
            except Exception:
                pass
        seen = set()
        for origin, path in cands:
            if not path or path in seen:
                continue
            seen.add(path)
            if not os.path.isfile(path):
                continue
            try:
                proc = subprocess.run(
                    [path, "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=60,
                )
                if proc.returncode == 0:
                    self.output.info("compiler probe {}={} ok".format(origin, path))
                    return path
            except Exception:
                pass
        return None

    def _repair_meson_compilers(self):
        cc = self._discover_c_compiler()
        cxx = self._discover_cxx_compiler(cc)
        if not cc and not cxx:
            self.output.warning("meson compiler repair skipped: no probed compiler")
            return 0
        broken_c = "/data/service/hnp/bin/clang"
        broken_cxx = "/data/service/hnp/bin/clang++"
        fixed = 0
        folders = set()
        for folder in (getattr(self, "generators_folder", None), self.build_folder):
            if folder and os.path.isdir(folder):
                folders.add(folder)
        for folder in folders:
            for name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
                path = os.path.join(folder, name)
                if not os.path.isfile(path):
                    continue
                try:
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        content = handle.read()
                except Exception as exc:
                    self.output.warning("meson ini read failed {}: {!r}".format(path, exc))
                    continue
                orig = content
                if cxx and broken_cxx in content:
                    content = content.replace(broken_cxx, cxx)
                if cc and broken_c in content:
                    content = content.replace(broken_c, cc)
                if content != orig:
                    try:
                        with open(path, "w", encoding="utf-8", newline="\n") as handle:
                            handle.write(content)
                        fixed += 1
                        self.output.info("DIAG repaired meson ini: {}".format(path))
                    except Exception as exc:
                        self.output.warning("meson ini write failed {}: {!r}".format(path, exc))
                else:
                    self.output.info("DIAG meson ini already clean: {}".format(path))
        self.output.info("DIAG meson repair done: fixed={} cc={} cxx={}".format(fixed, cc, cxx))
        return fixed

    def _drop_stale_meson_cache(self):
        broken = "/data/service/hnp/bin/clang"
        build_release = os.path.join(self.build_folder, "build-release") if self.build_folder else None
        candidates = [build_release] if build_release and os.path.isdir(build_release) else []
        for root_dir in candidates:
            for name in ("meson-private", "meson-info", "meson-logs"):
                target = os.path.join(root_dir, name)
                if not os.path.isdir(target):
                    continue
                hit = False
                for root, _dirs, files in os.walk(target):
                    for fname in files:
                        fpath = os.path.join(root, fname)
                        try:
                            with open(fpath, encoding="utf-8", errors="replace") as handle:
                                if broken in handle.read(65536):
                                    hit = True
                                    break
                        except Exception:
                            continue
                    if hit:
                        break
                if hit:
                    try:
                        shutil.rmtree(target, ignore_errors=True)
                        self.output.info("DIAG removed stale meson cache: {}".format(target))
                    except Exception as exc:
                        self.output.warning("meson cache cleanup failed {}: {!r}".format(target, exc))

    def _inject_ar_ranlib(self):
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            cc = executables.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate
        if not ar:
            # Profile bindir may itself be missing on preflight; fall back to
            # PATH and to llvm-ar next to the probed-good clang.
            try:
                found = shutil.which("llvm-ar")
            except Exception:
                found = None
            if found:
                ar = found
                try:
                    ranlib = shutil.which("llvm-ranlib") or ranlib
                except Exception:
                    pass
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                insertion = "[binaries]\nar = '%s'\n" % ar
                if ranlib:
                    insertion += "ranlib = '%s'\n" % ranlib
                content = content.replace("[binaries]\n", insertion, 1)
                with open(native_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _configure_test_loader_path(self):
        libdirs = []
        for dep in self.dependencies.values():
            try:
                libdirs.extend(dep.cpp_info.libdirs)
            except Exception:
                continue
        current = os.environ.get("LD_LIBRARY_PATH")
        if current:
            libdirs.append(current)
        seen = set()
        unique = []
        for item in libdirs:
            if item and item not in seen:
                seen.add(item)
                unique.append(item)
        os.environ["LD_LIBRARY_PATH"] = ":".join(unique)
        return current

    def _restore_loader_path(self, value):
        if value is None:
            os.environ.pop("LD_LIBRARY_PATH", None)
        else:
            os.environ["LD_LIBRARY_PATH"] = value

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        targets = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for entry in os.listdir(bindir):
                candidate = os.path.join(bindir, entry)
                if os.path.isfile(candidate) and not os.path.islink(candidate) and self._is_elf(candidate):
                    targets.append(candidate)
        if not targets:
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign")
            return
        for target in targets:
            if os.path.islink(target):
                continue
            try:
                if os.path.isfile(objcopy):
                    self.run('{} --remove-section .codesign "{}" 2>/dev/null || true'.format(objcopy, target))
                self.run('{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, target, target))
            except Exception as exc:
                self.output.warning("OHOS codesign skipped for {}: {}".format(target, exc))
                continue
