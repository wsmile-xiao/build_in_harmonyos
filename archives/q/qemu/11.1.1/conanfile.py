#!/usr/bin/env python3
"""Conan recipe — QEMU 11.1.1 (system emulator, riscv64-softmmu).

QEMU's build is driven by its own `./configure` which wraps Meson + Ninja
under the hood.  It links glib/pixman/zlib and produces executables
(qemu-system-riscv64, qemu-img, qemu-nbd, ...).

Platform adaptations for HarmonyOS PC (arm64):
  - meson.build: host_os "HarmonyOS" is normalized to "linux" so the
    CONFIG_LINUX code paths (syscall wrappers, UFFD, SG_IO, PR manager) are
    compiled instead of falling back to the non-Linux stubs.
  - net/can/meson.build: skip can_socketcan (requires a Linux CAN device the
    OHOS host does not provide) while keeping host_os==linux for the rest.
  - Configure disables optional host features unavailable/broken on OHOS:
    kvm/hvf, GTK/SDL/VNC/OpenGL UI, D-Bus display, Linux keyring (sysroot
    linux/keyctl.h uses __user undeclared), guest-agent (missing getutxent),
    libssh/gnutls/nettle crypto, bzip2/lzo/snappy/zstd compression, seccomp,
    curl, vhost-user/vhost-kernel, slirp.
  - Meson+Ninja need an absolute clang/llvm toolchain on PATH: the OHOS SDK
    compiler lives under /data/service/hnp/bin and is not on the default PATH.
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


def _is_elf_file(path):
    try:
        with open(path, "rb") as fh:
            return fh.read(4) == b"\x7fELF"
    except OSError:
        return False


class QemuConan(ConanFile):
    name = "qemu"
    version = "11.1.1"
    description = "QEMU 11.1.1 system emulator (riscv64-softmmu) for HarmonyOS PC"
    license = "GPL-2.0-or-later"
    homepage = "https://www.qemu.org"
    url = "https://gitlab.com/qemu-project/qemu"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def config_options(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("qemu currently supports only OHOS armv8")

    def requirements(self):
        # QEMU links glib (gmodule/gio), pixman and zlib.
        self.requires("glib/2.84.0", transitive_headers=True, transitive_libs=True)
        self.requires("pixman/0.46.4", transitive_headers=True, transitive_libs=True)
        # zlib is pulled in transitively but declared explicitly for clarity.
        self.requires("zlib/1.3.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        source_data = self.conan_data["sources"]
        get(self, url=source_data["url"], sha256=source_data.get("sha256", ""), strip_root=True)

    def generate(self):
        # Emit .pc files for ALL requirements (glib, pixman, zlib + their
        # transitive deps pcre2/libffi) into the generators folder, so Meson's
        # pkg-config lookup resolves every glib-2.0 Requires (libpcre2-8 ...).
        pkgconfig = PkgConfigDeps(self)
        pkgconfig.generate()

        # Write our extra env to its OWN script (NOT "conanbuild", which Conan
        # owns and aggregates). We source it in build() via env="qemu_env".
        env = Environment()
        sdk_bin = "/data/service/hnp/bin"
        if os.path.isdir(sdk_bin):
            # QEMU's configure picks clang via --cc, but Meson still probes
            # llvm-ar/llvm-ranlib/llvm-nm/llvm-strip and ninja by bare name.
            env.prepend_path("PATH", sdk_bin)
            env.define("AR", os.path.join(sdk_bin, "llvm-ar"))
            env.define("RANLIB", os.path.join(sdk_bin, "llvm-ranlib"))
            env.define("NM", os.path.join(sdk_bin, "llvm-nm"))
            env.define("STRIP", os.path.join(sdk_bin, "llvm-strip"))
        # mkvenv's tooling group (setuptools/wheel/pip per pythondeps.toml)
        # is only version-pinned ("accepted >="), NOT vendored under
        # python/wheels/, so pip must fetch it online.  CI round 4 (build
        # #61865, 2026-09-26) died when pip's default index
        # (files.pythonhosted.org) read-timed out from the CI egress -- the
        # vendored qemu.qmp wheel died with the same batch resolution.
        # Pin pip to the community mirror (the index mandated by the build
        # environment docs; coverage of setuptools/wheel/pip/qemu-qmp
        # verified live) and give it CI-grade patience.  Harmless on dev
        # machines whose default resolution already works.
        env.define("PIP_INDEX_URL",
                   "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple")
        env.define("PIP_DEFAULT_TIMEOUT", "60")
        env.define("PIP_RETRIES", "10")
        # CI workers ship python as an HNP under /data/service/hnp.  Three
        # CI rounds narrowed the venv failure to its true root:
        #   R1 (2026-09-23): venv python dies with "No module named
        #       'encodings'" in configure's mkvenv.
        #   R2 (2026-09-24, build #59984): injecting PYTHONHOME via
        #       shutil.which() probing did not help; dump still showed
        #       PYTHONHOME=(not set).
        #   R3 (2026-09-25, rrev 4c2424da): deterministic isfile() probing
        #       still not set in the dump -- and CPython's venv module
        #       EXPLAINS it: _call_new_python() pops PYTHONHOME/PYTHONPATH
        #       before spawning the "-m ensurepip" child (venv/__init__.py),
        #       so an env var can NEVER reach the process that crashes.
        # The actual defect is the venv HOME LANDMARK: configure picks
        # python3 through a symlinked bin dir (/data/service/hnp/bin), so
        # venv writes pyvenv.cfg home=<that dir> and the venv python looks
        # for <home>/lib/pythonX.Y/os.py inside a bin directory -> miss ->
        # falls back to the build-time baked prefix ($HOME/usr/local on CI),
        # which holds no stdlib.  Fix: hand configure a PRIVATE interpreter
        # dir whose layout makes the landmark valid:
        #   <build>/pymbin/python3 -> probed interpreter
        #   <build>/pymbin/lib     -> <stdlib prefix>/lib
        # pyvenv.cfg home=<build>/pymbin then resolves
        # pymbin/lib/pythonX.Y/os.py through the symlink for the venv
        # python AND its ensurepip child with no env var involved.
        # PYTHONHOME is kept only as a harmless fallback for non-venv
        # python spawns (configure/mkvenv themselves ran fine on CI).
        # Candidates are enumerated with os.path.isfile() (X_OK-independent)
        # and the prefix is derived from where the interpreter ACTUALLY
        # loads its stdlib (encodings.__file__), validated against
        # lib/pythonX.Y/os.py; a zero-subprocess layout scan is the
        # fallback.  On machines whose default resolution already works
        # this is a no-op.
        py_versions = ("python3", "python", "python3.12", "python3.11",
                       "python3.10", "python3.9")
        probe_dirs = []
        if os.path.isdir(sdk_bin):
            probe_dirs.append(sdk_bin)
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
        if os.path.isdir(home_bin):
            probe_dirs.append(home_bin)
        probe_dirs.extend(
            d for d in os.environ.get("PATH", "").split(os.pathsep) if d)
        seen = set()
        candidates = []
        for d in probe_dirs:
            for name in py_versions:
                pyexe = os.path.join(d, name)
                if pyexe not in seen and os.path.isfile(pyexe):
                    seen.add(pyexe)
                    candidates.append(pyexe)
        for pyname in py_versions:
            pyexe = shutil.which(pyname)
            if pyexe and pyexe not in seen:
                seen.add(pyexe)
                candidates.append(pyexe)
        chosen_pyexe = None
        cand = None
        cand_lib = "lib"  # primary path validates cand/lib below
        for pyexe in candidates:
            try:
                # encodings is loaded by the interpreter itself at startup:
                # if this process runs at all, its stdlib location is proven.
                probe = subprocess.run(
                    [pyexe, "-B", "-c",
                     "import sys, os, encodings; "
                     "assert sys.version_info >= (3, 9); "
                     "q = os.path.dirname(os.path.abspath(encodings.__file__)); "
                     "q = os.path.dirname(q); "
                     "q = os.path.dirname(q); "
                     "q = os.path.dirname(q); "
                     "print('python%d.%d' % sys.version_info[:2]); "
                     "print(q)"],
                    capture_output=True, text=True, timeout=30, check=True)
                lines = probe.stdout.splitlines()
                if len(lines) >= 2:
                    p = lines[1]
                    if p and os.path.isdir(p) and os.path.isfile(
                            os.path.join(p, "lib", lines[0], "os.py")):
                        chosen_pyexe = pyexe
                        cand = p
                        break
            except Exception:
                continue
        if cand is None:
            # Zero-subprocess fallback: no interpreter could be executed
            # (fork denied / exec bits unreadable on exotic layouts).  Trust
            # the on-disk layout instead: accept a probe dir as the bin/ of
            # a prefix that actually ships lib[64]/pythonX.Y/os.py.
            for d in probe_dirs:
                for pv in ("python3.12", "python3.11", "python3.10",
                           "python3.9"):
                    for libname in ("lib", "lib64"):
                        if os.path.isfile(
                                os.path.join(d, os.pardir, libname,
                                             pv, "os.py")):
                            cand = os.path.normpath(os.path.join(d, os.pardir))
                            cand_lib = libname
                            chosen_pyexe = os.path.join(d, "python3")
                            if not os.path.isfile(chosen_pyexe):
                                chosen_pyexe = os.path.join(d, "python")
                            if not os.path.isfile(chosen_pyexe):
                                chosen_pyexe = None  # PYTHONHOME/lib landmark only
                            break
                    if cand is not None:
                        break
                if cand is not None:
                    break
        if cand is not None:
            if chosen_pyexe is not None:
                wraps = os.path.join(self.build_folder, "pymbin")
                os.makedirs(wraps, exist_ok=True)
                for link, target in (("python3", chosen_pyexe),
                                     ("lib", os.path.join(cand, cand_lib))):
                    p = os.path.join(wraps, link)
                    if os.path.islink(p) or os.path.isfile(p):
                        os.remove(p)  # HMDFS: no ln -sf; rm then link
                    elif os.path.isdir(p):
                        shutil.rmtree(p)  # stale dir in our private wraps dir
                    if not os.path.exists(p):
                        os.symlink(target, p)
                # Must precede sdk_bin so configure's "check py" resolves
                # python3 to the landmark-correct dir, not the raw HNP
                # symlink (prepend order: later prepend wins the front).
                env.prepend_path("PATH", wraps)
            env.define("PYTHONHOME", cand)
        else:
            self.output.warning(
                "no usable python3 (>=3.9) found; QEMU configure "
                "will fail without one")
        # Point pkg-config at both the generated .pc dir (PkgConfigDeps emits
        # glib-2.0/pixman-1/zlib + transitive pcre2/libffi) and glib's own
        # lib/pkgconfig (which ships the gmodule-*/gthread/gio .pc sub-modules).
        gen_dir = self.generators_folder.replace("\\", "/")
        glib_pc = os.path.join(self.dependencies["glib"].package_folder, "lib/pkgconfig")
        env.define("PKG_CONFIG_PATH", f"{gen_dir}:{glib_pc}")

        # Embed RUNPATH to every requirement's lib dir so the produced
        # executables can locate the shared libs (pixman-1, glib, ...) at
        # runtime.  Without this the packaged bins report
        # "Error loading shared library libpixman-1.so.0" (rc=127) on OHOS,
        # because Meson only records build-time -L paths, not $ORIGIN.
        for dep_name in ("pixman", "glib", "zlib"):
            dep = self.dependencies.get(dep_name)
            if dep is None:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                env.append("LDFLAGS", f"-Wl,-rpath,{libdir}")
        env.vars(self).save_script("qemu_env")
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)

        # The tarball bundles the sources of several subprojects (dtc,
        # keycodemapdb, berkeley-softfloat-3, berkeley-testfloat-3, libvduse)
        # but ships [wrap-git] files for them, so Meson tries to `git
        # fetch` them from gitlab.com (unreachable in the OHOS build env).
        # When a .wrap has a matching bundled directory, drop the .wrap so
        # Meson uses the bundled sources instead of fetching.
        sp_dir = os.path.join(self.source_folder, "subprojects")
        if os.path.isdir(sp_dir):
            for name in os.listdir(sp_dir):
                wrap = os.path.join(sp_dir, name + ".wrap")
                bundled = os.path.join(sp_dir, name)
                if name.endswith(".wrap"):
                    continue
                if os.path.isfile(wrap) and os.path.isdir(bundled):
                    self.output.info(f"Using bundled subproject {name} (removing {name}.wrap)")
                    os.remove(wrap)

        if self.settings.os == "OHOS" and self.settings.arch == "armv8":
            cc = "/data/service/hnp/bin/clang"
            cxx = "/data/service/hnp/bin/clang++"
            ar = "/data/service/hnp/bin/llvm-ar"
        else:
            cc = os.environ.get("CC", "clang")
            cxx = os.environ.get("CXX", "clang++")
            ar = os.environ.get("AR", "llvm-ar")

        prefix = self.package_folder.replace("\\", "/")
        src = self.source_folder.replace("\\", "/")
        build_dir = os.path.join(self.build_folder, "b").replace("\\", "/")
        os.makedirs(build_dir, exist_ok=True)

        # QEMU wants out-of-tree build: run configure from build_dir.
        configure = (
            f"cd '{build_dir}' && '{src}/configure' "
            f"--prefix='{prefix}' "
            f"--target-list=riscv64-softmmu "
            f"--cc='{cc}' --cxx='{cxx}' "
            f"--disable-werror --disable-kvm --disable-hvf "
            f"--disable-dbus-display --disable-keyring "
            f"--disable-guest-agent --disable-guest-agent-msi "
            f"--disable-gtk --disable-sdl --disable-vnc --disable-opengl "
            f"--disable-libssh --disable-nettle --disable-gnutls "
            f"--disable-bzip2 --disable-lzo --disable-snappy --disable-lzfse "
            f"--disable-zstd --disable-seccomp --disable-curl "
            f"--disable-vhost-user --disable-vhost-kernel --disable-slirp "
        )
        self.run(configure, env="qemu_env")

        self.run(f"cd '{build_dir}' && ninja -j{os.cpu_count() or 2}", env="qemu_env")
        self.run(f"cd '{build_dir}' && ninja install", env="qemu_env")

    def _sign_ohos_elf(self, target):
        """OHOS refuses to load an unsigned ELF (Operation not permitted / rc=126).

        Re-sign every packaged executable so test_package can actually run them.
        Follows the E077 four-step flow: remove .codesign -> sign -selfSign 1.
        """
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        if not os.path.isfile(target):
            return
        self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
        self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')

    def _sign_all_elfs(self):
        targets = []
        for subdir in ("bin", "libexec", "lib"):
            binary_dir = os.path.join(self.package_folder, subdir)
            if os.path.isdir(binary_dir):
                for name in os.listdir(binary_dir):
                    path = os.path.join(binary_dir, name)
                    if os.path.isfile(path) and not os.path.islink(path) and _is_elf_file(path):
                        targets.append(path)
        for pattern in (os.path.join(self.package_folder, "lib", "**", "*.so*"),):
            targets.extend(glob.glob(pattern, recursive=True))
        seen = set()
        for target in targets:
            if target in seen:
                continue
            seen.add(target)
            self._sign_ohos_elf(target)

    def package(self):
        # `ninja install` with --prefix=<package_folder> already staged all
        # binaries/data into the package folder; nothing further to copy.
        if str(self.settings.os) == "OHOS":
            self._sign_all_elfs()

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.define_path("PATH", bindir)
        self.cpp_info.libs = []
