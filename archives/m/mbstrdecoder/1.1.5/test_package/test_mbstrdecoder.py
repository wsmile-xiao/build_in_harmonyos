#!/usr/bin/env python3
"""mbstrdecoder consumer test (R34): real API usage — MultiByteStrDecoder."""
import sys


def main() -> int:
    import mbstrdecoder

    if mbstrdecoder.__version__ != "1.1.5":
        print(f"FAIL: mbstrdecoder version {mbstrdecoder.__version__}",
              file=sys.stderr)
        return 1
    # 真实 API：MultiByteStrDecoder 解码（核心——chardet 依赖链真实运行——
    # unicode_str 是 @property（属性访问——非方法——TypeError 实测））
    dec = mbstrdecoder.MultiByteStrDecoder("hello")
    text = dec.unicode_str
    if text != "hello":
        print(f"FAIL: decode result {text!r}", file=sys.stderr)
        return 1
    print("OK: mbstrdecoder 1.1.5 (MultiByteStrDecoder ok, chardet linked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
