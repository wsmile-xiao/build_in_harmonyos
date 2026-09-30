#!/usr/bin/env python3
"""Conan test_package for dbus-glib 0.114.1 (L1 consumer test).

Why pkg-config and not CMakeDeps: the published glib OHOS binaries ship
empty component INTERFACE include dirs in their CMake metadata (known
E216 class issue, first characterised on glib/2.88.0), so CMake consumers
cannot resolve glib-object.h; the generated .pc files carry the full
Cflags. For an autotools-era library the pkg-config flow is the canonical
consumer path anyway.

The 0.114.1 revision only re-pins dependencies (glib/2.84.0.1 line, so
that one graph can carry gtk3 + dbus-glib); the consumer test is carried
over unchanged from 0.114 and re-executed for this revision.

Two layers, both executing real functionality (R34: no print-only
stubs):
  1. test_dbus_glib — C consumer compiled and linked against
     libdbus-glib-1 via pkg-config, calling the specializable GType
     registry, a typed collection append round-trip and DBUS_GERROR
     mapping;
  2. dbus-binding-tool — the packaged executable runs end-to-end and
     its generated client glue is content-checked.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import load, mkdir, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

SAMPLE_INTERFACE = """<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
  <interface name="org.freedesktop.Sample">
    <method name="Hello">
      <arg type="s" direction="in" name="who"/>
      <arg type="u" direction="out" name="reply"/>
    </method>
    <signal name="Changed">
      <arg type="i" name="value"/>
    </signal>
  </interface>
</node>
"""


class DbusGlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        env = Environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self, scope="build").save_script("test-pkg-config-path")

    def build(self):
        # Same accessor AutotoolsToolchain uses internally: the profile
        # conf value is a dict, conf_info.get without check_type can
        # hand back the raw string / default in test context.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or shutil.which("clang") \
            or shutil.which("cc") or "cc"
        mkdir(self, self.build_folder)
        self.run(f'{cc} -g -O2 "{os.path.join(self.source_folder, "test.c")}" '
                 '-o test_dbus_glib '
                 '$(pkg-config --cflags --libs dbus-glib-1)',
                 cwd=self.build_folder, env="conanbuild")

    def test(self):
        # 1. real API consumer binary (static link incl. glib/dbus chain)
        self.run("./test_dbus_glib", cwd=self.build_folder, env="conanrun")

        # 2. packaged executable end-to-end: dbus-binding-tool codegen.
        # Invoke by absolute path: bindirs of a library-type package are
        # not injected into the run-env PATH by design.
        tool = os.path.join(
            self.dependencies["dbus-glib"].package_folder,
            "bin", "dbus-binding-tool")
        xml = os.path.join(self.build_folder, "sample-interface.xml")
        glue = os.path.join(self.build_folder, "sample-client-glue.h")
        save(self, xml, SAMPLE_INTERFACE)
        self.run(f'"{tool}" --mode=glib-client '
                 f'--output="{glue}" "{xml}"',
                 cwd=self.build_folder, env="conanrun")
        content = load(self, glue)
        for marker in ("dbus_g_proxy_begin_call", "org_freedesktop_Sample",
                       "Hello"):
            if marker not in content:
                raise Exception(
                    f"dbus-binding-tool output missing '{marker}'")
        self.output.info("dbus-glib test_package: API + codegen verified")
