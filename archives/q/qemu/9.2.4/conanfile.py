#!/usr/bin/env python3
"""Conan recipe for QEMU 9.2.4 on HarmonyOS PC (aarch64).

QEMU is a machine emulator and virtualiser.  On HarmonyOS PC it is what makes
ARM artefacts actually *executable* on the host: a cross toolchain such as
``gcc-11-cross`` (target ``arm-none-eabi``) can compile and link for ARM but
cannot run the result, because the host has no AArch32 compatibility layer and
no ARM emulator.

Build system: QEMU ships its own ``configure`` shell script (not autotools).
It reads CC/CFLAGS/LDFLAGS, writes ``config-meson.cross`` and hands the real
work to meson + ninja, so this recipe drives ``configure``/``ninja`` directly
instead of going through ``MesonToolchain``.

Targets: arm-softmmu + aarch64-softmmu (system emulation) and
arm-linux-user + aarch64-linux-user (user-mode emulation, i.e. running ARM
Linux binaries directly on the host).
"""
import json
import os
import shutil
import stat
import subprocess
import time
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

# QEMU is installed under this prefix inside a DESTDIR staging area; the value
# only matters for QEMU's own relocatable path arithmetic, which turns
# "<prefix>/share/qemu" into a path relative to the executable.  That is what
# lets the packaged binaries find share/qemu/pc-bios wherever the package is
# unpacked (meson_options.txt: relocatable = true by default).
STAGING_PREFIX = "/usr"

# Upstream unit tests that cannot pass on the OHOS PC host.  Each is blocked by
# a property of this machine rather than by a QEMU defect, and each was
# reproduced individually:
#
#   test-char              needs /dev/ptmx and /dev/pts, neither of which this
#                          sandbox mounts (opening /dev/tty fails with ENXIO)
#   test-io-channel-socket binds an AF_UNIX socket, but bind(2) returns EPERM
#                          in every writable directory here
#   test-io-channel-file   asserts the permission bits it set with chmod(2),
#                          while the filesystem forces 0660 regardless
#   test-util-filemonitor  asserts inotify event ordering and semantics this
#                          filesystem does not preserve
#   test-replication       needs O_DIRECT, which the filesystem rejects with
#                          EINVAL (the check is also non-deterministic here)
#
# They are named one by one on purpose: the exclusion is narrow, so a
# regression in any *other* unit test still fails the build.
HOST_LIMITED_UNIT_TESTS = (
    "qemu:test-char",
    "qemu:test-io-channel-file",
    "qemu:test-io-channel-socket",
    "qemu:test-replication",
    "qemu:test-util-filemonitor",
)


class QemuConan(ConanFile):
    name = "qemu"
    version = "9.2.4"
    description = (
        "Generic machine emulator and virtualiser (system + user mode) for "
        "HarmonyOS PC: qemu-system-arm/aarch64, qemu-arm/aarch64, qemu-img"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.qemu.org/"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    options = {
        "target_list": [
            "arm-softmmu,aarch64-softmmu,arm-linux-user,aarch64-linux-user",
            "arm-softmmu,aarch64-softmmu",
        ],
        "with_slirp": [True, False],
        "with_capstone": [True, False],
    }
    default_options = {
        "target_list": "arm-softmmu,aarch64-softmmu,arm-linux-user,aarch64-linux-user",
        "with_slirp": True,
        "with_capstone": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration(
                "this qemu port builds for OHOS/Linux hosts only"
            )
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "this qemu port targets AArch64 hosts (arch=armv8) only"
            )

    def requirements(self):
        # glib is mandatory; pixman backs the display code and zlib the
        # image/compression paths.  libfdt is QEMU's flattened device-tree
        # library, libslirp implements "-netdev user" and capstone powers the
        # monitor disassembler -- the last two are option-controlled.
        #
        # glib is pinned to 2.84.0 because that is what the already-published
        # libslirp/4.9.3 requires; asking for a newer glib here makes Conan
        # report "Version conflict: Conflict between glib/2.84.0 and
        # glib/2.88.0 in the graph. Conflict originates from libslirp/4.9.3".
        self.requires("glib/2.84.0")
        self.requires("pixman/0.46.4")
        self.requires("zlib/1.3.1")
        self.requires("libfdt/1.7.2")
        if self.options.with_slirp:
            self.requires("libslirp/4.9.3")
        if self.options.with_capstone:
            self.requires("capstone/5.0.7")

        # Feature libraries that QEMU probes for and that the artifact
        # repository publishes, so every one of them is turned on explicitly
        # below.  Declaring a dependency without enabling the feature is what
        # left the previous revision with a capstone that was required but
        # silently unused (see the capstone note in _configure_command), so
        # each of these is paired with an `--enable-*` that fails loudly rather
        # than an `auto` probe that degrades quietly.
        #
        # libgcrypt is the crypto backend.  nettle is the other candidate but is
        # unusable here: its companion hogweed/3.9.1 requires gmp/6.3.0.1 while
        # nettle/3.9.1 pins gmp/6.3.0, and Conan reports a version conflict for
        # the two together.  gcrypt needs no gmp at all and provides the same
        # PBKDF2/hash coverage (crypto/pbkdf-gcrypt.c), which is what makes the
        # upstream test-crypto-pbkdf suite a real suite instead of an empty one.
        self.requires("libgcrypt/1.11.0")
        # Block-layer compression and DMG support.
        self.requires("zstd/1.5.6")
        self.requires("lzo/2.10")
        self.requires("snappy/1.1.7")
        self.requires("lzfse/1.0")
        self.requires("bzip2/1.0.8")
        # linux-aio (host disk I/O) and seccomp (syscall sandboxing).
        self.requires("libaio/0.3.112")
        self.requires("libseccomp/2.5.4")
        # Screenshot support.
        self.requires("libpng/1.6.39")
        #
        # keyutils is deliberately *not* declared, even though the artifact
        # repository publishes libkeyutils/1.6.3: enabling it turns
        # crypto/secret_keyring.c on, and the host then kills the keyring
        # syscalls outright.  A C probe confirms the sandbox behaviour rather
        # than a missing symbol:
        #
        #   add_key(...)  / keyctl(GET_KEYRING_ID, ...)  ->  killed by SIGSYS
        #   exit status 159 (128 + 31), with /proc/self/status showing
        #   "Seccomp: 2" and "Seccomp_filters: 1"
        #
        # With CONFIG_KEYUTILS defined, tests/unit/test-crypto-secret.c stops
        # skipping its keyring cases (the block is guarded by
        # `#if defined(CONFIG_KEYUTILS) && defined(CONFIG_SECRET_KEYRING)`) and
        # the suite dies instead of passing, which is a worse outcome than not
        # offering the feature on a host that cannot support it.

    def build_requirements(self):
        # QEMU's configure/build driver is meson + ninja, and its own
        # buildoptions machinery needs python3.  Declaring them keeps the
        # build independent of whatever happens to be on the CI worker PATH.
        # Versions are pinned to what the artifact repository actually
        # publishes (meson/1.11.1 and newer do not exist there).
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")
        # configure builds its own venv from an interpreter (see
        # _python_binary): the worker's /data/service/hnp/bin/python3 reports a
        # base prefix that does not hold a stdlib, so the venv it creates cannot
        # start at all -- `python -m ensurepip` then dies with
        # "No module named 'encodings'" and configure aborts with
        # "python venv creation failed".  A published interpreter is used
        # instead, because it carries its own stdlib under its package prefix.
        self.tool_requires("python/3.12.9")

    def layout(self):
        basic_layout(self, src_folder="src", build_folder="build")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # build helpers
    # ------------------------------------------------------------------
    def _mem_available_mb(self):
        try:
            with open("/proc/meminfo") as handle:
                for line in handle:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) // 1024
        except OSError:
            pass
        return None

    def _run(self, command, what, retries=6, retry_delay=45, cwd=None):
        """Run a build command, riding out this host's intermittent fork-OOM.

        The CI hardware class occasionally refuses to fork for minutes at a
        time (Committed_AS exceeds CommitLimit on a memory-oversubscribed
        host); that surfaces as ``posix_spawn: Out of memory`` or a bare
        ``sh: can't fork`` rather than as a compiler error, so the command is
        retried instead of failing the build.
        """
        last = None
        for attempt in range(1, retries + 1):
            available = self._mem_available_mb()
            self.output.info("[{}] attempt {}/{} (MemAvailable={}MB)".format(
                what, attempt, retries, available if available is not None else "?"))
            result = self.run(command, cwd=cwd, ignore_errors=True)
            if result == 0:
                return
            last = result
            if attempt < retries:
                time.sleep(retry_delay)
        raise ConanException("{} failed with exit code {}".format(what, last))

    def _pkg_config_path(self):
        """Directories to search for the .pc files of this recipe's deps.

        ``PkgConfigDeps`` writes generated .pc files into the generators
        folder; their contents already point at the dependency folders with
        absolute paths.  The dependencies' own pkgconfig directories are added
        as well, because a few of them only ship hand-written .pc files.
        """
        entries = [self.generators_folder]
        for dep in self.dependencies.values():
            for libdir in list(dep.cpp_info.libdirs) + list(dep.cpp_info.includedirs):
                candidate = Path(libdir) / "pkgconfig"
                if candidate.is_dir():
                    entries.append(str(candidate))
        # keep order, drop duplicates
        seen, ordered = set(), []
        for entry in entries:
            if entry not in seen:
                seen.add(entry)
                ordered.append(entry)
        return ":".join(ordered)

    def _python_binary(self):
        """Interpreter handed to ``configure --python`` and used for its venv.

        QEMU's configure calls ``mkvenv.py create pyvenv`` and then
        ``ensurepip`` inside that venv.  Both steps need an interpreter whose
        own prefix holds a complete stdlib: the CI worker's python3 resolves
        ``sys.base_prefix`` to a directory with no ``lib/python3.12``, so the
        venv it produces dies before running anything:

            Fatal Python error: init_fs_encoding: failed to get the Python
            codec of the filesystem encoding
            ModuleNotFoundError: No module named 'encodings'

        The python/3.12.9 package keeps its stdlib under its own prefix, so the
        venv it creates starts normally.
        """
        for dep in self.dependencies.values():
            if dep.ref.name != "python":
                continue
            for bindir in dep.cpp_info.bindirs:
                candidate = os.path.join(bindir, "python3")
                if os.path.isfile(candidate):
                    return candidate
        raise ConanException("python tool_requires is missing or has no bin/python3")

    def _python_lib_dirs(self):
        """Library directories the interpreter (and its venv) resolve against.

        python/3.12.9's binaries link ``libpython3.12.so.1.0`` without a
        RUNPATH, so the interpreter -- and therefore every ``pyvenv/bin/...``
        entry point configure generates -- only starts when this directory is on
        LD_LIBRARY_PATH.

        Deliberately *only* the interpreter's own libdir: libpython itself needs
        nothing but libc, while putting the dependency subtree (openssl and
        friends) on the path shadows other libraries with incompatible
        versions -- with it, even ``import ssl`` fails to relocate
        (``SSL_CTX_set_msg_callback: symbol not found``).  QEMU's configure and
        mkvenv install meson from the vendored wheels offline, so they never
        need those modules.
        """
        for dep in self.dependencies.values():
            if dep.ref.name != "python":
                continue
            return [d for d in dep.cpp_info.libdirs if os.path.isdir(d)]
        return []

    def _python_shim_dir(self):
        """Directory whose ``python3`` is the interpreter from the requirement.

        configure puts the interpreter's libdir on LD_LIBRARY_PATH so that the
        venv it builds can start (see _build_env_prefix).  That variable is
        inherited by everything the build spawns, including glib's helper
        scripts -- ``gdbus-codegen``, ``glib-mkenums`` and friends start with
        ``#!/usr/bin/env python3`` and would then pair the *host* interpreter
        with the *required* libpython:

            File ".../python3.12/xml/parsers/expat.py", line 4, in <module>
              from pyexpat import *
            ModuleNotFoundError: No module named 'pyexpat'

        (the host's extension modules do not match that libpython's ABI, so the
        stdlib module that imports them cannot be loaded).  Putting a shim
        directory in front of PATH makes every ``env python3`` resolve to the
        same interpreter whose libdir is on the path, which keeps the pair
        consistent.  The shim also sets the variable itself, so a child that
        receives a cleared environment still works.
        """
        libdirs = self._python_lib_dirs()
        if not libdirs:
            return None
        interpreter = self._python_binary()
        shim_dir = os.path.join(self.build_folder, "python-shims")
        os.makedirs(shim_dir, exist_ok=True)
        script = '#!/bin/sh\nLD_LIBRARY_PATH="{libs}:$LD_LIBRARY_PATH" exec {py} "$@"\n'.format(
            libs=":".join(libdirs), py=interpreter)
        for name in ("python3", "python", "python3.12"):
            path = os.path.join(shim_dir, name)
            with open(path, "w") as handle:
                handle.write(script)
            os.chmod(path, 0o755)
        return shim_dir

    def _path_prefix(self):
        """PATH entries the build commands need, most specific first."""
        entries = []
        shim_dir = self._python_shim_dir()
        if shim_dir:
            entries.append(shim_dir)
        entries.extend(entry for entry in self._dep_bin_dirs().split(":") if entry)
        return ":".join(entries)

    def _build_env_prefix(self):
        """Shell prefix giving every build command a consistent interpreter.

        Two things are set together, and they must travel as a pair:

        * ``LD_LIBRARY_PATH`` with the required interpreter's libdir, because
          configure builds a venv whose entry points exec python, which links
          ``libpython3.12.so.1.0`` without a RUNPATH;
        * ``PATH`` with the shim directory first, so that the ``#!/usr/bin/env
          python3`` scripts glib ships (gdbus-codegen, glib-mkenums, ...) resolve
          to that same interpreter instead of the host one -- pairing the host
          binary with the required libpython breaks its stdlib
          (``No module named 'pyexpat'``).

        configure, ninja (both the build and the install target) and the meson
        test driver all spawn these scripts, so all of them use this prefix.
        Returns "" when there is no python requirement.
        """
        libdirs = self._python_lib_dirs()
        if not libdirs:
            return ""
        return 'PATH="{}:$PATH" LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH"'.format(
            self._path_prefix(), ":".join(libdirs))

    def _dep_bin_dirs(self):
        """Directories holding the dependencies' own helper executables.

        meson's ``find_program('gdbus-codegen')`` resolves through PATH, and on
        this host that lands on ``/data/service/hnp/bin/gdbus-codegen`` -- a
        wrapper whose shebang is ``#!/usr/bin/python3``, which does not exist
        here, so the custom_target dies with exit code 126 and ninja stops.
        The glib package ships a working copy, so its bin directory is put in
        front of PATH instead of relying on the system one.
        """
        entries = []
        for dep in self.dependencies.values():
            for bindir in list(dep.cpp_info.bindirs):
                if os.path.isdir(bindir) and bindir not in entries:
                    entries.append(bindir)
        return ":".join(entries)

    def _ohos_shim_dir(self):
        """Create shim headers that de-collide two sysroot kernel headers.

        OHOS's sysroot ships bionic-derived ``linux/socket.h`` and
        ``linux/sysinfo.h`` that name their structs ``sockaddr_storage`` and
        ``sysinfo`` -- the same names the C library declares in
        <sys/socket.h> and <sys/sysinfo.h>.  Any translation unit that sees both
        fails to compile:

            ../src/linux-user/strace.c:14:
            sysroot/usr/include/linux/socket.h:35:8:
            error: redefinition of 'sockaddr_storage'

        and ``linux/netlink.h``, ``linux/can.h`` and ``linux/if_packet.h`` all
        chain into ``linux/socket.h``, so the collision reaches linux-user,
        the CAN backend and the network code alike.

        Upstream's UAPI headers call the struct __kernel_sockaddr_storage
        precisely to avoid this.  These shims rename the sysroot's copy while
        still including the real header through ``include_next``, so the
        kernel-side constants remain visible and nothing collides.
        """
        shim_dir = os.path.join(self.build_folder, "ohos-sysroot-shims")
        linux_dir = os.path.join(shim_dir, "linux")
        os.makedirs(linux_dir, exist_ok=True)

        shims = {
            "socket.h": ("sockaddr_storage", "OHOS_LINUX_SOCKET_SHIM"),
            "sysinfo.h": ("sysinfo", "OHOS_LINUX_SYSINFO_SHIM"),
        }
        for name, (symbol, guard) in shims.items():
            path = os.path.join(linux_dir, name)
            with open(path, "w") as handle:
                handle.write(
                    "/* Generated by the Conan recipe for OHOS.\n"
                    " *\n"
                    " * The sysroot's linux/{name} declares a kernel-internal\n"
                    " * struct `{symbol}`, and the C library declares a struct of\n"
                    " * the same name in its own header.  Upstream's UAPI header\n"
                    " * uses a __kernel_* name to avoid the clash; rename it for\n"
                    " * the duration of this header so both definitions can\n"
                    " * coexist, then read the genuine sysroot header. */\n"
                    "#ifndef {guard}\n"
                    "#define {guard}\n"
                    "#define {symbol} __ohos_bionic_{symbol}\n"
                    "#include_next <linux/{name}>\n"
                    "#undef {symbol}\n"
                    "#endif\n".format(name=name, symbol=symbol, guard=guard))
        return shim_dir

    def _configure_command(self):
        cflags, ldflags = [], []

        # OHOS's sysroot ships kernel headers that still carry the kernel-side
        # sparse annotations.  `linux/keyctl.h` declares `char __user * hashname`
        # but only includes <linux/types.h>, so the empty `__user` definition
        # from <linux/compiler.h> is never reached and the declaration stops
        # parsing:
        #
        #   ../src/crypto/secret_keyring.c:23:
        #   sysroot/usr/include/linux/keyctl.h:83:14: error: expected ';' at
        #   end of declaration list      char __user * hashname;
        #
        # A normal kernel `headers_install` strips these annotations; the OHOS
        # sysroot keeps them (its own compiler.h notes the header set "should be
        # replaced by a scrubbed header").  Defining them empty on the command
        # line is exactly what the kernel does for userspace, and it fixes every
        # affected header at once (kvm.h, filter.h, cdrom.h, fd.h, vfio.h,
        # usbdevice_fs.h, capability.h, futex.h, ...) instead of disabling one
        # QEMU feature per build cycle.
        cflags.extend(["-D__user=", "-D__force="])

        # <linux/socket.h> and <linux/sysinfo.h> in this sysroot declare struct
        # names the C library also uses (sockaddr_storage, sysinfo); the shims
        # rename the kernel-side copies so both can be included.  They have to be
        # first on the include path to take effect.
        cflags.append("-I" + self._ohos_shim_dir())

        # The sysroot's linux/virtio_ring.h and linux/virtio_types.h are the
        # kernel-side copies.  They clash with QEMU's bundled standard-headers
        # (kernel _UAPI_... guards vs the bundled _LINUX_... ones), so whichever
        # include order a translation unit happens to have, both sets of types
        # can end up defined:
        #
        #   ../src/subprojects/libvhost-user/libvhost-user.c:27:
        #   sysroot/usr/include/linux/virtio_ring.h:...:
        #   error: redefinition of 'vring_desc'
        #
        # and they also omit vring_need_event(), a kernel-only helper that
        # libvhost-user and libvduse call.  Predefining their guards on the
        # command line keeps the sysroot copies out of *every* translation unit
        # regardless of include order, which leaves the bundled headers -- the
        # ones that do provide the helper -- as the single source of these
        # types.  (Fixing this inside one header only works when that header is
        # included first, which libvhost-user.c does not do.)
        cflags.extend(["-D_UAPI_LINUX_VIRTIO_TYPES_H", "-D_UAPI_LINUX_VIRTIO_RING_H"])

        # glib/pixman/slirp/capstone are located through pkg-config, but libfdt
        # is probed with cc.find_library('fdt') -- meson.build does not use
        # dependency() for it -- so its include and library directories have to
        # be handed over explicitly or the probe fails.
        fdt = self.dependencies["libfdt"].cpp_info
        cflags.extend("-I" + path for path in fdt.includedirs)
        ldflags.extend("-L" + path for path in fdt.libdirs)

        # capstone is found through pkg-config, but the header is at
        # <prefix>/include/capstone/capstone.h while QEMU compiles
        # `#include <capstone.h>` -- so the probe only succeeds if
        # <prefix>/include/capstone is on the include path.  The generated
        # capstone.pc that PkgConfigDeps writes says `-I<prefix>/include`, and
        # because the generators folder is first on PKG_CONFIG_PATH it shadows
        # the correct hand-written .pc shipped inside the package
        # (`-I<prefix>/include/capstone`).  QEMU then fails its
        # `cc.compiles('#include <capstone.h>')` check and, under the `auto`
        # option this recipe used to rely on, drops capstone without a word:
        #
        #   Run-time dependency capstone found: YES 5.0.7
        #   Running compile: #include <capstone.h>
        #   fatal error: 'capstone.h' file not found
        #   ...
        #   capstone                        : NO
        #
        # Adding the subdirectory explicitly fixes the probe, and the option is
        # `enabled` rather than `auto` so this can never regress silently again.
        if self.options.with_capstone:
            capstone = self.dependencies["capstone"].cpp_info
            cflags.extend("-I" + os.path.join(path, "capstone") for path in capstone.includedirs)
            cflags.extend("-I" + path for path in capstone.includedirs)
            ldflags.extend("-L" + path for path in capstone.libdirs)

        # bz2/lzo2/snappy/lzfse/aio are probed with cc.find_library(), not
        # dependency(), so their include and library directories have to be
        # handed over explicitly exactly like libfdt above.  The remaining new
        # dependencies (libzstd, libseccomp, libgcrypt, libpng, keyutils) ship a
        # usable .pc and are found by pkg-config, so they need nothing here.
        for name in ("bzip2", "lzo", "snappy", "lzfse", "libaio"):
            dep = self.dependencies[name].cpp_info
            cflags.extend("-I" + path for path in dep.includedirs)
            ldflags.extend("-L" + path for path in dep.libdirs)

        # The published snappy is a *static C++* library (libsnappy.a built from
        # snappy.cc), while QEMU probes it with what it thinks is a plain C link:
        #
        #   snappy = cc.find_library('snappy', has_headers: ['snappy-c.h'], ...)
        #   cc.links('#include <snappy-c.h> ...', dependencies: snappy)
        #
        # The find succeeds, but the link then fails on the C++ runtime symbols
        # the archive still carries, and with `--enable-snappy` that is a hard
        # configuration error rather than a quiet downgrade:
        #
        #   ld.lld: error: undefined symbol: operator new[](unsigned long)
        #   >>> referenced by snappy.cc
        #   ../src/meson.build:2010:4: ERROR: could not link libsnappy
        #
        # Adding the C++ runtime to the link line is what makes the probe (and
        # the final qemu-* links, which pull the same archive in through
        # block/snappy.c) resolve.  The static form is deliberate: it leaves the
        # produced binaries with no libc++_shared.so dependency -- verified on
        # the probe, whose NEEDED entry is libc.so alone, and which runs -- and
        # it pulls nothing at all into links that reference no C++ symbols.
        ldflags.extend(["-Wl,-Bstatic", "-lstdc++", "-Wl,-Bdynamic"])

        # RPATH for the shared dependencies.  Most of this package's libraries
        # are static in the artifact repository (glib, bzip2, lzo, snappy,
        # lzfse, libaio, libseccomp), but pixman, libslirp, capstone, libzstd,
        # libgcrypt and libgpg-error are published as .so only, so the installed
        # binaries cannot start without being able to find them:
        #
        #   Error loading shared library libzstd.so.1: (needed by .../qemu-img)
        #   Error relocating .../qemu-img: ZSTD_createCCtx: symbol not found
        #
        # Conan does not inject it here because configure is driven directly
        # (there is no CMake/MesonToolchain helper in this recipe), and the
        # knowledge base is explicit on how to handle it: system-name libraries
        # are forced static (R26), while "other libraries are managed by Conan
        # RPATH".  Two details matter:
        #
        # * DT_RPATH, not DT_RUNPATH (`--disable-new-dtags`).  DT_RUNPATH only
        #   applies to the object that requests it, so the second-level
        #   dependency libgcrypt -> libgpg-error.so.0 would be dropped and the
        #   binaries would still fail to relocate.
        # * absolute directories, not $ORIGIN-relative ones: $ORIGIN handling is
        #   recorded as unstable on this platform.
        # host dependencies only: the build tools (meson, ninja, python) are not
        # linked into the binaries and their libdirs must not end up in RPATH.
        rpath_dirs = []
        for dep in self.dependencies.host.values():
            for path in dep.cpp_info.libdirs:
                if path not in rpath_dirs:
                    rpath_dirs.append(path)
        ldflags.append("-Wl,--disable-new-dtags")
        ldflags.extend("-Wl,-rpath," + path for path in rpath_dirs)

        compiler = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compiler.get("c") or shutil.which("clang") or "clang"
        cxx = compiler.get("cpp") or shutil.which("clang++") or "clang++"

        parts = [
            self._build_env_prefix(),
            'PKG_CONFIG_PATH="{}"'.format(self._pkg_config_path()),
            "bash", os.path.join(self.source_folder, "configure"),
            "--prefix={}".format(STAGING_PREFIX),
            "--python={}".format(self._python_binary()),
            "--target-list={}".format(self.options.target_list),
            "--enable-fdt=system",
            "--disable-docs",
            "--disable-guest-agent",
            "--disable-werror",
            "--disable-gtk",
            "--disable-sdl",
            "--disable-vnc",
            "--disable-xen",
            "--disable-brlapi",
            "--disable-spice",
            "--disable-glusterfs",
            "--disable-libssh",
            "--disable-curl",
            "--disable-libnfs",
            # vhost-user is a *userspace* backend: it speaks the vhost protocol
            # over a unix socket and needs no /dev/vhost-net, so it works on this
            # kernel and is worth shipping (it backs "-netdev vhost-user" and the
            # vhost-user-blk server).  vhost-kernel, by contrast, is the
            # /dev/vhost-net acceleration path and stays off.  Leaving vhost-net
            # disabled, as an earlier revision did, left
            # CONFIG_VHOST_NET_USER undefined, so the backend was reported as
            # "network backend 'vhost-user' is not compiled into this binary" --
            # which is exactly what upstream's
            # virtio-net-tests/vhost-user/migrate qtest exercises.
            "--enable-vhost-net",
            "--disable-vhost-kernel",
            "--disable-rdma",
            # Features that are `auto` in QEMU and whose backing libraries the
            # artifact repository publishes.  `--enable-*` makes meson *fail*
            # when the probe does not find them, which is the point: an `auto`
            # probe that misses (a wrong include path, a shadowed .pc) silently
            # ships a binary without the feature.  That is exactly how the
            # previous revision lost capstone despite requiring it.
            "--enable-gcrypt",
            "--enable-zstd",
            "--enable-lzo",
            "--enable-snappy",
            "--enable-lzfse",
            "--enable-bzip2",
            "--enable-linux-aio",
            "--enable-seccomp",
            "--enable-png",
            "--cc={}".format(cc),
            "--cxx={}".format(cxx),
            # The quotes are required: Conan joins a list command with plain
            # spaces (it does not shell-escape the arguments), so an unquoted
            # "--extra-cflags=-D__user= -D__force= -I..." would be split by the
            # shell and the leftover "-D__force=" would be read as a meson
            # option, aborting with `Unknown option: "__force"`.
            '--extra-cflags="{}"'.format(" ".join(cflags)),
            '--extra-ldflags="{}"'.format(" ".join(ldflags)),
        ]
        if not self.options.with_slirp:
            parts.append("--disable-slirp")
        # `--enable-capstone` rather than leaving it to QEMU's `auto` probe: the
        # probe is exactly what silently discarded capstone before, and with the
        # include path fixed above it now has to either work or fail the build.
        if self.options.with_capstone:
            parts.append("--enable-capstone")
        else:
            parts.append("--disable-capstone")
        return " ".join(parts)

    def _meson_dir(self):
        """Directory meson actually configured.

        QEMU's configure creates ``./build`` only when it is run *inside* the
        source tree; driven out-of-tree it configures in the current
        directory.  Detect rather than assume.
        """
        direct = Path(self.build_folder) / "build.ninja"
        nested = Path(self.build_folder) / "build" / "build.ninja"
        if direct.is_file():
            return self.build_folder
        if nested.is_file():
            return str(nested.parent)
        raise ConanException(
            "qemu configure produced no build.ninja under {}".format(self.build_folder))

    def _meson_binary(self, meson_dir):
        """The meson recorded in the build tree, not whatever PATH resolves to.

        QEMU's configure builds a private virtualenv and runs the meson it
        installs there.  That is the only version guaranteed to understand the
        tree's own ``build.dat``: a different meson refuses to read it with
        "Build data file ... references functions or classes that don't exist",
        even when the two versions are adjacent.
        """
        candidate = os.path.join(meson_dir, "pyvenv", "bin", "meson")
        if os.path.isfile(candidate):
            return candidate
        return "meson"

    def _unit_suite_selection(self, meson_dir):
        """The unit tests to run, named explicitly.

        ``meson test --exclude`` only exists from meson 1.12 onwards, while the
        meson that actually drives this tree is the one QEMU installs into its
        private venv: the wheel bundled with 9.2.4 is meson 1.5.0, so an older
        meson is what a clean build gets.  Naming the tests to *run* instead of
        the tests to *skip* is accepted by 1.5.0, 1.11.0 and 1.12.0 alike, which
        is what makes this version-independent -- with ``--exclude`` the same
        recipe passed locally (venv meson 1.12.0, from the host PATH) and failed
        on the CI worker (venv meson 1.5.0) with
        ``meson: error: unrecognized arguments: --exclude``.

        The list is read from the tree's own ``intro-tests.json`` rather than a
        hard-coded literal, so the selection tracks the suite: every test meson
        reports under ``qemu:unit`` runs unless it is named in
        ``HOST_LIMITED_UNIT_TESTS``.  A test added upstream is run by default;
        only the documented exceptions are skipped.
        """
        intro = Path(meson_dir) / "meson-info" / "intro-tests.json"
        if not intro.is_file():
            raise ConanException(
                "{} is missing, so the unit suite cannot be selected".format(intro))

        selected = []
        skipped = []
        for test in json.loads(intro.read_text(encoding="utf-8")):
            if "qemu:unit" not in (test.get("suite") or []):
                continue
            if "qemu:" + test["name"] in HOST_LIMITED_UNIT_TESTS:
                skipped.append(test["name"])
            else:
                selected.append(test["name"])
        if not selected:
            raise ConanException("no runnable unit tests found in {}".format(intro))

        self.output.info(
            "[qemu] unit suite: {} selected, {} host-limited skipped ({})".format(
                len(selected), len(skipped), ", ".join(sorted(skipped)) or "none"))
        return selected

    def _sign_elf_tree(self, root):
        """ELF-sign every runnable host binary under ``root`` (OHOS only).

        HarmonyOS refuses to execve unsigned ELF images, so the packaged
        ``bin/qemu-*`` binaries would be unusable as shipped.  Same convention
        as the gcc-11-cross recipe.
        """
        if self.settings.os != "OHOS" or not os.path.isdir(root):
            return

        signer = (shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        objcopy = (shutil.which("llvm-objcopy") or shutil.which("objcopy")
                   or "/data/service/hnp/bin/llvm-objcopy")
        readelf = (shutil.which("llvm-readelf") or shutil.which("readelf")
                   or "/data/service/hnp/bin/llvm-readelf")
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires binary-sign-tool, llvm-objcopy and llvm-readelf")

        def is_runnable_elf(path):
            probe = subprocess.run(
                "{} -h {} | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'".format(readelf, path),
                shell=True, executable="/data/service/hnp/bin/bash",
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return probe.returncode == 0

        for candidate in Path(root).rglob("*"):
            if not candidate.is_file() or candidate.is_symlink():
                continue
            if not (candidate.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                continue
            target = str(candidate)
            if not is_runnable_elf(target):
                continue

            unsigned, signed = target + ".ohos-unsigned", target + ".ohos-signed"
            for scratch in (unsigned, signed):
                if os.path.exists(scratch):
                    os.unlink(scratch)
            shutil.copy2(target, unsigned)
            subprocess.run(
                "{} --remove-section .codesign {}".format(objcopy, unsigned),
                shell=True, executable="/data/service/hnp/bin/bash",
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            result = self.run(
                "{} sign -inFile {} -outFile {} -selfSign 1".format(
                    signer, unsigned, signed),
                ignore_errors=True, quiet=True)
            if result != 0:
                os.unlink(unsigned)
                raise ConanException(
                    "binary-sign-tool failed on {} (exit {})".format(target, result))
            sections = subprocess.run(
                "{} -S {}".format(readelf, signed),
                shell=True, executable="/data/service/hnp/bin/bash",
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if b".codesign" not in sections.stdout:
                raise ConanException(
                    "signed image has no .codesign section: {}".format(target))
            os.replace(signed, target)
            os.unlink(unsigned)
            os.chmod(target, os.stat(target).st_mode
                     | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # ------------------------------------------------------------------
    # build phases
    # ------------------------------------------------------------------
    def generate(self):
        # Writes the .pc files for glib/pixman/slirp/capstone and hands their
        # location to configure through PKG_CONFIG_PATH (see _configure_command).
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        os.makedirs(self.build_folder, exist_ok=True)

        self._run(self._configure_command(), what="qemu configure")
        meson_dir = self._meson_dir()
        self.output.info("[qemu] meson build directory: {}".format(meson_dir))

        # Deliberately restrained: this host is memory-oversubscribed, and a
        # wide ninja fan-out trades parallelism for fork-OOM retries.  The
        # interpreter environment is passed on because several build steps and
        # the meson test driver below run through the venv's python.
        jobs = str(max(1, min(build_jobs(self), 4)))
        env_prefix = self._build_env_prefix()
        self._run("{} ninja -C {} -j {}".format(env_prefix, meson_dir, jobs).strip(),
                  what="qemu ninja build")

        # Upstream's own unit suite runs natively on the build host (the
        # qtest/functional suites need a bootable guest, which this host
        # cannot provide), so these are the meaningful upstream checks here.
        # The tree's own meson is used for the reason given in _meson_binary(),
        # and only the documented host-limited tests are skipped.
        #
        # The tests are named individually rather than excluded with
        # `--exclude`, which meson only learned in 1.12: the venv meson comes
        # from the wheel bundled with this QEMU (1.5.0), so naming what to run
        # is the form that works across the versions actually in play.  See
        # _unit_suite_selection().
        #
        # No `--suite unit` here: that option *widens* the selection instead of
        # intersecting with it, so combining the two re-runs the very tests the
        # list leaves out (measured: all 99 ran, the 5 host-limited ones among
        # them).  The names alone are both sufficient and narrow.
        selection = " ".join(self._unit_suite_selection(meson_dir))
        self._run(
            "{} {} test -C {} --print-errorlogs {}".format(
                env_prefix, self._meson_binary(meson_dir), meson_dir, selection).strip(),
            what="qemu upstream unit suite", retries=2, retry_delay=20)

    def package(self):
        meson_dir = self._meson_dir()
        staging = os.path.join(self.build_folder, ".install-staging")
        if os.path.isdir(staging):
            shutil.rmtree(staging)
        os.makedirs(staging)

        # DESTDIR install, then normalise: QEMU's relocatable path machinery
        # (relocatable = true) resolves share/qemu relative to the executable,
        # so moving the tree afterwards is safe and the packaged binaries find
        # pc-bios no matter where the package is unpacked.
        self._run(
            "{} DESTDIR={} ninja -C {} install".format(
                self._build_env_prefix(), staging, meson_dir).strip(),
            what="qemu install")

        staged_prefix = os.path.join(staging, STAGING_PREFIX.lstrip("/"))
        if not os.path.isdir(staged_prefix):
            raise ConanException(
                "install staging prefix missing: {}".format(staged_prefix))
        for entry in sorted(os.listdir(staged_prefix)):
            shutil.move(os.path.join(staged_prefix, entry),
                        os.path.join(self.package_folder, entry))
        shutil.rmtree(staging, ignore_errors=True)

        for name in ("COPYING", "LICENSE"):
            candidate = os.path.join(self.source_folder, name)
            if os.path.isfile(candidate):
                shutil.copy2(candidate, os.path.join(self.package_folder, name))
                break

        self._sign_elf_tree(os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
