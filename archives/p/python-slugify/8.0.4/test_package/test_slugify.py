#!/usr/bin/env python3
"""python-slugify consumer test (L0c + R34): standalone test source
executed via self.run from conanfile.py test().

R34: actually call the tested API — slugify() transliteration +
smart_truncate() (pure user-space).

Usage: test_slugify.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    # site 可能为 pathsep 拼接的多路径（自身 + 依赖 text-unidecode）——
    # 按 os.pathsep 分割后逐路径检查/加入 sys.path
    paths = [p for p in site.split(os.pathsep) if p]
    if not any(os.path.isdir(os.path.join(p, "slugify")) for p in paths):
        raise AssertionError(f"slugify package missing in {paths}")
    sys.path = paths + sys.path
    # R34: 真实调用被测库 API
    import slugify

    # slugify 基础转写（含拼音/西里尔/重音字符）
    out = slugify.slugify("Hello, World!")
    if out != "hello-world":
        raise AssertionError(f"unexpected slugify result: {out!r}")
    # 中文转写（text-unidecode 运行时依赖）
    out_cn = slugify.slugify("我爱北京天安门")
    if not out_cn:
        raise AssertionError("Chinese transliteration produced empty slug")
    # smart_truncate
    s = slugify.smart_truncate("a very long title that needs truncating",
                               max_length=20)
    if not s or len(s) > 20:
        raise AssertionError(f"smart_truncate result too long: {s!r}")
    print(f"OK: python-slugify {slugify.__version__} "
          f"(slugify 'hello-world' + zh '{out_cn}' + truncate ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
