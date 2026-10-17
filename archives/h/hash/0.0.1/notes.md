# hash 0.0.1 适配笔记

## 编译环境
- 构建系统: makefile（上游仅有 test 目标，库由配方直接编译）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）
- 状态: published

## 编译步骤

1. `ohc-run.py init-build hash 0.0.1 --url=https://github.com/clibs/hash/archive/refs/tags/0.0.1.tar.gz`
   （GitHub 直连 urllib 超时，预置已下载 tarball 到 `~/tmp/builds/hash-0.0.1.tar.gz` 后重跑成功；
   SHA-256=380d2a5ae65f2b8e58beca6c54f35e796454c5da1cb6564ce1b2d9c3d5a5d839）
2. 上游自测: `CC=clang make test` → 9/9 通过（`✓ ok`, exit=0）
3. 配方: conanfile.py 直接用 Conan toolchain（R33）编译 `hash.c` 生成 `libhash.a`，
   打包 `hash.h`/`khash.h` 到头文件目录
4. `conan create . --build=missing` → G2 通过；test_package 消费者 + OHOS 专项测试通过
5. `ohc-run.py conan-verify hash 0.0.1` → G0-G4/L2/L4/L5 全部 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `settings.os.version` value not defined | OHOS profile 未定义 os.version 子设置 | 配方 `configure()` 中 `rm_safe("os.version")`（与 au/astc-encoder 同法） |
| 2 | OHOS 专项测试 10 万插入后 size=40339 | clibs/hash 存储键**指针**而非拷贝，复用栈缓冲区导致键别名去重 | 键使用 strdup 稳定堆内存，结束前统一 free |
| 3 | make -j20 jobserver mkfifo 失败 | HMDFS 不支持命名管道 | 非阻塞警告，单线程链接成功，不影响构建 |
| 4 | init-build urllib 下载 GitHub 超时 | 宿主网络对 github.com 直连慢 | curl 下载 tarball 预置 builds 目录，EXPECTED_SHA256 校验后重跑 |

## 源码修改
无补丁（上游源码未改动，无需 patches/）

## 依赖版本
无第三方依赖（纯 C99 + POSIX）

## 验证结果
- 上游测试: 9/9 = 100%（`make test`）
- OHOS 专项测试: 10 万条目压力/迭代/删除/清空/生命周期全过
- test_package 消费者: `test_hash_consumer: OK (public API exercised)`
- conan-verify: G1-G4 + L2/L4/L5 PASS

## 关键设计
- 上游 Makefile 只有 `test`/`clean` 目标，无库构建/安装规则 → 配方直接编译静态库（clib 风格包）
- C99 inline 函数（hash_set/get/has/del）在 -std=c99 下编译为外部 T 符号，可正常链接（已实测）
---

**编译结束**: 2026-09-18 20:56
**最终状态**: published
