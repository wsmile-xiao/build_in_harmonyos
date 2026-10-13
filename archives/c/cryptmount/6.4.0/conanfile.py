#!/usr/bin/env python3
"""Conan recipe for cryptmount 6.4.0 on HarmonyOS PC."""

import os
import shutil
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CryptmountConan(ConanFile):
    name = "cryptmount"
    version = "6.4.0"
    description = "Encrypted filesystem management utility using Linux device-mapper"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/rwpenney/cryptmount"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("device-mapper", "dm-crypt", "encrypted-filesystems")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = "AutotoolsDeps"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "run_mudslinger_ohos.sh",
             src=os.path.join(self.recipe_folder, "test_package"),
             dst=self.export_sources_folder)

    def requirements(self):
        self.requires("libdevmapper/1.02.198")
        self.requires("libgcrypt/1.12.2")

    def build_requirements(self):
        # CI workers ship autoconf, but not aclocal or autopoint. autoreconf
        # stops at the first missing helper, so both have to be declared.
        # configure.ac requests gettext 0.23.1, which gettext/0.22.5.1's
        # autopoint rejects, so those macros are copied below and autopoint
        # is skipped.
        self.tool_requires("automake/1.18")
        self.tool_requires("gettext/0.22.5.1")
        # configure.ac calls PKG_CHECK_MODULES. CI has no pkg.m4 or pkg-config.
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"],
            filename="cryptmount-v6.4.0.tar.gz", strip_root=True)

    def generate(self):
        arch = str(self.settings.arch)
        triplets = {"armv8": "aarch64-linux-gnu", "x86_64": "x86_64-linux-gnu"}
        build_triplets = {"armv8": "aarch64-unknown-ohos", "x86_64": "x86_64-unknown-ohos"}
        triplet = triplets.get(arch)
        build_triplet = build_triplets.get(arch)
        if not triplet or not build_triplet:
            raise ValueError(f"unsupported HarmonyOS PC architecture: {arch}")

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"--host={triplet}",
            f"--build={build_triplet}",
            "--prefix=/",
            "--with-libgcrypt",
            "--disable-nls",        # musl has no preinstalled gettext; messages stay untranslated
            "--disable-luks",       # LUKS integration requires libcryptsetup and dm kernel support
            "--disable-cswap",      # HarmonyOS PC does not expose the Linux swapon workflow
            "--disable-fsck",
        ])
        tc.generate()
        pkgconf = os.path.join(
            self.dependencies.build["pkgconf"].package_folder, "bin", "pkgconf")
        env = Environment()
        env.define("PKG_CONFIG", pkgconf)
        env.vars(self).save_script("cryptmount_pkgconfig")

    def _perl_for_automake(self):
        """CI workers have HNP perl. This device image does not, so fall back."""
        packaged = "/data/service/hnp/bin/perl"
        if os.path.isfile(packaged) and os.access(packaged, os.X_OK):
            return packaged
        found = shutil.which("perl")
        if not found:
            raise ConanException("perl is required to run aclocal")
        return found

    def _fix_automake_shebangs(self):
        """automake/1.18's real scripts are #!/data/service/hnp/bin/perl."""
        package_folder = self.dependencies.build["automake"].package_folder
        if not package_folder:
            raise ConanException("automake tool package has no package folder")
        perl = self._perl_for_automake()
        bindir = os.path.join(package_folder, "bin")
        for name in os.listdir(bindir):
            if not (name.startswith(".") and name.endswith("-real")):
                continue
            path = os.path.join(bindir, name)
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                first = handle.readline()
                rest = handle.read()
            if not first.startswith("#!"):
                continue
            interpreter = first[2:].strip().split()[0]
            if os.path.isfile(interpreter) and os.access(interpreter, os.X_OK):
                continue
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("#!{}\n".format(perl))
                handle.write(rest)

    def _stage_gettext_macros(self):
        """Put AM_GNU_GETTEXT macros where aclocal looks, without running autopoint."""
        package_folder = self.dependencies.build["gettext"].package_folder
        if not package_folder:
            raise ConanException("gettext tool package has no package folder")
        aclocal = os.path.join(package_folder, "share", "aclocal")
        m4_dir = os.path.join(self.source_folder, "m4")
        os.makedirs(m4_dir, exist_ok=True)
        copied = copy(self, "*.m4", src=aclocal, dst=m4_dir)
        if not copied:
            raise ConanException(
                "gettext package is missing share/aclocal macros: {}".format(aclocal))
        pkg_aclocal = os.path.join(
            self.dependencies.build["pkgconf"].package_folder, "share", "aclocal")
        if not copy(self, "pkg.m4", src=pkg_aclocal, dst=m4_dir):
            raise ConanException(
                "pkgconf package is missing share/aclocal/pkg.m4: {}".format(pkg_aclocal))
        rpath = os.path.join(self.source_folder, "config.rpath")
        if not os.path.isfile(rpath):
            bundled = os.path.join(package_folder, "share", "gettext", "config.rpath")
            if not os.path.isfile(bundled):
                raise ConanException("config.rpath is missing from the source and from gettext")
            copy(self, "config.rpath",
                 src=os.path.join(package_folder, "share", "gettext"),
                 dst=self.source_folder)

    def build(self):
        # The upstream Git tag is a source archive, not a release tarball; generate
        # configure/Makefile.in from its checked-in autotools inputs.
        apply_conandata_patches(self)
        self._fix_automake_shebangs()
        self._stage_gettext_macros()
        # AUTOPOINT=true is Autoconf's --exclude=autopoint. The worker PATH has
        # no autopoint, and gettext 0.22.5.1 would refuse AM_GNU_GETTEXT_VERSION 0.23.1.
        self.run("AUTOPOINT=true autoreconf --force --install",
                 cwd=self.source_folder, env="conanbuild")
        # Autoconf creates config.status scratch directories with umask 077.
        # HMDFS may deny later writes to those 0700 directories even to the
        # process that created them; use the ordinary owner/group-readable mode.
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, "r", encoding="utf-8") as f:
            configure_text = f.read()
        if "umask 077" in configure_text:
            with open(configure, "w", encoding="utf-8") as f:
                f.write(configure_text.replace("umask 077", "umask 022"))
        autotools = Autotools(self)
        autotools.configure()
        # Upstream enables its test CLI only for the cmtest target. Build that
        # variant first, run the rootless upstream cases, then rebuild the
        # ordinary binary so the packaged executable has no testing switches.
        # Keep clean and cmtest as separate make invocations: Conan supplies
        # parallel jobs, and combining independent goals lets clean race with
        # the test binary link.
        autotools.make(args=["clean"])
        autotools.make(args=["cmtest"])
        # Run the upstream cases that do not require root, loop devices or
        # device-mapper. The upstream launcher hard-codes /tmp and /bin/su,
        # which are unavailable on this HarmonyOS PC image.
        driver = os.path.join(self.export_sources_folder,
                              "run_mudslinger_ohos.sh")
        suite = os.path.join(self.build_folder, "testing")
        scratch = os.path.join(self.build_folder, "mudslinger-ohos")
        self.run(f'sh "{driver}" "{suite}" "{os.path.join(self.build_folder, "cryptmount")}" "{scratch}"',
                 env="conanrun")
        autotools.make(args=["clean"])
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses", "cryptmount"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
