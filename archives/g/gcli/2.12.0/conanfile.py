#!/usr/bin/env python3
"""Conan recipe for the Homebrew gcli 2.12.0 task."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class GcliConan(ConanFile):
    name = "gcli"
    version = "2.12.0"
    package_type = "application"

    description = "Portable command-line client for Git forges"
    license = "BSD-2-Clause"
    homepage = "https://sr.ht/~herrhotzenplotz/gcli"
    url = "https://git.sr.ht/~herrhotzenplotz/gcli"
    topics = ("github", "gitlab", "gitea", "bugzilla", "cli")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        res_src = os.path.join(self.recipe_folder, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.export_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("gcli supports Linux/OHOS builds only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        export_dir = os.path.join(os.path.dirname(self.source_folder), "e")
        res_src = os.path.join(export_dir, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.source_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def generate(self):
        self._write_libcurl_pc()
        self._write_libcrypto_pc()

    def _default_prefix(self):
        return os.environ.get("DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local")

    def _resource_headers(self):
        return os.path.join(self.source_folder, "res", "headers")

    def _write_default_prefix_pc(self, filename, name, description, version, libs, cflags="-I${includedir}"):
        prefix = self._default_prefix()
        os.makedirs(self.generators_folder, exist_ok=True)
        pc_path = os.path.join(self.generators_folder, filename)
        with open(pc_path, "w", encoding="utf-8") as pc:
            pc.write(
                f"prefix={prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n\n"
                f"Name: {name}\n"
                f"Description: {description}\n"
                f"Version: {version}\n"
                f"Libs: -L${{libdir}} {libs}\n"
                f"Cflags: {cflags}\n"
            )

    def _write_libcurl_pc(self):
        self._write_default_prefix_pc(
            "libcurl.pc",
            "libcurl",
            "HarmonyOS PC libcurl from DEFAULT_PREFIX with bundled public headers",
            "8.15.0",
            "-lcurl -lssl -lcrypto -lz",
            f"-I{self._resource_headers()} -I${{includedir}}",
        )

    def _write_libcrypto_pc(self):
        self._write_default_prefix_pc(
            "libcrypto.pc",
            "libcrypto",
            "HarmonyOS PC OpenSSL crypto library from DEFAULT_PREFIX",
            "3.5.6",
            "-lcrypto",
        )

    def _pkg_config_path(self):
        sysroot = self._default_prefix()
        paths = [
            self.generators_folder,
            os.path.join(sysroot, "lib", "pkgconfig"),
            os.path.join(sysroot, "share", "pkgconfig"),
        ]
        existing = os.environ.get("PKG_CONFIG_PATH")
        if existing:
            paths.append(existing)
        return os.pathsep.join(paths)

    def _append_env(self, name, value):
        existing = os.environ.get(name, "")
        return f"{existing} {value}".strip()

    def _env_prefix(self):
        sysroot = self._default_prefix()
        resource_headers = self._resource_headers()
        assignments = {
            "PKG_CONFIG_PATH": self._pkg_config_path(),
            "CPPFLAGS": self._append_env(
                "CPPFLAGS",
                f"-I{resource_headers} -I{sysroot}/include",
            ),
            "LDFLAGS": self._append_env(
                "LDFLAGS",
                f"-L{sysroot}/lib -Wl,-rpath,{sysroot}/lib",
            ),
            "CCACHE": "env",
        }
        return " ".join(f"{key}={shlex.quote(value)}" for key, value in assignments.items())

    def _patch_configure(self, configure):
        replace_in_file(
            self,
            configure,
            """\tfor x in $*; do
\t\tif command -v $x >/dev/null 2>&1 && [ -x $(command -v $x) ]; then
\t\t\tbinary="$(command -v $x)"
\t\t\tprintf " $binary\\n" >&2
\t\t\techo "${binary}"
\t\t\texit 0
\t\tfi
\tdone
""",
            """\tfor x in $*; do
\t\tbinary="$(command -v "$x" 2>/dev/null || true)"
\t\tcase "$binary" in
\t\t\t*=*) binary="${binary#*=}" ;;
\t\tesac
\t\tif [ -n "$binary" ]; then
\t\t\tprintf " $binary\\n" >&2
\t\t\techo "${binary}"
\t\t\texit 0
\t\tfi
\tdone
""",
            strict=True,
        )
        replace_in_file(
            self,
            configure,
            """REALPATH=${REALPATH:-$(find_program realpath realpath grealpath)}
[ $? -eq 0 ] || die "error: need realpath" # exit code of find_program()
""",
            """REALPATH=${REALPATH:-$(find_program realpath realpath grealpath)}
[ -n "${REALPATH}" ] || die "error: need realpath"
""",
            strict=True,
        )

    def _patch_makefile_in(self):
        makefile_in = os.path.join(self.source_folder, "Makefile.in")
        replace_in_file(
            self,
            makefile_in,
            """lex.yy.c: y.tab.h @SRCDIR@/src/pgen/lexer.l
\t$(LEX) @SRCDIR@/src/pgen/lexer.l
""",
            """lex.yy.c: @SRCDIR@/res/pgen_lexer.c
\tcp @SRCDIR@/res/pgen_lexer.c lex.yy.c
""",
            strict=True,
        )
        replace_in_file(
            self,
            makefile_in,
            "lex.yy.pgen$(OBJEXT_FOR_BUILD): lex.yy.c\n",
            "lex.yy.pgen$(OBJEXT_FOR_BUILD): y.tab.h lex.yy.c\n",
            strict=True,
        )

    def build(self):
        args = [
            "--prefix=/",
            "--disable-libedit",
            "--disable-libreadline",
            "--disable-liblowdown",
            "--disable-librt",
            "--release",
        ]
        configure = os.path.join(self.source_folder, "configure")
        self._patch_configure(configure)
        self._patch_makefile_in()
        self.run(f"{self._env_prefix()} {shlex.quote(configure)} {' '.join(args)}")
        self.run("make -j1")

    def package(self):
        self.run(f"make install DESTDIR={shlex.quote(self.package_folder)}")
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        sysroot = self._default_prefix()
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(sysroot, "lib"))
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
