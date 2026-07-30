#!/usr/bin/env python3
"""Conan consumer compile tests for xorgproto 2025.1."""

from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException


PC_MODULES = (
    "applewmproto",
    "bigreqsproto",
    "compositeproto",
    "damageproto",
    "dmxproto",
    "dpmsproto",
    "dri2proto",
    "dri3proto",
    "fixesproto",
    "fontsproto",
    "glproto",
    "inputproto",
    "kbproto",
    "presentproto",
    "randrproto",
    "recordproto",
    "renderproto",
    "resourceproto",
    "scrnsaverproto",
    "videoproto",
    "xcmiscproto",
    "xextproto",
    "xf86bigfontproto",
    "xf86dgaproto",
    "xf86driproto",
    "xf86vidmodeproto",
    "xineramaproto",
    "xproto",
    "xwaylandproto",
)


class XorgprotoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "header_smoke.c", "headers.txt"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )
        include_dirs = self.dependencies[
            self.tested_reference_str
        ].cpp_info.includedirs
        include_flags = " ".join(f'-I"{path}"' for path in include_dirs)
        template = Path(self.source_folder, "header_smoke.c").read_text(
            encoding="utf-8"
        )
        headers = self._headers()
        if len(headers) != 83 or len(set(headers)) != 83:
            raise ConanException("expected 83 unique public-header tests")
        build_dir = Path(self.build_folder)
        build_dir.mkdir(parents=True, exist_ok=True)
        for index, header in enumerate(headers, start=1):
            source = build_dir / f"header_{index:03d}.c"
            output = build_dir / f"header_{index:03d}.o"
            test_body = "    return tested_header[0] == '\\0';"
            if header == "X11/Xpoll.h":
                test_body = """    fd_set descriptor_set;
    FD_ZERO(&descriptor_set);
    (void)descriptor_set.__X_FDS_BITS;
    return XFD_ANYSET(&descriptor_set) != 0;"""
            source.write_text(
                template.replace("@HEADER_UNDER_TEST@", header).replace(
                    "@HEADER_TEST_BODY@", test_body
                ),
                encoding="utf-8",
            )
            self.run(
                f'"{compiler}" -std=c11 -Werror {include_flags} '
                f'-c "{source}" -o "{output}"'
            )

    def test(self):
        objects = sorted(Path(self.build_folder).glob("header_*.o"))
        if len(objects) != 83 or any(path.stat().st_size == 0 for path in objects):
            raise ConanException("83 independent header compile outputs are required")

        package_folder = Path(
            self.dependencies[self.tested_reference_str].package_folder
        )
        pc_dir = package_folder / "share" / "pkgconfig"
        errors = []
        for module in PC_MODULES:
            path = pc_dir / f"{module}.pc"
            if not path.is_file():
                errors.append(f"missing {path.name}")
                continue
            content = path.read_text(encoding="utf-8")
            if "prefix=${pcfiledir}/../.." not in content:
                errors.append(f"non-relocatable prefix in {path.name}")
            if "includedir=${prefix}/include" not in content:
                errors.append(f"wrong includedir in {path.name}")
        if errors:
            raise ConanException("; ".join(errors))
        self.output.info("validated 29 relocatable pkg-config modules")
        self.output.info("validated 83 independent public-header compile outputs")

    def _headers(self):
        return [
            line.strip()
            for line in Path(self.source_folder, "headers.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
