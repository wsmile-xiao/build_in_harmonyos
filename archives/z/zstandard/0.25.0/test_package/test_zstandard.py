#!/usr/bin/env python3
"""zstandard consumer test（R34：真实调用被测库 API）。

覆盖 C 扩展的真实功能路径（同时也验证扩展已链到 conan 的 libzstd）：
  * 一次性 compress / decompress 往返
  * 流式 stream_writer / stream_reader 往返
  * 版本信息（zstd 库版本）
导入失败或任一断言失败即返回非零。
"""
import io
import os
import sys


def main() -> int:
    try:
        import zstandard as zstd
    except ImportError as e:
        print(f"FAIL: cannot import zstandard: {e}", file=sys.stderr)
        return 1

    # 必须来自**被测包**，而非系统 site-packages 里恰好也装着的 zstandard ——
    # 否则 L1e 负向测试（移除包产物后重跑）会因测试仍通过而判「不真正依赖该包」。
    expect = os.environ.get("ZSTD_EXPECT_SITE")
    if expect:
        got = os.path.realpath(zstd.__file__ or "")
        if not got.startswith(os.path.realpath(expect)):
            print(f"FAIL: zstandard imported from {got!r}, "
                  f"expected under package {expect!r}", file=sys.stderr)
            return 1

    payload = b"hello zstandard " * 500

    # 1) 一次性往返
    try:
        cctx = zstd.ZstdCompressor(level=3)
        compressed = cctx.compress(payload)
        if not compressed or len(compressed) >= len(payload):
            print(f"FAIL: compression ineffective: {len(compressed)} vs "
                  f"{len(payload)}", file=sys.stderr)
            return 1
        dctx = zstd.ZstdDecompressor()
        restored = dctx.decompress(compressed, max_output_size=len(payload))
        if restored != payload:
            print("FAIL: round-trip mismatch (one-shot)", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: one-shot API raised: {e}", file=sys.stderr)
        return 1

    # 2) 流式往返
    #    注意 stream_writer 默认 closefd=True：with 退出时会**关闭**底层 buf，
    #    之后再 buf.getvalue() 会报 "I/O operation on closed file"（实测踩到）。
    try:
        buf = io.BytesIO()
        with cctx.stream_writer(buf, closefd=False) as w:
            w.write(payload)
        streamed = buf.getvalue()
        with dctx.stream_reader(io.BytesIO(streamed)) as r:
            got = r.read()
        if got != payload:
            print("FAIL: round-trip mismatch (stream)", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: streaming API raised: {e}", file=sys.stderr)
        return 1

    # 3) 版本信息（证明链到的 zstd 可用）
    try:
        zstd_ver = zstd.ZSTD_VERSION
    except Exception as e:
        print(f"FAIL: ZSTD_VERSION unavailable: {e}", file=sys.stderr)
        return 1

    print(f"OK: zstandard {zstd.__version__} real API ok "
          f"(one-shot + streaming round-trip; linked zstd {zstd_ver})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
