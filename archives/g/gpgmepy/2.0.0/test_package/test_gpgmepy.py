#!/usr/bin/env python3
"""消费测试：验证 gpgmepy 2.0.0 安装布局 + gpg 包可用。

gpgmepy 是 GPGME 的 Python 绑定（SWIG 扩展 gpg._gpgme + 纯 Python 包 gpg/，
装于 <pkg>/lib/python3.12/site-packages/gpg）。验证 3 组：
1. import gpg 来自 conan 包且 _gpgme SWIG 扩展 dlopen 成功（E212 签名）
2. 版本属性：gpg.version.versionstr=2.0.0 + gpgme.GPGME_VERSION
3. 核心 API：Context/Data 类、gpgme 模块属性、callbacks/results、
   gpg.Data 内存读写——不调用需真实 gpg 二进字的 Context/加解密（CI 自包含）
终态推导：任一断言失败即 exit 1（AssertionError），全部通过才 "ALL PASS"。
上游 26 个 tests/t-*.py 本地实跑、结果如实记于 PR body，不随归档。
"""
import sys

PASS = "PASS:"


def main():
    site, py_bin = sys.argv[1], sys.argv[2]
    print("interpreter: {}".format(py_bin))
    print("site-packages: {}".format(site))

    # 1. import gpg 必须解析到 conan 包，且 _gpgme 扩展已加载（R34 非空壳）
    sys.path.insert(0, site)
    import gpg
    import gpg._gpgme  # noqa: F401  触发 _gpgme*.so dlopen
    assert gpg.__file__.startswith(site), "gpg imported from " + gpg.__file__
    print(PASS + " import gpg 来自 conan 包，_gpgme SWIG 扩展 dlopen 成功")

    # 2. 版本属性（version.py.in @VERSION@ 替换 + gpgme 库版本）。
    #    gpg 包无 __version__ 字符串属性，版本在 gpg.version 模块。
    assert gpg.version.versionstr == "2.0.0", gpg.version.versionstr
    assert gpg.version.versionlist == ["2", "0", "0"]
    print(PASS + " gpg.version.versionstr == 2.0.0")
    from gpg import gpgme, results
    assert gpgme.GPGME_VERSION.startswith("1.24"), gpgme.GPGME_VERSION
    assert gpg.version.gpgme_versionstr == gpgme.GPGME_VERSION
    print(PASS + " gpgme.GPGME_VERSION = " + gpgme.GPGME_VERSION)

    # 3. 核心 API 存在性（不启动 gpg 引擎）
    assert callable(gpg.Context) and callable(gpg.Data)
    assert callable(gpgme.gpgme_check_version)
    assert callable(gpg.callbacks.passphrase_stdin)
    assert issubclass(results.DecryptResult, results.Result)
    # gpg.Data 内存缓冲区读写（纯内存 new_from_mem，无引擎）。不调用显式
    # release()：gpgmepy Data.release() 后 __del__ 二次释放同一句柄（upstream
    # 双重释放缺陷）→ 解释器退出段错误。
    d = gpg.Data(b"hello gpgmepy")
    mem = d.read(4096)
    assert mem == b"hello gpgmepy", mem
    del d
    print(PASS + " Context/Data 类 + gpgme 属性 + callbacks/results + Data 读写")

    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
