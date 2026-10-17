# etcd-cpp-apiv3 0.15.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-01
- 编译器: clang/clang++ (OHOS SDK, arm64)
- 状态: built

## 编译步骤

```bash
# profile（绝对路径，相对路径会被 conan 静默忽略）
PF=$PWD/ci/conan/profiles/ohos-aarch64

# 预置源码下载缓存（G2 镜像注入之外，W3/finish 无镜像时直接命中缓存）
# ~/.conan2/global.conf: core.sources:download_cache=/storage/Users/currentUser/.conan2/downloads
# 缓存文件: ~/.conan2/downloads/s/4516ecfa...(+.json，官方与 ghfast 双 URL)

# 创建包（含 test_package）
conan create archives/e/etcd-cpp-apiv3/0.15.4 \
  -pr:h=$PF -pr:b=$PF --build=missing

# 正式验证（八道门禁）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify etcd-cpp-apiv3 0.15.4
```

关键配置：
- `BUILD_ETCD_CORE_ONLY=ON`（避开 cpprestsdk，纯同步 API）
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 4.1.2 移除 <3.5 兼容，etcd 声明 3.3；经 conanfile `cache_variables` 下发——`tc.variables` 写入 toolchain 文件在 `cmake_minimum_required` 之后加载，无效；`cache_variables` 走 -D 命令行，有效）
- toolchain 显式预置 `Protobuf_PROTOC_EXECUTABLE`/`GRPC_CPP_PLUGIN`（交叉编译下 find_program REQUIRED 会失败；注意变量名无 `_PROGRAM` 后缀，与上游 CMakeLists 一致）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(3.3) 被拒 | CMake 4.1.2 移除 <3.5 兼容策略 | conanfile `cache_variables` 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | `GPR_ASSERT` 未声明 | grpc ≥1.70 公共头移除该宏 | 补丁 0001：`#ifndef` 兜底宏（上游 master 已有相同修复） |
| 3 | 依赖 cpprestsdk 不可用 | cpprestsdk 不在 ohpcd 制品仓 | `BUILD_ETCD_CORE_ONLY=ON`（core GLOB `src/**/*.cpp` 不含根下 Client.cpp，实测 ** 需匹配≥1 层目录，天然避开 pplx） |
| 4 | test_package `find_dependency(grpc)` 失败 | grpc/protobuf 配方 `cmake_find_mode=none`，CMakeDeps 不生成其 config；生成 config 用小写名查 `grpc_DIR`，而实际文件是 `gRPCConfig.cmake`（OHOS 大小写敏感） | test_package conanfile 显式设 `gRPC_DIR`/`Protobuf_DIR`/`utf8_range_DIR`/`absl_DIR`/`OPENSSL_ROOT_DIR` |
| 5 | 目标名不匹配：链接 `grpc::grpc`/`protobuf::protobuf` 但真实目标是 `gRPC::*`/`protobuf::libprotobuf` | 同上：CMakeDeps 默认依赖目标名 vs 注册表包 config 实际目标名 | test CMakeLists 先 find 真实 config，桥接 `grpc::grpc→gRPC::grpc++;gRPC::grpc;gRPC::gpr`、`protobuf::protobuf→protobuf::libprotobuf`，并预置 `grpc_FOUND`/`protobuf_FOUND` 跳过 find_dependency |
| 6 | libgrpc.a 的 zlib 符号未定义（deflateEnd 等） | gRPCConfig.cmake 不传播 zlib 链接 | test 链接 `zlib::zlib` 显式补充（与 grpc 包自身 test 做法一致） |
| 7 | conan-verify G2 突然回退：GPR_ASSERT 报错复现 | 框架镜像注入后恢复 conandata 内容但**不删除 `.ghfast-bak`**；下次 conan-verify 启动"崩溃恢复"用陈旧 bak 覆盖当前 conandata，吞掉后加的补丁登记 | 重写 conandata + 删除陈旧 bak 后重跑（框架已知缺陷，不改框架文件） |
| 8 | W3/finish 场景 GitHub 直连超时 | 网络限制：GitHub 不可达，仅 ghfast.top 镜像可用 | 预置 Conan 源码下载缓存（`core.sources:download_cache` + 双 URL 的 .json 元数据） |
| 9 | W3 junk check 报 84 软件包原子性违规 + 他人包隐藏文件 | 分支从本地 main（领先 origin/main 194 提交）切出，`git diff origin/main...HEAD` 含他人未推送工作 | `git reset --keep origin/main`（保留工作区他人未提交修改）后只提交 etcd 目录，diff 基点恢复纯净 |
| 10 | finish Step 3 clean-verify G0 失败（./configure 不存在） | clean_verify.py 硬编码 autotools 假设，对纯 CMake 项目无分支 | 框架已知局限，非阻塞（finish 仅警告）；真实构建由 conan-verify G2 与 W3 全链路覆盖 |
| 11 | finish Step 8 gen_summary 崩溃（'str' object has no attribute 'append'） | 框架 SUMMARY 生成器 bug | 不改框架文件；本 notes.md 即完整问题记录 |

## 源码修改

| 补丁 | 内容 |
|------|------|
| `patches/0001-src-v3-Action.cpp.patch` | `src/v3/Action.cpp` 添加 `#ifndef GPR_ASSERT` 兜底宏 + 显式 `<cstdio>`（镜像上游 master 修复，grpc ≥1.70 兼容） |

## 依赖版本

- grpc/1.70.0（ohpcd，静态；其内部要求 protobuf/33.6）
- protobuf/33.6（ohpcd）
- openssl/3.5.6（ohpcd）
- zlib/1.3.1（ohpcd，显式链接补充）

## 验证结果

```bash
$ conan create archives/e/etcd-cpp-apiv3/0.15.4 -pr:h=$PF -pr:b=$PF --build=missing
...
1/1 Test #1: test_etcd ........................   Passed    0.12 sec
100% tests passed, 0 tests failed out of 1

$ ohc-run.py conan-verify etcd-cpp-apiv3 0.15.4
✅ 配方验证通过: G1 G0 G2 G3 G4 L2 L4 L5 全部 PASS
```

test_package 走完整 protobuf+grpc 链路：构造 SyncClient、put/get/head，无服务器环境下 ParseResponse 将 grpc::Status 映射为 error_code（UNAVAILABLE）而不抛异常，可精确断言（R34 合规，实质调用 etcd API）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | 7.3KB | CMake 配方（CORE_ONLY + cache_variables 策略） |
| conandata.yml | 538B | 官方 URL + sha256 + 补丁登记（R39） |
| patches/0001-src-v3-Action.cpp.patch | ~1KB | GPR_ASSERT 兜底 |
| test_package/ | — | 4 文件（conanfile/CMakeLists/test_etcd.cpp/MANIFEST.yml） |
| reports/conan-verify-report.md | — | 八门禁 PASS 报告 |
| reports/conan-create.log | — | G2 干净构建日志 |

## 注意事项

- conan-verify 镜像注入的 `.ghfast-bak` 回滚缺陷：**每次修改 conandata 后跑 conan-verify 前，先删除残留 bak**，否则补丁登记会被吞。
- grpc/protobuf 为 `cmake_find_mode=none` 包：消费方需显式 `*_DIR` 指路 + 目标名桥接（本 test_package 的做法可复用）。
- 远端包 id：grpc/1.70.0@ohpcd/stable=d6feb83e469449a5edba73fdc34bf2a5c3854d0d，protobuf/33.6@ohpcd/stable=a3c051deb139e17bdef4965b92040fa58a49fcaf。
---

**编译结束**: 2026-09-01 11:51
**最终状态**: built
