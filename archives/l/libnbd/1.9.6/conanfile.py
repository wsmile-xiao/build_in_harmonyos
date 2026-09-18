#!/usr/bin/env python3
"""Conan recipe — libnbd 1.9.6 (NBD client library in userspace)。

Adaptation notes (OHOS / HarmonyOS PC aarch64):
  - Upstream git tag tarball ships WITHOUT generated C sources: lib/api.c,
    lib/states*.c, lib/states.h, lib/unlocked.h and the public header
    include/nbd.h are produced at build time by the OCaml generator
    (generator/).  Therefore ocaml is required as a tool_requires so that
    `ocamlc` is available on PATH during the build (its recipe exports
    cpp_info.bindirs + env_info.PATH).
  - The tarball has no `configure` script either, so autoreconf (bootstrap)
    must run before configure.
  - All optional features are disabled for a minimal, dependency-free core
    library: gnutls (TLS), libxml2 (URI), fuse3 (no ohpcd recipe), ocaml /
    python / golang language bindings, bash completion.  The core NBD client
    API (connect/read/write/…) does not require any of them.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` (and the now-orphaned parentheses) so config.status
    can create its temp dir."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class LibnbdConan(ConanFile):
    name = "libnbd"
    version = "1.9.6"
    description = "NBD client library in userspace"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libguestfs/libnbd"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # R03 尝试过默认 shared=True（使 dlopen 用例可运行）：手动 shared 构建下
    # dlopen 实测 exit 0 通过，但 conan 配方内启用 shared 时 libnbd.syms
    # version-script 路径（configure 解析 ${srcdir} 与文件实际位于 lib/ 错位）
    # 连续 5+ 次同类失败（R43 止损）。保持默认静态（R01/R02 基线一致，CI 绿），
    # dlopen 保留 SKIP 并在台账附 shared 实测证据与恢复条件。
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # OCaml generator (lib/api.c, lib/states*.c, include/nbd.h are
        # generated at build time; no generated files ship in the git tarball)
        self.tool_requires("ocaml/4.14.1.1.4")
        # The git archive ships no `configure`: build() bootstraps with
        # autoreconf.  The CI sandbox / minimal OHOS image lacks the automake
        # suite (only autoconf lives under /data/service/hnp/bin), so pull
        # automake + libtool in as tool_requires (same approach as
        # abiword-plugin-clarisworks / argp-standalone).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries default to static; libnbd is not a
        # system-name library so autotools defaults build both .a and .so.
        # Only force static for the shared=False option.
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--enable-shared")
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS",
        # kernel "HongMeng Kernel"), so pass the triplet explicitly
        # (config.sub supports *-linux-ohos); same approach as
        # abiword-plugin-clarisworks / argp-standalone.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # Minimal core build: disable optional features so the recipe has no
        # runtime/external dependency chain (fuse3 has no ohpcd recipe).
        # NOTE: do NOT pass --disable-ocaml: HAVE_OCAMLC (which gates the
        # OCaml generator that produces lib/api.c, lib/states*.c,
        # include/nbd.h) requires enable_ocaml=yes (configure.ac L378-381).
        # The ocaml tool_requires supplies ocamlc on PATH; the OCaml
        # language bindings subdir is skipped when ocamlfind is absent.
        tc.configure_args.extend([
            "--without-gnutls",
            "--without-libxml2",
            "--disable-fuse",
            "--disable-python",
            "--disable-golang",
            "--disable-bash-completion",
            "--disable-gcc-warnings",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # ocamlc locates its stdlib via OCAMLLIB (the ocaml recipe's binaries
        # embed a stale build-time cache path that does not exist after the
        # package is moved into the local cache), so export it explicitly for
        # the generator build.  Set on os.environ (not via the conan env
        # scripts) to keep the generated env files small.
        os.environ["OCAMLLIB"] = os.path.join(
            self.dependencies.build["ocaml"].package_folder, "lib", "ocaml")
        # Bytecode programs linked against str.cma/unix.cma need the OCaml
        # stublibs dir (dllcamlstr.so/dllunix.so) at load time.
        os.environ["CAML_LD_LIBRARY_PATH"] = os.path.join(
            self.dependencies.build["ocaml"].package_folder,
            "lib", "ocaml", "stublibs")
        # ocamldoc (bytecode, shebang points at the ocaml package's stale
        # build-time cache path) is only needed for the OCaml *bindings*
        # manpages, which we do not build (no ocamlfind → HAVE_OCAML=no).
        # Force OCAMLDOC=no so configure keeps the generator (HAVE_OCAMLC)
        # but skips the broken manpage rule.
        os.environ["OCAMLDOC"] = "no"
        autotools = Autotools(self)
        # The git tag tarball ships no configure script: bootstrap with
        # autoreconf in the source folder (generated files are produced
        # during build, and configure.ac lives there).
        self.run("autoreconf -i", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools.configure()
        # The OCaml generator binary is bytecode whose #! shebang embeds the
        # ocaml package's build-time cache path (…/.cache/conan2/…) which does
        # not exist after the package is moved into the local cache.  Build it
        # first, then fix the shebang in place to point at the current
        # ocamlrun before the rest of make (stamp-generator) executes it.
        self.run("make -C generator generator", env="conanbuild")
        gen = os.path.join(self.build_folder, "generator", "generator")
        ocamlrun = os.path.join(
            self.dependencies.build["ocaml"].package_folder, "bin", "ocamlrun")
        with open(gen, "r+b") as fh:
            fh.write(b"#!" + os.fsencode(ocamlrun) + b"\n")
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, pattern="nbd.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["nbd"]