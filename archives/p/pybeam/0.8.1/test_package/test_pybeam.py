#!/usr/bin/env python3
"""pybeam consumer test（R34：真实调用被测库 API）。

用一个**内联合法 BEAM 文件**（base64 源码字面量，非二进制数据文件 —— 后者在
CI 应用 PR diff 时会报 "missing binary patch data"）调用 `BeamFile` 真实解析，
并按上游 `test/test_beam_file.py` 的已知期望值断言。

这也同时验证 pybeam → construct 的**运行期依赖链**真实可用。
"""
import base64
import io
import sys

# 与上游 test/test_beam_file.py 的 setUp 同一份合成 BEAM 数据（732 字节）
_BEAM_B64 = (
    "Rk9SMQAAAtRCRUFNQXRvbQAAAFUAAAAICHNzaF9tYXRoBGlwb3cGY3J5cHRvB21vZF9wb3cQ"
    "Ynl0ZXNfdG9faW50ZWdlcgttb2R1bGVfaW5mbwZlcmxhbmcPZ2V0X21vZHVsZV9pbmZvAAAA"
    "Q29kZQAAAFwAAAAQAAAAAAAAAJkAAAAHAAAAAwEQmRACEiIwASAnFQEjKBUTAQwAMJkgBzAA"
    "mSAIEBAAATCZAAISYgABQEASA5kAThAgAVCZAAISYhABYEADE0ASA5kATiAwA1N0clQAAAAA"
    "SW1wVAAAADQAAAAEAAAAAwAAAAQAAAADAAAAAwAAAAUAAAABAAAABwAAAAgAAAABAAAABwAA"
    "AAgAAAACRXhwVAAAACgAAAADAAAABgAAAAEAAAAGAAAABgAAAAAAAAAEAAAAAgAAAAMAAAAC"
    "QXR0cgAAACiDbAAAAAFoAmQAA3ZzbmwAAAABbhAAj975Vn3zd3KKk8Fw7URLmmpqQ0luZgAA"
    "AUCDbAAAAARoAmQAB29wdGlvbnNsAAAABGgCZAAGb3V0ZGlyawA8L2hvbWUvYWJ1aWxkL3Jw"
    "bWJ1aWxkL0JVSUxEL290cF9zcmNfMTcuMS9saWIvc3NoL3NyYy8uLi9lYmluaAJkAAFpawA3"
    "L2hvbWUvYWJ1aWxkL3JwbWJ1aWxkL0JVSUxEL290cF9zcmNfMTcuMS9saWIva2VybmVsL3Ny"
    "Y2QAEHdhcm5fdW51c2VkX3ZhcnNkAApkZWJ1Z19pbmZvamgCZAAHdmVyc2lvbmsABTUuMC4x"
    "aAJkAAR0aW1laAZiAAAH4GECYQ9hC2EIYRJoAmQABnNvdXJjZWsAQS9ob21lL2FidWlsZC9y"
    "cG1idWlsZC9CVUlMRC9vdHBfc3JjXzE3LjEvbGliL3NzaC9zcmMvc3NoX21hdGguZXJsakxp"
    "dFQAAAAYAAAACnicY2BgYGRgYGBqzgIAAYcA8QAA"
)


def main() -> int:
    try:
        from pybeam import BeamFile
    except ImportError as e:
        print(f"FAIL: cannot import pybeam: {e}", file=sys.stderr)
        return 1

    raw = base64.b64decode(_BEAM_B64)
    if raw[:4] != b"FOR1" or raw[8:12] != b"BEAM":
        print(f"FAIL: embedded blob is not a BEAM file: {raw[:12]!r}",
              file=sys.stderr)
        return 1

    try:
        beam = BeamFile(io.BytesIO(raw))
    except Exception as e:
        print(f"FAIL: BeamFile(io.BytesIO(...)) raised: {e}", file=sys.stderr)
        return 1

    # 真实断言（期望值取自上游 test/test_beam_file.py）
    try:
        if beam.modulename != "ssh_math":
            print(f"FAIL: modulename = {beam.modulename!r}", file=sys.stderr)
            return 1
        if list(beam.atoms) != ["ssh_math", "ipow", "crypto", "mod_pow",
                                "bytes_to_integer", "module_info", "erlang",
                                "get_module_info"]:
            print(f"FAIL: atoms = {list(beam.atoms)!r}", file=sys.stderr)
            return 1
        if dict(beam.attributes) != {
                "vsn": [205091931631091061218511176690734587535]}:
            print(f"FAIL: attributes = {dict(beam.attributes)!r}", file=sys.stderr)
            return 1
        if list(beam.exports) != [("module_info", 1, 6),
                                  ("module_info", 0, 4), ("ipow", 3, 2)]:
            print(f"FAIL: exports = {list(beam.exports)!r}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: BeamFile attribute access raised: {e}", file=sys.stderr)
        return 1

    print("OK: pybeam real API ok (BeamFile parsed embedded BEAM: "
          f"modulename={beam.modulename}, {len(list(beam.atoms))} atoms, "
          f"{len(list(beam.exports))} exports)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
