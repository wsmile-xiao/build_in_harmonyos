#!/usr/bin/env python3
"""pyenchant consumer test（R34：真实调用被测库 API）。

核心是验证 **ctypes → libenchant-2 的绑定真实可用**（这是本包唯一的集成风险）。
不依赖系统拼写词典，故选取不需要词典的 API：
  * `import enchant` —— 触发 libenchant 加载（失败即报错）
  * `enchant.Broker()` —— 可实例化
  * `enchant.tokenize.unit_tokenize(...)` —— 纯 Python 分词，无需词典
导入失败或任一断言失败即返回非零。
"""
import os
import sys


def main() -> int:
    try:
        import enchant
    except ImportError as e:
        print(f"FAIL: cannot import enchant: {e}", file=sys.stderr)
        return 1

    # 0) 断言导入的确来自**被测包**而非系统恰好装着的 pyenchant。
    #    CI 的 L1e 负向测试会移除包产物后重跑，若此时仍能通过，即说明本测试没有
    #    真正依赖该包 —— 故必须显式校验来源（同批 zstandard 的 ZSTD_EXPECT_SITE）。
    expect_site = os.environ.get("PYENCHANT_EXPECT_SITE")
    if expect_site:
        origin = os.path.realpath(getattr(enchant, "__file__", "") or "")
        if not origin.startswith(os.path.realpath(expect_site) + os.sep):
            print(f"FAIL: enchant imported from {origin!r}, expected under "
                  f"{expect_site!r}", file=sys.stderr)
            return 1

    # 1) Broker 可实例化（内部会与 libenchant 交互）
    try:
        broker = enchant.Broker()
        if broker is None:
            print("FAIL: enchant.Broker() returned None", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: enchant.Broker() raised: {e}", file=sys.stderr)
        return 1

    # 2) 纯 Python 分词（不依赖词典）—— 真实功能调用
    #    注意 `unit_tokenize` 按**单元**（空白分隔）切分，不是按词：
    #    "hello world" 是 1 个单元；词级切分需 get_tokenizer(需词典)。
    try:
        from enchant.tokenize import unit_tokenize
        toks = [t[0] for t in unit_tokenize("hello world")]
        if toks != ["hello world"]:
            print(f"FAIL: unit_tokenize('hello world') -> {toks!r}",
                  file=sys.stderr)
            return 1
        if [t[0] for t in unit_tokenize("hello")] != ["hello"]:
            print("FAIL: unit_tokenize('hello') wrong", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: tokenize API raised: {e}", file=sys.stderr)
        return 1

    # 3) 语言枚举（无词典时应返回 list，允许为空）
    try:
        langs = enchant.list_languages()
        if not isinstance(langs, list):
            print(f"FAIL: list_languages() -> {type(langs).__name__}",
                  file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: list_languages() raised: {e}", file=sys.stderr)
        return 1

    print(f"OK: pyenchant real API ok (libenchant loaded via ctypes; "
          f"Broker ok, tokenize ok, list_languages -> {len(langs)} langs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
