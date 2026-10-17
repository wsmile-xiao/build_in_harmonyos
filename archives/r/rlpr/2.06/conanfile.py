"""Build the upstream rlpr 2.06 command-line suite."""

import os
import shutil
import stat
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RlprConan(ConanFile):
    name = "rlpr"
    version = "2.06"
    package_type = "application"
    description = "Remote line-printer client and proxy commands"
    license = "GPL-2.0-or-later"
    homepage = "https://packages.debian.org/source/sid/rlpr"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("rlpr supports Linux and OHOS")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("RLPR_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("RLPR_SOURCE_ARCHIVE is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # The old configure script runs an unsigned off_t probe in native
            # mode. Different accepted triples take its conservative cross path.
            toolchain.configure_args.append("--build=aarch64-unknown-linux-gnu")
            toolchain.configure_args.append("--host=aarch64-unknown-linux-musl")
        toolchain.configure_args.append("--disable-nls")
        toolchain.generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf")
        objcopy = shutil.which("llvm-objcopy")
        if not all((signer, readelf, objcopy)):
            raise ConanInvalidConfiguration("missing OHOS ELF signing tools")
        pending = path.with_name(path.name + ".rlpr-signing")
        signed = path.with_name(path.name + ".rlpr-signed")
        if pending.exists() or signed.exists():
            raise ConanInvalidConfiguration("stale rlpr signing sibling")
        try:
            shutil.copy2(path, pending)
            before = subprocess.run(
                [readelf, "-S", str(pending)], capture_output=True, text=True,
                check=True, timeout=10,
            ).stdout
            if ".codesign" in before:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", str(pending)],
                    check=True, timeout=10,
                )
            subprocess.run(
                [signer, "sign", "-inFile", str(pending), "-outFile", str(signed),
                 "-selfSign", "1"],
                check=True, capture_output=True, timeout=40,
            )
            after = subprocess.run(
                [readelf, "-S", str(signed)], capture_output=True, text=True,
                check=True, timeout=10,
            ).stdout
            if after.count(".codesign") != 1:
                raise ConanInvalidConfiguration("signed rlpr ELF lacks one .codesign section")
            signed.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IXUSR)
            os.replace(signed, path)
        finally:
            for temporary in (pending, signed):
                if temporary.exists():
                    temporary.unlink()

    def build(self):
        if str(self.settings.os) == "OHOS":
            # mktemp -d forces 0700, which HMDFS can expose with a different
            # numeric owner. Create the private scratch directory atomically
            # with group access instead; do not chmod shared system paths.
            configure = os.path.join(self.source_folder, "configure")
            replace_in_file(self, configure,
                            'tmp=`(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null` &&',
                            'tmp="${TMPDIR:-.}/confstat$$-$RANDOM"; (umask 007 && mkdir "$tmp") &&',
                            strict=True)
            replace_in_file(self, configure, 'tmp=./confstat$$-$RANDOM',
                            'tmp="${TMPDIR:-.}/confstat$$-$RANDOM"', strict=True)
            replace_in_file(self, configure, '(umask 077 && mkdir $tmp)',
                            '(umask 007 && mkdir "$tmp")', strict=True)
            # This release predates musl. Teach its bundled config.sub only
            # the actual target OS spelling, in the disposable build copy.
            script = Path(self.source_folder, "config.sub")
            original = script.read_bytes()
            machine_case = b"nto-qnx* | linux-gnu* | storm-chaos*"
            os_case = b"| -mingw32* | -linux-gnu* | -uxpv*"
            if original.count(machine_case) != 1 or original.count(os_case) != 1:
                raise ConanInvalidConfiguration("rlpr config.sub layout changed")
            adapted = original.replace(
                machine_case, b"nto-qnx* | linux-gnu* | linux-musl* | storm-chaos*"
            ).replace(
                os_case, b"| -mingw32* | -linux-gnu* | -linux-musl* | -uxpv*"
            )
            script.write_bytes(adapted)
            # HarmonyOS account UIDs need not have a passwd database entry.
            # These clients only use pw_name as their print-protocol identity.
            # A numeric UID is stable and avoids trusting USER/LOGNAME.
            missing_user = (
                b'if (pwd == 0 || pwd->pw_name == 0) {\n'
                b'\tmsg(R_ERROR, errno, "unable to resolve your username");\n'
                b'\treturn 0;\n'
                b'    }'
            )
            numeric_user = (
                b'if (pwd == 0 || pwd->pw_name == 0) {\n'
                b'\tstatic struct passwd fallback;\n'
                b'\tstatic char uid_name[32];\n'
                b'\tsnprintf(uid_name, sizeof(uid_name), "%lu",\n'
                b'\t         (unsigned long)getuid());\n'
                b'\tfallback.pw_name = uid_name;\n'
                b'\tpwd = &fallback;\n'
                b'    }'
            )
            for name in ("rlpr.c", "rlpq.c", "rlprm.c"):
                source = Path(self.source_folder, "src", name)
                if not source.is_file() or source.is_symlink():
                    raise ConanInvalidConfiguration(f"missing regular source: {name}")
                content = source.read_bytes()
                if content.count(missing_user) != 1:
                    raise ConanInvalidConfiguration(
                        f"rlpr user lookup layout changed in {name}"
                    )
                mode = stat.S_IMODE(source.stat().st_mode)
                try:
                    source.chmod(mode | stat.S_IWUSR)
                    source.write_bytes(content.replace(missing_user, numeric_user))
                finally:
                    source.chmod(mode)
        tools = Autotools(self)
        environment = Environment()
        make_args = ["-j1"]
        if str(self.settings.os) == "OHOS":
            scratch = Path(self.build_folder, ".autoconf-tmp")
            previous_umask = os.umask(0o007)
            try:
                scratch.mkdir(mode=0o770, exist_ok=False)
            finally:
                os.umask(previous_umask)
            environment.define("TMPDIR", str(scratch))
            linker = shutil.which("ld.lld")
            archiver = shutil.which("llvm-ar")
            ranlib = shutil.which("llvm-ranlib")
            if not all((linker, archiver, ranlib)):
                raise ConanInvalidConfiguration("missing OHOS ld.lld/llvm-ar/llvm-ranlib")
            environment.define("LD", linker)
            environment.define("AR", archiver)
            environment.define("RANLIB", ranlib)
            # This old Makefile assigns AR=ar even when configure sees AR.
            make_args.extend((f"AR={archiver}", f"RANLIB={ranlib}"))
        with environment.vars(self).apply():
            tools.configure()
            tools.make(args=make_args)
            # There are no registered TESTS/check_PROGRAMS in this release.
            tools.make(target="check", args=make_args)
        self.output.info("UPSTREAM_BUILD_PASS: rlpr make and make check (0 tests)")

    def package(self):
        # Do not run the upstream install-setuid, install-proxy or bsdlinks
        # targets: they chown/chmod setuid and modify /usr/bin.
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        root = Path(self.package_folder, "bin")
        for name in ("rlpr", "rlpq", "rlprm", "rlprd"):
            path = root / name
            if not path.is_file():
                raise ConanInvalidConfiguration("missing upstream command: " + name)
            if str(self.settings.os) == "OHOS":
                self._sign_elf(path)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
