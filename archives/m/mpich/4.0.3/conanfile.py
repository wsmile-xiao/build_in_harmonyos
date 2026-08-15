#!/usr/bin/env python3
"""Conan recipe for MPICH 4.0.3."""

import os
import shutil
from shlex import quote

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import collect_libs, copy, get, replace_in_file, rm, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MpichConan(ConanFile):
    name = "mpich"
    version = "4.0.3"
    description = "Portable implementation of the Message Passing Interface (MPI)"
    license = "MPICH"
    homepage = "https://www.mpich.org/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def build_requirements(self):
        self.tool_requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _config_shell(self):
        configured = os.environ.get("CONFIG_SHELL")
        if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        return shutil.which("bash") or shutil.which("sh") or "/system/bin/sh"

    def _compiler_executable(self, key, fallback):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        configured = compilers.get(key)
        candidate = configured
        if not (candidate and os.path.isfile(candidate)):
            candidate = shutil.which(fallback) or configured or fallback
        return self._shell_wrapped(candidate)

    def _tool_executable(self, *names):
        for name in names:
            candidate = shutil.which(name)
            if candidate:
                return self._shell_wrapped(candidate)
        return names[-1]

    def _shell_wrapped(self, candidate):
        if candidate and os.path.isfile(candidate):
            with open(candidate, "r", encoding="utf-8", errors="ignore") as wrapper:
                first_line = wrapper.readline()
            if first_line.startswith("#!") and "/bin/sh" in first_line:
                return f"{self._config_shell()} {candidate}"
        return candidate

    def _make_executable(self, path):
        os.chmod(path, os.stat(path).st_mode | 0o111)

    def _run_upstream_tests_enabled(self):
        value = os.environ.get("MPICH_RUN_UPSTREAM_TESTS", "").lower()
        return value in ("1", "on", "true", "yes")

    def _rewrite_wrapper_prefixes(self, root_folder):
        root_from_bin = "\n".join([
            'script_dir=$(dirname "$0")',
            'prefix=$(cd "$script_dir/.." && pwd)',
            'exec_prefix=$prefix',
            'sysconfdir=$prefix/etc',
            'includedir=$prefix/include',
            'libdir=$prefix/lib',
        ])
        for wrapper in ("mpicc", "mpicxx", "mpifort"):
            wrapper_path = os.path.join(root_folder, "bin", wrapper)
            if os.path.exists(wrapper_path):
                replace_in_file(
                    self,
                    wrapper_path,
                    "prefix=/\nexec_prefix=/\nsysconfdir=//etc\nincludedir=//include\nlibdir=//lib",
                    root_from_bin,
                )

    def _relax_autoconf_tmp_permissions(self):
        shell = self._config_shell()
        executable_helpers = {
            "compile",
            "config.guess",
            "config.rpath",
            "config.sub",
            "configure",
            "depcomp",
            "install-sh",
            "missing",
            "mkinstalldirs",
        }
        for root, _, files in os.walk(self.source_folder):
            for filename in files:
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8", errors="ignore") as script:
                    content = script.read()
                relaxed = content
                if filename == "configure":
                    relaxed = relaxed.replace("umask 077", "umask 002")
                    relaxed = relaxed.replace(
                        'if $ac_aux_dir/config.rpath "$host" > ',
                        'if ${CONFIG_SHELL:-/bin/sh} $ac_aux_dir/config.rpath "$host" > ',
                    )
                first_line, separator, rest = relaxed.partition("\n")
                is_script = first_line.startswith("#!")
                if is_script and ("/bin/sh" in first_line or "/bin/bash" in first_line):
                    relaxed = f"#!{shell}{separator}{rest}"
                if relaxed != content:
                    with open(path, "w", encoding="utf-8") as script:
                        script.write(relaxed)
                if is_script or filename in executable_helpers:
                    self._make_executable(path)

    def _configure_args(self):
        shared = bool(self.options.shared)
        args = [
            "--prefix=/",
            "--disable-fortran",
            "--disable-cxx",
            "--disable-romio",
            "--with-device=ch3:sock",
            "--with-pm=gforker",
            "--with-pmi=simple",
            "--with-hwloc=no",
            "--with-wrapper-dl-type=none",
            "--enable-fast=all",
            "--enable-g=none",
            "--enable-shared" if shared else "--disable-shared",
            "--disable-static" if shared else "--enable-static",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            args.append("--build=aarch64-unknown-linux-gnu")
        bash = self._config_shell()
        args.append(f"CONFIG_SHELL={bash}")
        return args

    def _make_tool_args(self, bash, cc, cxx, ar, ranlib, nm, ld):
        return [
            f"SHELL={quote(bash)}",
            f"CONFIG_SHELL={quote(bash)}",
            f"CC={quote(cc)}",
            f"CXX={quote(cxx)}",
            f"AR={quote(ar)}",
            f"RANLIB={quote(ranlib)}",
            f"NM={quote(nm)}",
            f"LD={quote(ld)}",
        ]

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def _run_upstream_tests(self, bash, cc, cxx, ar, ranlib, nm, ld):
        os.environ.setdefault("RUNTESTS_SHOWPROGRESS", "1")
        os.environ.setdefault("MPITEST_RETURN_WITH_CODE", "yes")
        perl = shutil.which("perl") or "perl"
        if os.path.isabs(perl):
            perl_root = os.path.dirname(os.path.dirname(perl))
            perl_lib = os.path.join(perl_root, "lib", "perl5")
            perl_paths = [
                os.path.join(perl_lib, "site_perl", "5.42.2", "aarch64-linux-thread-multi"),
                os.path.join(perl_lib, "site_perl", "5.42.2"),
                os.path.join(perl_lib, "vendor_perl", "5.42.2", "aarch64-linux-thread-multi"),
                os.path.join(perl_lib, "vendor_perl", "5.42.2"),
                os.path.join(perl_lib, "5.42.2", "aarch64-linux-thread-multi"),
                os.path.join(perl_lib, "5.42.2"),
            ]
            perl_paths = [path for path in perl_paths if os.path.isdir(path)]
            if perl_paths:
                existing = os.environ.get("PERL5LIB")
                os.environ["PERL5LIB"] = os.pathsep.join(perl_paths + ([existing] if existing else []))

        test_prefix = os.path.join(self.build_folder, "upstream-test-install")
        test_build = os.path.join(self.build_folder, "upstream-test-build")
        os.makedirs(test_prefix, exist_ok=True)
        os.makedirs(test_build, exist_ok=True)

        tool_args = self._make_tool_args(bash, cc, cxx, ar, ranlib, nm, ld)
        self.run(
            " ".join(["make -j1 install", f"DESTDIR={quote(test_prefix)}", *tool_args]),
            env="conanbuild",
        )
        self._rewrite_wrapper_prefixes(test_prefix)

        os.environ["PATH"] = os.path.join(test_prefix, "bin") + os.pathsep + os.environ.get("PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.path.join(test_prefix, "lib") + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")

        configure = os.path.join(self.source_folder, "test", "mpi", "configure")
        configure_args = [
            f"--with-mpi={test_prefix}",
            "--enable-fortran=no",
            "--enable-cxx=no",
            "--enable-romio=no",
            "--enable-fast",
            "--build=aarch64-unknown-linux-gnu",
            f"CONFIG_SHELL={bash}",
            f"PERL={perl}",
            f"PYTHON={shutil.which('python3') or 'python3'}",
            f"MPICXX={cxx}",
            f"CXX={cxx}",
            f"CXXCPP={cxx} -E",
        ]
        shell_env = (
            f"SHELL={quote(bash)} CONFIG_SHELL={quote(bash)} "
            f"CC={quote(cc)} CXX={quote(cxx)} "
            f"AR={quote(ar)} RANLIB={quote(ranlib)} NM={quote(nm)} LD={quote(ld)}"
        )
        self.run(
            f"cd {quote(test_build)} && {shell_env} {quote(bash)} {quote(configure)} "
            + " ".join(quote(arg) for arg in configure_args),
            env="conanbuild",
        )
        self._prepare_upstream_test_runner(test_build)

        test_args = ["make -j1 testing", *tool_args, "SUMMARY_BASENAME=summary-ohos-upstream"]
        testlist = os.environ.get("MPICH_UPSTREAM_TESTLIST")
        if testlist:
            test_args.append(f"TESTLIST={quote(testlist)}")
        testdirs = os.environ.get("MPICH_UPSTREAM_TESTDIRS")
        if testdirs:
            test_args.append(f"TESTDIRS={quote(testdirs)}")
        self.run(f"cd {quote(test_build)} && " + " ".join(test_args), env="conanbuild")
        self._assert_upstream_test_summary(test_build)

    def _prepare_upstream_test_runner(self, test_build):
        test_tmp = os.path.join(test_build, "tmp").replace("\\", "/")
        os.makedirs(test_tmp, exist_ok=True)
        runtests = os.path.join(test_build, "runtests")
        if os.path.exists(runtests):
            replace_in_file(self, runtests, '"/tmp/runtests-$name.lock"', f'"{test_tmp}/runtests-$name.lock"')
            replace_in_file(self, runtests, '"/tmp/runtests-mem.lock"', f'"{test_tmp}/runtests-mem.lock"')

    def _assert_upstream_test_summary(self, test_build):
        tap = os.path.join(test_build, "summary-ohos-upstream.tap")
        if not os.path.exists(tap):
            raise ConanException("MPICH upstream test TAP summary was not generated")
        passed = 0
        failed = 0
        skipped = 0
        with open(tap, "r", encoding="utf-8", errors="ignore") as summary:
            for line in summary:
                if line.startswith("not ok "):
                    failed += 1
                elif line.startswith("ok "):
                    passed += 1
                    if "# skip" in line.lower():
                        skipped += 1
        self.output.info(f"MPICH upstream tests: passed={passed} failed={failed} skipped={skipped}")
        if failed:
            raise ConanException(f"MPICH upstream tests failed: {failed} not ok entries in {tap}")

    def build(self):
        self._relax_autoconf_tmp_permissions()

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMPPREFIX"] = os.path.join(tmpdir, "sh")

        autotools = Autotools(self)
        bash = self._config_shell()
        cc = self._compiler_executable("c", "clang")
        cxx = self._compiler_executable("cpp", "clang++")
        ar = self._tool_executable("llvm-ar", "ar")
        ranlib = self._tool_executable("llvm-ranlib", "ranlib")
        nm = self._tool_executable("llvm-nm", "nm")
        ld = self._tool_executable("ld.lld", "lld", "ld")
        os.environ["SHELL"] = bash
        os.environ["CONFIG_SHELL"] = bash
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        os.environ["AR"] = ar
        os.environ["RANLIB"] = ranlib
        os.environ["NM"] = nm
        os.environ["LD"] = ld
        configure = os.path.join(self.source_folder, "configure")
        configure_args = " ".join(quote(arg) for arg in self._configure_args())
        shell_env = (
            f"SHELL={quote(bash)} CONFIG_SHELL={quote(bash)} "
            f"CC={quote(cc)} CXX={quote(cxx)} "
            f"AR={quote(ar)} RANLIB={quote(ranlib)} NM={quote(nm)} LD={quote(ld)}"
        )
        self.run(f"{shell_env} {quote(bash)} {quote(configure)} {configure_args}", env="conanbuild")
        self.run(
            " ".join(["make -j2", *self._make_tool_args(bash, cc, cxx, ar, ranlib, nm, ld)]),
            env="conanbuild",
        )
        # Full upstream MPI tests are large and require a scheduled device slot.
        # Set MPICH_RUN_UPSTREAM_TESTS=1 for the scheduled validation run.
        if self._run_upstream_tests_enabled():
            self._run_upstream_tests(bash, cc, cxx, ar, ranlib, nm, ld)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYRIGHT", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._rewrite_wrapper_prefixes(self.package_folder)
        for pattern in ("*.la", "*.dylib"):
            rm(self, pattern, folder=os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = libs or ["mpi"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "MPI")
        self.cpp_info.set_property("cmake_target_name", "MPI::MPI_C")
        self.cpp_info.set_property("pkg_config_name", "mpich")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
