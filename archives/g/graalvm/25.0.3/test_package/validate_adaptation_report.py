#!/usr/bin/env python3
"""Validate the packaged GraalVM headless provider-edge evidence."""

import json
import re
import subprocess
import sys
from pathlib import Path


EXPECTED_SYMBOLS = [
    "AWTCharAdvance",
    "AWTCountFonts",
    "AWTDrawGlyphList",
    "AWTFontAscent",
    "AWTFontDefaultChar",
    "AWTFontDescent",
    "AWTFontGenerateImage",
    "AWTFontMaxBounds",
    "AWTFontMaxByte1",
    "AWTFontMaxCharOrByte2",
    "AWTFontMinByte1",
    "AWTFontMinCharOrByte2",
    "AWTFontPerChar",
    "AWTFontTextExtents16",
    "AWTFreeChar",
    "AWTFreeFont",
    "AWTLoadFont",
    "AccelGlyphCache_RemoveAllCellInfos",
]
EXPECTED_EDGE = {
    "consumer": "lib/libfontmanager.so",
    "provider": "lib/libawt_headless.so",
}
EXPECTED_FONT_FILES = [
    "/system/fonts/HarmonyOS_Sans.ttf",
    "/system/fonts/HarmonyOS_Sans_Italic.ttf",
    "/system/fonts/HarmonyOS_Sans_SC.ttf",
    "/system/fonts/NotoSansMono[wdth,wght].ttf",
]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    if len(sys.argv) != 6:
        raise SystemExit(
            "usage: validate_adaptation_report.py REPORT FONTMANAGER "
            "READELF HEADLESS_SOURCE FONTCONFIG"
        )

    report_path = Path(sys.argv[1])
    font_manager = Path(sys.argv[2])
    readelf = Path(sys.argv[3])
    headless_source = Path(sys.argv[4])
    font_config = Path(sys.argv[5])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    closure = report["symbol_closure"]

    require(report["schema"] == 1, "unexpected adaptation report schema")
    require(
        report["materialized_runtime_provider_edges"] == [EXPECTED_EDGE],
        "materialized runtime provider edge changed",
    )
    require(closure["checked_package_elfs"] == 75, "ELF closure count changed")
    require(closure["provider_files"] == 77, "provider file count changed")
    require(
        closure["reachable_provider_checks"] == 336,
        "reachable provider check count changed",
    )
    require(
        closure["required_symbol_demands"] == 3374,
        "required symbol demand count changed: "
        f"{closure['required_symbol_demands']}",
    )
    require(
        closure["runtime_provider_edges"]
        == [{**EXPECTED_EDGE, "symbols": EXPECTED_SYMBOLS}],
        "runtime provider symbol edge changed",
    )
    require(closure["unresolved"] == 0, "symbol closure is unresolved")
    require(
        report["native_image_launchers"]
        == {
            "bin/native-image": {
                "kind": "signed-ohos-pie",
                "interpreter": "/lib/ld-musl-aarch64.so.1",
                "needed": ["libc.so"],
                "python_companion": "bin/native-image.py",
                "real_driver": "bin/native-image.real",
                "rpath": "",
            },
            "lib/svm/bin/native-image": {
                "kind": "signed-ohos-pie",
                "interpreter": "/lib/ld-musl-aarch64.so.1",
                "needed": ["libc.so"],
                "python_companion": "lib/svm/bin/native-image.py",
                "real_driver": "lib/svm/bin/native-image.real",
                "rpath": "",
            },
        },
        "Native Image launcher report changed",
    )

    require(
        report["font_configuration"]
        == {
            "path": "conf/fonts/fontconfig.HarmonyOS.properties",
            "system_font_files": EXPECTED_FONT_FILES,
        },
        "packaged font configuration report changed",
    )

    properties = {}
    for line in font_config.read_text(encoding="ascii").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, separator, value = line.partition("=")
            if not separator or not key or not value or key in properties:
                raise AssertionError("invalid font configuration")
            properties[key] = value
    require(
        properties.get("version") == "1"
        and properties.get("sequence.allfonts")
        == "latin-1,chinese-gb18030"
        and properties.get("sequence.fallback") == "chinese-gb18030",
        "logical-font sequence changed",
    )
    require(
        sorted(
            value
            for key, value in properties.items()
            if key.startswith("filename.")
        )
        == EXPECTED_FONT_FILES,
        "system-font mapping changed",
    )
    require(
        all(Path(name).is_file() for name in EXPECTED_FONT_FILES),
        "configured OpenHarmony system font is missing",
    )

    source = headless_source.read_text(encoding="utf-8")
    require(
        "System.load(" not in source and "System.loadLibrary(" not in source,
        "HeadlessSmoke must let java.desktop own native library loading",
    )

    dynamic = subprocess.run(
        [str(readelf), "-dW", str(font_manager)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    headless_needed = re.findall(
        r"Shared library: \[libawt_headless\.so\]", dynamic
    )
    xawt_needed = re.findall(r"Shared library: \[libawt_xawt\.so\]", dynamic)
    require(
        len(headless_needed) == 1 and not xawt_needed,
        "font manager DT_NEEDED does not select exactly one headless provider",
    )

    print("GRAALVM_ADAPTATION_REPORT_ASSERTIONS=15/15")


if __name__ == "__main__":
    main()
