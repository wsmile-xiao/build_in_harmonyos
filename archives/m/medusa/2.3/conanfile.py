#!/usr/bin/env python3
"""Conan recipe for medusa 2.3 (Medusa Parallel Network Login Auditor).

Upstream: https://github.com/jmk-foofus/medusa (foofus.net), GPL-2.0 with the
OpenSSL linking exemption.

Build system: GNU Autotools (the release tarball already ships `configure',
`Makefile.in` and `aclocal.m4', so no autoreconf/bootstrap step is needed).

OHOS notes
----------
* `configure' ends with an unconditional `case "$target" in *linux*)' that
  hardcodes `LIBDL="-ldl -lrt -lm"'.  HarmonyOS is musl-based and ships no
  separate librt (`clock_gettime()' and friends live in libc), so patch 0003
  drops `-lrt' for `*ohos*' targets.
* The 2018-era `config.guess'/`config.sub' bundled upstream do not know the
  `aarch64-unknown-linux-ohos' triplet, so patches 0001/0002 add it (same edit
  as the repository's canonical script `scripts/patch-autotools-ohos.pl').
* OpenSSL is a hard dependency: `configure' aborts without it, and the core
  binary calls `OSSL_PROVIDER_load()' during startup.
* medusa is a CLI tool plus dlopen()-ed `.mod' plugin modules that are
  installed into `<prefix>/lib/medusa/modules'.  The compiled-in
  `DEFAULT_MOD_PATH' therefore never matches the Conan package folder; the
  runtime module directories are exported through the documented
  `MEDUSA_MODULE_PATH' environment variable (see `package_info()').
* Optional service modules are enabled only when their library is present:
  SSH via libssh2 (+ libgcrypt for thread-safe libssh2), SMBv2/3 via libsmb2.
  AFP (afpfs-ng), NCP (ncpfs), PostgreSQL (libpq), RDP (FreeRDP3) and SVN
  (subversion) are not published in the OHOS registry, so they stay disabled -
  `configure' degrades gracefully for all of them.
"""
import os
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rm)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain


class MedusaConan(ConanFile):
    name = "medusa"
    version = "2.3"
    description = ("Medusa Parallel Network Login Auditor - fast, parallel, "
                   "modular login brute-forcer")
    license = "GPL-2.0-only"
    homepage = "https://github.com/jmk-foofus/medusa"
    url = "https://github.com/jmk-foofus/medusa"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    options = {
        "with_ssh": [True, False],
        "with_smb2": [True, False],
    }
    default_options = {
        "with_ssh": True,
        # medusa 2.3 looks for <prefix>/include/smb2/smb2.h, while the registry
        # libsmb2 package installs include/smb2/... relative to its own include
        # dir.  Keep SMBv2/3 off until that header layout is confirmed on the
        # device; the native SMBv1 SMBNT module is always built.
        "with_smb2": False,
    }

    #: memoised `_dep_prefix()` results; `generate()` asks for the same
    #: dependency several times (include dirs, lib dirs, one flag list each).
    _dep_prefix_cache = {}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # `strip_root=True' cannot be used here: `export_conandata_patches()'
        # has already copied `patches/' into the source folder, so when Conan
        # tries to hoist the tarball's single root directory below it, the
        # destination is not empty and the extracted tree is lost.  Extract
        # as-is and move the contents up explicitly.
        get(self, **self.conan_data["sources"])
        root = os.path.join(self.source_folder, "medusa-2.3")
        if os.path.isdir(root):
            for entry in os.listdir(root):
                shutil.move(os.path.join(root, entry),
                            os.path.join(self.source_folder, entry))
            os.rmdir(root)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            raise ConanException(
                "medusa sources were not unpacked correctly: "
                f"'configure' is missing in {self.source_folder}"
            )

    def validate(self):
        # R32: platform detection must accept both Linux and OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"medusa supports Linux and OHOS targets, got {self.settings.os}"
            )

    def requirements(self):
        # OpenSSL 3.x is mandatory.  3.0.21 is the upstream release medusa 2.3
        # was migrated to and the registry copy that still ships the `legacy'
        # provider module (`lib/ossl-modules/legacy.so') that medusa loads at
        # startup (SMBNT needs MD4/DES-ECB from it).
        #
        # 3.5.6.x cannot be used: that recipe passes `no-legacy no-module' and
        # deletes lib/ossl-modules, so OSSL_PROVIDER_load(NULL, "legacy") fails
        # and medusa aborts with ERR_FATAL before parsing any arguments.
        #
        # `override=True' is required because libssh2/1.11.1 pins
        # openssl/3.5.6.1; without the override the graph fails with
        # "Version conflict: Conflict between openssl/3.5.6.1 and openssl/3.0.21".
        # libssh2 then builds against 3.0.21 (verified: the same
        # OPENSSL_* cache variables and CRYPTO_BACKEND=OpenSSL it already uses).
        self.requires("openssl/3.0.21", override=True)
        if self.options.with_ssh:
            # configure() links the SSH module against libssh2 and additionally
            # requires libgcrypt (or GnuTLS) so that libssh2 is used in a
            # thread-safe way.
            self.requires("libssh2/1.11.1")
            self.requires("libgcrypt/1.11.0")
        if self.options.with_smb2:
            self.requires("libsmb2/6.2")

    def layout(self):
        # Autotools in-source build: keep the generators in their own folder.
        self.folders.build = "."
        self.folders.generators = "conan"

    # ------------------------------------------------------------------ build

    @staticmethod
    def _pkgconfig_version(prefix, name):
        """Version recorded in the package's own pkg-config files ('' if none).

        A Conan package store directory is `<name><hash>` and carries no version,
        so an installed package is asked for its version directly.  Both the
        canonical `<name>.pc` and any `*.pc` are accepted, because not every
        recipe names the file after the package.
        """
        import glob as _glob
        candidates = [os.path.join(prefix, "lib", "pkgconfig", f"{name}.pc")]
        candidates += sorted(_glob.glob(
            os.path.join(prefix, "lib", "pkgconfig", "*.pc")))
        for candidate in candidates:
            if not os.path.isfile(candidate):
                continue
            try:
                with open(candidate, "r", encoding="utf-8",
                          errors="replace") as fh:
                    for line in fh:
                        if line.startswith("Version:"):
                            return line.split(":", 1)[1].strip()
            except OSError:
                continue
        return ""

    def _dep_prefix(self, name):
        """Absolute package prefix of a dependency.

        `self.dependencies[...].package_folder' and `cpp_info.location' can both
        still be None while `generate()' runs (they are only bound once the
        dependency package has been materialised), so the directory is located
        directly inside the Conan package store as a last resort.  The store
        layout is `<store>/p/<name><hash>/p`, with `<store>` being the parent of
        the `p` folder that holds the already-resolved dependency paths.

        Store directory names carry no version, so the candidates are filtered by
        the version of the package's own pkg-config file against the version
        Conan resolved (`dep.ref.version'); an unverifiable ambiguity is reported
        instead of silently picking the first directory, which could otherwise
        point the build at a different version of the same library (e.g. the
        openssl pinned by libssh2 vs. the one this recipe overrides to).
        """
        cached = self._dep_prefix_cache.get(name)
        if cached:
            return cached

        dep = self.dependencies[name]
        prefix = dep.package_folder or dep.cpp_info.location
        if prefix:
            self._dep_prefix_cache[name] = prefix
            return prefix

        store = self._conan_store_root()
        if store:
            import glob as _glob
            # Conan truncates the package name to five characters in the store
            # folder name (`openssl' -> `opens3b77e8c5f6d9b'), so match on the
            # truncated prefix rather than the full reference name.
            stub = name[:5]
            matches = [
                candidate
                for candidate in sorted(_glob.glob(os.path.join(store, "p", f"{stub}*", "p")))
                if os.path.isdir(os.path.join(candidate, "include", name))
            ]
            wanted = dep.ref.version if dep.ref else None
            verified = [
                candidate for candidate in matches
                if wanted and self._pkgconfig_version(candidate, name) == str(wanted)
            ]
            if len(verified) == 1:
                self.output.info(
                    f"store lookup for '{name}': {verified[0]} "
                    f"(verified as version {wanted})"
                )
                self._dep_prefix_cache[name] = verified[0]
                return verified[0]
            if len(matches) == 1:
                # Single structural match: nothing else it could be.
                if wanted and not verified:
                    self.output.warning(
                        f"store lookup for '{name}': {matches[0]} matches by "
                        f"layout but its pkg-config does not report version "
                        f"{wanted}; using it anyway (only candidate)"
                    )
                self._dep_prefix_cache[name] = matches[0]
                return matches[0]
            if matches:
                raise ConanException(
                    f"cannot resolve the package prefix of dependency '{name}': "
                    f"{len(matches)} store candidates match the layout and none "
                    f"could be verified as version {wanted!r}: {matches}. "
                    f"Point the recipe at one of them explicitly instead of "
                    f"letting the store directory order decide."
                )

        raise ConanException(
            f"cannot resolve the package prefix of dependency '{name}': "
            f"package_folder={dep.package_folder!r} "
            f"cpp_info.location={dep.cpp_info.location!r}"
        )

    def _conan_store_root(self):
        """Root of the Conan package store, derived from a resolved dep path."""
        for include in self._autotools_deps_flags()[0]:
            path = include[2:]
            marker = os.sep + "p" + os.sep
            if marker in path:
                return path.split(marker)[0]
        return ""

    def _dep(self, name, what):
        """Absolute include/lib directories of one Conan dependency."""
        rel_dirs = (self.dependencies[name].cpp_info.includedirs if what == "include"
                    else self.dependencies[name].cpp_info.libdirs)
        prefix = self._dep_prefix(name)
        return [os.path.join(prefix, d) for d in rel_dirs if d]

    def _autotools_deps_flags(self):
        """Resolved `-I' / `-L' flags produced by Conan's `AutotoolsDeps'.

        `AutotoolsDeps' resolves transitive dependency paths itself; the flags
        are read back from the script it writes, because the same information
        cannot be assembled reliably from `cpp_info' alone.
        """
        path = os.path.join(self.generators_folder, "conanautotoolsdeps.sh")
        values = {}
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line.startswith("export "):
                        continue
                    name, _, value = line[len("export "):].partition("=")
                    name = name.strip()
                    value = value.strip().strip('"')
                    for marker in ("${%s:+ }" % name, "${%s:-}" % name):
                        value = value.replace(marker, "")
                    values[name] = value.strip()
        includes = [f for f in values.get("CPPFLAGS", "").split()
                    if f.startswith("-I")]
        libdirs = [f for f in values.get("LDFLAGS", "").split()
                   if f.startswith("-L")]
        return list(dict.fromkeys(includes)), list(dict.fromkeys(libdirs))

    def generate(self):
        # Let Conan resolve the transitive dependency paths.
        AutotoolsDeps(self).generate()

        includes, libdirs = self._autotools_deps_flags()

        # openssl is consumed through an override (libssh2 pins another
        # version), so it does not appear in the generated deps script; add its
        # directories explicitly.
        openssl_prefix = self._dep_prefix("openssl")
        for directory in self._dep("openssl", "include"):
            flag = f"-I{directory}"
            if flag not in includes:
                includes.append(flag)
        for directory in self._dep("openssl", "lib"):
            flag = f"-L{directory}"
            if flag not in libdirs:
                libdirs.append(flag)
        if self.options.with_smb2:
            for directory in self._dep("libsmb2", "include"):
                flag = f"-I{directory}"
                if flag not in includes:
                    includes.append(flag)
            for directory in self._dep("libsmb2", "lib"):
                flag = f"-L{directory}"
                if flag not in libdirs:
                    libdirs.append(flag)

        self.output.info(f"dependency include flags: {includes}")
        self.output.info(f"dependency library flags: {libdirs}")

        tc = AutotoolsToolchain(self)

        # medusa's configure resets CPPFLAGS (it rebuilds the variable from
        # `-I/usr/include -I/usr/local/include ...' before using it), so include
        # paths pushed through CPPFLAGS by the environment are discarded.  They
        # travel in CFLAGS/CXXFLAGS instead, which configure keeps and the
        # generated Makefile substitutes verbatim.
        # Conan 2.29.1's AutotoolsToolchain exposes extra_cflags /
        # extra_cxxflags / extra_ldflags (there is no extra_cppflags).
        tc.extra_cflags.extend(includes)
        tc.extra_cxxflags.extend(includes)
        tc.extra_ldflags.extend(libdirs)
        # configure links a `conftest' against the dependency LIBS it inherits
        # from the conanbuild environment (AutotoolsToolchain exports e.g.
        # `-lgcrypt -lgpg-error -lssh2') and then runs it.  Those shared
        # libraries are not on the loader path, which makes configure abort with
        # "Error loading shared library ..." / "cannot run C compiled programs";
        # the matching rpath keeps them loadable during the probe.
        for libdir in libdirs:
            rpath = f"-Wl,-rpath,{libdir[2:]}"
            if rpath not in tc.extra_ldflags:
                tc.extra_ldflags.append(rpath)

        # `configure --with-ssl=PREFIX' is what upstream's own OpenSSL probe
        # understands.
        tc.configure_args.append(f"--with-ssl={openssl_prefix}")
        if self.options.with_smb2:
            # `configure --with-libsmb2=PREFIX' only appends -IPREFIX/include/smb2
            # and then looks for <smb2/smb2.h>; the plain include dir of the
            # package is already part of `includes' above.
            tc.configure_args.append(
                f"--with-libsmb2={self._dep_prefix('libsmb2')}"
            )

        # A few modules that upstream enables by default can never be built on
        # OHOS because their libraries are not published in the registry.
        tc.configure_args.extend([
            "--enable-module-afp=no",
            "--enable-module-ncp=no",
            "--enable-module-postgres=no",
            "--enable-module-rdp=no",
            "--enable-module-svn=no",
            "--enable-module-smbnt-smb2=" +
            ("yes" if self.options.with_smb2 else "no"),
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # The patches touch `configure.ac', which makes automake's timestamp
        # rules want to re-run aclocal/autoconf/automake during `make'.  The
        # toolchain has no automake 1.17 (the release tarball was generated with
        # it), so that rebuild fails with "aclocal-1.17: command not found".
        # The generated files shipped in the tarball are already up to date, so
        # their timestamps are pushed forward again.
        for generated in ("aclocal.m4", "configure", "config.h.in",
                          "Makefile.in", os.path.join("src", "Makefile.in"),
                          os.path.join("src", "modsrc", "Makefile.in")):
            path = os.path.join(self.source_folder, generated)
            if os.path.exists(path):
                os.utime(path)

        # `make -jN' uses a jobserver FIFO, and creating one fails on HarmonyOS
        # with "mkfifo: Operation not permitted"; build serially instead.
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream ships no test suite (`Makefile.am' declares no TESTS and the
        # release tarball has no test directory), so `make check' is a no-op
        # that only exercises automake's built-in `check' target.  It is still
        # invoked for gate parity; the real verification lives in test_package.
        autotools.make(target="check", args=["-j1"])

    # ---------------------------------------------------------------- package

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # libtool archives and macOS bundles are never useful in a Conan package.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rm(self, "*.dylib", os.path.join(self.package_folder, "lib"))

        self._copy_openssl_legacy_provider()
        self._sign_binaries()

    def _copy_openssl_legacy_provider(self):
        """Ship the OpenSSL `legacy' provider next to medusa.

        medusa aborts with ERR_FATAL unless `OSSL_PROVIDER_load(NULL, "legacy")'
        succeeds (the SMBNT module needs MD4 and DES-ECB from it), and the
        statically linked libcrypto loads that provider as a DSO.  The provider
        lives in the openssl package, whose location inside the Conan cache is
        not known at `package_info()' time, so it is copied into this package
        and `OPENSSL_MODULES' points here - that keeps the package usable
        without any external environment setup.
        """
        bundled = os.path.join(self.package_folder, "lib", "ossl-modules", "legacy.so")
        if os.path.isfile(bundled):
            return

        candidates = []
        try:
            candidates.append(self._dep_prefix("openssl"))
        except ConanException:
            pass
        store = self.dependencies["openssl"].package_folder
        if store:
            candidates.append(store)

        for prefix in candidates:
            candidate = os.path.join(prefix, "lib", "ossl-modules")
            legacy = os.path.join(candidate, "legacy.so")
            if os.path.isfile(legacy):
                dst = os.path.join(self.package_folder, "lib", "ossl-modules")
                copy(self, "*.so", src=candidate, dst=dst)
                self.output.info(f"bundled OpenSSL providers from {candidate}")
                return
        self.output.warn(
            "OpenSSL 'legacy' provider not found in the openssl package - the "
            "packaged medusa binary will abort at startup unless OPENSSL_MODULES "
            "is set to a directory that contains legacy.so"
        )

    def _sign_binaries(self):
        """HarmonyOS requires a `.codesign' section before an ELF can run."""
        if str(self.settings.os) != "OHOS":
            return

        sign_tool = shutil.which("binary-sign-tool") or \
            "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or \
            "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.exists(sign_tool):
            self.output.warn(
                f"{sign_tool} not found - skipping ELF signing; the packaged "
                "binaries will not be executable on the device"
            )
            return

        bindir = os.path.join(self.package_folder, "bin")
        for name in sorted(os.listdir(bindir)):
            binary = os.path.join(bindir, name)
            if not os.path.isfile(binary):
                continue
            if os.path.exists(objcopy):
                subprocess.run([objcopy, "--remove-section", ".codesign", binary],
                               capture_output=True, timeout=30)
            signed = binary + ".signed.tmp"
            for attempt in range(3):
                result = subprocess.run(
                    [sign_tool, "sign", "-inFile", binary,
                     "-outFile", signed, "-selfSign", "1"],
                    capture_output=True, timeout=60)
                if result.returncode == 0 and os.path.exists(signed):
                    shutil.move(signed, binary)
                    break
                time.sleep(1)
            else:
                if os.path.exists(signed):
                    os.remove(signed)
                raise ConanException(
                    f"ELF signing failed after 3 attempts for {binary}; "
                    "the binary will not be executable on HarmonyOS"
                )
            os.chmod(binary, 0o755)

    def package_info(self):
        # medusa is a command-line tool, not a linkable library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["lib/medusa"]

        module_dir = os.path.join(self.package_folder, "lib", "medusa", "modules")
        if os.path.isdir(module_dir):
            # `DEFAULT_MOD_PATH' is baked in at compile time as an absolute
            # path and cannot follow the Conan package folder.  medusa checks
            # the documented MEDUSA_MODULE_PATH variable first.
            self.runenv_info.define_path("MEDUSA_MODULE_PATH", module_dir)
            self.buildenv_info.define_path("MEDUSA_MODULE_PATH", module_dir)

        # The OpenSSL `legacy' provider shipped inside this package (see
        # `package()'): medusa refuses to start without it and libcrypto loads
        # it as a DSO.  Having it here keeps the package self-contained.
        provider_dir = os.path.join(self.package_folder, "lib", "ossl-modules")
        if os.path.isdir(provider_dir):
            self.runenv_info.define_path("OPENSSL_MODULES", provider_dir)
            self.buildenv_info.define_path("OPENSSL_MODULES", provider_dir)
