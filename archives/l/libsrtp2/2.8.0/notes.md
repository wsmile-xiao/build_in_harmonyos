# libsrtp2 2.8.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

```bash
# 官方 tag 源码
# https://github.com/cisco/libsrtp/archive/refs/tags/v2.8.0.tar.gz
# sha256: d123dcff5c56d4f1a9006f2b311ea99a85016cbf3bb24b1007885d422237db85

cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
         -DBUILD_SHARED_LIBS=OFF \
         -DLIBSRTP_TEST_APPS=ON \
         -DENABLE_OPENSSL=OFF \
         -DENABLE_WARNINGS_AS_ERRORS=OFF \
         -DENABLE_WARNINGS=ON
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直接下载超时 (E017) | 网络问题 | 使用 ghfast.top 镜像临时下载核验 SHA-256（conandata.yml 仍为官方 URL） |
| 2 | conan-init 生成 autotools 模板 | 模板按 URL 猜测构建系统 | 手工修正为 CMake 配方（与上游 CMakeLists 匹配） |

## 依赖版本

无外部依赖（ENABLE_OPENSSL=OFF 使用内置 crypto：AES-ICM/AES-GCM/SHA-1）

## 验证结果

```bash
ctest --output-on-failure   # 12/12 passed (aes_calc_128/256, sha1_driver, datatypes_driver,
                            # cipher_driver, kernel_driver, rdbx_driver, replay_driver,
                            # roc_driver, srtp_driver, test_srtp, rtpw_test)
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64  # 通过
```

## 交付物

- 静态库: libsrtp2.a（install 产物仅 lib/ + include/srtp2/，无 bin/ 可执行文件 → 非 CLI 库）

## 注意事项

- 库名为 libsrtp2，CMake 导出目标 libSRTP::srtp2，静态库文件名 libsrtp2.a
- package_info: cpp_info.libs=["srtp2"]，cmake_file_name="libSRTP"
- 静态库无需 ELF 签名
---

**编译结束**: 2026-09-17 09:01
**最终状态**: built
