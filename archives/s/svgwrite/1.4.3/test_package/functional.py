"""Package-only SVG generation checks that require no display or network."""

import json
import os
import platform
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


SVG_NS = "http://www.w3.org/2000/svg"


def main():
    package = Path(sys.argv[1]).resolve()
    report = Path(sys.argv[2])
    import svgwrite
    from svgwrite import data, extensions

    results = []

    def check(name, action):
        try:
            action()
            results.append({"name": name, "passed": True})
            print("PASS", name, flush=True)
        except Exception as exc:
            results.append({"name": name, "passed": False,
                            "error": f"{type(exc).__name__}: {exc}"})
            print("FAIL", name, flush=True)

    def packaged_import():
        for module in (svgwrite, data, extensions):
            imported = Path(module.__file__).resolve()
            assert os.path.commonpath([str(imported), str(package)]) == str(package), imported

    def basic_shapes():
        drawing = svgwrite.Drawing(size=("100px", "50px"))
        drawing.add(drawing.rect(insert=(1, 2), size=(20, 10), fill="red"))
        drawing.add(drawing.circle(center=(50, 25), r=5, fill="blue"))
        root = ET.fromstring(drawing.tostring())
        assert root.tag == f"{{{SVG_NS}}}svg"
        assert len(root.findall(f"{{{SVG_NS}}}rect")) == 1
        assert len(root.findall(f"{{{SVG_NS}}}circle")) == 1

    def group_and_text():
        drawing = svgwrite.Drawing(size=("100px", "50px"))
        group = drawing.g(id="shapes")
        group.add(drawing.line((0, 0), (10, 10), stroke="black"))
        group.add(drawing.text("OHOS", insert=(5, 20)))
        drawing.add(group)
        root = ET.fromstring(drawing.tostring())
        groups = root.findall(f"{{{SVG_NS}}}g")
        assert len(groups) == 1
        assert groups[0].attrib["id"] == "shapes"
        assert groups[0].find(f"{{{SVG_NS}}}text").text == "OHOS"

    def file_output():
        report.parent.mkdir(parents=True, exist_ok=True)
        output = report.with_name("generated.svg")
        drawing = svgwrite.Drawing(str(output), size=("24px", "24px"))
        drawing.add(drawing.path(d="M 0,0 L 24,24", stroke="green"))
        drawing.save()
        root = ET.parse(output).getroot()
        assert root.find(f"{{{SVG_NS}}}path") is not None

    def ohos_aarch64_unicode_path_roundtrip():
        assert platform.machine().lower() in ("aarch64", "arm64")
        output = report.with_name("svgwrite-ohos-应用文件.svg")
        output.parent.mkdir(parents=True, exist_ok=True)
        assert output.parent.is_dir()
        try:
            drawing = svgwrite.Drawing(str(output), size=("24px", "24px"))
            drawing.add(drawing.path(d="M 0,0 L 24,24", stroke="green"))
            drawing.save()
            assert output.is_file()
            root = ET.parse(output).getroot()
            assert root.tag == f"{{{SVG_NS}}}svg"
            path_element = root.find(f"{{{SVG_NS}}}path")
            assert path_element is not None
            assert path_element.attrib["d"] == "M 0,0 L 24,24"
        finally:
            output.unlink(missing_ok=True)

    for name, action in (("packaged_import", packaged_import),
                         ("basic_shapes", basic_shapes),
                         ("group_and_text", group_and_text),
                         ("file_output", file_output),
                         ("ohos_aarch64_unicode_path_roundtrip", ohos_aarch64_unicode_path_roundtrip)):
        check(name, action)

    summary = {"package_folder": str(package), "total": len(results),
               "passed": sum(item["passed"] for item in results),
               "cases": results}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{summary['passed']}/{summary['total']} passed", flush=True)
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
