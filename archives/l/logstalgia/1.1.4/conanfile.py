#!/usr/bin/env python3
"""Conan recipe - logstalgia 1.1.4 (Autotools) for HarmonyOS PC.

logstalgia is a HTTP access log visualization tool that replays or streams
web server access logs as a retro arcade game simulation (SDL2 + desktop
OpenGL).

OHOS adaptation strategy (all verified locally on 2026-09-09):

1. Upstream source is the official release tarball (a `make dist` artifact):
   it ships a pre-generated `configure`, `Makefile.in`, `aclocal.m4`,
   `build-aux/config.guess|config.sub` AND the full `src/core` submodule
   content. No autoreconf / submodule handling needed.

2. OHOS has no desktop GL/GLU/GLEW. The GL stack is provided by:
   - gl4es/1.1.6 (conan pkg): `libGL.so` (desktop GL 1.5/2.1 over GLES2)
     plus `GL/gl.h`, `GL/glext.h`, `GL/glu.h` headers.
   - compat/glu_glew_shim.cpp (this recipe): gl4es ships GLU *declarations*
     only (no glu* symbols in libGL.so), so we implement the five GLU
     functions logstalgia actually uses (gluPerspective, gluProject,
     gluUnProject, gluErrorString, gluBuild2DMipmaps + configure-time
     gluBeginCurve) and the three GLEW runtime symbols (glewInit,
     glewGetErrorString, glewExperimental) as libGLU.a.
   - compat/GL/glew.h (this recipe): a minimal GLEW header shim.
     Core's gl.h does `#include <GL/glew.h>`; the shim maps it onto gl4es
     headers, defines GLEW_VERSION_2_0 (gl4es targets desktop GL 2.1) and
     GL_COMPUTE_SHADER (GL 4.3 constant referenced by Core's shader.cpp but
     absent from gl4es' glext.h; never dereferenced at runtime because
     logstalgia ships no compute shaders).

3. configure drives everything through pkg-config and env overrides, so no
   upstream source patch is needed. The recipe generates alias .pc files
   (gl/glu/glew/freetype2) next to PkgConfigDeps output:
   - `gl`  -> gl4es (provides -lGL)
   - `glu` -> libGLU.a shim
   - `glew`-> shim headers (-lGLU for the runtime symbols)
   - `freetype2` -> conan freetype (upstream requires >= 9.0.3, the libtool
     version of freetype 2.14.3 is 26.6.20)

4. Boost: conan boost/1.84.0 (manual lib build) provides
   libboost_filesystem.a; libboost_system is header-only since 1.69 so
   --with-boost-system=boost_filesystem satisfies AX_BOOST_SYSTEM's
   AC_CHECK_LIB (the check links against an existing lib and looks up
   `exit`, a libc symbol). BOOST_SP_NO_PTHREAD_SETCANCELSTATE is required
   (OHOS musl lacks pthread_setcancelstate) and comes from the boost
   recipe's cpp_info; we also pass it explicitly in CPPFLAGS.

5. Runtime (E467 class): configure conftests are run through the OHOS
   dynamic loader, so LD_LIBRARY_PATH must expose libc++_shared.so (SDK
   llvm lib dir) plus every shared dependency libdir; the recipe injects
   them via buildenv_info. test_package additionally points LIBGL_GLES/
   LIBGL_EGL at the OHOS system GLES3/EGL libs (same pattern as gl4es'
   own test_package).
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LogstalgiaConan(ConanFile):
    name = "logstalgia"
    version = "1.1.4"
    description = "Web server access log visualization tool (HTTP log replay as a retro arcade game)"
    license = "GPL-3.0-or-later"
    homepage = "https://logstalgia.io/"
    url = "https://github.com/acaudwell/Logstalgia"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    exports_sources = (
        "compat/glu_glew_shim.cpp",
        "compat/GL/glew.h",
    )

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # zlib conflict: boost/1.84.0 requires zlib/1.3.1 while the
        # libpng/sdl2-image closure is built against zlib/1.3.1.1.
        # Override to 1.3.1.1 (same resolution as abiword plugins, W0 notes).
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("sdl2/2.30.10")
        self.requires("sdl2-image/2.8.12")
        self.requires("boost/1.84.0")
        self.requires("glm/0.9.9.8")
        self.requires("freetype/2.14.3.1")
        self.requires("pcre2/10.45.1.1")
        self.requires("libpng/1.6.58.2")
        self.requires("gl4es/1.1.6")

    def build_requirements(self):
        # configure uses pkg-config heavily; pkgconf from the registry keeps
        # behaviour identical between local and CI sandboxes.
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compat_dir(self):
        return os.path.join(self.source_folder, "compat")

    def _write_alias_pc(self, gens_dir, name, description, version, libs, cflags):
        pc = os.path.join(gens_dir, f"{name}.pc")
        with open(pc, "w", encoding="utf-8") as f:
            f.write("\n".join([
                f"Name: {name}",
                f"Description: {description}",
                f"Version: {version}",
                f"Libs: {libs}",
                f"Cflags: {cflags}",
                "",
            ]))
        return pc

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        gens = self.generators_folder
        gl4es = self.dependencies["gl4es"]
        gl4es_root = gl4es.package_folder
        gl4es_inc = os.path.join(gl4es_root, "include")
        compat = self._compat_dir()
        compat_inc = compat
        compat_lib = os.path.join(compat, "lib")

        # ---- alias .pc files for names upstream configure expects ----
        # gl -> gl4es libGL.so
        self._write_alias_pc(
            gens, "gl",
            "gl4es desktop-GL compatibility layer (libGL.so on OHOS)",
            "1.1.6",
            f"-L{os.path.join(gl4es_root, 'lib')} -lGL",
            f"-I{gl4es_inc}")
        # glu -> our static GLU shim
        self._write_alias_pc(
            gens, "glu",
            "GLU software shim (Mesa-style maths, static libGLU.a) for OHOS",
            "1.0.0",
            f"-L{compat_lib} -lGLU",
            f"-I{compat_inc} -I{gl4es_inc}")
        # glew -> our GLEW header shim + runtime symbols in libGLU.a
        self._write_alias_pc(
            gens, "glew",
            "OHOS GLEW shim (headers only, symbols in libGLU.a)",
            "2.1.0",
            f"-L{compat_lib} -lGLU",
            f"-I{compat_inc}")
        # freetype2 -> conan freetype (libtool version 26.6.20 >= 9.0.3)
        ft = self.dependencies["freetype"]
        ft_root = ft.package_folder
        self._write_alias_pc(
            gens, "freetype2",
            "FreeType 2 font engine (alias of conan freetype)",
            "26.6.20",
            f"-L{os.path.join(ft_root, 'lib')} -lfreetype",
            f"-I{os.path.join(ft_root, 'include', 'freetype2')}")

        # ---- AutotoolsToolchain: flags & configure overrides ----
        tc = AutotoolsToolchain(self, prefix=self.package_folder)
        environment = tc.environment()

        glm = self.dependencies["glm"]
        boost = self.dependencies["boost"]

        # ---- E467: configure conftests are executed by the OHOS loader and
        # need libc++_shared.so (SDK llvm lib) plus every shared dependency
        # loadable. The generated conanbuild.sh source-chain proved fragile
        # under the conan subprocess (LD_LIBRARY_PATH exported inside the
        # script did not reach the loader); applying the Environment from
        # python (env.vars(self).apply()) injects it into the subprocess env
        # directly - verified working (same environment as abx/0.1 uses via
        # toolchain env, plus the explicit apply() belt-and-braces).
        self._loader_env = Environment()
        libdirs = set()
        for dep in self.dependencies.values():
            if dep.package_folder and dep.cpp_info.libdirs:
                for libdir in dep.cpp_info.libdirs:
                    libdirs.add(os.path.join(dep.package_folder, libdir))
        sdk_cxx = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                   "ohos/native/llvm/lib/aarch64-linux-ohos")
        for d in sorted(libdirs) + [sdk_cxx]:
            self._loader_env.append_path("LD_LIBRARY_PATH", d)

        # ---- AutotoolsToolchain: flags & configure overrides ----
        tc = AutotoolsToolchain(self)

        glm = self.dependencies["glm"]
        boost = self.dependencies["boost"]

        tc.configure_args.append("--build=aarch64-linux")
        tc.configure_args.append("--host=aarch64-linux")
        # AX_BOOST_BASE wants a prefix with include/ and lib/
        tc.configure_args.append(f"--with-boost={boost.package_folder}")
        # boost_system is header-only since 1.69: satisfy AX_BOOST_SYSTEM's
        # AC_CHECK_LIB(<name>, exit) with an existing library from the boost pkg.
        tc.configure_args.append("--with-boost-system=boost_filesystem")

        # GL/GLU/GLEW headers come from gl4es + shim; glm is checked via
        # plain AC_CHECK_HEADER (no pkg-config), so CPPFLAGS must carry it.
        tc.configure_args.append(
            "CPPFLAGS=-I{} -I{} -I{} -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE".format(
                gl4es_inc, compat_inc,
                os.path.join(glm.package_folder, "include")))
        # libboost_filesystem.a lives in the boost package libdir
        tc.configure_args.append(
            f"LDFLAGS=-L{os.path.join(boost.package_folder, 'lib')}")
        # PKG_CONFIG_PATH: PkgConfigDeps output + alias pc files.
        tc.configure_args.append(f"PKG_CONFIG_PATH={gens}")

        tc.generate(env=environment)

        # build() drives configure through explicit bash (mksh resets
        # LD_LIBRARY_PATH, see _bash()); keep the full configure argument
        # list (flags + overrides from above) for that call.
        self._configure_args = list(tc.configure_args)

    def _bash(self):
        """Explicit bash path. OHOS /bin/sh is mksh, which RESETS
        LD_LIBRARY_PATH on startup (verified: a correct value exported into
        the parent env is silently dropped by /bin/sh -c). conan's self.run()
        wraps commands with /bin/sh, so every conftest would die with
        "Error loading shared library libc++_shared.so". Driving
        configure/make through hnp bash (same approach as sdcc/4.6.0 and
        ntl/11.6.0 recipes) keeps the loader environment intact."""
        return os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

    def _run_bash(self, cmd, env):
        """Run a command through bash. The conanbuild env-file chain is
        sourced first, then the E467 loader paths are exported, then the
        command runs. The payload is written to a script file to avoid any
        shell-quoting pitfalls with nested quotes."""
        sh = self._bash()
        env_files = "\n".join(
            f'. "{f}"' for f in self._conanbuild_scripts())
        script = os.path.join(self.build_folder, "run_build_step.sh")
        ld_value = env._values.get("LD_LIBRARY_PATH")
        ld_paths = []
        if ld_value is not None:
            for v in ld_value._values:
                if isinstance(v, str):
                    ld_paths.append(v)
        export_ld = ""
        if ld_paths:
            export_ld = 'export LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH"'.format(
                ":".join(ld_paths))
        with open(script, "w", encoding="utf-8") as f:
            f.write(f"#!/usr/bin/env bash\nset -e\n{env_files}\n{export_ld}\n{cmd}\n")
        self.run(f"{sh} {script}", env=None)

    def _conanbuild_scripts(self):
        """Absolute paths of the generated conanbuild*.sh chain to source."""
        gens = self.generators_folder
        scripts = []
        for name in ("conanbuildenv-release-armv8.sh", "conanautotoolstoolchain.sh"):
            p = os.path.join(gens, name)
            if os.path.isfile(p):
                scripts.append(p)
        return scripts

    def _loader_env_ld_paths(self):
        """LD_LIBRARY_PATH entries recorded in self._loader_env (E467)."""
        ld_value = self._loader_env._values.get("LD_LIBRARY_PATH") \
            if getattr(self, "_loader_env", None) else None
        paths = []
        if ld_value is not None:
            for v in ld_value._values:
                if isinstance(v, str):
                    paths.append(v)
        return paths

    def _materialize_compat(self):
        """Ensure compat/{glu_glew_shim.cpp,GL/glew.h} exist in the
        source folder. exports_sources normally provides them, but the CI
        worker showed the nested header missing while the .cpp arrived;
        re-copy from the recipe folder as a belt-and-braces measure."""
        compat = self._compat_dir()
        targets = [
            ("glu_glew_shim.cpp", "glu_glew_shim.cpp"),
            (os.path.join("GL", "glew.h"),
             os.path.join("GL", "glew.h")),
        ]
        for rel, _ in targets:
            dst = os.path.join(compat, rel)
            if os.path.isfile(dst):
                continue
            src_dir = os.path.join(self.recipe_folder, "compat") \
                if self.recipe_folder else None
            if src_dir and os.path.isfile(os.path.join(src_dir, rel)):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                copy(self, rel, src_dir, os.path.dirname(dst))
            else:
                raise ConanException(
                    f"compat file missing and not recoverable: {rel}")

    def build(self):
        # 0. defensive compat materialization: exports_sources copies the
        # compat files into the source folder. On CI the original
        # compat/include/GL/glew.h was silently DROPPED by the repo-wide
        # .gitignore rule `archives/**/include/` (never committed), so the
        # file layout is now compat/GL/glew.h. Belt-and-braces: re-copy
        # both compat files from the recipe folder (the git checkout on
        # CI) in case exports_sources misses them again.
        self._materialize_compat()

        # 1. compile the GLU/GLEW shim into compat/lib/libGLU.a
        compat = self._compat_dir()
        compat_lib = os.path.join(compat, "lib")
        os.makedirs(compat_lib, exist_ok=True)
        gl4es = self.dependencies["gl4es"]
        gl4es_inc = os.path.join(gl4es.package_folder, "include")
        shim_src = os.path.join(compat, "glu_glew_shim.cpp")
        shim_obj = os.path.join(compat_lib, "glu_glew_shim.o")
        cxx = self.conf.get("tools.build:compiler_executables",
                            default={}, check_type=dict).get(
                                "cpp", "clang++")
        ar = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict).get("ar", "llvm-ar")
        self.run(f"{cxx} -std=gnu++11 -c {shim_src} -o {shim_obj} "
                 f"-I{gl4es_inc} -I{os.path.join(compat, 'include')}",
                 env="conanbuild")
        self.run(f"{ar} rcs {os.path.join(compat_lib, 'libGLU.a')} {shim_obj}",
                 env="conanbuild")

        # 1.5 headless matrix self-test (AI review PR #9149 follow-up):
        # link a tiny probe against libGLU.a and assert the GLU matrix
        # maths (identity inverse, P*M order, project/unproject round-trip).
        # Runs without any GL context - evidence lands in the CI log.
        probe_src = os.path.join(compat, "shim_selftest_probe.cpp")
        stub_src = os.path.join(compat, "gl_stub_for_probe.cpp")
        probe_bin = os.path.join(compat_lib, "shim_selftest_probe")
        with open(probe_src, "w", encoding="utf-8") as f:
            f.write(
                "#include <cstdio>\n"
                "extern \"C\" int glu_glew_shim_selftest(void);\n"
                "int main() {\n"
                "    int rc = glu_glew_shim_selftest();\n"
                '    std::printf("glu_glew_shim_selftest: %s (rc=%d)\\n",'
                " rc == 0 ? \"PASS\" : \"FAIL\", rc);\n"
                "    return rc;\n"
                "}\n")
        # stub the two GL entry points the shim's texture path references:
        # the self-test only exercises pure matrix maths, so the stubs are
        # never called - they merely satisfy the static linker. (Linking the
        # real gl4es libGL crashes on headless workers during its loader
        # init without LIBGL_* env.)
        with open(stub_src, "w", encoding="utf-8") as f:
            f.write(
                "extern \"C\" {\n"
                "void glTexImage2D() {}\n"
                "void glMultMatrixd(const double*) {}\n"
                "}\n")
        self.run(f"{cxx} -std=gnu++11 {probe_src} {stub_src} -o {probe_bin} "
                 f"-I{gl4es_inc} -I{compat} "
                 f"{os.path.join(compat_lib, 'libGLU.a')}",
                 env="conanbuild")
        # drive the probe through the same bash-script path as configure/make
        # (OHOS /bin/sh resets LD_LIBRARY_PATH; see _bash()).
        self._run_bash(f"{probe_bin}", self._loader_env)

        # 2. upstream configure + make (release tarball ships configure).
        # Driven through bash: /bin/sh (mksh) resets LD_LIBRARY_PATH, which
        # kills every configure conftest (E467 loader issue, see _bash()).
        # AutotoolsToolchain already injects --prefix/--bindir/... into
        # configure_args, so just quote and forward the whole list.
        import shlex
        src = self.source_folder
        bld = self.build_folder
        quoted_args = " ".join(shlex.quote(a) for a in self._configure_args)
        configure_cmd = (
            f'cd {shlex.quote(bld)} && {shlex.quote(os.path.join(src, "configure"))}'
            + (" " + quoted_args if quoted_args else ""))
        # E114/E011: configure embeds a config.status template that creates
        # a 0700 temp dir via `umask 077 && mktemp -d "./confXXXXXX"`;
        # HMDFS setgid semantics make it unwritable ("subs1.awk: Permission
        # denied"). Patch the configure script (the embedded template) before
        # running it (same fix as abx/0.1).
        configure_script = os.path.join(src, "configure")
        self._make_config_status_tmp_writable(configure_script)

        self._run_bash(configure_cmd, self._loader_env)

        self._run_bash(f'cd {shlex.quote(bld)} && make -j{os.cpu_count() or 2}',
                       self._loader_env)

    @staticmethod
    def _make_config_status_tmp_writable(path):
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        patched = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`',
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            'mkdir "$tmp"',
        )
        if patched != content:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(patched)

    def package(self):
        # The upstream Makefile installs bin/logstalgia + share/logstalgia
        # data files + a man page. package_folder is not known at
        # generate() time (prefix would silently default to "/"), so
        # install by hand from the build tree (copy pattern used by many
        # recipes in this repo).
        bld = self.build_folder
        src = self.source_folder
        compat = self._compat_dir()
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "logstalgia", bld, bindir)
        # data files (fonts/textures/example log) - expected at
        # SDLAPP_RESOURCE_DIR = <prefix>/share/logstalgia
        resdir = os.path.join(self.package_folder, "share", "logstalgia")
        os.makedirs(resdir, exist_ok=True)
        copy(self, "ball.tga", os.path.join(src, "data"), resdir)
        copy(self, "glow.tga", os.path.join(src, "data"), resdir)
        copy(self, "example.log", os.path.join(src, "data"), resdir)
        fontsdir = os.path.join(resdir, "fonts")
        os.makedirs(fontsdir, exist_ok=True)
        copy(self, "README", os.path.join(src, "data", "fonts"), fontsdir)
        copy(self, "FreeMonoBold.ttf", os.path.join(src, "data", "fonts"), fontsdir)
        copy(self, "FreeSerif.ttf", os.path.join(src, "data", "fonts"), fontsdir)
        # Ship the GLU/GLEW shim static lib so the consumer-side test phase
        # (test_package) can link glu_glew_shim_selftest() and verify the
        # matrix maths there too (AI review PR #9643 follow-up: the self-test
        # used to run only in the build() probe). Not part of the public
        # consumer interface (logstalgia is an application package) - nothing
        # declares it in cpp_info.libs.
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        copy(self, "libGLU.a", os.path.join(compat, "lib"), libdir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # runenv: consumers that launch logstalgia need LIBGL_* pointed at
        # the OHOS system GLES3/EGL stacks (same pattern as gl4es pkg).
        self.runenv_info.define("LIBGL_GLES", "/system/lib64/libGLESv3.so")
        self.runenv_info.define("LIBGL_EGL", "/system/lib64/libEGL.so")
