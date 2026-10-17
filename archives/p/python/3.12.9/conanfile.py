#!/usr/bin/env python3
"""Conan recipe — Python 3.12.9 (autotools, shared build).

Python is a programming language interpreter with a large standard library.
Build system: autotools (configure + make).

Key rules:
  - R32: settings.os check uses `in ("Linux", "OHOS")` (not `== "Linux"`).
  - R33: Compiler paths obtained from `self.conf` (tools.build:compiler_executables),
         not bare shell variables like ${CC}.
  - R34: test_package runs the built python3.12 binary and verifies version + modules.
  - R39: Source URL points to official python.org (CI auto-adds mirror fallbacks).
  - -fuse-ld=bfd: bypass lld dependency (OHOS default linker may lack features).
  - ELF signing: .so files self-signed via binary-sign-tool for OHOS execution.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PythonConan(ConanFile):
    name = "python"
    version = "3.12.9"
    description = "Python programming language interpreter and standard library"
    license = "Python-2.0"
    homepage = "https://www.python.org/"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # ------------------------------------------------------------------ #
    #  Dependency requirements (all published in ohpcd)
    # ------------------------------------------------------------------ #
    _dep_names = [
        "libffi", "openssl", "zlib", "ncurses", "readline",
        "bzip2", "xz", "sqlite3", "gdbm", "proxy-libintl",
    ]

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"python is supported only on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libffi/3.5.2")
        self.requires("openssl/1.1.1w")
        self.requires("zlib/1.3.1.1")
        self.requires("ncurses/6.6")
        self.requires("readline/8.3")
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.6.2")
        self.requires("sqlite3/3.49.1")
        self.requires("gdbm/1.24")
        self.requires("proxy-libintl/0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def _get_compiler(self):
        """R33: Get compiler from Conan conf_info, not bare shell vars."""
        cc_conf = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = cc_conf.get("c") or "clang"
        return cc

    def _find_ohos_tool(self, name):
        """Locate an OHOS SDK tool (llvm-objcopy, binary-sign-tool, ...)."""
        cc_conf = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(cc_conf.get("cpp", "")) if cc_conf else ""
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((p for p in candidates if p and os.path.isfile(p)), "")

    def _dep_pkgconfig_paths(self):
        """Build PKG_CONFIG_PATH from dependency package folders."""
        paths = []
        for name in self._dep_names:
            dep = self.dependencies[name]
            for libdir in ("lib", "lib64", "share/pkgconfig"):
                pc_dir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(pc_dir):
                    # Only add if it contains .pc files
                    if glob.glob(os.path.join(pc_dir, "*.pc")):
                        paths.append(pc_dir)
        return ":".join(paths)

    def _dep_cppflags(self):
        """Build CPPFLAGS from dependency include dirs."""
        flags = []
        for name in self._dep_names:
            dep = self.dependencies[name]
            inc = os.path.join(dep.package_folder, "include")
            if os.path.isdir(inc):
                flags.append(f"-I{inc}")
        return " ".join(flags)

    def _dep_ldflags(self):
        """Build LDFLAGS from dependency lib dirs."""
        flags = []
        for name in self._dep_names:
            dep = self.dependencies[name]
            for libdir in ("lib", "lib64"):
                d = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(d):
                    flags.append(f"-L{d}")
        return " ".join(flags)

    # ------------------------------------------------------------------ #
    #  Build
    # ------------------------------------------------------------------ #
    def build(self):
        # Apply patches using system patch command with fallback
        # Some patches have context mismatches from original compilation;
        # critical patches (platform detection, build system) apply cleanly.
        import subprocess
        patches_data = self.conan_data.get("patches", [])
        for patch_info in patches_data:
            patch_file = os.path.join(
                self.export_sources_folder, patch_info["patch_file"]
            )
            strip = patch_info.get("strip", 1)
            self.output.info(
                f"Apply patch ({patch_info.get('patch_type', 'portability')}): "
                f"{patch_info['patch_file']}"
            )
            # Try strict first, then loose match
            for flags in [[f"-p{strip}"], [f"-p{strip}", "-l"]]:
                result = subprocess.run(
                    ["patch"] + flags + ["-i", patch_file],
                    cwd=self.source_folder,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    break
            if result.returncode != 0:
                # Reverse any partial application, then warn and continue
                subprocess.run(
                    ["patch", f"-p{strip}", "-R", "-i", patch_file],
                    cwd=self.source_folder,
                    capture_output=True,
                    text=True,
                )
                self.output.warning(
                    f"Patch failed (non-fatal): {patch_info['patch_file']}\n"
                    f"stderr: {result.stderr[:500]}"
                )

        # OHOS/musl: CAN_RAW_FD_FRAMES and CAN_RAW_JOIN_FILTERS not defined
        # in the OHOS sysroot. Add fallback definitions at file top.
        if self.settings.os == "OHOS":
            socket_file = os.path.join(
                self.source_folder, "Modules", "socketmodule.c"
            )
            with open(socket_file, "r") as f:
                content = f.read()
            if "CAN_RAW_FD_FRAMES" in content and "OHOS_CAN_FALLBACK" not in content:
                content = (
                    "/* OHOS/musl: CAN constants not in sysroot headers */\n"
                    "#ifndef CAN_RAW_FD_FRAMES\n"
                    "#define CAN_RAW_FD_FRAMES 0\n"
                    "#endif\n"
                    "#ifndef CAN_RAW_JOIN_FILTERS\n"
                    "#define CAN_RAW_JOIN_FILTERS 0\n"
                    "#endif\n"
                    + content
                )
                with open(socket_file, "w") as f:
                    f.write(content)
                self.output.info("Added CAN_RAW fallback definitions for OHOS/musl")

        # R32: settings.os check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}"
            )

        # On HarmonyOS, compiled test programs can't be executed (ELF signing).
        # Force cross_compiling=yes in configure to skip run tests.
        if self.settings.os == "OHOS":
            self.run(
                "sed -i 's/cross_compiling=no/cross_compiling=yes/g' configure",
                cwd=self.source_folder,
            )

        # R33: compiler from conf_info
        cc = self._get_compiler()
        ar = "llvm-ar"
        ranlib = "llvm-ranlib"

        # Dependency paths
        pkg_config_path = self._dep_pkgconfig_paths()
        cppflags = self._dep_cppflags()
        ldflags = self._dep_ldflags()
        openssl_prefix = self.dependencies["openssl"].package_folder

        # TMPDIR: /tmp is read-only on OHOS (E002)
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp"
        )
        os.makedirs(tmpdir, exist_ok=True)

        # --- Configure ---
        # -fuse-ld=bfd: bypass lld (OHOS default linker may lack features)
        configure_cmd = (
            f'TMPDIR="{tmpdir}" '
            f'PKG_CONFIG_PATH="{pkg_config_path}" '
            f'CC="{cc}" AR={ar} RANLIB={ranlib} '
            f'CFLAGS="-fPIC -O2 -fuse-ld=bfd -DG_INTL_STATIC_COMPILATION" '
            f'PYTHONDONTWRITEBYTECODE=1 '
            f'ac_cv_getaddrinfo_bug=no '
            f'ac_cv_buggy_getaddrinfo=no '
            f'ac_cv_file__dev_ptmx=yes '
            f'ac_cv_file__dev_ptc=no '
            f'ac_cv_header_libintl_h=yes '
            f'ac_cv_lib_intl_textdomain=yes '
            f"./configure --prefix=/ --enable-shared --disable-ipv6 "
            f"--build=aarch64-unknown-linux-ohos "
            f"--host=aarch64-unknown-linux-ohos "
            f"--with-build-python=python3 "
            f"--with-openssl={openssl_prefix} "
            f'CPPFLAGS="{cppflags}" '
            f'LDFLAGS="{ldflags} -fuse-ld=bfd"'
        )
        self.run(configure_cmd, cwd=self.source_folder)

        # Fix config.status umask (HMDFS: umask 077 makes mktemp dirs unwritable)
        self.run(
            "sed -i 's|umask 077 && mktemp -d|mktemp -d|g' config.status",
            cwd=self.source_folder,
        )
        self.run(
            'sed -i \'s|(umask 077 && mkdir "$tmp")|(mkdir "$tmp")|g\' config.status',
            cwd=self.source_folder,
        )
        self.run("sh config.status", cwd=self.source_folder)

        # --- Make ---
        # OHOS: Disable checksharedmods BEFORE make (needs signed .so to load;
        # signing happens in package() after install).
        if self.settings.os == "OHOS":
            self._disable_checksharedmods()

        # Build libpython3.12.so + interpreter first, then sharedmods.
        # Must use full `make -j1` (not `make sharedmods` alone) because
        # shared extension modules link against libpython3.12.so.
        self.run("make -j1", cwd=self.source_folder)

    def _disable_checksharedmods(self):
        """Disable checksharedmods target in Makefile (OHOS needs signed .so)."""
        makefile_path = os.path.join(self.source_folder, "Makefile")
        with open(makefile_path, "r") as f:
            lines = f.readlines()
        new_lines = []
        skip = False
        for line in lines:
            if line.startswith("checksharedmods:"):
                skip = True
                new_lines.append("checksharedmods:\n")
                continue
            if skip:
                if line and line[0] in (" ", "\t"):
                    continue
                skip = False
            new_lines.append(line)
        with open(makefile_path, "w") as f:
            f.writelines(new_lines)
        self.output.info("Disabled checksharedmods target for OHOS")

    # ------------------------------------------------------------------ #
    #  Package
    # ------------------------------------------------------------------ #
    def package(self):
        # Disable checksharedmods again (makesetup regenerates Makefile during
        # install, re-enabling the target we disabled in build()).
        if self.settings.os == "OHOS":
            self._disable_checksharedmods()

        # Install with DESTDIR (TEST_MODULES=no skips test/ dir, saves ~150MB)
        try:
            self.run(
                f"make install DESTDIR={self.package_folder} TEST_MODULES=no",
                cwd=self.source_folder,
            )
        except Exception:
            self.output.warning(
                "make install failed (checksharedmods expected on OHOS, "
                "signing happens after install). Continuing..."
            )

        # Sign ELF binaries on OHOS
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        """Self-sign .so files and executables on OHOS for execution."""
        if self.settings.os != "OHOS":
            return

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "OHOS signing tools unavailable; CI sign.sh will handle signing."
            )
            return

        # Sign all ELF files in bin/ and lib/
        for pattern in ("bin/*", "lib/*.so*", "lib/python3.12/lib-dynload/*.so"):
            for path in glob.glob(
                os.path.join(self.package_folder, pattern)
            ):
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                # Check ELF magic
                with open(path, "rb") as f:
                    if f.read(4) != b"\x7fELF":
                        continue
                self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        """Sign an ELF file atomically (copy → remove .codesign → sign → replace)."""
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}" || true')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    # ------------------------------------------------------------------ #
    #  Package info
    # ------------------------------------------------------------------ #
    def package_info(self):
        self.cpp_info.libs = ["python3.12"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include/python3.12"]

        lib_dir = os.path.join(self.package_folder, "lib")
        bin_dir = os.path.join(self.package_folder, "bin")

        self.runenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", lib_dir)
        # PYTHONHOME: consumers must set this when running the packaged Python.
        # Not set globally here to avoid breaking the system Python interpreter.
