#!/usr/bin/env python3
"""omegaconf consumer test (R34): real API usage — OmegaConf.create."""
import sys


def main() -> int:
    import omegaconf

    if omegaconf.__version__ != "2.3.1":
        print(f"FAIL: omegaconf version {omegaconf.__version__}",
              file=sys.stderr)
        return 1
    # 真实 API：OmegaConf.create（核心——antlr4/yaml 依赖链真实运行）
    cfg = omegaconf.OmegaConf.create({"a": 1, "b": {"c": 2}})
    if cfg.a != 1 or cfg.b.c != 2:
        print(f"FAIL: OmegaConf.create result {cfg}", file=sys.stderr)
        return 1
    print("OK: omegaconf 2.3.1 (OmegaConf.create ok, antlr4/yaml linked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
