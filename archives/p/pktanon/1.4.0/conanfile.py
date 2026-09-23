#!/usr/bin/env python3
"""Conan recipe for pktanon 1.4.0 — packet trace anonymization CLI tool.

pktanon (Packet Trace ANONymization) is a command-line tool from the KIT
Telematics group that anonymizes pcap network traces based on XML "profiles".
It links the Apache Xerces-C++ XML parser (used to parse the profile XML) and
uses Boost headers (boost/cstdint.hpp, checked by configure via
boost/pool/object_pool.hpp).

Build system: autotools. The only build artifact is the executable
``bin/pktanon`` (package_type = application, no libraries).

Version background: upstream never published a formal non-dev "1.4.0"
release. The only official 1.4.0-series distribution is the website tarball
``pktanon-1.4.0-dev.tar.gz`` whose configure.ac reports ``1.4.0-dev``; the
GitHub mirror (KIT-Telematics/pktanon) has moved to 2.0-beta on master with
no tags/releases. The recipe version is therefore 1.4.0 while the source URL
points at the official -dev tarball (see notes.md / manifest.yaml).

HarmonyOS portability notes (both are upstream bugs, no __OHOS__ macros):
  1. configure/config.status temp-dir dance hardcodes ``umask 077`` which
     combined with HMDFS' forced setgid creates a drwx--S--- directory that
     is unwritable even by its owner -> "could not setup config files
     machinery" (knowledge E129).  We rewrite ``umask 077`` -> ``umask 022``
     in the configure script before running it (the same fix that was
     verified in the exploration build).
  2. src/Timer.h LINUX branch calls sleep(1) but never includes <unistd.h>;
     on musl libc (OHOS) it is not pulled in transitively, so the symbol is
     undeclared.  Add the missing include.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PktanonConan(ConanFile):
    name = "pktanon"
    version = "1.4.0"
    description = "pktanon - profile-based packet trace anonymization tool"
    license = "GPL-2.0-or-later"
    homepage = "https://www.tm.kit.edu/software/pktanon/"
    url = ""
    topics = ("network", "anonymization", "pcap", "privacy", "xerces")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Boost is consumed as headers only (configure checks
        # boost/pool/object_pool.hpp; the code includes boost/cstdint.hpp).
        self.requires("boost/1.84.0")
        # xerces-c/3.2.5 is published as a static archive (no runtime NEEDED).
        self.requires("xerces-c/3.2.5")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("pktanon is supported only on Linux and OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Inject dependency include/lib search paths into configure so that
        # both the configure-time checks and the automake compile/link rules
        # can find boost/xerces-c headers and the static xerces-c archive.
        cppflags = []
        ldflags = []
        for dep_name in ("boost", "xerces-c"):
            dep = self.dependencies[dep_name]
            cppflags.extend("-I" + d for d in dep.cpp_info.includedirs)
            ldflags.extend("-L" + d for d in dep.cpp_info.libdirs)
        # Out-of-tree builds (conan build folder != source folder) break the
        # upstream Makefile.am's relative ``-Isrc`` include (2011-era Makefile,
        # no VPATH support): headers such as anonprimitives/AnonPrimitive.h live
        # under <source>/src but the compiler runs from build-release/. Point
        # CPPFLAGS at the absolute source src/ dir.
        src_inc = os.path.join(self.source_folder, "src")
        if os.path.isdir(src_inc):
            cppflags.append("-I" + src_inc)
        if cppflags:
            tc.configure_args.append("CPPFLAGS=" + " ".join(cppflags))
        if ldflags:
            tc.configure_args.append("LDFLAGS=" + " ".join(ldflags))
        tc.generate()

    def _patch_configure_umask(self):
        """Neutralize the umask-077 temp-dir dance in configure (E129).

        configure is executable in the tarball; ``save()`` may rewrite the
        file through a temp+rename that drops the exec bit on hmdfs, so we
        explicitly restore 0o755 afterwards.
        """
        configure = os.path.join(self.source_folder, "configure")
        contents = load(self, configure)
        new = contents.replace("umask 077", "umask 022")
        if new != contents:
            save(self, configure, new)
        os.chmod(configure, 0o755)

    def _strip_shebang_helpers(self):
        """Strip the leading #! line of the shipped autotools helper scripts.

        On the HarmonyOS adaptation worker the kernel refuses to exec a file
        whose first line is a ``#!`` shebang (EACCES, AppSpawn sandbox
        policy), while a plain POSIX-sh text file is executed through the
        shell ENOEXEC fallback and inside configure every aux script is
        already run via an explicit ``$SHELL`` (configure emits
        ``ac_config_guess="$SHELL .../config.guess"``).  Stripping the
        shebang therefore keeps the whole configure/make/install chain
        working under both the sandboxed local worker and the regular CI
        runner (where the change is a harmless no-op).  The scripts are
        POSIX sh, so interpreting them without the shebang is equivalent.
        """
        import re
        scripts = ("configure", "config.guess", "config.sub", "install-sh",
                   "missing", "depcomp", "compile")
        for name in scripts:
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            contents = load(self, path)
            if not contents.startswith("#!"):
                continue  # no shebang (or already stripped) -> idempotent
            lines = contents.splitlines(keepends=True)
            # Only strip when the first line really is a #! line.
            if re.match(r"#!\s*\S+", lines[0]):
                save(self, path, "".join(lines[1:]).lstrip("\n"))

    def _patch_timer_unistd(self):
        """Add the missing <unistd.h> include to the Timer.h LINUX branch.

        The pristine file uses CRLF line endings and the LINUX branch may
        carry trailing tabs, so a plain literal match is not reliable; use a
        regex keyed on the single ``#include <pthread.h>`` (only present in
        the LINUX branch) and preserve the existing newline style.
        """
        import re
        path = os.path.join(self.source_folder, "src", "Timer.h")
        contents = load(self, path)
        if re.search(r"#\s*include\s*<unistd\.h>", contents):
            return  # already fixed (idempotent)
        pat = re.compile(r"(#\s*include\s*<pthread\.h>\s*\r?\n)")
        if not pat.search(contents):
            self.output.warning("Timer.h pthread include not found; "
                                "unistd.h fix not applied")
            return
        newline = "\r\n" if "\r\n" in contents else "\n"
        contents = pat.sub(r"\1\t#include <unistd.h>" + newline, contents, count=1)
        save(self, path, contents)

    def _patch_anon_shuffle(self):
        """Replace C++17-removed std::random_shuffle in AnonShuffle.cpp.

        The 2011-era code calls ``random_shuffle`` which was removed in
        C++17 (the OHOS profile builds with -std=c++17).  Replace it with
        std::shuffle + an std::mt19937 seeded from std::random_device, and
        make sure <algorithm>/<random> are included.
        """
        path = os.path.join(self.source_folder, "src", "anonprimitives",
                            "AnonShuffle.cpp")
        if not os.path.isfile(path):
            return
        contents = load(self, path)
        if "std::shuffle" in contents and "#include <random>" in contents:
            return  # already fixed (idempotent)
        contents = contents.replace(
            '#include "AnonShuffle.h"',
            '#include "AnonShuffle.h"\n#include <algorithm>\n#include <random>',
            1)
        contents = contents.replace(
            "random_shuffle (permvector.begin (), permvector.end ());",
            "std::shuffle (permvector.begin (), permvector.end (), "
            "std::mt19937 (std::random_device{} ()));")
        save(self, path, contents)

    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_umask()
        self._patch_timer_unistd()
        self._patch_anon_shuffle()
        self._strip_shebang_helpers()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream ships no test suite (Makefile.am declares no TESTS /
        # check_PROGRAMS); "make check" is a no-op. Functional verification of
        # the binary lives in test_package (real pcap anonymization run).

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
