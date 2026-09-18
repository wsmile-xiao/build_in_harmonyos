#!/usr/bin/env python3
"""Conan recipe — libzimg 3.0.6 (Autotools, upstream-faithful).

zimg is a scaling, colorspace conversion and dithering library (C/C++,
vapoursynth ecosystem). Upstream: https://github.com/sekrit-twc/zimg

This is the autotools build of the 3.0.6 release (task #13534):

- The release tarball ships Autotools inputs only (configure.ac/Makefile.am/
  autogen.sh) — no generated configure. The recipe bootstraps them with
  tool_requires automake/1.18 + libtool/2.5.4.1 and the system autoconf
  (hnp PATH), then runs the real ./configure && make && make install.
- Device-native build: the worker is aarch64 running OHOS itself, so
  --build/--host are both aarch64-linux (no cross toolchain juggling; the
  ohos clang from tools.build:compiler_executables compiles for the host).
- STL_LIBS=-lc++: zimg.pc.in's Libs.private defaults to -lstdc++; OHOS
  uses libc++, the upstream-supported override variable carries it.
- Upstream unit tests ARE executed (--enable-unit-test): 122 gtest cases
  (96 generic + 26 aarch64 NEON variants selected by configure for the
  ARM backend). The googletest submodule slot is filled from the official
  gtest 1.14.0 tarball (last C++14-compatible release; 1.15+ needs C++17
  while zimg builds C++14) and is built by the upstream configure.ac cmake
  step exactly as upstream CI does. `make check` runs the whole suite and
  the recipe parses the gtest summary for the PR report.
- E114/E206 family: configure's `umask 077` is rewritten to 022 before
  configure runs (HMDFS mktemp permission workaround, gmime precedent).

zimg vs libzimg naming: the previously merged archives/z/zimg/3.0.6 recipe
bypassed autotools (direct clang++ build, no upstream tests) and was
published to the registry as zimg/3.0.6. This task's platform branch is
feat/libzimg-3.0.6 and CI L0n requires branch == <pkg>-<version>, so this
recipe (a separate, autotools-faithful package with upstream test closure)
is named libzimg — both packages stay installable side by side and the
registry holds no libzimg/3.0.6 yet.
"""
import json
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibzimgConan(ConanFile):
    name = "libzimg"
    version = "3.0.6"
    description = "Scaling, colorspace conversion, and dithering library"
    license = "WTFPL"
    homepage = "https://github.com/sekrit-twc/zimg"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libzimg 3.0.6 supports Linux/OHOS, got {self.settings.os}"
            )

    def build_requirements(self):
        # The release tarball has no configure/Makefile.in: bootstrap with
        # registry-published autotools (autoconf itself is on the hnp PATH).
        # Pinned exact versions: automake 1.18 m4 dir layout must match the
        # aclocal that runs (a 1.17 aclocal against 1.18 share/ dies with
        # "@am_AUTOM4TE@ inaccessible"), same versions as gmime 3.0.6.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # sources[0]: zimg release tarball
        get(self, **self.conan_data["sources"][0], strip_root=True,
            retry=5, retry_wait=15)
        # sources[1]: googletest 1.14.0 fills the empty submodule slot the
        # upstream build expects (configure.ac cmake-builds it when
        # --enable-unit-test is given; Makefile.am links the in-tree lib).
        gt = os.path.join(self.source_folder, "test", "extra", "googletest")
        if os.path.isdir(gt):
            shutil.rmtree(gt)
        os.makedirs(gt, exist_ok=True)
        get(self, **self.conan_data["sources"][1], strip_root=True,
            destination=gt, retry=5, retry_wait=15)
        marker = os.path.join(gt, "googletest", "CMakeLists.txt")
        if not os.path.isfile(marker):
            raise Exception("googletest source did not unpack into test/extra/googletest")

    # ------------------------------------------------------------------
    # Bootstrap the autotools chain (gmime 3.0.6 pattern): aclocal ->
    # autoconf -> libtoolize -> automake. All under env="conanbuild" so the
    # tool_requires environment is applied.
    # ------------------------------------------------------------------
    def _bootstrap_autotools(self):
        src = self.source_folder
        am_pkg = None
        try:
            am_pkg = self.dependencies.build["automake"].package_folder
        except Exception:
            am_pkg = None
        aclocal_bin = os.path.join(am_pkg, "bin", "aclocal") if am_pkg else shutil.which("aclocal")
        automake_bin = os.path.join(am_pkg, "bin", "automake") if am_pkg else shutil.which("automake")

        self.output.info("Bootstrap: aclocal")
        self.run(f'"{aclocal_bin}" --force -I m4', cwd=src, env="conanbuild")
        if not os.path.isfile(os.path.join(src, "aclocal.m4")):
            raise Exception("aclocal did not produce aclocal.m4")

        self.output.info("Bootstrap: autoconf")
        autoconf_bin = shutil.which("autoconf") or "autoconf"
        self.run(f'"{autoconf_bin}" -o configure configure.ac', cwd=src, env="conanbuild")
        if not os.path.isfile(os.path.join(src, "configure")):
            raise Exception("autoconf did not produce configure")
        # A bootstrap-missed macro stays as a literal call in the generated
        # configure and explodes at runtime — fail fast here instead.
        with open(os.path.join(src, "configure"), "r", encoding="utf-8", errors="ignore") as fh:
            cfg_text = fh.read()
        for macro in ("AX_CHECK_COMPILE_FLAG", "AX_PTHREAD", "AM_INIT_AUTOMAKE", "LT_INIT"):
            if re.search(rf"^[^#]*\b{macro}\s*\(", cfg_text, re.M):
                raise Exception(f"configure contains unexpanded macro {macro}()")

        self.output.info("Bootstrap: libtoolize")
        lt_pkg = None
        try:
            lt_pkg = self.dependencies.build["libtool"].package_folder
        except Exception:
            lt_pkg = None
        libtoolize_bin = os.path.join(lt_pkg, "bin", "libtoolize") if lt_pkg else shutil.which("libtoolize")
        # Stage _lt_pkgdatadir (build-aux + m4 + libltdl) from the package
        # so libtoolize finds its data dirs (abiword/gmime pattern).
        pkgdatadir = None
        if lt_pkg:
            try:
                src_aux = os.path.join(lt_pkg, "share", "libtool", "build-aux")
                src_m4 = os.path.join(lt_pkg, "share", "aclocal")
                if os.path.isdir(src_aux):
                    pkgdatadir = os.path.join(self.build_folder, "libtool-data")
                    for sub, sdir in (("build-aux", src_aux), ("m4", src_m4)):
                        dst = os.path.join(pkgdatadir, sub)
                        os.makedirs(dst, exist_ok=True)
                        if os.path.isdir(sdir):
                            for fname in os.listdir(sdir):
                                sfile = os.path.join(sdir, fname)
                                if os.path.isfile(sfile):
                                    shutil.copy2(sfile, os.path.join(dst, fname))
                    ltdl = os.path.join(pkgdatadir, "libltdl")
                    os.makedirs(ltdl, exist_ok=True)
                    keep = os.path.join(ltdl, "keep.txt")
                    if not os.path.exists(keep):
                        with open(keep, "w") as fh:
                            fh.write("x\n")
            except Exception as exc:
                self.output.warning(f"libtoolize staging failed: {exc}")
                pkgdatadir = None
        cmd = f'"{libtoolize_bin}" --copy --force --install'
        if pkgdatadir:
            cmd = f'_lt_pkgdatadir="{pkgdatadir}" ' + cmd
        self.run(cmd, cwd=src, env="conanbuild")
        if not os.path.isfile(os.path.join(src, "ltmain.sh")):
            raise Exception("libtoolize did not produce ltmain.sh")

        self.output.info("Bootstrap: automake")
        self.run(f'"{automake_bin}" --add-missing --copy --no-force', cwd=src, env="conanbuild")
        if not os.path.isfile(os.path.join(src, "Makefile.in")):
            raise Exception("automake did not produce Makefile.in")

        # E114/E206: configure writes `umask 077` before running config.status
        # mktemp temp dirs; HMDFS blocks those permission bits. 022 works.
        cfg = os.path.join(src, "configure")
        if os.path.isfile(cfg):
            replace_in_file(self, cfg, "umask 077", "umask 022", strict=False)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--disable-static")
            tc.configure_args.append("--enable-shared")
        # Device-native build on the aarch64/OHOS worker: both triplets
        # aarch64-linux keep AC_CANONICAL_HOST happy and select the ARM
        # backend (ZIMG_ARM + NEON sources) for aarch64.
        tc.configure_args.append("--build=aarch64-linux")
        tc.configure_args.append("--host=aarch64-linux")
        # Run the upstream gtest suite in build() (task hard requirement).
        tc.configure_args.append("--enable-unit-test")
        # OHOS libc++ runtime for zimg.pc Libs.private (-lstdc++ default).
        tc.configure_args.append("STL_LIBS=-lc++")
        # libtool links shared libs with -nostdlib (injected by the OHOS
        # clang wrapper), which drops clang's implicit libclang_rt.builtins;
        # matrix.cpp instantiates RowMatrix<long double> and aarch64
        # long double is fp128 (__addtf3 and friends live in builtins).
        # Add it explicitly so libzimg.so has no undefined soft-float refs.
        if self.settings.os == "OHOS":
            try:
                tc.extra_ldflags.append("-lclang_rt.builtins")
            except Exception:
                tc.ldflags.append("-lclang_rt.builtins")
        tc.generate()

        # OHOS toolchain env fixes (gmime pattern): resolve llvm tools and
        # make sure AR/RANLIB point at real executables, plus the SDK
        # aarch64-linux-ohos lib dir for libc++_shared.so at test runtime.
        if str(self.settings.os) == "OHOS":
            env = Environment()
            tools = {n: shutil.which(n) for n in ("ar", "as", "strip", "nm", "ranlib")}
            missing = [n for n, p in tools.items() if p is None]
            if missing:
                raise ConanInvalidConfiguration(
                    f"Required build tools not in PATH: {', '.join(missing)}")
            env.define_path("AR", tools["ar"])
            env.define_path("AS", tools["as"])
            env.define_path("STRIP", tools["strip"])
            env.define_path("NM", tools["nm"])
            env.define_path("RANLIB", tools["ranlib"])
            perl = shutil.which("perl")
            if perl:
                env.define_path("PERL", perl)
            # unit_test links libc++_shared.so from the OHOS SDK; the CI
            # profile's LD_LIBRARY_PATH covers llvm/lib but not the
            # aarch64-linux-ohos subdir where libc++_shared.so lives.
            sdk_cxx = ("/data/service/hnp/ohos-sdk.org/"
                       "ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos")
            if os.path.isdir(sdk_cxx):
                env.prepend_path("LD_LIBRARY_PATH", sdk_cxx)
            env.vars(self).save_script("libzimg_ohos_buildenv")

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._bootstrap_autotools()
        else:
            self._bootstrap_autotools()

        autotools = Autotools(self)
        autotools.configure()
        # HMBS [make_jobserver_fifo]: single-job build (FIFO jobserver
        # unsupported on this FS; -j1 avoids the race entirely).
        autotools.make(args=["-j1"])
        self._run_upstream_make_check()

    # ------------------------------------------------------------------
    # Upstream test suite: `make check` builds test/unit_test (gtest 1.14 +
    # musl-libm reference lib) and runs it. On aarch64 the suite registers
    # 122 cases (96 generic + 26 NEON). The gtest summary is parsed and
    # re-emitted as HMBS_UPSTREAM_TEST_RESULT for the PR report.
    # ------------------------------------------------------------------
    def _run_upstream_make_check(self):
        make_bin = shutil.which("make") or "make"
        log_name = "make_check.log"
        self.run(f"{make_bin} check -j1 > {log_name} 2>&1", cwd=self.build_folder, env="conanbuild")
        log_path = os.path.join(self.build_folder, log_name)
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as fh:
                out = fh.read()
        except OSError:
            out = ""
        # automake test-driver captures the unit_test stdout into
        # test/unit_test.log; the gtest counters live there, not in the
        # make log. Read both.
        gtest_out = ""
        for extra in ("test/unit_test.log", "test/test-suite.log"):
            p = os.path.join(self.build_folder, extra)
            if os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                        gtest_out += fh.read()
                except OSError:
                    pass
        # automake test harness verdict first (TESTS = test/unit_test)
        am_pass = len(re.findall(r"^PASS: ", out, re.M))
        am_fail = len(re.findall(r"^FAIL: ", out, re.M))
        # gtest per-case counters (unit_test binary output)
        src = gtest_out or out
        m = re.search(r"\[\s+PASSED\s+\]\s+(\d+) tests?\.", src)
        passed = int(m.group(1)) if m else 0
        m2 = re.search(r"\[\s+FAILED\s+\]\s+(\d+) tests?", src)
        failed = int(m2.group(1)) if m2 else am_fail
        m3 = re.search(r"(\d+) tests? from (\d+) test suites? ran", src)
        ran = int(m3.group(1)) if m3 else passed + failed
        status = "passed" if failed == 0 and am_fail == 0 else "failed"
        tail = "\n".join(src.splitlines()[-15:]) if src else "(empty)"
        self.output.info(f"make check tail:\n{tail}")
        marker = {
            "status": status,
            "framework": "autotools make check (gtest)",
            "command": f"{make_bin} check -j1",
            "discovered": 122,
            "executed": ran,
            "passed": passed,
            "failed": failed,
            "am_pass": am_pass,
            "am_fail": am_fail,
            "reason": "" if status == "passed" else tail[-400:],
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        self.output.info(line)
        try:
            with open(os.path.join(self.build_folder, "upstream_test_result.json"), "w", encoding="utf-8") as fh:
                json.dump(marker, fh, ensure_ascii=False)
        except OSError as exc:
            self.output.warning(f"cannot persist upstream result: {exc}")
        if status != "passed":
            raise Exception(
                f"upstream unit tests failed: {failed} gtest case(s) FAILED; see {log_name}")

    def package(self):
        autotools = Autotools(self)
        try:
            autotools.install(args=["-j1"])
        except Exception as exc:
            self.output.warning(f"autotools.install failed ({exc}); python fallback install")
            self._fallback_install_python()
        # .la files carry the build-machine prefix and are useless to conan
        # consumers (they confuse downstream libtool links).
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for la in os.listdir(lib_dir):
                if la.endswith(".la"):
                    os.unlink(os.path.join(lib_dir, la))
        # doc/share noise is not shipped.
        share_dir = os.path.join(self.package_folder, "share")
        if os.path.isdir(share_dir):
            shutil.rmtree(share_dir, ignore_errors=True)
        # Ship the upstream test result JSON for cache-hit re-emission.
        try:
            copy(self, "upstream_test_result.json", self.build_folder,
                 os.path.join(self.package_folder, "res"))
        except Exception as exc:
            self.output.warning(f"cannot ship upstream result: {exc}")
        if self.settings.os == "OHOS" and self.options.shared:
            self._sign_shared_libs()

    def _fallback_install_python(self):
        """Pure-Python install fallback for chmod/hardlink-restricted FS."""
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(inc_dir, exist_ok=True)
        # library: search .libs dirs in source tree (in-source build)
        if self.options.shared:
            names = ("libzimg.so.2.0.0",)
        else:
            names = ("libzimg.a",)
        for root, _dirs, files in os.walk(self.source_folder):
            for f in files:
                if f in names:
                    src = os.path.join(root, f)
                    shutil.copy2(src, os.path.join(lib_dir, f))
        # symlinks for the shared lib
        if self.options.shared:
            base = os.path.join(lib_dir, "libzimg.so.2.0.0")
            for link in ("libzimg.so.2", "libzimg.so"):
                dst = os.path.join(lib_dir, link)
                if os.path.lexists(dst):
                    os.unlink(dst)
                os.symlink("libzimg.so.2.0.0", dst)
        copy(self, "zimg.h", src=os.path.join(self.source_folder, "src", "zimg", "api"), dst=inc_dir, keep_path=False)
        copy(self, "zimg++.hpp", src=os.path.join(self.source_folder, "src", "zimg", "api"), dst=inc_dir, keep_path=False)
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        pc_src = os.path.join(self.source_folder, "zimg.pc")
        if os.path.isfile(pc_src):
            pc_dir = os.path.join(lib_dir, "pkgconfig")
            os.makedirs(pc_dir, exist_ok=True)
            shutil.copy2(pc_src, os.path.join(pc_dir, "zimg.pc"))

    def _sign_shared_libs(self):
        """OHOS requires ELF code signatures for on-device execution.

        Same flow as the previously merged zimg recipe: llvm-objcopy strips
        any existing .codesign section and binary-sign-tool self-signs the
        library so test_package can dlopen/link it on an OHOS host.
        binary-sign-tool NEEDED libc++.so (__h namespace) which only the
        system /system/lib64/libc++.so provides — the SDK's libc++.so is a
        linker script the loader cannot use; masking it breaks the tool
        with 86 __h symbol errors (exit 127). Build an explicit env with
        /system/lib64 first so the run is independent of the profile.
        """
        objcopy = shutil.which("llvm-objcopy")
        signer = shutil.which("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning("sign tools not found; skipping OHOS code signing")
            return
        sdk_cxx = ("/data/service/hnp/ohos-sdk.org/"
                   "ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos")
        # subprocess with an explicit LD_LIBRARY_PATH (system /system/lib64
        # first: the sign tool needs the real __h libc++.so; the SDK one is
        # a linker script). ConanFile.run's cmd wrapper mangles the inline
        # env prefix (exit 127), so call the tools directly.
        import subprocess
        sign_env = dict(os.environ)
        parts = [p for p in sign_env.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p]
        for add in (sdk_cxx, "/system/lib64"):
            while add in parts:
                parts.remove(add)
            parts.insert(0, add)
        # /system/lib64 ends up FIRST (inserted last): the sign tool needs
        # the real __h-namespace libc++.so; the SDK libc++.so is a linker
        # script that masks it otherwise.
        sign_env["LD_LIBRARY_PATH"] = os.pathsep.join(parts)
        libdir = os.path.join(self.package_folder, "lib")
        for name in ("libzimg.so.2.0.0", "libzimg.so.2", "libzimg.so"):
            path = os.path.join(libdir, name)
            if not os.path.exists(path):
                continue
            signed = path + ".signed"
            for cmd in (
                [objcopy, "--remove-section", ".codesign", path],
                [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            ):
                proc = subprocess.run(cmd, env=sign_env,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                if proc.returncode != 0:
                    self.output.warning(
                        f"OHOS code signing failed for {name} "
                        f"(rc={proc.returncode}): {proc.stdout.decode(errors='replace')[-200:]}")
                    break
            else:
                if os.path.isfile(signed):
                    os.replace(signed, path)
                    self.output.info(f"OHOS code-signed {name}")

    def package_info(self):
        self.cpp_info.libs = ["zimg"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "zimg")
        self.cpp_info.set_property("cmake_file_name", "zimg")
        self.cpp_info.set_property("cmake_target_name", "zimg::zimg")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
