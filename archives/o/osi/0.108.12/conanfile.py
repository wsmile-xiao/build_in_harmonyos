#!/usr/bin/env python3
"""Conan recipe — osi 0.108.12 (COIN-OR Open Solver Interface, autotools)."""
import glob
import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building, load_toolchain_args
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rename, replace_in_file, rm, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import check_min_vs, is_msvc, msvc_runtime_flag

required_conan_version = ">=2.28"


class OsiConan(ConanFile):
    name = "osi"
    version = "0.108.12"
    description = "COIN-OR Open Solver Interface, a uniform API for LP/MIP solvers"
    topics = ("coin-or", "osi", "lp", "solver", "interface")
    homepage = "https://github.com/coin-or/Osi"
    license = "EPL-2.0"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "build_type", "compiler"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("coinutils/2.11.13", transitive_headers=True)

    def validate(self):
        if self.settings.os == "Windows" and self.options.shared:
            raise ConanInvalidConfiguration(
                "osi does not support shared builds on Windows"
            )
        if hasattr(self, "settings_build") and cross_building(self) and self.options.shared:
            raise ConanInvalidConfiguration(
                "osi shared not supported yet when cross-building"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        os.makedirs(self._sample_data_folder(), exist_ok=True)
        get(
            self,
            **self.conan_data["test_sources"]["data_sample"],
            strip_root=True,
            destination=self._sample_data_folder(),
        )
        apply_conandata_patches(self)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-blas",
            "--without-lapack",
            "--without-cplex",
            "--without-gurobi",
            "--without-mosek",
            "--without-xpress",
            "--without-soplex",
            "--without-glpk",
        ])
        # Explicit --build avoids config.guess temp-file failures on HMDFS
        # (verified in coinutils/2.11.13.1); --disable-dependency-tracking
        # avoids HMDFS config.status temp file issues.
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-musl")
            tc.configure_args.append("--disable-dependency-tracking")
        if is_msvc(self):
            tc.extra_cxxflags.append("-EHsc")
            tc.configure_args.append(f"--enable-msvc={msvc_runtime_flag(self)}")
            if check_min_vs(self, "180", raise_invalid=False):
                tc.extra_cflags.append("-FS")
                tc.extra_cxxflags.append("-FS")
        env = tc.environment()
        if is_msvc(self):
            env.define("CC", "cl -nologo")
            env.define("CXX", "cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", "lib -nologo")
        if self._settings_build.os == "Windows":
            env.define("PKG_CONFIG_PATH", self.generators_folder)
        if str(self.settings.os) == "OHOS":
            # COIN-OR configure falls back when pkg-config is unavailable on
            # OHOS; keep the generated .pc dir visible for any remaining
            # PKG_CHECK_MODULES probes (explicit --with-coinutils-* below is
            # the primary bypass, same as coin-or/0.108.12).
            env.define("PKG_CONFIG_PATH", self.generators_folder)
        # HMBS readonly_tmp: /tmp is read-only on HarmonyOS (erofs).
        # Propagate the HMBS-injected writable TMPDIR/TMP/TEMP so autoconf
        # mktemp/config.status temp files never fall back to /tmp.
        # Only the temp root is redirected; no tests are skipped.
        tmpdir = self._writable_tmpdir()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        tc.generate(env)

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            work_folder = self._ohos_work_folder()
            tmpdir = self._writable_tmpdir()
            previous_umask = os.umask(0o002)
            try:
                os.makedirs(work_folder, mode=0o775, exist_ok=True)
                os.makedirs(tmpdir, mode=0o775, exist_ok=True)
            finally:
                os.umask(previous_umask)
            # Export writable TMPDIR to every subprocess (compiler temp files
            # and shell heredocs inherit from os.environ, not just the prefix).
            # Respects HMBS-injected TMPDIR; only the temp root is redirected.
            os.environ["TMPDIR"] = tmpdir
            os.environ["TMP"] = tmpdir
            os.environ["TEMP"] = tmpdir

            # Fix shebangs: /bin/sh and /bin/bash may not exist on OHOS.
            # Prefer HMBS/CONFIG_SHELL bash (respects TMPDIR) over system sh
            # (verified pattern in coinutils/2.11.13.1).
            config_shell = self._build_shell()
            ohos_shell = "/system/bin/sh"
            for script_name in ("configure", "install-sh", "config.sub",
                                "config.guess", "ltmain.sh"):
                for base in (self.source_folder,
                             os.path.join(self.source_folder, "Osi")):
                    sp = os.path.join(base, script_name)
                    if os.path.isfile(sp):
                        self.run(
                            f"sed -i '1s|#!/bin/bash|#!{config_shell}|' '{sp}'")
                        self.run(
                            f"sed -i '1s|#!/bin/sh|#!{ohos_shell}|' '{sp}'")
                        self.run(
                            f"sed -i '1s|#! /bin/sh|#!{ohos_shell}|' '{sp}'")

            configure_scripts = (
                "configure",
                os.path.join("Osi", "configure"),
            )
            for relative_path in configure_scripts:
                configure = os.path.join(self.source_folder, relative_path)
                replace_in_file(
                    self,
                    configure,
                    "(umask 077 && mkdir $tmp)",
                    "(umask 002 && mkdir $tmp)",
                )
                replace_in_file(
                    self,
                    configure,
                    "umask 077 && mktemp -d",
                    "umask 002 && mktemp -d",
                )
            replace_in_file(
                self,
                os.path.join(
                    self.source_folder, "Osi", "src", "Osi", "Makefile.in"
                ),
                "\t$(install_sh_DATA) config_osi.h",
                "\t$(SHELL) $(install_sh_DATA) config_osi.h",
            )
            configure_args = load_toolchain_args(self.generators_folder).get(
                "configure_args", ""
            )
            configure = os.path.join(self.source_folder, "configure")
            # Resolve working compilers explicitly instead of trusting the
            # toolchain default (OHOS has clang only; a stale gcc/cc default
            # surfaces as opaque "C compiler cannot create executables").
            cc = self._resolve_ohos_compiler("c")
            cxx = self._resolve_ohos_compiler("cpp")
            self.output.info(f"OHOS compilers: CC={cc} CXX={cxx}")
            os.environ["CC"] = cc
            os.environ["CXX"] = cxx
            # Smoke test: compile+link+run a minimal program so a real
            # toolchain failure exposes its stderr before configure hides it.
            smoke_c = os.path.join(tmpdir, "ohos_cc_smoke.c")
            smoke_bin = os.path.join(tmpdir, "ohos_cc_smoke")
            with open(smoke_c, "w", encoding="utf-8") as f:
                f.write("int main(void){return 0;}\n")
            self.run(
                f"{self._tmp_env_prefix(tmpdir)}"
                f"{shlex.quote(cc)} {shlex.quote(smoke_c)} "
                f"-o {shlex.quote(smoke_bin)}",
                cwd=work_folder)
            self.run(shlex.quote(smoke_bin), cwd=work_folder)
            # Source conanbuild.sh so CC/CXX from the toolchain are visible
            # even when self.run wraps the command (verified coinutils pattern).
            buildenv = os.path.join(self.generators_folder, "conanbuild.sh")
            source_prefix = f". {shlex.quote(buildenv)} && " if os.path.isfile(buildenv) else ""
            cc_prefix = f"CC={shlex.quote(cc)} CXX={shlex.quote(cxx)} "
            # Bypass pkg-config fallback: OHOS has no pkg-config binary, so
            # AC_COIN_CHECK_PACKAGE skips to the fallback probe which cannot
            # see the Conan cache. Pass absolute coinutils paths explicitly
            # (same flags as the same-upstream coin-or/0.108.12 recipe).
            cu_dir = self.dependencies["coinutils"].package_folder
            coinutils_flags = (
                f" --with-coinutils-incdir={shlex.quote(os.path.join(cu_dir, 'include', 'coin'))}"
                f" --with-coinutils-lib='-L{cu_dir}/lib -lCoinUtils -lz -lm'"
            )
            command = shlex.join([config_shell, configure])
            command = f"CONFIG_SHELL={shlex.quote(config_shell)} {command}"
            command = f"{command}{coinutils_flags}"
            if configure_args:
                command = f"{command} {configure_args}"
            command = f"{self._tmp_env_prefix(tmpdir)}{cc_prefix}{command}"
            try:
                self.run(f"{source_prefix}{command}", cwd=work_folder)
            except Exception:
                for log_rel in ("config.log", os.path.join("Osi", "config.log")):
                    log_path = os.path.join(work_folder, log_rel)
                    if os.path.isfile(log_path):
                        self.run(
                            f"tail -n 120 {shlex.quote(log_path)}",
                            cwd=work_folder)
                raise
            # HMDFS: mktemp with umask 077 fails for ./confstat* temp dirs.
            # Minimal fix: relax umask to 022 (keeps mktemp, HMBS
            # local_mktemp=1) and remove stale temp dirs. Do NOT replace
            # mktemp with fixed ./conftmp: mkdir prints nothing so $tmp
            # stays empty and fallback mkdir fails with "File exists /
            # cannot create a temporary directory in ." on re-run.
            for cs_rel in ("config.status", os.path.join("Osi", "config.status")):
                csp = os.path.join(work_folder, cs_rel)
                if os.path.isfile(csp):
                    self.run(f"sed -i 's|umask 077|umask 022|g' '{csp}'")
                    cs_dir = os.path.dirname(csp)
                    self.run(
                        f"{source_prefix}{self._tmp_env_prefix(tmpdir)}"
                        f"CONFIG_SHELL={shlex.quote(config_shell)} "
                        f"rm -rf ./conftmp ./confstat* && "
                        f"{shlex.quote(config_shell)} config.status",
                        cwd=cs_dir)
            self.run(f"{source_prefix}{self._tmp_env_prefix(tmpdir)}{cc_prefix}make -j1", cwd=work_folder)
            if str(self._settings_build.os) == "OHOS":
                self._run_ohos_upstream_tests(work_folder)
            else:
                self.output.info(
                    "Skipping upstream unitTest execution while cross-building; "
                    "the target executable cannot run on this build machine."
                )
        else:
            autotools.configure()
            autotools.make()
            if cross_building(self):
                self.output.info(
                    "Skipping upstream unitTest execution while cross-building; "
                    "the target executable cannot run on this build machine."
                )
            else:
                autotools.make(target="test")
                self._emit_hmbs_upstream_marker({
                    "status": "passed",
                    "framework": "autotools",
                    "command": "make test",
                    "discovered": 1,
                    "executed": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                })

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) == "OHOS":
            # HMDFS install shim (hardlink=0/chmod=0) makes libtool
            # `install -c .libs/*.a + chmod 644` flaky: install reports
            # success but the file is missing for the subsequent chmod
            # (observed: chmod cannot access .../lib/libOsi.a). Pre-create
            # dest dirs, source the buildenv so the shim is on PATH, try
            # `make install`, then verify and fall back to a pure-Python
            # manual copy (no install/chmod/hardlink) if libs are missing.
            work_folder = self._ohos_work_folder()
            destination = shlex.quote(self.package_folder)
            tmp_prefix = self._tmp_env_prefix(self._writable_tmpdir())
            buildenv = os.path.join(self.generators_folder, "conanbuild.sh")
            source_prefix = (
                f". {shlex.quote(buildenv)} && "
                if os.path.isfile(buildenv) else ""
            )
            os.makedirs(
                os.path.join(self.package_folder, "lib"), exist_ok=True
            )
            os.makedirs(
                os.path.join(self.package_folder, "include", "coin"),
                exist_ok=True,
            )
            try:
                self.run(
                    f"{source_prefix}{tmp_prefix}"
                    f"make install DESTDIR={destination} -j1",
                    cwd=work_folder,
                )
            except Exception:
                self.output.warning(
                    "make install failed, falling back to manual copy"
                )
            missing_libs = not glob.glob(
                os.path.join(self.package_folder, "lib", "libOsi*.a")
            )
            # Upstream public headers are .hpp (e.g. OsiRowCut.hpp); a
            # successful `make install` must stage them. Check explicitly so
            # a libs-only install still triggers the manual header staging.
            missing_headers = not os.path.isfile(
                os.path.join(
                    self.package_folder, "include", "coin", "OsiRowCut.hpp")
            )
            if missing_libs or missing_headers:
                if missing_libs:
                    self.output.warning(
                        "make install did not stage libOsi.a, "
                        "copying built artifacts manually"
                    )
                else:
                    self.output.warning(
                        "make install staged libs but missed Osi headers, "
                        "copying headers manually"
                    )
                for lib in glob.glob(
                    os.path.join(work_folder, "**", ".libs", "*.a"),
                    recursive=True,
                ):
                    copy(self, os.path.basename(lib),
                         src=os.path.dirname(lib),
                         dst=os.path.join(self.package_folder, "lib"))
                # Public headers live in-source (.hpp, e.g. OsiRowCut.hpp, plus
                # .h); generated config headers live in the out-of-source
                # work folder. Stage both.
                for pattern in ("*.h", "*.hpp"):
                    for header in glob.glob(
                        os.path.join(
                            self.source_folder, "Osi", "src", "Osi", pattern),
                    ):
                        copy(self, os.path.basename(header),
                             src=os.path.dirname(header),
                             dst=os.path.join(
                                 self.package_folder, "include", "coin"))
                    for header in glob.glob(
                        os.path.join(
                            self.source_folder, "Osi", "src",
                            "OsiCommonTest", pattern),
                    ):
                        copy(self, os.path.basename(header),
                             src=os.path.dirname(header),
                             dst=os.path.join(
                                 self.package_folder, "include", "coin"))
                for header in glob.glob(
                    os.path.join(work_folder, "**", "config_osi.h"),
                    recursive=True,
                ):
                    copy(self, os.path.basename(header),
                         src=os.path.dirname(header),
                         dst=os.path.join(
                             self.package_folder, "include", "coin"))
                staged = glob.glob(
                    os.path.join(self.package_folder, "lib", "*.a"))
                if not staged:
                    raise ConanInvalidConfiguration(
                        "OHOS manual install fallback found no built "
                        f"libraries under {work_folder}"
                    )
                if not os.path.isfile(
                    os.path.join(
                        self.package_folder, "include", "coin",
                        "OsiRowCut.hpp")
                ):
                    raise ConanInvalidConfiguration(
                        "OHOS manual install fallback staged no "
                        "OsiRowCut.hpp; check Osi/src/Osi/*.hpp sources"
                    )
        else:
            autotools = Autotools(self)
            autotools.install(args=["-j1"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)
        if is_msvc(self):
            for libname in ("Osi", "OsiCommonTests"):
                rename(self,
                       os.path.join(self.package_folder, "lib", f"lib{libname}.lib"),
                       os.path.join(self.package_folder, "lib", f"{libname}.lib"))
        self._sign_shared_libraries()
        self._stage_upstream_marker()

    def _stage_upstream_marker(self):
        # Stage the build-time upstream marker into package res/ so
        # test_package can re-emit the real result on cache-hit runs
        # where build() is skipped. Missing file: warn only, never forge.
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream_test_result.json")
            if os.path.isfile(src):
                res_dir = os.path.join(self.package_folder, "res")
                os.makedirs(res_dir, exist_ok=True)
                shutil.copy2(src, os.path.join(res_dir, "hmbs_upstream_test_result.json"))
                txt = os.path.join(self.build_folder, "hmbs_upstream_test_result.txt")
                if os.path.isfile(txt):
                    shutil.copy2(txt, os.path.join(res_dir, "hmbs_upstream_test_result.txt"))
            else:
                self.output.warning(
                    "Upstream marker persistence file not found in build folder; "
                    "cache-hit runs will rely on package res from a previous build."
                )
        except Exception as exc:
            self.output.warning(f"Could not stage upstream marker: {exc}")

    def _ohos_work_folder(self):
        return os.path.join(self.build_folder, "ohos-work")

    def _sample_data_folder(self):
        return os.path.join(self.source_folder, "_test_data", "Sample")

    def _writable_tmpdir(self):
        # HMBS injects a task-private writable TMPDIR (HMDFS); /tmp is erofs
        # read-only on HarmonyOS. Reuse it verbatim; only fall back to a
        # build-folder directory when the injected vars are absent (e.g.
        # local `conan create` outside preflight).
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key, "").strip()
            if candidate:
                return candidate
        fallback = os.path.join(self.build_folder, "tmp")
        return fallback

    def _tmp_env_prefix(self, tmpdir):
        quoted = shlex.quote(tmpdir)
        return f"TMPDIR={quoted} TMP={quoted} TEMP={quoted} "

    def _build_shell(self):
        # Prefer bash (respects TMPDIR) over system sh (mksh hardcodes /tmp
        # for heredoc/command-substitution temp files, which is erofs
        # read-only). NB: conanbuild.sh may export CONFIG_SHELL=/bin/sh,
        # so only accept CONFIG_SHELL when it points at bash; otherwise
        # an mksh config_shell reintroduces the readonly /tmp failure.
        bash_candidates = ["/data/service/hnp/bin/bash"]
        env_shell = os.environ.get("CONFIG_SHELL", "").strip()
        if env_shell and os.path.basename(env_shell) in ("bash", "bash.exe"):
            bash_candidates.insert(0, env_shell)
        for candidate in tuple(bash_candidates):
            if candidate and os.path.isfile(candidate):
                return candidate
        if str(self._settings_build.os) == "OHOS":
            return "/system/bin/sh"
        shell = shutil.which("sh")
        if not shell:
            raise ConanInvalidConfiguration(
                "osi requires sh on the build machine"
            )
        return shell

    def _resolve_ohos_compiler(self, kind):
        # Resolve a working compiler without trusting a single conf value.
        # Chain: conf tools.build:compiler_executables -> env CC/CXX ->
        # PATH lookup -> well-known OHOS toolchain dir -> bare name.
        # Only absolute paths verified with isfile are used directly;
        # otherwise fall back to PATH/bare names so the real toolchain
        # error surfaces instead of a stale conf path.
        conf_map = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        conf_key = "c" if kind == "c" else "cpp"
        env_key = "CC" if kind == "c" else "CXX"
        bare = "clang" if kind == "c" else "clang++"
        candidates = []
        conf_val = (conf_map.get(conf_key, "") or "").strip()
        if conf_val:
            first = shlex.split(conf_val)[0] if conf_val else ""
            if first and os.path.isabs(first) and os.path.isfile(first):
                return conf_val
            if first:
                candidates.append(first)
        env_val = (os.environ.get(env_key, "") or "").strip()
        if env_val:
            candidates.append(shlex.split(env_val)[0])
        which_bare = shutil.which(bare)
        if which_bare:
            candidates.append(which_bare)
        candidates.append(os.path.join("/data/service/hnp/bin", bare))
        candidates.append(conf_val)
        candidates.append(bare)
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if os.path.isabs(candidate):
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
            else:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved
                return candidate
        return bare

    def _sign_shared_libraries(self):
        if str(self.settings.os) != "OHOS" or not self.options.get_safe("shared"):
            return

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS shared libraries require llvm-objcopy and binary-sign-tool"
            )

        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        for library in libraries:
            if os.path.islink(library):
                continue
            self._sign_elf_atomically(library, objcopy, signer)

    def _run_ohos_upstream_tests(self, work_folder):
        test_dir = os.path.join(work_folder, "Osi", "test")
        tmp_prefix = self._tmp_env_prefix(self._writable_tmpdir())
        cc = os.environ.get("CC", "").strip() or self._resolve_ohos_compiler("c")
        cxx = os.environ.get("CXX", "").strip() or self._resolve_ohos_compiler("cpp")
        cc_prefix = f"CC={shlex.quote(cc)} CXX={shlex.quote(cxx)} "
        buildenv = os.path.join(self.generators_folder, "conanbuild.sh")
        source_prefix = f". {shlex.quote(buildenv)} && " if os.path.isfile(buildenv) else ""
        self.run(f"{source_prefix}{tmp_prefix}{cc_prefix}make unitTest -j1", cwd=test_dir)
        unit_test = os.path.join(test_dir, "unitTest")
        self._sign_ohos_executable(unit_test)
        unittestflags = f"unittestflags=-mpsDir={self._sample_data_folder()}"
        self.run(f"{source_prefix}{tmp_prefix}{cc_prefix}make test -j1 {shlex.quote(unittestflags)}", cwd=test_dir)
        self._emit_hmbs_upstream_marker({
            "status": "passed",
            "framework": "autotools",
            "command": "make -C Osi/test test unittestflags=-mpsDir=<Data-Sample>",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
        })

    def _emit_hmbs_upstream_marker(self, marker):
        line = f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(marker, separators=(',', ':'))}"
        # Dual channel: print() reaches stdout directly, output.info reaches
        # the Conan log. Both land in the preflight log for the HMBS parser.
        print(line, flush=True)
        self.output.info(line)
        # Persist to the build folder so package() can stage it into the
        # package res/ dir for cache-hit re-emission from test_package.
        try:
            build_dir = self.build_folder
            if build_dir:
                with open(os.path.join(build_dir, "hmbs_upstream_test_result.json"),
                          "w", encoding="utf-8") as f:
                    json.dump(marker, f)
                with open(os.path.join(build_dir, "hmbs_upstream_test_result.txt"),
                          "w", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception as exc:
            self.output.warning(f"Could not persist upstream marker: {exc}")

    def _sign_ohos_executable(self, path):
        if str(self.settings.os) != "OHOS":
            return
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(f"OHOS test executable not found: {path}")

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS upstream tests require llvm-objcopy and binary-sign-tool"
            )
        self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")

    def package_info(self):
        self.cpp_info.components["libosi"].set_property("pkg_config_name", "osi")
        self.cpp_info.components["libosi"].libs = ["Osi"]
        self.cpp_info.components["libosi"].includedirs = [
            os.path.join("include", "coin")
        ]
        self.cpp_info.components["libosi"].requires = ["coinutils::coinutils"]

        self.cpp_info.components["osi-unittests"].set_property(
            "pkg_config_name", "osi-unittests"
        )
        self.cpp_info.components["osi-unittests"].libs = ["OsiCommonTests"]
        self.cpp_info.components["osi-unittests"].requires = ["libosi"]
