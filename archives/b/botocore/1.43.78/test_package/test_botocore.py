#!/usr/bin/env python3
"""botocore consumer test (R34): real API usage — version + Session."""
import sys


def main() -> int:
    import botocore
    import botocore.session

    if botocore.__version__ != "1.43.78":
        print(f"FAIL: botocore version {botocore.__version__}",
              file=sys.stderr)
        return 1
    # 真实 API：创建 Session（botocore 核心——加载配置/凭据链——
    # Session 无 region_name 属性（AttributeError 实测）——不访问）
    s = botocore.session.Session()
    print("OK: botocore 1.43.78 session ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
