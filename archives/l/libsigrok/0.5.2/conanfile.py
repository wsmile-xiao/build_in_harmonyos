"""libsigrok 0.5.2 core and non-USB drivers for OHOS PC."""

import os
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibsigrokConan(ConanFile):
    name = "libsigrok"
    version = "0.5.2"
    package_type = "library"
    description = "Signal-acquisition library and hardware drivers"
    homepage = "https://sigrok.org/"
    license = "GPL-3.0-or-later"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def requirements(self):
        # Use the published GLib binary with the same zlib patch family as
        # libzip; the older GLib package carries stale libtool .la paths.
        # libsigrok.h exposes GLib types; keep its headers and libraries in
        # the consumer graph even when the producer binary is already built.
        self.requires("glib/2.88.0",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libzip/1.11.4")
        self.requires("zlib/1.3.1.1", override=True)

    def build_requirements(self):
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self, build_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("LIBSIGROK_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("local source archive is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            toolchain.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
                "--disable-bindings", "--disable-all-drivers",
                "--enable-demo", "--without-libusb",
                "--without-libserialport", "--without-libftdi",
                "--without-libhidapi", "--without-libbluez",
            ])
        toolchain.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not signer or not readelf:
            raise ConanInvalidConfiguration("OHOS ELF signer/readelf missing")
        original = Path(path)
        pending = original.with_name(original.name + ".sigrok-signing")
        signed = original.with_name(original.name + ".sigrok-signed")
        if pending.exists() or signed.exists():
            raise ConanInvalidConfiguration("stale signing sibling")
        previous_umask = os.umask(0o022)
        try:
            shutil.copy2(original, pending)
            existing = subprocess.run([readelf, "-S", str(pending)], check=True,
                                      capture_output=True, text=True, timeout=20)
            if ".codesign" in existing.stdout:
                objcopy = shutil.which("llvm-objcopy")
                if not objcopy:
                    raise ConanInvalidConfiguration("Existing signature requires llvm-objcopy")
                # Re-sign only this disposable build-tree copy, never cache inputs.
                subprocess.run([objcopy, "--remove-section=.codesign", str(pending)],
                               check=True, capture_output=True, text=True, timeout=20)
                sections = subprocess.run([readelf, "-S", str(pending)], check=True,
                                          capture_output=True, text=True, timeout=20)
                if ".codesign" in sections.stdout:
                    raise ConanException("Old signature was not removed from private copy")
            result = subprocess.run([signer, "sign", "-inFile", str(pending),
                                     "-outFile", str(signed), "-selfSign", "1"],
                                    capture_output=True, text=True, timeout=40)
            if result.returncode:
                raise ConanException("OHOS ELF signing failed (rc=" +
                                     str(result.returncode) + "): " +
                                     (result.stdout + result.stderr)[-2000:])
            sections = subprocess.run([readelf, "-S", str(signed)], check=True,
                                      capture_output=True, text=True, timeout=20)
            if ".codesign" not in sections.stdout:
                raise ConanException("signed ELF has no .codesign")
            os.chmod(signed, original.stat().st_mode)
            os.replace(signed, original)
        finally:
            os.umask(previous_umask)
            for temporary in (pending, signed):
                if temporary.exists():
                    temporary.unlink()

    def _refresh_config_sub(self):
        tuple_name = "aarch64-unknown-linux-ohos"
        compiler = self.conf.get("tools.build:compiler_executables", default={}).get("c")
        roots = []
        if compiler:
            roots.append(Path(compiler).parent.parent / "share")
        automake = shutil.which("automake")
        if automake:
            roots.append(Path(automake).resolve().parent.parent / "share")
        roots.extend([Path("/data/service/hnp/share"),
                      Path("/storage/Users/currentUser/usr/local/share")])
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        environment = os.environ.copy()
        environment["TMPDIR"] = self.build_folder
        for root in roots:
            candidates = sorted(root.glob("automake-*/config.sub"), reverse=True)
            candidates.append(root / "autoconf" / "build-aux" / "config.sub")
            for candidate in candidates:
                if not candidate.is_file():
                    continue
                result = subprocess.run([shell, str(candidate), tuple_name],
                                        env=environment, capture_output=True,
                                        text=True, timeout=20)
                if result.returncode == 0 and result.stdout.strip() == tuple_name:
                    shutil.copy2(candidate, os.path.join(self.build_folder,
                                                         "autostuff", "config.sub"))
                    self.output.info("REFRESHED_CONFIG_SUB_FOR_OHOS")
                    return
        # CI workers do not necessarily ship the same Automake version as the
        # development target.  The release bundles a 2018 config.sub; add only
        # the precise linux-ohos kernel/OS pattern to our private build copy.
        bundled = Path(self.build_folder, "autostuff", "config.sub")
        contents = bundled.read_text(encoding="utf-8")
        replacements = (
            ("linux-musl* | linux-uclibc* | uclinux-uclibc*",
             "linux-musl* | linux-ohos* | linux-uclibc* | uclinux-uclibc*"),
            ("-linux-newlib* | -linux-musl* | -linux-uclibc*",
             "-linux-newlib* | -linux-musl* | -linux-ohos* | -linux-uclibc*"),
        )
        for old, new in replacements:
            if contents.count(old) != 1:
                raise ConanInvalidConfiguration(
                    "bundled config.sub layout is not the expected 2018 release")
            contents = contents.replace(old, new, 1)
        bundled.write_text(contents, encoding="utf-8")
        result = subprocess.run([shell, str(bundled), tuple_name],
                                env=environment, capture_output=True,
                                text=True, timeout=20)
        if result.returncode != 0 or result.stdout.strip() != tuple_name:
            raise ConanInvalidConfiguration("build-local config.sub rejects OHOS tuple")
        self.output.info("PATCHED_BUNDLED_CONFIG_SUB_FOR_OHOS")

    def _libtool_overlay(self):
        """Keep broken dependency .la metadata out of libtool's link search.

        Some published OHOS packages contain libdir='//lib' or a build-time
        /usr/local/lib. Copy only linker inputs into this build-local overlay;
        never alter the dependency cache or a shared package revision.
        """
        overlay = Path(self.build_folder, ".libsigrok-libtool")
        overlay.mkdir(exist_ok=False)
        copied = 0
        for dependency in self.dependencies.host.values():
            library_dir = Path(dependency.package_folder, "lib")
            if not library_dir.is_dir():
                continue
            for archive in library_dir.glob("*.la"):
                metadata = archive.read_text(encoding="utf-8")
                actual = re.findall(r"^libdir='([^']*)'$", metadata,
                                    flags=re.MULTILINE)
                if len(actual) != 1:
                    raise ConanException(f"invalid libtool libdir: {archive}")
                if actual[0] == str(library_dir):
                    continue
                fixed = re.sub(r"^libdir='[^']*'$",
                               f"libdir='{overlay}'", metadata,
                               count=1, flags=re.MULTILINE)
                (overlay / archive.name).write_text(fixed, encoding="utf-8")
                stem = archive.name[:-3]
                for library in library_dir.glob(stem + ".so*"):
                    if library.is_file():
                        shutil.copy2(library, overlay / library.name)
                static = library_dir / (stem + ".a")
                if static.is_file():
                    shutil.copy2(static, overlay / static.name)
                copied += 1
        for archive in overlay.glob("*.la"):
            metadata = archive.read_text(encoding="utf-8")
            def replace_archive(match):
                replacement = overlay / match.group(1)
                if not replacement.is_file():
                    raise ConanException(f"unresolved libtool archive: {match.group(0)}")
                return str(replacement)
            metadata = re.sub(r"//lib/(lib[^ '\"]+\.la)", replace_archive,
                              metadata)
            archive.write_text(metadata, encoding="utf-8")
        self.output.info(f"BUILD_LOCAL_LIBTOOL_OVERLAY_ENTRIES={copied}")
        return overlay

    def build(self):
        if str(self.settings.os) == "OHOS":
            self._refresh_config_sub()
        overlay = self._libtool_overlay()
        environment = Environment()
        if str(self.settings.os) == "OHOS":
            configure = os.path.join(self.build_folder, "configure")
            replace_in_file(self, configure,
                            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                            'tmp="${TMPDIR:-.}/conf$$-$RANDOM"; (umask 007 && mkdir "$tmp") &&',
                            strict=True)
            replace_in_file(self, configure, 'tmp=./conf$$-$RANDOM',
                            'tmp="${TMPDIR:-.}/conf$$-$RANDOM"', strict=True)
            replace_in_file(self, configure, '(umask 077 && mkdir "$tmp")',
                            '(umask 007 && mkdir "$tmp")', strict=True)
            scratch = Path(self.build_folder, ".autoconf-tmp")
            previous_umask = os.umask(0o007)
            try:
                scratch.mkdir(mode=0o770, exist_ok=False)
            finally:
                os.umask(previous_umask)
            environment.define("TMPDIR", str(scratch))
            # Use the target's POSIX shell for generated helpers, rather than
            # inheriting Bash whose HMDFS getcwd diagnostics can pollute tests.
            environment.define("CONFIG_SHELL", "/system/bin/sh")
        environment.prepend("LDFLAGS", f"-L{overlay} ")
        check_tmp = Path(self.build_folder, ".check-tmp")
        check_tmp.mkdir(exist_ok=False)
        # Check 0.15 tries TEMP, then P_tmpdir=/tmp, before TMPDIR.
        environment.define("TEMP", str(check_tmp))
        for dependency in list(self.dependencies.host.values()) + list(self.dependencies.build.values()):
            environment.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(dependency.package_folder, "lib"))
        check_libdir = os.path.join(self.dependencies["check"].package_folder, "lib")
        environment.prepend_path("LD_LIBRARY_PATH", check_libdir)
        # make check executes an uninstalled test linked to libsigrok.so.4.
        # Dependency directories alone cannot provide our build-tree SONAME.
        environment.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(self.build_folder, ".libs"))
        with environment.vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
            if str(self.settings.os) == "OHOS" and self.options.shared:
                libraries = [p for p in Path(self.build_folder, ".libs").glob("libsigrok.so*")
                             if p.is_file() and not p.is_symlink()]
                if not libraries:
                    raise ConanException("missing build-tree libsigrok shared ELF")
                for library in libraries:
                    self._sign_elf(library)
            # Check 0.15 requires a format argument for ck_assert_msg.
            # Keep the assertion and test count unchanged in the build copy.
            test_source = Path(self.build_folder, "tests", "strutil.c")
            original = test_source.read_text(encoding="utf-8")
            old = "ck_assert_msg(saved_locale != NULL);"
            if original.count(old) != 1:
                raise ConanException("unexpected upstream locale assertion")
            test_source.write_text(
                original.replace(old,
                                 'ck_assert_msg(saved_locale != NULL, "%s", "locale unavailable");'),
                encoding="utf-8")
            self.output.info("CHECK_0_15_COMPAT_TEST_FIX")
            autotools.make(target="tests/main", args=["-j1"])
            if str(self.settings.os) == "OHOS":
                # tests/main is a libtool shell wrapper; sign its ELF payload.
                self._sign_elf(os.path.join(self.build_folder, "tests", ".libs", "main"))
            # Conan's self.run build environment can shadow this test-only
            # library path. Execute the registered make check target with the
            # explicit current process environment instead.
            self.output.info(f"CHECK_RUNTIME_LIBDIR={check_libdir}")
            check_command = ["make", "check", "-j1"]
            if str(self.settings.os) == "OHOS":
                check_command.append("SHELL=/system/bin/sh")
            result = subprocess.run(check_command,
                                    cwd=self.build_folder,
                                    env=os.environ.copy(), check=False)
            if result.returncode:
                # Automake otherwise only exposes FAIL: tests/main in worker
                # stdio. Preserve the real assertion/loader error for diagnosis.
                for relative in ("tests/main.log", "test-suite.log"):
                    diagnostic = Path(self.build_folder, relative)
                    self.output.error(f"UPSTREAM_FAILURE_LOG_BEGIN {relative}")
                    if diagnostic.is_file():
                        self.output.error(diagnostic.read_text(encoding="utf-8", errors="replace"))
                    else:
                        self.output.error("upstream did not create this diagnostic log")
                    self.output.error(f"UPSTREAM_FAILURE_LOG_END {relative}")
                raise ConanException(f"upstream make check failed: {result.returncode}")
            main_log = Path(self.build_folder, "tests", "main.log")
            report = main_log.read_text(encoding="utf-8", errors="replace")
            if not re.search(r"(?m)^100%: Checks: 76, Failures: 0, Errors: 0$", report):
                raise ConanException("upstream Check inventory differs from 76/76")
        self.output.info("UPSTREAM_1_OF_1_TEST_BINARY_PASS")
        self.output.info("UPSTREAM_76_OF_76_CHECKS_PASS")

    def package(self):
        Autotools(self).install()
        pc = Path(self.package_folder, "lib", "pkgconfig", "libsigrok.pc")
        content = pc.read_text(encoding="utf-8")
        content, count = re.subn(r"^prefix=.*$", "prefix=${pcfiledir}/../..",
                                 content, count=1, flags=re.MULTILINE)
        if count != 1:
            raise ConanException("libsigrok.pc has no unique prefix")
        pc.write_text(content, encoding="utf-8")
        if str(self.settings.os) == "OHOS" and self.options.shared:
            candidates = [p for p in Path(self.package_folder, "lib").glob("libsigrok.so.*")
                          if p.is_file() and not p.is_symlink()]
            if len(candidates) != 1:
                raise ConanException("expected one real libsigrok shared ELF")
            self._sign_elf(candidates[0])
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sigrok"]
        self.cpp_info.set_property("pkg_config_name", "libsigrok")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
