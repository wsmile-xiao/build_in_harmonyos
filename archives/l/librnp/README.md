# librnp

RNP 是高性能 C++ OpenPGP 库，被 Mozilla Thunderbird 使用，提供密钥管理、加解密、签名验签等完整的 OpenPGP 功能。

## OHOS 适配
- 构建系统为 CMake，默认 Botan 后端，对接制品仓 botan2/2.19.5（BOTAN_ROOT_DIR）
- 内建 sexpp（SYSTEM_LIBSEXPP=OFF），json-c/zlib/bzip2 用原生查找模块显式对接
- 上游 gtest 套件用制品仓 gtest/1.17.0（DOWNLOAD_GTEST=OFF），cli_tests 需 GnuPG，在 OHOS 上自动跳过
- 默认静态库；同时产出 rnp/rnpkeys 命令行工具

## 依赖
- botan2/2.19.5
- json-c/0.18
- zlib/1.3.1
- bzip2/1.0.8
- gtest/1.17.0（测试）

## 功能验证
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
./test_librnp  # 期望输出 test librnp 0.18.1: OK
rnp --version  # 期望输出版本信息
```

## 参考
- 官网: https://www.rnpgp.org/
- 源码: https://github.com/rnpgp/rnp
