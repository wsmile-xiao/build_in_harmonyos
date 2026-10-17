#!/usr/bin/env python3
"""Conan recipe — pgbackrest 2.59.0 (meson) for HarmonyOS PC / OpenHarmony aarch64.

pgbackrest is a C11 command-line backup/restore tool for PostgreSQL. Upstream
2.59.0 uses a Meson build system; the released distribution tarball carries the
generated sources (help/interface headers) so the upstream code-generation
toolchain, the Perl based documentation helpers and libyaml are not required to
build the C core.
"""

import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PgbackrestConan(ConanFile):
    name = "pgbackrest"
    version = "2.59.0"
    description = "Reliable PostgreSQL backup and restore tool"
    license = "MIT"
    homepage = "https://pgbackrest.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        self.requires("openssl/3.5.6.1")
        self.requires("libpq/18.6")
        self.requires("libxml2/2.15.3.1")
        self.requires("lz4/1.10.0.3")
        self.requires("zstd/1.5.7.1")
        self.requires("bzip2/1.0.8.2")
        self.requires("zlib/1.3.1.1")
        self.requires("libssh2/1.11.1")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        # The upstream `smoke` suite drives a full backup/restore cycle against a
        # real PostgreSQL cluster, so a server has to be available at build time.
        self.tool_requires("postgresql/18.3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["libssh2"] = "enabled"
        tc.project_options["libzstd"] = "enabled"
        tc.project_options["libsystemd"] = "disabled"
        tc.generate()
        self._adapt_meson_toolchain()

    def _adapt_meson_toolchain(self):
        """Bridge upstream Meson dependency lookups to Conan's generated files.

        * upstream meson.build asks for ``liblz4`` while the Conan lz4 package
          publishes ``lz4.pc`` -> provide a forwarding ``liblz4.pc``.
        * bz2 is located with ``cc.find_library('bz2')`` (not pkg-config), so the
          Conan bzip2 include/lib directories have to be added to the compiler
          and linker arguments.
        * Meson probes the archiver by bare name (``llvm-ar``), which is not on
          PATH on CI workers, so the absolute path is written into the native file.
        """
        generators = self.generators_folder

        lz4_pc = os.path.join(generators, "lz4.pc")
        if os.path.isfile(lz4_pc):
            version = "0"
            with open(lz4_pc, encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("Version:"):
                        version = line.split(":", 1)[1].strip()
                        break
            with open(os.path.join(generators, "liblz4.pc"), "w", encoding="utf-8") as handle:
                handle.write(
                    "Name: liblz4\n"
                    "Description: forwarding .pc for the Conan lz4 package\n"
                    "Version: {}\n"
                    "Requires: lz4\n".format(version)
                )

        bz2 = self.dependencies["bzip2"].cpp_info
        bz2_cflags = "".join("'-I{}', ".format(path) for path in bz2.includedirs)
        bz2_lflags = "".join("'-L{}', ".format(path) for path in bz2.libdirs)
        if not bz2_cflags or not bz2_lflags:
            raise ConanException("bzip2 package does not expose include/lib dirs")

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = compilers.get("ar")
        ranlib = compilers.get("ranlib")
        cc_dir = os.path.dirname(compilers.get("c") or "") if os.path.sep in (compilers.get("c") or "") else ""
        if not ar and cc_dir:
            candidate = os.path.join(cc_dir, "llvm-ar")
            ar = candidate if os.path.isfile(candidate) else None
        if not ranlib and cc_dir:
            candidate = os.path.join(cc_dir, "llvm-ranlib")
            ranlib = candidate if os.path.isfile(candidate) else None
        if not ar:
            raise ConanException("unable to locate an archiver for the Meson build")

        native = os.path.join(generators, "conan_meson_native.ini")
        with open(native, encoding="utf-8") as handle:
            content = handle.read()
        content = content.replace("c_args = [", "c_args = [{}".format(bz2_cflags), 1)
        content = content.replace("c_link_args = [", "c_link_args = [{}".format(bz2_lflags), 1)
        binaries = "[binaries]\nar = '{}'\n".format(ar)
        if ranlib:
            binaries += "ranlib = '{}'\n".format(ranlib)
        content = content.replace("[binaries]\n", binaries, 1)
        with open(native, "w", encoding="utf-8") as handle:
            handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_smoke_test()

    def _run_upstream_smoke_test(self):
        """Run the upstream `smoke` suite (full backup/restore against PostgreSQL)."""
        postgresql = self.dependencies.build["postgresql"]
        pg_bin = os.path.join(postgresql.package_folder, "bin")
        os.environ["PGBACKREST_SMOKE_PG_BIN_PATH"] = pg_bin
        os.environ["TMPDIR"] = self._smoke_work_root()
        os.environ["TMP"] = os.environ["TMPDIR"]
        os.environ["TEMP"] = os.environ["TMPDIR"]
        self.run(
            "meson test -C {} --print-errorlogs".format(self.build_folder),
            env="conanbuild",
        )

    def _smoke_work_root(self):
        """Pick a scratch directory whose files are owned by the current user.

        The smoke suite restores a cluster into its work directory and pgbackrest refuses to
        restore to a path that is not owned by the running user. On HarmonyOS the shared
        /storage mount reports a different owner than the application uid, so a directory on a
        filesystem that reports the real uid is preferred.
        """
        candidates = []
        if os.environ.get("XDG_RUNTIME_DIR"):
            candidates.append(os.path.join(os.environ["XDG_RUNTIME_DIR"], "pgbackrest-smoke"))
        candidates.append("/data/storage/el2/base/tmp/pgbackrest-smoke")
        candidates.append("/data/local/tmp/pgbackrest-smoke")
        candidates.append(os.path.join(self.build_folder, "tmp"))

        for candidate in candidates:
            try:
                os.makedirs(candidate, exist_ok=True)
                probe = os.path.join(candidate, ".owner-probe")
                with open(probe, "w", encoding="utf-8"):
                    pass
                owned = os.stat(probe).st_uid == os.geteuid()
                os.unlink(probe)
            except OSError:
                continue
            if owned:
                return candidate

        return os.path.join(self.build_folder, "tmp")

    def package(self):
        Meson(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._resign_elf()

    def _resign_elf(self):
        """Re-sign the installed executable for HarmonyOS.

        ``meson install`` rewrites the RUNPATH while installing a binary, which invalidates the
        signature the linker had embedded in the ``.codesign`` section. HarmonyOS refuses to
        execute an ELF whose signature does not match (EPERM), so the installed binary is
        re-signed with the platform tool.
        """
        if self.settings.os != "OHOS":
            return

        hnp_bin = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp_bin, "llvm-objcopy")
        signer = os.path.join(hnp_bin, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanException("HarmonyOS signing tools not found in {}".format(hnp_bin))

        for path in sorted(glob.glob(os.path.join(self.package_folder, "bin", "*"))):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            with open(path, "rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    continue
            self.run('"{objcopy}" --remove-section .codesign "{path}"'.format(objcopy=objcopy, path=path))
            self.run(
                '"{signer}" sign -inFile "{path}" -outFile "{path}.signed" -selfSign 1'.format(
                    signer=signer, path=path
                )
            )
            os.replace(path + ".signed", path)
            os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
