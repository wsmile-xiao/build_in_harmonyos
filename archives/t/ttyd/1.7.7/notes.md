# ttyd 1.7.7 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-08-17
- 编译器: clang/clang++ (OHOS aarch64 profile)
- 状态: built

## 上游身份

- 官方仓库: https://github.com/tsl0922/ttyd（维护者 Shuanglei Tao / tsl0922）
- 版本/tag: 1.7.7
- 源码: https://github.com/tsl0922/ttyd/archive/refs/tags/1.7.7.tar.gz
- SHA256: 039dd995229377caee919898b7bd54484accec3bba49c118e2d5cd6ec51e3650
- 许可证: MIT
- 语言/构建: C / CMake（cmake_minimum_required 3.12）
- 产物: `ttyd` 可执行文件（bin/ttyd）+ man/ttyd.1

## 依赖（制品仓 ohpcd 均已发布）

| 依赖 | 版本 | 用途 |
|------|------|------|
| libwebsockets | 4.3.5.1 | WebSocket/HTTP 服务；**必须开启 LWS_WITH_LIBUV**（ttyd CMakeLists 无条件 FATAL_ERROR 检查） |
| libuv | 1.52.1 | 事件循环与 PTY 管道（ttyd pty.c 直接使用 uv_pipe/uv_async） |
| json-c | 0.18 | 配置/协议 JSON 解析 |
| zlib | 1.3.1 | HTTP 压缩 |
| openssl | 3.5.6 | TLS（libwebsockets 启用 SSL 时 ttyd 需要） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libwebsockets/4.3.5 无法满足 ttyd 构建 | ttyd CMakeLists 检查 LWS_WITH_LIBUV 宏，4.3.5 制品未开启 libuv 支持（lws_config.h 中 #undef） | 使用依赖项重新发布的 libwebsockets/4.3.5.1（LWS_WITH_LIBUV=ON，依赖 libuv） |
| 2 | json-c/libuv 找不到 | ttyd CMakeLists 用 find_path/find_library 而非 CONFIG target 查找 | conanfile.py generate() 中通过 CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH 注入各依赖 include/lib 路径 |
| 3 | CMake 4.x 策略报错 | 上游 cmake_minimum_required 3.12 与 CMake 4.1 策略冲突 | tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5" |

## 源码修改

无（未生成补丁，未修改上游源码）。

## 上游测试

ttyd 1.7.7 上游无自动化测试：
- 源码树无 tests/ 目录（仅 src/ html/ man/ scripts/ cmake/）
- CMakeLists.txt 无 enable_testing()/add_test()，无 `make check` 目标
- .github/workflows 仅交叉编译（scripts/cross-build.sh）与前端打包
- 因此上游测试用例数 = 0（核验依据见 test_package/MANIFEST.yml）

## 验证结果

```bash
# 依赖预检（W0）
bash ci/scripts/preflight_check.sh ttyd/1.7.7 --deps "libwebsockets/4.3.5.1 json-c/0.18 zlib/1.3.1 openssl/3.5.6 libuv/1.52.1"
# 全部 [OK] 已发布

# CMake 配置验证
cmake -S <ttyd-1.7.7> ... # -- Looking for LWS_WITH_LIBUV - found → 配置成功
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（application 类型，5 个依赖） |
| conandata.yml | 官方源码 URL（含镜像 fallback）+ SHA256 |
| test_package/ | 消费者测试（test.sh 验证 --version/--help/-h/最小服务启动） |

## 注意事项

- 依赖链：ttyd → libwebsockets/4.3.5.1 → openssl/3.5.6，libwebsockets 4.3.5.1 已带 libuv 支持
- test_package 的 test.sh 在 OHOS 上通过 VirtualRunEnv 运行；可执行文件需签名（OHOS ELF）
- finish 只能标记 built，不得标记 published（未走 release/upload CI）
---

**编译结束**: 2026-08-18 21:40
**最终状态**: built
