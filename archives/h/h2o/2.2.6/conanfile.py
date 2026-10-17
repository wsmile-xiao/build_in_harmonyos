#!/usr/bin/env python3
"""Conan recipe for the H2O HTTP server 2.2.6 on OpenHarmony."""

import glob
import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    export_conandata_patches,
    get,
    load,
    save,
    unzip,
)
from conan.tools.gnu import PkgConfigDeps


class H2OConan(ConanFile):
    name = "h2o"
    version = "2.2.6"
    description = "Optimized HTTP server with HTTP/2 support"
    license = "MIT"
    homepage = "https://github.com/h2o/h2o"
    url = "https://github.com/h2o/h2o"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_upstream_tests": [True, False],
    }
    default_options = {"shared": False, "with_upstream_tests": False}

    def requirements(self):
        self.requires("libuv/1.52.1")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        if self.options.with_upstream_tests:
            # The upstream `check` target invokes Perl's prove runner.
            self.tool_requires("perl/5.42.2")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        archive_dir = os.environ.get("H2O_SOURCE_ARCHIVE_DIR")
        self._extract_source(self.conan_data["sources"], self.source_folder, archive_dir)
        self._verify_bundled_dependencies()
        for submodule in self.conan_data["submodules"]:
            destination = os.path.join(self.source_folder, submodule["path"])
            self._extract_source(submodule, destination, archive_dir)
        apply_conandata_patches(self)
        self._disable_neverbleed_for_ohos_upstream_tests()

    def _verify_bundled_dependencies(self):
        for dependency in self.conan_data["bundled_dependencies"]:
            required_file = os.path.join(
                self.source_folder, dependency["path"], dependency["required_file"]
            )
            if not os.path.isfile(required_file):
                raise ConanInvalidConfiguration(
                    "H2O source archive is missing the bundled dependency input: "
                    f"{dependency['path']}/{dependency['required_file']}"
                )

    def _disable_neverbleed_for_ohos_upstream_tests(self):
        """Bypass the target-rejected neverbleed child only in native tests."""
        if os.environ.get("H2O_TEST_DISABLE_NEVERBLEED") != "1":
            return

        source = os.path.join(self.source_folder, "src", "main.c")
        contents = load(self, source)
        include_marker = "#include <stdio.h>\n#include <unistd.h>\n"
        include_replacement = "#include <stdio.h>\n#include <stdlib.h>\n#include <unistd.h>\n"
        neverbleed_marker = (
            "    int use_neverbleed = 1, use_picotls = 1;     /* enabled by default */\n\n"
            "    if (!listener_is_new) {"
        )
        neverbleed_replacement = (
            "    int use_neverbleed = 1, use_picotls = 1;     /* enabled by default */\n"
            "    if (getenv(\"H2O_TEST_DISABLE_NEVERBLEED\") != NULL)\n"
            "        use_neverbleed = 0;\n\n"
            "    if (!listener_is_new) {"
        )
        if include_marker not in contents or neverbleed_marker not in contents:
            raise ConanInvalidConfiguration(
                "H2O source did not match the guarded neverbleed test preparation"
            )
        contents = contents.replace(include_marker, include_replacement, 1)
        save(self, source, contents.replace(neverbleed_marker, neverbleed_replacement, 1))

        fastcgi_source = os.path.join(
            self.source_folder, "lib", "handler", "configurator", "fastcgi.c"
        )
        fastcgi_contents = load(self, fastcgi_source)
        fastcgi_marker = '    char dirname[] = "/tmp/h2o.fcgisock.XXXXXX";\n'
        fastcgi_replacement = (
            "    char dirname[1024];\n"
            "    const char *test_tmpdir = getenv(\"H2O_TEST_TMPDIR\");\n"
            "    if (test_tmpdir != NULL && *test_tmpdir != '\\0') {\n"
            "        int dirname_len = snprintf(dirname, sizeof(dirname), \"%s/h2o.fcgisock.XXXXXX\", test_tmpdir);\n"
            "        if (dirname_len < 0 || (size_t)dirname_len >= sizeof(dirname)) {\n"
            "            h2o_configurator_errprintf(cmd, node, \"H2O_TEST_TMPDIR is too long\");\n"
            "            return -1;\n"
            "        }\n"
            "    } else {\n"
            "        snprintf(dirname, sizeof(dirname), \"%s\", \"/tmp/h2o.fcgisock.XXXXXX\");\n"
            "    }\n"
        )
        if fastcgi_marker not in fastcgi_contents:
            raise ConanInvalidConfiguration(
                "H2O FastCGI source did not match the guarded test preparation"
            )
        fastcgi_argv_marker = "    char *argv[10];\n"
        fastcgi_helper_marker = (
            "        argv[i++] = kill_on_close_cmd_path = "
            "h2o_configurator_get_cmd_path(\"share/h2o/kill-on-close\");\n"
        )
        if (
            fastcgi_argv_marker not in fastcgi_contents
            or fastcgi_helper_marker not in fastcgi_contents
        ):
            raise ConanInvalidConfiguration(
                "H2O FastCGI helper launch did not match the guarded test preparation"
            )
        fastcgi_contents = fastcgi_contents.replace(
            fastcgi_marker, fastcgi_replacement, 1
        )
        fastcgi_contents = fastcgi_contents.replace(
            fastcgi_argv_marker, "    char *argv[11];\n", 1
        ).replace(
            fastcgi_helper_marker,
            "        kill_on_close_cmd_path = "
            "h2o_configurator_get_cmd_path(\"share/h2o/kill-on-close\");\n"
            "        argv[i++] = \"/bin/sh\";\n"
            "        argv[i++] = kill_on_close_cmd_path;\n",
            1,
        )
        save(self, fastcgi_source, fastcgi_contents)

        env_test_source = os.path.join(self.source_folder, "t", "40env.t")
        env_test_contents = load(self, env_test_source)
        env_test_marker = '  fastcgi.spawn: "exec \\$H2O_ROOT/share/h2o/fastcgi-cgi"\n'
        if env_test_marker not in env_test_contents:
            raise ConanInvalidConfiguration(
                "H2O environment test did not match the guarded test preparation"
            )
        save(
            self,
            env_test_source,
            env_test_contents.replace(
                env_test_marker,
                '  fastcgi.spawn: "exec /bin/sh \\$H2O_ROOT/share/h2o/fastcgi-cgi"\n',
                1,
            ),
        )

    def _extract_source(self, source, destination, archive_dir):
        if archive_dir:
            archive = os.path.join(archive_dir, source["archive"])
            if not os.path.isfile(archive):
                raise ConanInvalidConfiguration(
                    f"H2O source archive does not exist: {archive}"
                )
            check_sha256(self, archive, source["sha256"])
            unzip(self, archive, destination=destination, strip_root=True)
            return
        get(
            self,
            url=source["url"],
            sha256=source["sha256"],
            filename=source["archive"],
            destination=destination,
            strip_root=True,
        )

    def generate(self):
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._write_openssl_compat_module()
        self._write_zlib_compat_module()
        compat_prelude = self._write_cmake_compat_prelude()
        toolchain = CMakeToolchain(self)
        # H2O 2.2.6 calls FIND_PACKAGE(OpenSSL) and consumes FindOpenSSL's
        # legacy variables, while CMakeDeps exports lowercase `openssl`.
        toolchain.variables["CMAKE_MODULE_PATH"] = self.generators_folder
        # H2O checks the uppercase legacy OpenSSL variables after PROJECT().
        # CMakeDeps exposes a Config package first on the CI image, so load the
        # bridge explicitly before H2O's subsequent FIND_PACKAGE calls.
        toolchain.variables["CMAKE_PROJECT_h2o_INCLUDE"] = compat_prelude
        toolchain.variables["BUILD_SHARED_LIBS"] = self.options.shared
        toolchain.variables["WITH_BUNDLED_SSL"] = False
        toolchain.variables["WITH_MRUBY"] = False
        toolchain.variables["WITH_PICOTLS"] = True
        toolchain.generate()

    def _write_cmake_compat_prelude(self):
        """Load Conan dependency bridges immediately after H2O's PROJECT call."""
        prelude = os.path.join(self.generators_folder, "h2o-conan-compat.cmake")
        save(
            self,
            prelude,
            "include(\"${CMAKE_CURRENT_LIST_DIR}/FindOpenSSL.cmake\")\n"
            "include(\"${CMAKE_CURRENT_LIST_DIR}/FindZLIB.cmake\")\n",
        )
        return prelude

    def _write_openssl_compat_module(self):
        openssl_version = self.dependencies["openssl"].ref.version
        compat_contents = f"""# Bridge H2O's legacy OpenSSL contract to Conan CMakeDeps.
include("${{CMAKE_CURRENT_LIST_DIR}}/openssl-config.cmake")
if(NOT TARGET openssl::openssl)
    message(FATAL_ERROR "Conan OpenSSL target is missing")
endif()
set(OpenSSL_FOUND TRUE)
set(OPENSSL_FOUND TRUE)
set(OpenSSL_VERSION "{openssl_version}")
set(OPENSSL_VERSION "{openssl_version}")
set(OPENSSL_INCLUDE_DIR "${{openssl_INCLUDE_DIRS}}")
set(OPENSSL_INCLUDE_DIRS "${{openssl_INCLUDE_DIRS}}")
set(OPENSSL_LIBRARIES openssl::openssl)
"""
        save(
            self,
            os.path.join(self.generators_folder, "FindOpenSSL.cmake"),
            compat_contents,
        )

    def _write_zlib_compat_module(self):
        zlib_version = self.dependencies["zlib"].ref.version
        compat_contents = f"""# Bridge H2O's legacy Zlib contract to Conan CMakeDeps.
include("${{CMAKE_CURRENT_LIST_DIR}}/zlib-config.cmake")
if(NOT TARGET zlib::zlib)
    message(FATAL_ERROR "Conan ZLIB target is missing")
endif()
if(NOT TARGET ZLIB::ZLIB)
    add_library(ZLIB::ZLIB INTERFACE IMPORTED)
    target_link_libraries(ZLIB::ZLIB INTERFACE zlib::zlib)
endif()
set(ZLIB_FOUND TRUE)
set(ZLIB_VERSION "{zlib_version}")
set(ZLIB_INCLUDE_DIR "${{zlib_INCLUDE_DIRS}}")
set(ZLIB_INCLUDE_DIRS "${{zlib_INCLUDE_DIRS}}")
set(ZLIB_LIBRARY_DIRS "${{zlib_LIB_DIRS}}")
set(ZLIB_LIBRARIES ZLIB::ZLIB)
"""
        save(
            self,
            os.path.join(self.generators_folder, "FindZLIB.cmake"),
            compat_contents,
        )

    def build(self):
        cmake = CMake(self)
        # CMake reads this before it evaluates H2O's legacy top-level project.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        # H2O's upstream test entry is the custom CMake `check` target.
        if self._can_run_upstream_tests():
            perl = self.dependencies.build["perl"]
            self._install_pinned_test_modules(perl)
            self._run_complete_upstream_tap(perl)
        elif self.options.with_upstream_tests:
            self.output.info(
                "with_upstream_tests requested, but this is not a native runnable "
                "build; leaving H2O upstream tests disabled"
            )

    def _can_run_upstream_tests(self):
        return (
            bool(self.options.with_upstream_tests)
            and can_run(self)
            and not cross_building(self)
        )

    def _install_pinned_test_modules(self, perl):
        """Install the upstream Perl test closure below the build folder.

        These archives are deliberately neither Conan requirements nor package
        contents. A native test must receive a complete offline directory via
        H2O_TEST_CPAN_ARCHIVE_DIR; each archive is checked before extraction so
        the test cannot silently resolve a different CPAN release or use
        cpanm's network solver.
        """
        archive_dir = os.environ.get("H2O_TEST_CPAN_ARCHIVE_DIR")
        if not archive_dir:
            raise ConanInvalidConfiguration(
                "H2O upstream tests require H2O_TEST_CPAN_ARCHIVE_DIR with the "
                "SHA-256-pinned CPAN closure from conandata.yml"
            )
        if not os.path.isdir(archive_dir):
            raise ConanInvalidConfiguration(
                f"H2O_TEST_CPAN_ARCHIVE_DIR is not a directory: {archive_dir}"
            )

        perl_bin = os.path.join(perl.package_folder, "bin", "perl")
        if not os.path.isfile(perl_bin):
            raise ConanInvalidConfiguration(
                "H2O upstream tests require perl/5.42.2 to provide bin/perl"
            )

        test_root = os.path.join(self.build_folder, "h2o-upstream-test-perl")
        test_prefix = os.path.join(test_root, "prefix")
        sources_dir = os.path.join(test_root, "sources")
        os.makedirs(test_prefix, exist_ok=True)
        os.makedirs(sources_dir, exist_ok=True)
        runner = self._create_perl_test_runner(perl, test_prefix, self.source_folder)

        for distribution in self.conan_data["upstream_test_cpan"]:
            archive = os.path.join(archive_dir, distribution["archive"])
            if not os.path.isfile(archive):
                raise ConanInvalidConfiguration(
                    "H2O upstream tests require the pinned CPAN archive: "
                    f"{distribution['archive']}"
                )
            check_sha256(self, archive, distribution["sha256"])

            source_dir = os.path.join(
                sources_dir, distribution["archive"].removesuffix(".tar.gz")
            )
            if os.path.isdir(source_dir):
                shutil.rmtree(source_dir)
            os.makedirs(source_dir, exist_ok=True)
            unzip(self, archive, destination=source_dir, strip_root=True)
            self._install_perl_distribution(runner, perl_bin, source_dir, test_prefix)

        return test_prefix

    def _create_perl_test_runner(self, perl, test_prefix, h2o_source):
        """Write a shell runner that keeps pure-Perl and XS paths aligned."""
        perl_bin = os.path.join(perl.package_folder, "bin", "perl")
        perl_core = os.path.join(
            perl.package_folder, "lib", "perl5", str(perl.ref.version)
        )
        if not os.path.isdir(perl_core):
            raise ConanInvalidConfiguration(
                f"H2O upstream tests require the Conan Perl core library: {perl_core}"
            )
        core_arch_dirs = [
            entry
            for entry in os.listdir(perl_core)
            if os.path.isfile(os.path.join(perl_core, entry, "Config.pm"))
            and os.path.isfile(os.path.join(perl_core, entry, "Config_heavy.pl"))
        ]
        if len(core_arch_dirs) != 1:
            raise ConanInvalidConfiguration(
                "H2O upstream tests require exactly one Conan Perl architecture "
                f"library below {perl_core}; found {core_arch_dirs}"
            )
        tools_dir = os.path.join(self.build_folder, "h2o-upstream-test-tools")
        os.makedirs(tools_dir, exist_ok=True)
        openssl_conf = os.path.join(tools_dir, "openssl-tls12.cnf")
        save(
            self,
            openssl_conf,
            "openssl_conf = openssl_init\n\n"
            "[openssl_init]\n"
            "ssl_conf = ssl_sect\n\n"
            "[ssl_sect]\n"
            "system_default = system_default_sect\n\n"
            "[system_default_sect]\n"
            "MinProtocol = TLSv1.2\n"
            "MaxProtocol = TLSv1.2\n",
        )
        test_tmp = os.environ.get("H2O_TEST_TMPDIR")
        if not test_tmp:
            raise ConanInvalidConfiguration(
                "H2O upstream tests require H2O_TEST_TMPDIR to name a short, "
                "writable, test-only directory"
            )
        if not os.path.isabs(test_tmp):
            raise ConanInvalidConfiguration(
                f"H2O_TEST_TMPDIR must be an absolute path: {test_tmp}"
            )
        test_tmp = os.path.abspath(test_tmp)
        neverbleed_socket = os.path.join(test_tmp, "openssl-privsep.XXXXXX", "_")
        if len(os.fsencode(neverbleed_socket)) >= 100:
            raise ConanInvalidConfiguration(
                "H2O_TEST_TMPDIR is too long for neverbleed's Unix-domain socket: "
                f"{test_tmp}"
            )
        os.makedirs(test_tmp, exist_ok=True)
        if not os.access(test_tmp, os.W_OK | os.X_OK):
            raise ConanInvalidConfiguration(
                f"H2O_TEST_TMPDIR must be writable and searchable: {test_tmp}"
            )
        executable_tools_dir = os.path.join(test_tmp, "h2o-upstream-test-tools")
        os.makedirs(executable_tools_dir, exist_ok=True)
        self._create_test_mktemp_wrapper(executable_tools_dir)
        self._create_test_openssl_wrapper(executable_tools_dir)
        perl_core_arch = os.path.join(perl_core, core_arch_dirs[0])
        relocated_config = self._create_relocated_perl_config(
            perl, perl_core_arch, tools_dir
        )
        openssl_prefix = self.dependencies["openssl"].package_folder
        openssl_lib = os.path.join(openssl_prefix, "lib")
        runner = os.path.join(tools_dir, "run-perl-test-tool")
        save(
            self,
            runner,
            "#!/bin/sh\n"
            "set -eu\n"
            f"PERL={shlex.quote(perl_bin)}\n"
            f"PREFIX={shlex.quote(test_prefix)}\n"
            f"H2O_SOURCE={shlex.quote(h2o_source)}\n"
            f"PERL_CORE={shlex.quote(perl_core)}\n"
            f"PERL_CORE_ARCH={shlex.quote(perl_core_arch)}\n"
            f"PERL_RELOCATED_CONFIG={shlex.quote(relocated_config)}\n"
            f"TEST_TMP={shlex.quote(test_tmp)}\n"
            f"TEST_ARCH={shlex.quote(core_arch_dirs[0])}\n"
            f"OPENSSL_CONF={shlex.quote(openssl_conf)}\n"
            "TEST_LIB=\"$PREFIX/lib/perl5:$PREFIX/lib/perl5/$TEST_ARCH\"\n"
            "export PERL5LIB=\"$TEST_LIB:$PERL_RELOCATED_CONFIG:$PERL_CORE:$PERL_CORE_ARCH:$H2O_SOURCE\"\n"
            "export TMPDIR=\"$TEST_TMP\"\n"
            "export H2O_TEST_TMPDIR=\"$TEST_TMP\"\n"
            "if [ ! -d \"$TEST_TMP\" ] || [ ! -w \"$TEST_TMP\" ]; then\n"
            "    echo \"H2O upstream tests require a writable test temporary directory: $TEST_TMP\" >&2\n"
            "    exit 1\n"
            "fi\n"
            "export H2O_NEVERBLEED_TMPDIR=\"$TEST_TMP\"\n"
            "export H2O_TEST_DISABLE_NEVERBLEED=1\n"
            f"export PATH={shlex.quote(executable_tools_dir)}:{shlex.quote(tools_dir)}:\"$PATH\"\n"
            f"export OPENSSL_PREFIX={shlex.quote(openssl_prefix)}\n"
            f"export LD_LIBRARY_PATH={shlex.quote(openssl_lib)}"
            "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\n"
            "exec \"$@\"\n",
        )
        os.chmod(runner, 0o755)
        return runner

    def _create_relocated_perl_config(self, perl, perl_core_arch, tools_dir):
        """Shadow only Perl's stale packaged Config paths during upstream tests."""
        original_lib = "//lib/perl5"
        relocated_lib = os.path.join(perl.package_folder, "lib", "perl5")
        relocated_root = os.path.join(tools_dir, "perl-relocated-config")
        relocated_arch = os.path.join(relocated_root, os.path.basename(perl_core_arch))
        if os.path.isdir(relocated_root):
            shutil.rmtree(relocated_root)
        os.makedirs(relocated_arch, exist_ok=True)

        for config_name in ("Config.pm", "Config_heavy.pl"):
            source_config = os.path.join(perl_core_arch, config_name)
            contents = load(self, source_config)
            if original_lib not in contents:
                raise ConanInvalidConfiguration(
                    "H2O upstream tests require a relocatable Conan Perl "
                    f"{config_name} containing {original_lib}"
                )
            save(
                self,
                os.path.join(relocated_arch, config_name),
                contents.replace(original_lib, relocated_lib),
        )
        return relocated_arch

    def _create_test_mktemp_wrapper(self, tools_dir):
        """Make Autoconf temp paths writable on the HarmonyOS shared volume."""
        system_mktemp = shutil.which("mktemp")
        if not system_mktemp:
            raise ConanInvalidConfiguration(
                "H2O upstream tests require mktemp for the FCGI CPAN configure step"
            )
        wrapper = os.path.join(tools_dir, "mktemp")
        save(
            self,
            wrapper,
            "#!/bin/sh\n"
            "set -eu\n"
            f"SYSTEM_MKTEMP={shlex.quote(system_mktemp)}\n"
            "created=\"$(\"$SYSTEM_MKTEMP\" \"$@\")\"\n"
            "if [ -d \"$created\" ]; then\n"
            "    chmod g+rwx \"$created\"\n"
            "else\n"
            "    chmod g+rw \"$created\"\n"
            "fi\n"
            "printf '%s\\n' \"$created\"\n",
        )
        os.chmod(wrapper, 0o755)

    def _create_test_openssl_wrapper(self, tools_dir):
        """Build an executable TLS 1.2 OpenSSL probe for the native TAP run."""
        system_openssl = shutil.which("openssl")
        if not system_openssl:
            raise ConanInvalidConfiguration(
                "H2O upstream tests require an openssl client for TLS probes"
            )
        wrapper = os.path.join(tools_dir, "openssl")
        wrapper_source = f"{wrapper}.c"
        save(
            self,
            wrapper_source,
            "#include <stdio.h>\n"
            "#include <stdlib.h>\n"
            "#include <string.h>\n"
            "#include <unistd.h>\n\n"
            f"static const char *system_openssl = {json.dumps(system_openssl)};\n\n"
            "int main(int argc, char **argv) {\n"
            "    if (argc > 1 && strcmp(argv[1], \"s_client\") == 0) {\n"
            "        char **forward = calloc((size_t)argc + 2, sizeof(*forward));\n"
            "        if (forward == NULL) {\n"
            "            perror(\"calloc\");\n"
            "            return 127;\n"
            "        }\n"
            "        forward[0] = (char *)system_openssl;\n"
            "        forward[1] = argv[1];\n"
            "        forward[2] = \"-tls1_2\";\n"
            "        for (int index = 2; index < argc; ++index)\n"
            "            forward[index + 1] = argv[index];\n"
            "        execv(system_openssl, forward);\n"
            "    } else {\n"
            "        argv[0] = (char *)system_openssl;\n"
            "        execv(system_openssl, argv);\n"
            "    }\n"
            "    perror(system_openssl);\n"
            "    return 127;\n"
            "}\n",
        )
        compiler = shutil.which("clang")
        if not compiler:
            raise ConanInvalidConfiguration(
                "H2O upstream tests require clang to build the TLS probe wrapper"
            )
        compiler_env = os.environ.copy()
        test_tmp = compiler_env.get("H2O_TEST_TMPDIR")
        if test_tmp:
            compiler_env.update({"TMPDIR": test_tmp, "TMP": test_tmp, "TEMP": test_tmp})
        completed = subprocess.run(
            [compiler, "-O2", "-o", wrapper, wrapper_source],
            env=compiler_env,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode:
            raise ConanException(
                "H2O upstream tests could not build the TLS probe wrapper: "
                f"{completed.stderr.strip()}"
            )
        os.remove(wrapper_source)

    def _install_perl_distribution(self, runner, perl_bin, source_dir, test_prefix):
        makefile = os.path.join(source_dir, "Makefile.PL")
        build_pl = os.path.join(source_dir, "Build.PL")
        # Avoid a CPAN distribution prompting for optional external tests. The
        # upstream-provided default is retained, and this only applies while
        # constructing the isolated test closure.
        runner_command = f"PERL_MM_USE_DEFAULT=1 sh {shlex.quote(runner)}"
        if os.path.isfile(makefile):
            self._run_perl_test_source_command(
                source_dir,
                f"{runner_command} {shlex.quote(perl_bin)} Makefile.PL "
                f"INSTALL_BASE={shlex.quote(test_prefix)}",
            )
            self._run_perl_test_source_command(source_dir, f"{runner_command} make")
            self._run_perl_test_source_command(
                source_dir, f"{runner_command} make pure_install"
            )
            return
        if os.path.isfile(build_pl):
            self._run_perl_test_source_command(
                source_dir,
                f"{runner_command} {shlex.quote(perl_bin)} Build.PL "
                f"--install_base {shlex.quote(test_prefix)}",
            )
            self._run_perl_test_source_command(
                source_dir, f"{runner_command} {shlex.quote(perl_bin)} Build"
            )
            self._run_perl_test_source_command(
                source_dir,
                f"{runner_command} {shlex.quote(perl_bin)} Build install",
            )
            return
        raise ConanInvalidConfiguration(
            f"Pinned CPAN archive has no supported installer: {source_dir}"
        )

    def _run_perl_test_source_command(self, source_dir, command):
        # On the HarmonyOS PC, Conan's self.run wrapper can leave Autoconf
        # with an unusable cwd even though the source directory exists.
        # Start the test-only CPAN command directly with its explicit cwd.
        self.output.info(f"RUN (direct upstream-test tool): {command}")
        completed = subprocess.run(
            command,
            shell=True,
            cwd=source_dir,
            executable="/bin/sh",
            check=False,
        )
        if completed.returncode:
            raise ConanException(
                f"H2O upstream test dependency command failed with {completed.returncode}"
            )

    def _run_complete_upstream_tap(self, perl):
        """Run the exact top-level t/*.t scope with the matching Conan Perl.

        Calling CMake's custom check target would resolve a bare prove through
        Conan's process wrapper. Execute its complete command directly so the
        test cannot silently select the system Perl or its XS modules.
        """
        perl_bin = os.path.join(perl.package_folder, "bin", "perl")
        prove_script = os.path.join(perl.package_folder, "bin", "prove")
        if not os.path.isfile(perl_bin) or not os.path.isfile(prove_script):
            raise ConanInvalidConfiguration(
                "H2O upstream tests require perl/5.42.2 to provide bin/perl and bin/prove"
            )

        test_files = [
            os.path.relpath(test_file, self.source_folder)
            for test_file in sorted(glob.glob(os.path.join(self.source_folder, "t", "*.t")))
        ]
        if not test_files:
            raise ConanInvalidConfiguration("H2O upstream test scope t/*.t is empty")

        runner = os.path.join(self.build_folder, "h2o-upstream-test-tools", "run-perl-test-tool")
        if not os.path.isfile(runner):
            raise ConanInvalidConfiguration("H2O upstream test runner was not generated")
        test_env = os.environ.copy()
        test_env["H2O_ROOT"] = os.path.abspath(self.build_folder)
        test_env["BINARY_DIR"] = os.path.abspath(self.build_folder)
        command = [
            "sh",
            runner,
            perl_bin,
            prove_script,
            "--exec",
            perl_bin,
            "-v",
            *test_files,
        ]
        self.output.info("RUN (direct complete upstream TAP): " + shlex.join(command))
        completed = subprocess.run(command, cwd=self.source_folder, env=test_env, check=False)
        if completed.returncode:
            raise ConanException(
                f"H2O complete upstream TAP failed with {completed.returncode}"
            )

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["h2o", "h2o-evloop"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "libh2o")
