#!/usr/bin/env python3
"""Conan recipe revision 2.1.28.1 for Cyrus SASL 2.1.28 source."""

import os
import posixpath
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CyrusSaslConan(ConanFile):
    name = "cyrus-sasl"
    version = "2.1.28.1"
    description = "SASL authentication framework and libsasl2 library"
    license = "BSD-Attribution-HPND-disclaimer"
    homepage = "https://www.cyrusimap.org/sasl/"
    url = "https://github.com/cyrusimap/cyrus-sasl"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_upstream_tests": [True, False],
        "with_sasldb": [True, False],
        "with_saslauthd_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_upstream_tests": False,
        "with_sasldb": False,
        "with_saslauthd_tests": False,
    }
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.options.with_sasldb and not self.options.with_upstream_tests:
            raise ConanInvalidConfiguration(
                "with_sasldb is reserved for the native upstream test harness; "
                "enable with_upstream_tests as well"
            )
        if self.options.with_upstream_tests and not self.options.with_sasldb:
            raise ConanInvalidConfiguration(
                "the upstream testsuite requires the sasldb/LMDB test closure"
            )
        if self.options.with_saslauthd_tests and not self._uses_test_sasldb():
            raise ConanInvalidConfiguration(
                "with_saslauthd_tests requires the native upstream sasldb/LMDB "
                "test closure"
            )
        if self.options.with_saslauthd_tests:
            self._saslauthd_socket_dir()
        if self.options.with_upstream_tests and self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "the upstream testsuite candidate is supported only for OHOS"
            )
        if self.options.with_upstream_tests and not can_run(self):
            raise ConanInvalidConfiguration(
                "with_upstream_tests requires a native runnable OHOS target"
            )

    def requirements(self):
        if self._uses_test_sasldb():
            # This target-side dependency exists only while building the
            # disposable upstream test tree. The installed tree is db_none.
            self.requires(
                "lmdb/0.9.35",
                visible=False,
                transitive_headers=True,
                transitive_libs=True,
            )

    def package_id(self):
        self.info.options.rm_safe("with_upstream_tests")
        self.info.options.rm_safe("with_sasldb")
        self.info.options.rm_safe("with_saslauthd_tests")
        try:
            del self.info.requires["lmdb"]
        except KeyError:
            pass

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        if self._uses_test_sasldb():
            AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        test_source = None
        if self.options.with_upstream_tests and can_run(self):
            test_source = self._prepare_upstream_test_source()
        if self.settings.os == "OHOS":
            self._build_ohos_tree(self.source_folder, with_sasldb=False)
        else:
            autotools.configure()
            autotools.make(args=["-j1"])
        if test_source:
            daemon_run_dir = None
            if self.options.with_saslauthd_tests:
                daemon_run_dir = self._saslauthd_socket_dir()
                os.makedirs(daemon_run_dir, exist_ok=True)
            self._build_ohos_tree(
                test_source,
                with_sasldb=True,
                use_test_environment=True,
                daemon_run_dir=daemon_run_dir,
            )
            self._run_upstream_tests(test_source)
            if daemon_run_dir:
                self._run_saslauthd_test(test_source, daemon_run_dir)

    def package(self):
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            tmpdir = os.path.join(self.source_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            install_sh = self._copy_install_sh_for_ohos(self.source_folder, tmpdir)
            self.run(
                f'TMPDIR="{tmpdir}" make install DESTDIR="{self.package_folder}" -j1 '
                f'{self._ohos_make_vars(install_sh)}'
            )
        else:
            autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["sasl2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "cyrus-sasl")
        self.cpp_info.set_property("cmake_target_name", "cyrus-sasl::cyrus-sasl")
        self.cpp_info.set_property("pkg_config_name", "libsasl2")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]

    def _build_cc_for_ohos(self):
        executables = self.conf.get("tools.build:compiler_executables", default={})
        return executables.get("c") or executables.get("cc") or "clang"

    def _configure_args(
        self, with_sasldb=False, daemon_run_dir=None, daemon_dbpath=None
    ):
        args = []
        if self.settings.os == "OHOS":
            args.extend(["--build=aarch64-unknown-linux-gnu", "--host=aarch64-unknown-linux-gnu"])
        if self.options.shared:
            args.extend(["--enable-shared", "--disable-static"])
        else:
            args.extend(["--disable-shared", "--enable-static", "--with-staticsasl"])
        if with_sasldb:
            args.extend(["--enable-auth-sasldb", "--with-dblib=lmdb"])
        else:
            args.extend(["--disable-auth-sasldb", "--with-dblib=none"])
        if daemon_run_dir:
            if not daemon_dbpath:
                raise ConanInvalidConfiguration(
                    "the saslauthd test tree requires an explicit sasldb path"
                )
            args.extend([
                f"--with-dbpath={os.path.abspath(daemon_dbpath)}",
                f"--with-saslauthd={daemon_run_dir}",
            ])
        else:
            args.append("--without-saslauthd")
        args.extend([
            "--prefix=/",
            "--disable-dependency-tracking",
            "--disable-sample",
            "--disable-staticdlopen",
            "--disable-alwaystrue",
            "--disable-gssapi",
            "--disable-httpform",
            "--disable-krb4",
            "--disable-ldapdb",
            "--disable-login",
            "--disable-ntlm",
            "--disable-otp",
            "--disable-passdss",
            "--disable-sia",
            "--disable-sql",
            "--disable-srp",
            "--disable-srp-setpass",
            "--without-authdaemond",
            "--without-des",
            "--without-gdbm",
            "--without-ldap",
            "--without-mysql",
            "--without-openssl",
            "--without-opie",
            "--without-pam",
            "--without-pgsql",
            "--without-pwcheck",
            "--without-sqlite",
            "--without-sqlite3",
        ])
        return args

    def _uses_test_sasldb(self):
        return self.options.with_upstream_tests and self.options.with_sasldb

    def _saslauthd_socket_dir(self):
        socket_root = "/data/storage/el2/base/cache"
        socket_dir = os.environ.get("CYRUS_SASLAUTHD_SOCKET_DIR")
        if not socket_dir:
            raise ConanInvalidConfiguration(
                "with_saslauthd_tests requires CYRUS_SASLAUTHD_SOCKET_DIR "
                f"as a unique child of {socket_root}"
            )
        normalized = posixpath.normpath(socket_dir)
        if (
            not posixpath.isabs(normalized)
            or posixpath.dirname(normalized) != socket_root
        ):
            raise ConanInvalidConfiguration(
                "CYRUS_SASLAUTHD_SOCKET_DIR must be an absolute direct child of "
                f"{socket_root}"
            )
        return normalized

    def _build_ohos_tree(
        self, source_folder, with_sasldb, use_test_environment=False, daemon_run_dir=None
    ):
        configure = os.path.join(source_folder, "configure")
        tmpdir = os.path.join(source_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        build_cc = self._build_cc_for_ohos()
        configure_args = " ".join(
            shlex.quote(arg)
            for arg in self._configure_args(
                with_sasldb=with_sasldb,
                daemon_run_dir=daemon_run_dir,
                daemon_dbpath=(
                    os.path.join(source_folder, "utils", "sasldb")
                    if daemon_run_dir
                    else None
                ),
            )
        )
        command = (
            f'TMPDIR="{tmpdir}" CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh '
            f'CC_FOR_BUILD="{build_cc}" CPP_FOR_BUILD="{build_cc} -E" '
            f'/system/bin/sh "{configure}" {configure_args}'
        )
        self._run_ohos_command(command, source_folder, use_test_environment)
        self._copy_linksrcs_for_ohos(source_folder, with_sasldb=with_sasldb)
        install_sh = self._copy_install_sh_for_ohos(source_folder, tmpdir)
        self._run_ohos_command(
            f'TMPDIR="{tmpdir}" make -j1 {self._ohos_make_vars(install_sh)}',
            source_folder,
            use_test_environment,
        )

    def _run_ohos_command(self, command, cwd, use_test_environment):
        if use_test_environment:
            self.run(command, cwd=cwd, env="conanbuild")
        else:
            self.run(command, cwd=cwd)

    def _prepare_upstream_test_source(self):
        test_source = os.path.join(self.build_folder, "upstream-tests")
        if os.path.exists(test_source):
            shutil.rmtree(test_source)
        # Keep the LMDB/sasldb configuration out of the source tree packaged below.
        shutil.copytree(self.source_folder, test_source)
        return test_source

    def _run_upstream_tests(self, source_folder):
        utils_dir = os.path.join(source_folder, "utils")
        testsuite = os.path.join(utils_dir, ".libs", "testsuite")
        saslpasswd = os.path.join(utils_dir, ".libs", "saslpasswd2")
        database = os.path.join(utils_dir, "sasldb")
        library_dir = os.path.join(source_folder, "lib", ".libs")
        plugin_dir = os.path.join(source_folder, "plugins", ".libs")

        self.run(f"make testsuite", cwd=utils_dir, env="conanbuild")
        self.run(f"test -x {shlex.quote(testsuite)}", env="conanbuild")
        self.run(f"test -x {shlex.quote(saslpasswd)}", env="conanbuild")
        self.run(
            f"printf '1234\\n' | LD_LIBRARY_PATH={shlex.quote(library_dir)}:${{LD_LIBRARY_PATH:-}} "
            f"SASL_PATH={shlex.quote(plugin_dir)} "
            f"{shlex.quote(saslpasswd)} -p "
            f"-f {shlex.quote(database)} -c ken",
            cwd=utils_dir,
            env="conanbuild",
        )
        self.run(f"test -s {shlex.quote(database)}", env="conanbuild")
        self.run(
            f"LD_LIBRARY_PATH={shlex.quote(library_dir)}:${{LD_LIBRARY_PATH:-}} "
            f"SASL_PATH={shlex.quote(plugin_dir)} "
            f"{shlex.quote(testsuite)} -a",
            cwd=utils_dir,
            env="conanbuild",
        )

    def _run_saslauthd_test(self, source_folder, run_dir):
        daemon_dir = os.path.join(source_folder, "saslauthd")
        daemon = os.path.join(daemon_dir, "saslauthd")
        test_client = os.path.join(daemon_dir, "testsaslauthd")
        socket_path = os.path.join(run_dir, "mux")
        log_path = os.path.join(run_dir, "saslauthd.log")
        library_dir = os.path.join(source_folder, "lib", ".libs")
        plugin_dir = os.path.join(source_folder, "plugins", ".libs")
        environment = (
            f"LD_LIBRARY_PATH={shlex.quote(library_dir)}:${{LD_LIBRARY_PATH:-}} "
            f"SASL_PATH={shlex.quote(plugin_dir)}"
        )

        self._verify_saslauthd_socket_dir(run_dir)
        self.run(f"test -x {shlex.quote(daemon)}", env="conanbuild")
        self.run(f"test -x {shlex.quote(test_client)}", env="conanbuild")
        command = (
            "set -eu; "
            f"test ! -e {shlex.quote(socket_path)}; "
            f"{environment} {shlex.quote(daemon)} -a sasldb -m {shlex.quote(run_dir)} -d "
            f">{shlex.quote(log_path)} 2>&1 & daemon_pid=$!; "
            "cleanup() { kill \"$daemon_pid\" 2>/dev/null || true; "
            "wait \"$daemon_pid\" 2>/dev/null || true; }; "
            "trap cleanup EXIT HUP INT TERM; attempt=0; "
            f"while [ ! -e {shlex.quote(socket_path)} ] && [ \"$attempt\" -lt 30 ]; do "
            "if ! kill -0 \"$daemon_pid\" 2>/dev/null; then "
            f"cat {shlex.quote(log_path)}; exit 1; fi; "
            "sleep 1; attempt=$((attempt + 1)); done; "
            f"test -e {shlex.quote(socket_path)} || {{ cat {shlex.quote(log_path)}; exit 1; }}; "
            f"{environment} {shlex.quote(test_client)} -u ken -p 1234 "
            f"-f {shlex.quote(socket_path)}"
        )
        self.run(command, cwd=daemon_dir, env="conanbuild")

    def _verify_saslauthd_socket_dir(self, run_dir):
        socket_path = posixpath.join(run_dir, "cyrus-pr3400-socket-preflight")
        program = """
import os
import socket
import sys

run_dir, socket_path = sys.argv[1:]
os.makedirs(run_dir, exist_ok=True)
if os.path.lexists(socket_path):
    raise SystemExit(f"refusing pre-existing socket path: {socket_path}")
sock = socket.socket(socket.AF_UNIX)
bound = False
try:
    sock.bind(socket_path)
    bound = True
finally:
    sock.close()
    if bound:
        os.unlink(socket_path)
"""
        self.run(
            f"python3 -c {shlex.quote(program)} {shlex.quote(run_dir)} "
            f"{shlex.quote(socket_path)}",
            env="conanbuild",
        )

    def _ohos_make_vars(self, install_sh):
        return (
            f'MKDIR_P="/system/bin/sh {install_sh} -c -d" '
            f'INSTALL="/system/bin/sh {install_sh} -c" '
            f'INSTALL_PROGRAM="/system/bin/sh {install_sh} -c" '
            f'INSTALL_DATA="/system/bin/sh {install_sh} -c -m 644"'
        )

    def _copy_install_sh_for_ohos(self, source_folder, tmpdir):
        source = os.path.join(source_folder, "config", "install-sh")
        destination = os.path.join(tmpdir, "install-sh")
        shutil.copy2(source, destination)
        os.chmod(destination, 0o755)
        return destination

    def _copy_linksrcs_for_ohos(self, source_folder, with_sasldb):
        links = {
            "plugins/cram.c": "lib/cram.c",
            "plugins/digestmd5.c": "lib/digestmd5.c",
            "plugins/plain.c": "lib/plain.c",
            "plugins/anonymous.c": "lib/anonymous.c",
        }
        if with_sasldb:
            links.update({
                "plugins/sasldb.c": "lib/sasldb.c",
                "sasldb/allockey.c": "lib/allockey.c",
                "sasldb/db_lmdb.c": "lib/db_lmdb.c",
            })
        else:
            links["sasldb/db_none.c"] = "lib/db_none.c"
        for source, target in links.items():
            shutil.copy2(
                os.path.join(source_folder, source),
                os.path.join(source_folder, target),
            )
