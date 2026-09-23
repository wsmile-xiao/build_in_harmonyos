#!/usr/bin/env python3
"""Conan recipe for daemontools-encore 1.11 — UNIX service supervision tools.

daemontools-encore is Bruce Guenter's enhanced, backwards-compatible fork of
D. J. Bernstein's public-domain daemontools: 20 command line tools that start,
supervise, control and log long-running services (supervise, svscan, svc, svok,
svstat, svup, multilog, envdir, envini, envuidgid, setuidgid, setuser, fghack,
pgrphack, readproctitle, setlock, softlimit, svscanboot, tai64n, tai64nlocal).

Build system (DJB package style, no configure script)
-----------------------------------------------------
The tarball ships a generated ``Makefile`` plus five user-editable ``conf-*``
files.  Upstream's README states the intended workflow: "Adjust the values in
the conf-* files if necessary, build the programs by running 'make', edit the
conf-bin and conf-man files and put the destination directory for programs and
man pages in the first line of each respectively, as root run 'make install'."
This recipe therefore *configures* the build through that documented interface
instead of carrying patches:

* ``conf-cc`` / ``conf-ld`` are written from the Conan toolchain
  (``tools.build:compiler_executables`` + ``GnuToolchain`` flags), so the OHOS
  profile's clang is used and no shell variable has to be present at all;
* ``conf-bin`` / ``conf-man`` are pointed at ``bin/`` and ``share/man/`` inside
  the Conan package folder, so upstream's own ``./installer`` performs the
  install of the upstream ``BIN`` / ``MAN`` manifests verbatim.

``make programs man`` builds the 20 programs and their man pages;
``make install`` installs them; nothing else is generated.

Upstream regression suite
-------------------------
The upstream suite (``make rts``, 21 cases in ``rts.tests/``) starts real
``supervise`` processes, which need ``mkfifo(2)`` for their control channel.
On HarmonyOS PC user processes may not create FIFOs (HMMAC/SELinux, knowledge
entry E074), so ``supervise`` aborts with
"unable to read supervise/control: file does not exist" and the concatenated
suite spins forever in its own ``waitok`` helper.  The suite is consequently
never run from ``build()`` (it would hang ``conan create``); the per-case device
runs and their raw logs are collected under ``reports/`` and summarised in
``reports/upstream-tests.md``.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout

# Programs shipped by upstream BIN manifest (installed into bin/).
PROGRAMS = (
    "envdir",
    "envini",
    "envuidgid",
    "fghack",
    "multilog",
    "pgrphack",
    "readproctitle",
    "setlock",
    "setuidgid",
    "setuser",
    "softlimit",
    "supervise",
    "svc",
    "svok",
    "svscan",
    "svscanboot",
    "svstat",
    "svup",
    "tai64n",
    "tai64nlocal",
)

# Upstream conf-cc carries these warning flags; they are kept so that the
# recipe compiles the sources with the same diagnostics upstream intends.
UPSTREAM_WARNINGS = ("-Wall", "-Wshadow", "-Wcast-align", "-Wwrite-strings")


class DaemontoolsEncoreConan(ConanFile):
    name = "daemontools-encore"
    version = "1.11"
    description = ("Service supervision tools derived from D. J. Bernstein's daemontools: "
                   "supervise, svscan, svc, multilog, envdir, setuidgid, softlimit, setlock, tai64n")
    license = "MIT"
    homepage = "https://untroubled.org/daemontools-encore/"
    url = "https://github.com/bruceg/daemontools-encore"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is only supported on Linux/OHOS, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The DJB build never reads CFLAGS/CC from the environment (it reads the
        # conf-* files), but generating the toolchain keeps the flags used in
        # build() identical to every other recipe in this repository.
        tc = GnuToolchain(self)
        tc.generate()

    def _conf_lines(self):
        """Return the conf-cc and conf-ld command lines for this profile."""
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        tc = GnuToolchain(self)
        # GnuToolchain.defines holds bare macro names (no -D prefix).
        cflags = tc.cflags + ["-D" + d for d in tc.defines] + list(UPSTREAM_WARNINGS)
        return cc, " ".join(cflags), " ".join(tc.ldflags)

    def build(self):
        apply_conandata_patches(self)
        cc, cflags, ldflags = self._conf_lines()
        self.output.info(f"conf-cc: {cc} {cflags}")
        self.output.info(f"conf-ld: {cc} {ldflags}")

        # DJB build configuration interface (upstream README: edit conf-* before make).
        save(self, os.path.join(self.source_folder, "conf-cc"),
             f"{cc} {cflags}\n\nThis will be used to compile .c files.\n")
        save(self, os.path.join(self.source_folder, "conf-ld"),
             f"{cc} {ldflags}\n\nThis will be used to link .o files into an executable.\n")

        # `make -B` forces a full rebuild without deleting anything.  Upstream's
        # `make clean` is unusable here: it removes every name listed in the
        # shipped TARGETS file, and that list contains `man` and `targets`,
        # which on a case-insensitive filesystem (OHOS HMDFS: `MAN` and `man`
        # are the same inode, verified with os.path.samefile) deletes the
        # upstream MAN install manifest and TARGETS itself - the later
        # `make install` then fails with "No rule to make target 'MAN'".
        self.run("make -j1 -B programs man", cwd=self.source_folder)

    def _precreate_manifest_dirs(self, manifest, dest):
        """Create the directories declared by an upstream install manifest.

        installer.c creates a directory only for the ``d`` lines of BIN/MAN and
        uses the mode written there (MAN declares ``d:::755:/man8::``).  On OHOS
        HMDFS the restrictive mode sticks while the later chmod() is a no-op and
        the recorded owner is the share owner (20001006) instead of the process
        euid (20020084), so the directory ends up 2700 and the very next
        open(O_CREAT) inside it fails with EACCES:

            installer: fatal: unable to write .../share/man/man8/envdir.8: access denied
            $ mkdir -m 700 probe && touch probe/x
            touch: cannot touch 'probe/x': Permission denied

        Pre-creating the directory with a group-accessible mode turns the
        installer's mkdir() into the EEXIST case that installer.c already
        ignores, and install proceeds normally.  On a case-sensitive Linux
        filesystem this is a no-op (upstream's own chmod still applies).
        """
        path = os.path.join(self.source_folder, manifest)
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                fields = line.rstrip("\n").split(":")
                if len(fields) < 5 or fields[0].lstrip("?") != "d":
                    continue
                subdir = fields[4].strip("/")
                if subdir:
                    os.makedirs(os.path.join(dest, subdir), mode=0o777, exist_ok=True)

    def package(self):
        # Upstream install rules (./installer) read their destination from the
        # first line of conf-bin / conf-man.  The destination directories have
        # to exist beforehand: upstream expects /usr/local/bin to be there
        # already, and installer.c only creates the directories declared in the
        # manifests themselves.
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man")
        os.makedirs(bindir, mode=0o777, exist_ok=True)
        os.makedirs(mandir, mode=0o777, exist_ok=True)
        self._precreate_manifest_dirs("MAN", mandir)
        save(self, os.path.join(self.source_folder, "conf-bin"),
             f"{bindir}\n\nPrograms are installed in this directory.\n")
        save(self, os.path.join(self.source_folder, "conf-man"),
             f"{mandir}\n\nMan pages are installed in subdirectories of this directory.\n")
        self.run("make -j1 install", cwd=self.source_folder)

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
