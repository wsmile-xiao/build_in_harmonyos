#!/usr/bin/env python3
"""Conan recipe — Godot 4.7.2-stable (upstream tag 4.7.2-stable), SCons build.

Cross-compiled for HarmonyOS PC (OHOS aarch64) as a release *export template*
(`target=template_release`): the editor build (TOOLS_ENABLED) is trimmed away,
which is the intended runtime shape for playing/exported games on device.

SCons toolchain injection strategy (C-class know-how, see notes.md):
- Godot's SCons layer has NO sysroot/target concept of its own; CC/CXX alone
  only swap the compiler path. The injection point is the generic SCons
  variables `ccflags=`/`linkflags=` (SConstruct appends them verbatim to every
  compile/link action) — verified to reach 100% of 2407 compile commands.
- Platform selection: `platform=linuxbsd` + OHOS sysroot (musl/libc++), all
  Linux desktop deps (X11/wayland/dbus/pulse/alsa/udev/fontconfig/speechd/
  accesskit) disabled at configure time; godot's builtin thirdparty bundles
  (freetype/harfbuzz/icu/mbedtls/zlib/zstd/...) keep the recipe dependency-free.
- musl quirks handled by the two patches: no libatomic in sysroot (64-bit
  atomics are libc builtins), and SDL's async-cancellation setup block is
  removed outright (deferred cancellation is the POSIX default and nothing
  in the engine calls pthread_cancel; musl provides no
  pthread_setcanceltype()).
- SCons runs through `python3 -m SCons` from an isolated pip --target dir
  (same pattern as gpsd/3.26 and dxx-rebirth/0.6 recipes in this repo).
"""

import os

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class GodotConan(ConanFile):
    name = "godot"
    version = "4.7.2-stable"
    description = "Godot Engine - multi-platform 2D and 3D game engine (release export template)"
    license = "MIT"
    homepage = "https://godotengine.org"
    url = "https://github.com/godotengine/godot"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # SCons build helper installed into an isolated buildenv prefix.
    # Cannot be a tool_requires (not in ohpcd registry); pip --target keeps
    # build() free of ambient tool assumptions (R33).
    _SCONS_VERSION = "4.11.1"

    # Export-template module trim: drop heavyweight/exotic modules that do not
    # affect game playback (C# mono, jolt physics, raycast/embree, XR family,
    # editor-only asset pipelines). See notes.md experiment 6 for the matrix.
    _DISABLED_MODULES = [
        "mono", "jolt_physics", "raycast", "openxr", "webxr", "mobile_vr",
        "camera", "fbx", "xatlas_unwrap", "vhacd", "lightmapper_rd",
    ]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Zero external requirements: godot vendors freetype, harfbuzz, icu4c,
        # mbedtls, zlib, zstd, brotli, enet, miniupnpc, wslay, pcre2, libpng,
        # libjpeg-turbo, libwebp, libogg, libvorbis, libtheora, astcenc,
        # basis_universal, etcpak, thorvg, glslang, spirv-* and more (69
        # thirdparty/ dirs) as builtins.
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        scons_prefix = os.path.join(self.build_folder, "_scons_env")
        os.makedirs(scons_prefix, exist_ok=True)
        self.run(
            "python3 -m pip install --quiet --no-input "
            f"--target={scons_prefix} scons=={self._SCONS_VERSION}",
            env="build",
        )

        if self.settings.os == "OHOS":
            # OHOS executors have no /bin/sh on PATH, and SCons's posix
            # platform hardcodes env['SHELL'] = 'sh' — job spawns die with
            # "sh: No such file or directory". Patch the installed SCons
            # module to use the OHOS system shell instead (same fix as
            # gpsd/3.26; CI log PR #9775 build #45541 confirmed the failure).
            self.run(
                f"PYTHONPATH={scons_prefix} python3 -c \""
                r"import SCons.Platform.posix as m;"
                r"f=m.__file__;"
                r"s=open(f).read();"
                r"old=r\"env['SHELL']          = 'sh'\";"
                r"new=r\"env['SHELL']          = '/system/bin/sh'\";"
                r"open(f,'w').write(s.replace(old,new) if old in s else s);"
                r"print('patched posix SHELL ->', f)"
                "\"",
                env="build",
            )

        VirtualBuildEnv(self).generate()
        env = Environment()
        env.define_path("PYTHONPATH", scons_prefix)
        env.vars(self).save_script("scons_env")

    def _ohos_cross_flags(self):
        """Resolve --target/--sysroot for OHOS cross compilation.

        Follows the repo-standard discovery chain (see aespipe/2.4h):
        1. tools.build:sysroot conf (if the profile supplies it)
        2. <compiler-dir>/../sysroot.. walking up to 5 parents (SDK layout)
        3. target flag only (worker wrapper profile supplies resources)
        """
        target = "aarch64-linux-ohos"
        flags = [f"--target={target}"]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compilers.get("c") or compilers.get("cpp")
        candidates = []
        configured = self.conf.get("tools.build:sysroot", default="", check_type=str)
        if configured:
            candidates.append(configured)
        if compiler:
            directory = os.path.dirname(os.path.abspath(compiler))
            for _ in range(5):
                candidates.append(os.path.join(directory, "sysroot"))
                parent = os.path.dirname(directory)
                if parent == directory:
                    break
                directory = parent
        for candidate in candidates:
            if os.path.isdir(candidate):
                flags.append(f"--sysroot={candidate}")
                break
        return " ".join(flags)

    def _scons_args(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        args = [
            f'CC="{cc}"',
            f'CXX="{cxx}"',
            "use_llvm=yes",
            # OHOS sysroot has no libatomic; libc++ is linked dynamically and
            # managed by conan — see patch 0001 and notes.md failure mode #1/#2.
            "use_static_cpp=no",
            "platform=linuxbsd",
            "target=template_release",
            "arch=arm64",
            "production=no",
            "lto=none",  # keep CI link time bounded
            # Linux desktop stack fully trimmed for the OHOS runtime.
            "x11=no", "wayland=no", "dbus=no", "pulseaudio=no", "alsa=no",
            "udev=no", "fontconfig=no", "speechd=no", "accesskit=no",
            "touch=no",
            # Unit tests are compiled into the binary (doctest) so the
            # consumer can run them headless on device: godot --test.
            "tests=yes",
            "progress=no",
        ]
        if self.settings.os == "OHOS":
            cross = self._ohos_cross_flags()
            args.append(f'ccflags="{cross}"')
            args.append(f'linkflags="{cross}"')
        for m in self._DISABLED_MODULES:
            args.append(f"module_{m}_enabled=no")
        return " ".join(args)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("Godot requires a Linux-compatible POSIX host")
        apply_conandata_patches(self)
        # Redirect build objects to a subdir so the binary is easy to collect.
        jobs = os.cpu_count() or 2
        jobs = min(jobs, 4)  # bounded parallelism: heavy TUs (harfbuzz/icu)
        self.run(f"python3 -m SCons -j{jobs} {self._scons_args()}")

    def package(self):
        # SCons has no install target for executables; collect the artifact.
        import glob
        import shutil

        from conan.tools.files import copy

        matches = glob.glob(
            os.path.join(self.build_folder, "bin", "godot.linuxbsd.template_release.*")
        )
        matches = [m for m in matches if os.path.isfile(m)]
        if not matches:
            self.output.error("godot binary not found under bin/ — build failed?")
            return
        binary = matches[0]
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        dest = os.path.join(bindir, "godot")
        shutil.copy2(binary, dest)
        os.chmod(dest, 0o755)
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
