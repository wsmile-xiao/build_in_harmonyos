#!/usr/bin/env python3
"""Conan recipe for xcb-proto 1.17.0."""

import os
import shutil
import subprocess
from pathlib import Path
from xml.etree import ElementTree

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


PROTOCOL_XMLS = (
    "bigreq.xml",
    "composite.xml",
    "damage.xml",
    "dbe.xml",
    "dpms.xml",
    "dri2.xml",
    "dri3.xml",
    "ge.xml",
    "glx.xml",
    "present.xml",
    "randr.xml",
    "record.xml",
    "render.xml",
    "res.xml",
    "screensaver.xml",
    "shape.xml",
    "shm.xml",
    "sync.xml",
    "xc_misc.xml",
    "xevie.xml",
    "xf86dri.xml",
    "xf86vidmode.xml",
    "xfixes.xml",
    "xinerama.xml",
    "xinput.xml",
    "xkb.xml",
    "xprint.xml",
    "xproto.xml",
    "xselinux.xml",
    "xtest.xml",
    "xv.xml",
    "xvmc.xml",
)

XCBGEN_MODULES = (
    "__init__.py",
    "align.py",
    "error.py",
    "expr.py",
    "matcher.py",
    "state.py",
    "xtypes.py",
)


class XcbProtoConan(ConanFile):
    name = "xcb-proto"
    version = "1.17.0"
    description = "XCB XML protocol descriptions and Python generator helpers"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/proto/xcbproto"
    package_type = "build-scripts"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xcb-proto supports Linux and OHOS, not {self.settings.os}"
            )

    def package_id(self):
        # XML, XSD, Python source, and pkg-config metadata are target independent.
        self.info.clear()

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)
        source = Path(self.source_folder)
        protocol_dir = source / "src"
        module_dir = source / "xcbgen"
        self._require_exact_inventory(protocol_dir, PROTOCOL_XMLS, "*.xml")
        self._require_exact_inventory(module_dir, XCBGEN_MODULES, "*.py")

        schema = protocol_dir / "xcb.xsd"
        if not schema.is_file():
            raise ConanException("upstream xcb.xsd is missing")

        for name in PROTOCOL_XMLS:
            ElementTree.parse(protocol_dir / name)
        for name in XCBGEN_MODULES:
            module = module_dir / name
            compile(module.read_text(encoding="utf-8"), str(module), "exec")

        xmllint = shutil.which("xmllint")
        if xmllint:
            try:
                subprocess.run(
                    [
                        xmllint,
                        "--noout",
                        "--schema",
                        str(schema),
                        *(str(protocol_dir / name) for name in PROTOCOL_XMLS),
                    ],
                    check=True,
                )
            except PermissionError:
                self.output.warning(
                    "upstream schema check skipped because xmllint cannot execute"
                )
            else:
                self.output.info(
                    "upstream schema check validated 32 protocol XML files"
                )
        else:
            self.output.warning(
                "upstream schema check skipped because xmllint is unavailable"
            )

    def package(self):
        source = Path(self.source_folder)
        protocol_src = source / "src"
        protocol_dst = Path(self.package_folder) / "share" / "xcb"
        python_dst = (
            Path(self.package_folder) / "lib" / "python3" / "site-packages" / "xcbgen"
        )
        protocol_dst.mkdir(parents=True, exist_ok=True)
        python_dst.mkdir(parents=True, exist_ok=True)

        for name in PROTOCOL_XMLS:
            (protocol_dst / name).write_bytes((protocol_src / name).read_bytes())
        (protocol_dst / "xcb.xsd").write_bytes(
            (protocol_src / "xcb.xsd").read_bytes()
        )
        for name in XCBGEN_MODULES:
            (python_dst / name).write_bytes(
                (Path(self.source_folder) / "xcbgen" / name).read_bytes()
            )

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "xml-xcb.txt",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "share", "doc", "xcb-proto"),
            keep_path=False,
        )

        pc_dir = Path(self.package_folder) / "share" / "pkgconfig"
        pc_dir.mkdir(parents=True, exist_ok=True)
        (pc_dir / "xcb-proto.pc").write_text(
            "prefix=${pcfiledir}/../..\n"
            "exec_prefix=${prefix}\n"
            "datarootdir=${prefix}/share\n"
            "datadir=${datarootdir}\n"
            "xcbincludedir=${datadir}/xcb\n"
            "pythondir=${prefix}/lib/python3/site-packages\n"
            "\n"
            "Name: XCB Proto\n"
            "Description: X protocol descriptions for XCB\n"
            "Version: 1.17.0\n",
            encoding="utf-8",
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/xcb"]
        self.cpp_info.set_property("pkg_config_name", "xcb-proto")

        pc_dir = os.path.join(self.package_folder, "share", "pkgconfig")
        python_dir = os.path.join(
            self.package_folder, "lib", "python3", "site-packages"
        )
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.buildenv_info.append_path("PYTHONPATH", python_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PYTHONPATH", python_dir)

    @staticmethod
    def _require_exact_inventory(directory, expected, pattern):
        actual = tuple(sorted(path.name for path in directory.glob(pattern)))
        if actual != tuple(sorted(expected)):
            raise ConanException(
                f"unexpected {pattern} inventory in {directory}: {actual}"
            )
