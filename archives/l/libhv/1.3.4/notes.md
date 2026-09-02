# libhv 1.3.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: clang/clang++ (15.0.4, target aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

libhv 上游以 CMake 为主构建系统（BUILD.md 推荐；同时提供自定义 configure bash
脚本，但非 GNU autoconf，conan 配方采用 CMake 模板）。

```bash
# 原生验证（HarmonyOS aarch64 设备）
cmake -S libhv-1.3.4 -B build -DBUILD_UNITTEST=ON -DBUILD_EXAMPLES=ON \
      -DBUILD_SHARED=ON -DBUILD_STATIC=ON
cmake --build build --target unittest -j4   # 上游 unit test 全量编译
# 工具化验证
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # recipe + test_package，退出 0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-stdlib=libstdc++` 报 invalid library name | 缓存 ohos-aarch64 profile 的 libcxx 与 OHOS clang 不匹配（clang 只支持 libc++） | 用仓库 ci/conan/profiles/ohos-aarch64 覆盖缓存 profile（libcxx=libc++） |
| 2 | test_package 运行时报 `libhv.so` 符号找不到 | 共享库在 OHOS 设备动态加载受签名/加载路径限制 | 配方默认静态（shared=False），链接 libhv_static.a |
| 3 | conan-init 生成 autotools 模板与 libhv 不符 | libhv 主构建是 CMake | 配方改为 CMake 模板（CMakeToolchain + CMake） |
| 4 | finish W3 junk_check full 模式失败 | 本地未提交变更时 `origin/main...HEAD` diff 为空，junk_check 回退 full 模式扫到基线其他库历史垃圾 | 按 W2 原子性提交仅 libhv 变更，junk_check 进入 incremental 模式只检查本库 |

## 源码修改

无（未改动上游源码，零补丁）。

## 依赖版本

无外部 Conan 依赖（libhv 自带协议栈；pthread/m/dl 为系统库）。上游可选
openssl/nghttp2 等默认关闭（WITH_OPENSSL=OFF 等），R01 未启用。

## 验证结果

```bash
# 上游 unit test（unittest/ + evpp/），本机原生编译运行
# 独立上游用例 38 项，PASS 35，全量通过率 35/38 = 92.1%
#   不可运行 3 项：ping(ICMP raw socket 平台限制)、ftp/sendmail(需外部 FTP/SMTP 服务)
# 全部 35 项实际执行用例均通过（执行通过率 100%）
# HarmonyOS 专项测试 ohos_echo_test：20/20 PASS（含本机 127.0.0.1 TCP 回环真实往返）
# conan create：退出 0，test_package 消费者测试 100% 通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 构建配方，默认静态（libhv_static.a） |
| conandata.yml | 官方源码 + gh-proxy 镜像，SHA-256 f0a9a197... |
| test_package/test.c | 消费者测试：真实调用 hv_base64/md5/hbase API |
| packaging/libhv-1.3.4-ohos-aarch64.tar.gz | 预编译包（include + lib） |

## 注意事项

- libhv 库名 hv/hv_static，头文件安装到 include/hv/，消费者 include 路径用
  `include/`（即 `#include "hv/hbase.h"`）。
- OHOS 设备动态加载自建未签名 .so 受限，本配方默认静态链接保证消费者可用。
- 上游测试台账完整版见任务回报（libhv_test_ledger.md，SHA-256
  ee61f884bec525d64b83ed3b6fccdbd7c2758129c8517cafd54d6b4e989ced0e）。

---

**编译结束**: 2026-09-02 03:26
**最终状态**: built
