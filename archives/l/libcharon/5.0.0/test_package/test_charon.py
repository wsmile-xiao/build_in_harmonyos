# Copyright (c) 2026 龙骑士 (liucu).
# Consumer test for the libcharon 5.0.0 conan package (HarmonyOS PC).
#
# R34: every check really calls the packaged Charon API (no print-only
# shells). Each check prints one `CHECK-OK: <name>` line; the conanfile
# counts those lines for the HMBS_TEST_PACKAGE_RESULT marker, and any
# failed assert aborts with a non-zero exit code. All data is built
# in-code (non-empty by construction); no external fixtures needed.
import io
import sys

from Charon.filetypes.GCodeFile import GCodeFile, InvalidHeaderException
from Charon.filetypes.OpenPackagingConvention import OpenPackagingConvention
from Charon.filetypes.UltimakerFormatPackage import UltimakerFormatPackage
from Charon.OpenMode import OpenMode
from Charon.ReadOnlyError import ReadOnlyError
from Charon.VirtualFile import VirtualFile
from Charon.WriteOnlyError import WriteOnlyError

CHECKS = []


def check(name):
    def wrap(func):
        CHECKS.append((name, func))
        return func
    return wrap


GCODE_ULTI = (
    b";FLAVOR:UltiGCode\n"
    b";TIME:100\n"
    b";LAYER:0\n"
    b"G1 X0 Y0\n"
    b"M104 S200\n"
)


@check("gcode_header")
def gcode_header():
    metadata = GCodeFile.parseHeader(io.BytesIO(GCODE_ULTI))
    assert metadata["flavor"] == "UltiGCode", metadata
    assert metadata["machine_type"] == "ultimaker2", metadata
    prefixed = GCodeFile.parseHeader(io.BytesIO(GCODE_ULTI),
                                     prefix="/metadata/toolpath/default/")
    assert prefixed["/metadata/toolpath/default/flavor"] == "UltiGCode", prefixed


@check("gcode_openstream")
def gcode_openstream():
    reader = GCodeFile()
    reader.openStream(io.BytesIO(GCODE_ULTI), "text/x-gcode", OpenMode.ReadOnly)
    data = reader.getData("/metadata")
    assert data["/metadata/toolpath/default/flavor"] == "UltiGCode", data
    body = reader.getStream("/toolpath").read()
    assert body == GCODE_ULTI, len(body)
    reader.close()


@check("opc_roundtrip")
def opc_roundtrip():
    payload = b"G1 X1 Y2\nM105\n" * 64
    assert len(payload) > 0
    stream = io.BytesIO()
    package = OpenPackagingConvention()
    package.openStream(stream, mode=OpenMode.WriteOnly)
    package.setData({"/mymodel/toolpath": payload})
    package.setMetadata({"/author": "libcharon-test"})
    package.close()

    stream.seek(0)
    package = OpenPackagingConvention()
    package.openStream(stream)
    result = package.getData("/mymodel/toolpath")
    assert result == {"/mymodel/toolpath": payload}, result
    meta = package.getMetadata("/author")
    assert meta == {"/metadata/author": "libcharon-test"}, meta
    raw = package.toByteArray()
    assert len(raw) > 0, len(raw)
    package.close()


@check("virtualfile_facade")
def virtualfile_facade():
    facade = VirtualFile()
    facade.openStream(io.BytesIO(GCODE_ULTI), "text/x-gcode", OpenMode.ReadOnly)
    data = facade.getData("/metadata")
    assert data["/metadata/toolpath/default/flavor"] == "UltiGCode", data
    body = facade.getStream("/toolpath").read()
    assert b"M104" in body, len(body)
    facade.close()


@check("exceptions")
def exceptions():
    try:
        GCodeFile.parseHeader(io.BytesIO(b";TIME:5\n"))
    except InvalidHeaderException:
        pass
    else:
        raise AssertionError("missing FLAVOR must raise InvalidHeaderException")

    stream = io.BytesIO()
    package = OpenPackagingConvention()
    package.openStream(stream, mode=OpenMode.WriteOnly)
    package.setData({"/hello.txt": b"Hello world!"})
    package.close()
    stream.seek(0)
    package = OpenPackagingConvention()
    package.openStream(stream)
    try:
        package.setData({"/other.txt": b"x"})
    except ReadOnlyError:
        pass
    else:
        raise AssertionError("setData in ReadOnly must raise ReadOnlyError")
    package.close()

    package = OpenPackagingConvention()
    package.openStream(io.BytesIO(), "application/x-opc", OpenMode.WriteOnly)
    try:
        package.getData("/hello.txt")
    except WriteOnlyError:
        pass
    else:
        raise AssertionError("getData in WriteOnly must raise WriteOnlyError")
    package.close()


@check("ufp_aliases")
def ufp_aliases():
    payload = b";FLAVOR:UltiGCode\n;TIME:7\nG28\n"
    stream = io.BytesIO()
    package = UltimakerFormatPackage()
    package.openStream(stream, mode=OpenMode.WriteOnly)
    package.setData({"/toolpath/default": payload})
    package.close()

    stream.seek(0)
    package = UltimakerFormatPackage()
    package.openStream(stream)
    result = package.getData("/toolpath/default")
    assert result == {"/toolpath/default": payload}, result
    paths = package.listPaths()
    assert len(paths) > 0, paths
    package.close()


def main():
    failed = 0
    for name, func in CHECKS:
        try:
            func()
        except Exception as exc:
            print("CHECK-FAIL: %s: %r" % (name, exc))
            failed += 1
        else:
            print("CHECK-OK: %s" % name, flush=True)
    print("checks: %d passed, %d failed out of %d" % (
        len(CHECKS) - failed, failed, len(CHECKS)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
