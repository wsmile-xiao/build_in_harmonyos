# re 4.9.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-18
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

```bash
cmake -B build \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_PREFIX_PATH=/storage/Users/currentUser/usr/local \
  -DUSE_OPENSSL=ON \
  -DLIBRE_BUILD_SHARED=OFF \
  -DLIBRE_BUILD_STATIC=ON
cmake --build build -j1
cmake --install build
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OpenSSL 头文件缺失错误 | 系统未安装 OpenSSL 开发头文件 | 安装 openssl 3.5.6 预编译包（cmd-pkgs），头文件在 /storage/Users/currentUser/usr/local/include/openssl/ |
| 2 | CMake 不识别 OHOS 为 UNIX 系统 | CMake 内置平台检测不包含 HarmonyOS | 补丁 0002-cmake-ohos-support.patch：在 CMakeLists.txt 中增加 OHOS/HarmonyOS 判断 |
| 3 | libre.so 缺少 _mod_open/_mod_sym/_mod_close 符号 | 原因同上，src/mod/dl.c 和 src/net/posix/pif.c 未被编译 | 补丁 0002-cmake-ohos-support.patch |
| 4 | HMAC-SHA1/SHA256 无后端问题 | OHOS 上 OpenSSL 编译后端可用 | 使用 OpenSSL 后端，无 OpenSSL/mbedTLS 时保留上游 `#error` 编译失败保护，不添加静默全零 stub |

## 源码修改

- 0002-cmake-ohos-support.patch: CMakeLists.txt 添加 OHOS/HarmonyOS 平台支持

## 依赖版本

- OpenSSL 3.5.6（Conan 依赖，已发布到 ohpcd 远端：recipe rev 748fc4deb56588d6f8ce900b21e8eb0a，package ID 6b129b068851896169fae42d399fa922d239ce8a，profile OHOS/armv8/clang15/libc++）

## 验证结果

```bash
# 验证库文件
ls -la /storage/Users/currentUser/usr/local/lib/libre.*
# 输出:
# -rw-r--r-- libre.a (静态库)
# -rw-r--r-- libre.so (共享库)

# 验证符号
nm -D /storage/Users/currentUser/usr/local/lib/libre.so | grep -E "T _mod_open|T _mod_sym|T _mod_close|T net_if_list"
# 所有符号已正确导出
```

## 注意事项

- re 的实际构建系统是 CMake（不是 autotools），manifest.yaml 已修正
- 使用 `-DLIBRE_BUILD_SHARED=OFF` 避免共享库污染系统路径
- openssl/3.5.6 已发布到 ohpcd Conan 远端，re 通过 requirements() 声明 Conan 依赖（recipe rev 748fc4deb56588d6f8ce900b21e8eb0a，package ID 6b129b068851896169fae42d399fa922d239ce8a），CMakeDeps 生成 openssl::openssl
---

**编译结束**: 2026-07-31 16:44
**最终状态**: built
