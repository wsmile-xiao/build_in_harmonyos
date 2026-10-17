#!/usr/bin/env python3
"""Conan recipe for the OpenLDAP rewrite/remap overlay."""

import glob
import os
import shlex
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    get,
    replace_in_file,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OpenLdapOverlayRwmConan(ConanFile):
    name = "openldap-overlay-rwm"
    version = "2.6.13"
    description = "OpenLDAP rewrite/remap slapd overlay"
    license = "OLDAP-2.8"
    homepage = "https://www.openldap.org/"
    url = "https://www.openldap.org/"
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def requirements(self):
        # slapd's dynamic loader needs libltdl. All other OpenLDAP optional
        # dependencies are disabled for this narrowly scoped overlay package.
        self.requires(
            "libtool/2.5.4",
            headers=True,
            libs=True,
            run=True,
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "openldap-overlay-rwm supports Linux and OHOS only"
            )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(
            self,
            os.path.join(
                self.source_folder,
                "libraries",
                "liblunicode",
                "Makefile.in",
            ),
            "\t\t$(LN_S) $$ii . ; \\",
            "\t\t/bin/cp $$ii . ; \\",
            strict=True,
        )
        self._patch_upstream_test_wrappers()

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            tc.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-ohos",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        tc.configure_args.extend(
            [
                "--enable-dynamic=yes",
                "--enable-shared=yes",
                "--enable-static=no",
                "--enable-syslog=no",
                "--enable-ipv6=no",
                "--enable-local=no",
                "--enable-slapd=yes",
                "--enable-modules=yes",
                "--enable-backends=no",
                "--enable-null=yes",
                "--enable-ldap=mod",
                "--enable-mdb=no",
                "--enable-relay=mod",
                "--enable-overlays=no",
                "--enable-rwm=mod",
                "--enable-syncprov=mod",
                "--enable-cleartext=yes",
                "--enable-spasswd=no",
                "--with-cyrus-sasl=no",
                "--with-systemd=no",
                "--with-fetch=no",
                "--with-threads=posix",
                "--with-tls=no",
                "--with-argon2=no",
                "--with-mp=longlong",
            ]
        )
        tc.generate()

    def build(self):
        tmpdir = self._configure_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        self._prepend_env_path(
            "LD_LIBRARY_PATH",
            os.path.join(self.dependencies["libtool"].package_folder, "lib"),
        )

        autotools = Autotools(self)
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args", ""
        )
        configure = os.path.join(self.source_folder, "configure")
        default_shell = (
            "/system/bin/sh"
            if str(self.settings_build.os) == "OHOS"
            else "/bin/sh"
        )
        config_shell = os.environ.get("CONFIG_SHELL", default_shell)
        command = shlex.join([config_shell, configure])
        command = f"CONFIG_SHELL={shlex.quote(config_shell)} {command}"
        if configure_args:
            command = f"{command} {configure_args}"
        try:
            self.run(command)
        except Exception:
            config_log = os.path.join(self.build_folder, "config.log")
            if os.path.isfile(config_log):
                with open(config_log, encoding="utf-8", errors="replace") as log:
                    log_tail = "".join(log.readlines()[-200:])
                    self.output.error(
                        "configure config.log (last 200 lines):\n%s" % log_tail
                    )
            raise
        autotools.make(target="depend", args=["-j1"])
        autotools.make(args=["-j1"])
        self._run_upstream_rwm_tests(config_shell, tmpdir)

    def package(self):
        Autotools(self).install(args=["-j1"])

        # Clients and administrator symlinks belong to other OpenLDAP
        # subpackages. Keep only the ABI-matched libraries, private slapd test
        # host, and rwm module produced by this source build.
        rmdir(self, os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "sbin"))
        for archive in glob.glob(
            os.path.join(self.package_folder, "lib", "*.a")
        ):
            os.remove(archive)
        for archive in glob.glob(
            os.path.join(self.package_folder, "lib", "*.la")
        ):
            os.remove(archive)
        module_dir = os.path.join(
            self.package_folder, "libexec", "openldap"
        )
        for test_module in ("back_ldap", "back_relay", "syncprov"):
            for artifact in glob.glob(
                os.path.join(module_dir, "%s.*" % test_module)
            ):
                os.remove(artifact)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # slapd loads the overlay at runtime; consumers do not link to it.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["libexec/openldap"]
        self.cpp_info.resdirs = ["libexec/openldap"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.runenv_info.define_path(
            "OPENLDAP_MODULE_PATH",
            os.path.join(self.package_folder, "libexec", "openldap"),
        )

    @staticmethod
    def _prepend_env_path(name, value):
        current = os.environ.get(name)
        os.environ[name] = value + (os.pathsep + current if current else "")

    def _configure_tmpdir(self):
        roots = []
        if str(self.settings_build.os) == "OHOS":
            roots.append("/data/storage/el2/base/cache")
        injected = os.environ.get("TMPDIR")
        if injected:
            roots.append(injected)
        roots.append(os.path.join(self.build_folder, "_tmp"))

        for root in dict.fromkeys(roots):
            try:
                os.makedirs(root, exist_ok=True)
                candidate = tempfile.mkdtemp(
                    prefix="openldap-overlay-rwm-",
                    dir=root,
                )
                probe = os.path.join(candidate, ".write-probe")
                with open(probe, "w", encoding="ascii") as handle:
                    handle.write("ok")
                os.remove(probe)
                self.output.info("Using configure temporary directory: %s" % candidate)
                return candidate
            except OSError as error:
                self.output.warning(
                    "Configure temporary root is unusable: %s (%s)"
                    % (root, error)
                )

        raise ConanInvalidConfiguration(
            "no writable temporary directory is available for configure"
        )

    def _run_upstream_rwm_tests(self, config_shell, tmpdir):
        tests = (
            "test028-idassert",
            "test030-relay",
            "test039-glue-ldap-concurrency",
            "test047-ldap",
            "test079-proxy-timeout",
            "test087-librewrite",
            "test088-syncprov-glue-rwm",
            "its9468",
        )
        tests_dir = os.path.join(self.build_folder, "tests")
        run_script = os.path.join(tests_dir, "run")
        source_tests = os.path.join(self.source_folder, "tests")
        test_tmpdir = self._upstream_test_tmpdir(tmpdir)
        base_port = 20000 + (os.getpid() % 1000) * 20

        for index, test_name in enumerate(tests):
            test_dir = os.path.join(
                test_tmpdir, "upstream-%s" % test_name
            )
            log_file = os.path.join(test_tmpdir, "%s.log" % test_name)
            env = {
                "CONFIG_SHELL": config_shell,
                "USER_TESTDIR": test_dir,
                "USER_DATADIR": os.path.join(source_tests, "data"),
                "USER_SCHEMADIR": os.path.join(
                    self.source_folder, "servers", "slapd", "schema"
                ),
                "SLAPD_BASEPORT": str(base_port + index * 10),
            }
            assignments = " ".join(
                "%s=%s" % (name, shlex.quote(value))
                for name, value in env.items()
            )
            test_command = shlex.join(
                [
                    config_shell,
                    run_script,
                    "-b",
                    "ldif",
                    test_name,
                ]
            )
            command = (
                "cd %s && %s %s > %s 2>&1; "
                "rc=$?; cat %s; exit $rc"
                % (
                    shlex.quote(tests_dir),
                    assignments,
                    test_command,
                    shlex.quote(log_file),
                    shlex.quote(log_file),
                )
            )
            self.output.info("Running upstream rwm test: %s" % test_name)
            self.run(shlex.join([config_shell, "-c", command]))
            with open(log_file, encoding="utf-8", errors="replace") as log:
                output = log.read()
            if ">>>>> Test succeeded" not in output:
                raise ConanInvalidConfiguration(
                    "upstream rwm test did not execute completely: %s"
                    % test_name
                )
            if test_name == "test030-relay" and not all(
                marker in output
                for marker in ("Using relay backend", "Using ldap backend")
            ):
                raise ConanInvalidConfiguration(
                    "upstream relay test did not exercise relay and ldap"
                )

    def _upstream_test_tmpdir(self, configure_tmpdir):
        roots = []
        if str(self.settings_build.os) == "OHOS":
            roots.append("/data/storage/el2/base/cache")
        roots.append(configure_tmpdir)

        for root in dict.fromkeys(roots):
            candidate = None
            try:
                os.makedirs(root, exist_ok=True)
                candidate = tempfile.mkdtemp(
                    prefix="openldap-rwm-tests-",
                    dir=root,
                )
                os.chmod(candidate, 0o770)
                probe = os.path.join(candidate, ".write-probe")
                fifo = os.path.join(candidate, ".fifo-probe")
                with open(probe, "w", encoding="ascii") as handle:
                    handle.write("ok")
                os.remove(probe)
                os.mkfifo(fifo, 0o660)
                os.remove(fifo)
                self.output.info(
                    "Using upstream test temporary directory: %s"
                    % candidate
                )
                return candidate
            except OSError as error:
                self.output.warning(
                    "Upstream test temporary root is unusable: %s (%s)"
                    % (root, error)
                )
                if candidate and os.path.isdir(candidate):
                    rmdir(self, candidate)

        raise ConanInvalidConfiguration(
            "no writable FIFO-capable directory is available for tests"
        )

    def _patch_upstream_test_wrappers(self):
        run_script = os.path.join(self.source_folder, "tests", "run.in")
        replace_in_file(
            self,
            run_script,
            "\t$SCRIPT $*",
            '\t"${CONFIG_SHELL-/bin/sh}" "$SCRIPT" $*',
            strict=True,
        )

        defines = os.path.join(
            self.source_folder, "tests", "scripts", "defines.sh"
        )
        replace_in_file(
            self,
            defines,
            "umask 077",
            "umask 007",
            strict=True,
        )
        replace_in_file(
            self,
            defines,
            'LIBTOOL="${LIBTOOL-$TESTWD/../libtool}"',
            'LIBTOOL="${LIBTOOL-$TESTWD/../libtool}"\n'
            'TEST_SHELL="${CONFIG_SHELL-/bin/sh}"',
            strict=True,
        )
        replace_in_file(
            self,
            defines,
            'PROGDIR="$OBJDIR/tests/progs"',
            'PROGDIR="$OBJDIR/tests/progs"\n'
            'TESTPROGDIR="$OBJDIR/tests/progs/.libs"',
            strict=True,
        )
        replace_in_file(
            self,
            defines,
            'SLAPDBIN="$OBJDIR/servers/slapd/slapd"',
            'SLAPDBIN="$TEST_SHELL $OBJDIR/servers/slapd/slapd"',
            strict=True,
        )
        wrapper_commands = {
            'LLOADD="$SLAPD_WRAPPER $OBJDIR/servers/lloadd/lloadd -s0"':
                'LLOADD="$SLAPD_WRAPPER $TEST_SHELL '
                '$OBJDIR/servers/lloadd/lloadd -s0"',
            'LDAPPASSWD="$CLIENTDIR/ldappasswd $TOOLARGS"':
                'LDAPPASSWD="$TEST_SHELL $CLIENTDIR/ldappasswd $TOOLARGS"',
            'LDAPSASLSEARCH="$CLIENTDIR/ldapsearch $SASLARGS '
            '$TOOLPROTO $LDAP_TOOLARGS -LLL"':
                'LDAPSASLSEARCH="$TEST_SHELL $CLIENTDIR/ldapsearch '
                '$SASLARGS $TOOLPROTO $LDAP_TOOLARGS -LLL"',
            'LDAPSASLWHOAMI="$CLIENTDIR/ldapwhoami $SASLARGS '
            '$LDAP_TOOLARGS"':
                'LDAPSASLWHOAMI="$TEST_SHELL $CLIENTDIR/ldapwhoami '
                '$SASLARGS $LDAP_TOOLARGS"',
            'LDAPSEARCH="$CLIENTDIR/ldapsearch $TOOLPROTO $TOOLARGS -LLL"':
                'LDAPSEARCH="$TEST_SHELL $CLIENTDIR/ldapsearch '
                '$TOOLPROTO $TOOLARGS -LLL"',
            'LDAPRSEARCH="$CLIENTDIR/ldapsearch $TOOLPROTO $TOOLARGS"':
                'LDAPRSEARCH="$TEST_SHELL $CLIENTDIR/ldapsearch '
                '$TOOLPROTO $TOOLARGS"',
            'LDAPDELETE="$CLIENTDIR/ldapdelete $TOOLPROTO $TOOLARGS"':
                'LDAPDELETE="$TEST_SHELL $CLIENTDIR/ldapdelete '
                '$TOOLPROTO $TOOLARGS"',
            'LDAPMODIFY="$CLIENTDIR/ldapmodify $TOOLPROTO $TOOLARGS"':
                'LDAPMODIFY="$TEST_SHELL $CLIENTDIR/ldapmodify '
                '$TOOLPROTO $TOOLARGS"',
            'LDAPADD="$CLIENTDIR/ldapmodify -a $TOOLPROTO $TOOLARGS"':
                'LDAPADD="$TEST_SHELL $CLIENTDIR/ldapmodify -a '
                '$TOOLPROTO $TOOLARGS"',
            'LDAPMODRDN="$CLIENTDIR/ldapmodrdn $TOOLPROTO $TOOLARGS"':
                'LDAPMODRDN="$TEST_SHELL $CLIENTDIR/ldapmodrdn '
                '$TOOLPROTO $TOOLARGS"',
            'LDAPWHOAMI="$CLIENTDIR/ldapwhoami $TOOLARGS"':
                'LDAPWHOAMI="$TEST_SHELL $CLIENTDIR/ldapwhoami $TOOLARGS"',
            'LDAPCOMPARE="$CLIENTDIR/ldapcompare $TOOLARGS"':
                'LDAPCOMPARE="$TEST_SHELL $CLIENTDIR/ldapcompare $TOOLARGS"',
            'LDAPEXOP="$CLIENTDIR/ldapexop $TOOLARGS"':
                'LDAPEXOP="$TEST_SHELL $CLIENTDIR/ldapexop $TOOLARGS"',
            'MONITORDATA=$SRCDIR/scripts/monitor_data.sh':
                'MONITORDATA="$TEST_SHELL '
                '$SRCDIR/scripts/monitor_data.sh"',
            'SLAPDTESTER=$PROGDIR/slapd-tester':
                'SLAPDTESTER="$TEST_SHELL $PROGDIR/slapd-tester"',
            'LDIFFILTER=$PROGDIR/ldif-filter':
                'LDIFFILTER="$TEST_SHELL $PROGDIR/ldif-filter"',
            'SLAPDMTREAD=$PROGDIR/slapd-mtread':
                'SLAPDMTREAD="$TEST_SHELL $PROGDIR/slapd-mtread"',
        }
        for original, replacement in wrapper_commands.items():
            replace_in_file(
                self, defines, original, replacement, strict=True
            )

        rewrite_test = os.path.join(
            self.source_folder,
            "tests",
            "scripts",
            "test087-librewrite",
        )
        replace_in_file(
            self,
            rewrite_test,
            "$TESTWD/../libraries/librewrite/rewrite -f",
            '"${CONFIG_SHELL-/bin/sh}" '
            "$TESTWD/../libraries/librewrite/rewrite -f",
            strict=True,
        )
        concurrency_test = os.path.join(
            self.source_folder,
            "tests",
            "scripts",
            "test039-glue-ldap-concurrency",
        )
        replace_in_file(
            self,
            concurrency_test,
            '-P "$PROGDIR"',
            '-P "$TESTPROGDIR"',
            strict=True,
        )
