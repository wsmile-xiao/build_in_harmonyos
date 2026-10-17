#!/usr/bin/env python3
"""Conan recipe — bitlbee-facebook 1.2.2.

Builds the Facebook Messenger protocol plugin module (facebook.so) for
BitlBee (the IRC <-> instant messaging gateway).  The module is dlopen()ed
by the bitlbee daemon at runtime and is never linked against by consumers.

Host (bitlbee) header supply:
  The conan bitlbee/3.6 package ships only the bin/bitlbee executable — no
  headers and no bitlbee.pc (upstream `make install install-dev` output is
  not part of that package).  Upstream CI (bitlbee-facebook
  .github/workflows/ci.yml) clones bitlbee and builds the plugin against
  a `make install install-dev` tree.  This recipe reproduces those
  install-dev semantics from the bitlbee 3.6 sdist (conandata.yml key
  `bitlbee_dev_source`): it runs the bitlbee configure (custom shell script,
  generates config.h; requires an SSL library — hence the openssl require)
  and flattens `*.h lib/*.h protocols/*.h` + the generated config.h into a
  private include dir.  The bitlbee conan package itself is NOT required:
  it provides nothing the plugin build consumes (host relationship is a
  runtime deployment concern, same approach as the abiword-plugin-* recipes).

OHOS adaptations:
  - bootstrap: the tarball ships no `configure` (autogen.sh runs
    autoreconf); build() runs `autoreconf -fi`.  pkg.m4 (PKG_CHECK_MODULES/
    PKG_CHECK_VAR macros) is exported with the recipe under m4/ and injected
    via ACLOCAL_PATH — the CI sandbox has no system pkg.m4 (pattern from
    abiword-plugin-docbook).
  - E114: the generated configure's config.status creates its temp dir with
    `umask 077 && mktemp -d`, which yields an unwritable drwx--S--- dir on
    HMDFS — patched out before configure runs.
  - E236: the conan pcre2/libffi packages carry stale .la metadata
    (libdir='//lib') that libtool chokes on.  The .a archives are copied
    into a build-private .la-free directory and referenced via -L/-l; the
    conan cache stays untouched.
  - E074: make -j1 (HMDFS jobserver fifo EPERM).
  - Static embedding: the conan glib/json-glib packages are static-only, so
    glib-2.0/gobject/gio/gmodule/json-glib/libffi/pcre2/zlib are all
    statically embedded into facebook.so (final module DT_NEEDED is
    libc.so only).  zlib must be zlib/1.3.1.1 (PIC rebuild) — zlib/1.3.1's
    libz.a is non-PIC and cannot link into a shared module; the plugin
    really uses zlib at runtime (fb_util_zlib_deflate/inflate for Facebook
    MQTT payloads).  glib/2.84.0 + json-glib/1.6.6 match the bitlbee/3.6
    and json-glib dependency graph (glib itself does not require zlib, so
    there is no 1.3.1 <-> 1.3.1.1 conflict in this graph).
  - PKG_CHECK_MODULES bypass: configure looks up bitlbee/glib-2.0/gio-2.0/
    gobject-2.0/json-glib-1.0 via pkg-config, but the conan PkgConfigDeps
    generator only emits the aggregated glib-2.0.pc for glib (no
    gio-2.0.pc/gobject-2.0.pc) and there is no usable bitlbee.pc.  All six
    <MODULE>_CFLAGS/<MODULE>_LIBS variables (plus GLIB_GENMARSHAL) are set
    explicitly from conan dependency paths — pkg.m4 honours preset env
    vars and skips the pkg-config queries entirely (plugindir then falls
    back to upstream's default $libdir/bitlbee).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, \
    export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """Point AUTOCONF/AUTOHEADER/AUTOM4TE/SED env vars at whatever is on
    PATH (the installed automake/aclocal hardcode absolute paths that do
    not exist in this environment)."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


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


class BitlbeeFacebookConan(ConanFile):
    name = "bitlbee-facebook"
    version = "1.2.2"
    description = "Facebook Messenger protocol plugin for BitlBee (IRC <-> IM gateway)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/bitlbee/bitlbee-facebook"
    url = ""  # CI fills this

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 无源码补丁（patches: {}）——调用保留为标准 conan 习惯
        # （补丁列表后续如需添加，经 conandata.yml patches 登记）
        export_conandata_patches(self)
        # m4/pkg.m4: PKG_CHECK_MODULES/PKG_CHECK_VAR macros for the
        # autoreconf bootstrap.  The CI sandbox cannot see the system
        # aclocal dir ($HOME/.local/...), so the macro travels with the
        # recipe (pattern from abiword-plugin-docbook).
        _src_m4 = os.path.join(self.recipe_folder, "m4")
        _dst_m4 = os.path.join(self.export_sources_folder, "m4")
        if os.path.isdir(_src_m4) and not os.path.exists(_dst_m4):
            shutil.copytree(_src_m4, _dst_m4)
            self.output.info(f"  [ok] exported m4 macros to {_dst_m4}")

    def requirements(self):
        # All statically embedded into facebook.so (conan glib/json-glib
        # packages are static-only on OHOS):
        self.requires("glib/2.84.0")       # same as bitlbee/3.6 + json-glib/1.6.6
        self.requires("json-glib/1.6.6")
        self.requires("libffi/3.4.4")      # pulled via gobject closure marshalling
        self.requires("pcre2/10.40")       # pulled via glib
        # zlib/1.3.1.1 = PIC rebuild of 1.3.1 (1.3.1 libz.a is non-PIC and
        # cannot be linked into a shared module); the plugin really calls
        # zlib at runtime (Facebook MQTT payload deflate/inflate).
        self.requires("zlib/1.3.1.1")
        # Build-only: the bitlbee 3.6 sdist configure (config.h generation)
        # hard-requires an SSL library (--ssl=openssl, same as the
        # bitlbee/3.6 build itself).
        self.requires("openssl/1.1.1w")

    def build_requirements(self):
        # The tarball ships no `configure`, so build() must run
        # `autoreconf -fi` to bootstrap.  The build host (CI sandbox /
        # minimal OHOS HNP image) only provides the autoconf family under
        # /data/service/hnp/bin — no automake/libtoolize (same approach as
        # abiword-plugin-clarisworks / argp-standalone).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "bitlbee-facebook is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # .pc files for the dependency graph (used by the bitlbee sdist
        # configure for glib event-handler detection).
        PkgConfigDeps(self).generate()
        # ACLOCAL_PATH -> recipe m4/ (must be appended BEFORE
        # VirtualBuildEnv.generate(), otherwise the env file is already
        # written and the injection does not take effect).
        _m4_dir = os.path.join(self.source_folder, "m4")
        if os.path.isdir(_m4_dir):
            self.buildenv_info.append_path("ACLOCAL_PATH", _m4_dir)
        # VirtualBuildEnv: bring tool_requires (automake/libtool) bin dirs
        # into the conanbuild PATH.
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # Skip the config.guess probe (works on this host, but the CI
        # sandbox probe is unreliable under HMDFS; config.sub supports
        # *-linux-ohos — pattern from abiword-plugin-clarisworks).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")

        glib_pkg = self.dependencies["glib"].package_folder
        json_pkg = self.dependencies["json-glib"].package_folder
        la_free = os.path.join(self.build_folder, "la-free")
        bitlbee_dev_inc = os.path.join(self.build_folder, "bitlbee-dev",
                                       "include")

        # pkg.m4 preset-variable bypass of PKG_CHECK_MODULES for
        # bitlbee/glib/json-glib (all values from conan dependency paths,
        # R33).  BITLBEE_LIBS must be non-empty for the pkg.m4
        # both-variables-set bypass; a bare -L of the .la-free dir is a
        # harmless no-op (the plugin does not link the host).
        # This conan version exposes AutotoolsToolchain.environment() as a
        # METHOD returning a fresh Environment — take it, extend it with the
        # recipe's own vars and pass it back through generate(env=...).
        env = tc.environment()
        env.define("BITLBEE_CFLAGS", "-I{}".format(bitlbee_dev_inc))
        env.define("BITLBEE_LIBS", "-L{}".format(la_free))
        env.define("GLIB_CFLAGS", "-I{} -I{}".format(
            os.path.join(glib_pkg, "include", "glib-2.0"),
            os.path.join(glib_pkg, "lib", "glib-2.0", "include")))
        env.define(
            "GLIB_LIBS",
            "-L{} -L{} -lglib-2.0 -lgobject-2.0 -lgio-2.0 "
            "-lgmodule-2.0 -lffi -lpcre2-8 -lz".format(
                os.path.join(glib_pkg, "lib"), la_free))
        env.define("JSON_CFLAGS", "-I{} -I{}".format(
            os.path.join(json_pkg, "include", "json-glib-1.0"),
            os.path.join(json_pkg, "include")))
        env.define("JSON_LIBS", "-L{} -ljson-glib-1.0".format(
            os.path.join(json_pkg, "lib")))
        env.define("GLIB_GENMARSHAL",
                   os.path.join(glib_pkg, "bin", "glib-genmarshal"))
        tc.generate(env=env)

    def _prepare_bitlbee_dev(self):
        """Reproduce bitlbee 3.6 `make install install-dev` from the sdist:
        run the (custom, non-autoconf) configure to generate config.h, then
        flatten *.h lib/*.h protocols/*.h + config.h into bitlbee-dev/include."""
        sdist = os.path.join(self.build_folder, "bitlbee-sdist")
        get(self, **self.conan_data["bitlbee_dev_source"], strip_root=True,
            destination=sdist)
        inst = os.path.join(self.build_folder, "bitlbee-dev-build")
        openssl_inc = os.path.join(
            self.dependencies["openssl"].package_folder, "include")

        env = Environment()
        # glib-2.0.pc from PkgConfigDeps (event handler detection);
        # openssl headers for --ssl=openssl (same as the bitlbee/3.6 build).
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        env.define("CPPFLAGS", "-I{}".format(openssl_inc))
        with env.vars(self, scope="conanbuild").apply():
            self.run('"{}" --build=aarch64-unknown-linux-ohos '
                     '--ssl=openssl --prefix="{}"'.format(
                         os.path.join(sdist, "configure"), inst),
                     cwd=sdist, env="conanbuild")

        inc = os.path.join(self.build_folder, "bitlbee-dev", "include")
        os.makedirs(inc, exist_ok=True)
        # install-dev header set: $(wildcard *.h lib/*.h protocols/*.h) + config.h
        for pattern in ("*.h", "lib/*.h", "protocols/*.h"):
            for f in glob.glob(os.path.join(sdist, pattern)):
                copy(self, os.path.basename(f),
                     src=os.path.dirname(f), dst=inc)
        copy(self, "config.h", src=sdist, dst=inc)
        self.output.info(
            "  [ok] bitlbee-dev: {} headers".format(
                len(os.listdir(inc))))

    def _prepare_la_free(self):
        """E236: copy the .a archives that libtool would otherwise resolve
        through stale .la metadata (libdir='//lib' in the pcre2/libffi
        packages) into a build-private .la-free directory."""
        la_free = os.path.join(self.build_folder, "la-free")
        os.makedirs(la_free, exist_ok=True)
        for dep_name, libname in (("libffi", "libffi.a"),
                                  ("pcre2", "libpcre2-8.a"),
                                  ("zlib", "libz.a")):
            dep = self.dependencies[dep_name]
            src = None
            for libdir in dep.cpp_info.libdirs:
                candidate = os.path.join(dep.package_folder, libdir, libname)
                if os.path.isfile(candidate):
                    src = candidate
                    break
            if not src:
                raise ConanInvalidConfiguration(
                    "{} not found in {} package".format(libname, dep_name))
            copy(self, libname, src=os.path.dirname(src), dst=la_free)
        return la_free

    def build(self):
        # 无源码补丁（patches: {}）——no-op 调用，适配均构建期完成
        apply_conandata_patches(self)
        _prepare_autotools_env()
        # bitlbee install-dev reproduction (headers + config.h)
        self._prepare_bitlbee_dev()
        # .la-free static archive directory (E236)
        self._prepare_la_free()

        # Bootstrap configure from configure.ac (tarball ships none)
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))

        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # plugindir defaults to $libdir/bitlbee (upstream fallback), and
        # conan's AutotoolsToolchain prefix points make install at the
        # package folder -> <package>/lib/bitlbee/facebook.so
        autotools.install()
        # E236: keep the package .la-free (the module is dlopen()ed, never
        # linked through libtool metadata)
        la = os.path.join(self.package_folder, "lib", "bitlbee",
                          "facebook.la")
        if os.path.exists(la):
            os.remove(la)

    def package_info(self):
        # dlopen-based plugin module: consumers never link against it, but
        # they need to locate it in lib/bitlbee/ (bitlbee's PLUGINDIR).
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/bitlbee"]
