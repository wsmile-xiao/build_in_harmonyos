#!/usr/bin/env python3
"""cccolutils 消费者视角测试（5 检查点）。

用设备 python3 在 conanrun 环境（PYTHONPATH 指向包内 site-packages，
LD_LIBRARY_PATH 含 krb5/libpython）下导入打包的 cccolutils 扩展并真实
调用 API。检查点全部通过则退出码 0，任一失败退出码 1。
"""

import os
import sys
import tempfile

failures = []


def check(name, cond):
    print("[CCCOLUTILS-CHECK %s] %s" % (name, "PASS" if cond else "FAIL"))
    if not cond:
        failures.append(name)


def main():
    # E002：OHOS /tmp erofs 只读，临时凭据缓存目录落到可写位置
    tmpbase = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
    os.makedirs(tmpbase, exist_ok=True)
    cache_dir = tempfile.mkdtemp(prefix="cccolutils_krb", dir=tmpbase)
    # 只使用本临时 DIR: 缓存集合（不读取系统 ~/.krb5 等，保证 has_creds 语义确定）
    os.environ["KRB5CCNAME"] = "DIR:" + cache_dir

    # 1) 导入扩展模块
    import cccolutils
    check("import", True)

    # 2) 模块含 PyInit 约定的两个 API
    check("api_get_user_for_realm", callable(getattr(cccolutils, "get_user_for_realm", None)))
    check("api_has_creds", callable(getattr(cccolutils, "has_creds", None)))

    # 3) 无凭据缓存的未知 realm → None（get_user_for_realm 真实走
    #    krb5_cccol_cursor 遍历，空集合返回 Py_None）
    check("unknown_realm_none", cccolutils.get_user_for_realm("NO_SUCH_REALM") is None)

    # 4) 空 DIR: 缓存集合 → has_creds() 为 False
    check("has_creds_false", cccolutils.has_creds() is False)

    print("CCCOLUTILS_TEST_RESULT: %d/5 passed" % (5 - len(failures)))
    if failures:
        print("FAILED checks: %s" % ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
