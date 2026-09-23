# odo 0.2.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

odo 是纯 Makefile 工程（C99 + POSIX），无 configure/cmake，无第三方依赖。

```bash
# 1. 直接 make（用 Conan toolchain 提供的 CC，R33）
make CC=clang -j1

# 2. 上游测试
make test          # → ./test_odo → "all tests passed"

# 3. Conan 打包
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
conan test test_package "odo/0.2.2@"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-p` 输出与预期不符导致的 test 断言失败 | 上游 `-p` 语义是"自增+打印"，非"纯打印"；`-c` 才是纯读 | 对照 upstream main.c 确认语义，修正 test.sh 断言 |
| 2 | W3 L1e 误判"test 不依赖被测包" | Step 2 staging `make install` 残留 `/usr/local/bin/odo`，test 命中 PATH 残留 | 删除 staging 残留二进制，仅用 Conan 包内 bin/odo |
| 3 | W3 jc_junk 误报 543 个无关包的垃圾文件 | `origin/main` 引用陈旧，`git diff origin/main...HEAD` 把无关提交算进检查范围 | 本地 ref 对齐真实基线 + pr.diff 模式（与真实 CI 的 PR diff 同构） |

## 源码修改

无补丁。上游源码零修改直接编译通过。

## 依赖版本

无第三方依赖（纯 C99 + POSIX 系统调用：open/mmap/fstat/ftruncate/munmap/__sync CAS）。

## 验证结果

```bash
# 上游测试
make test                    # → all tests passed（并发 9998 次自增 + set + inc 断言）

# 消费者测试（test_package/test.sh）
./test.sh                    # → odo consumer test: all passed（inc/cat/-p/set/reset 6 项断言）

# W3 本地 CI 模拟
0 0 0 0 51200             # conan create + L0/L1/L1e/L4/L5 全 pass，Pass rate 100% (1/1)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 应用型配方（package_type=application） |
| conandata.yml | 源码 URL + sha256 |
| test_package/test.sh | 消费者测试（调用 odo 公开 CLI） |
| commands.json | 命令行工具声明（R38） |

## 注意事项

- repo 根与 CI 的 `packaging/` 目录是 CI 运行时产物，已被 .gitignore 忽略，不随 PR 提交；
- `.ci-result.json` 由 finish W3 自动生成（含日志 SHA256），禁止手改；
- libXext 的两个工作区幽灵改动（README.md/manifest.yaml）与本任务无关，未纳入本次提交。
---

**编译结束**: 2026-09-19 20:04
**最终状态**: built
