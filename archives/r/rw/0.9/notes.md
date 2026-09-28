# rw 0.9 适配笔记

## 编译环境

- 构建系统: 上游 Autotools；HarmonyOS 配方采用上游 README 明示的 ISO C99 手工构建路径
- 编译日期: 2026-09-27
- 目标环境: HarmonyOS PC aarch64
- 工具链: OHOS Clang 15.0.4、Conan 2.29.1、QEMU 10.2.1
- 状态: built

## 编译步骤

上游 `rw.c` 与 `rw.h` 构成独立的 `librw`，只依赖 C99 标准库。配方从 Conan profile
取得 C 编译器和归档器，使用 `-std=c99 -O2 -fPIC` 编译后生成静态库；`shared=True`
时生成共享库。默认静态库使 OHOS aarch64 消费者测试能够在统一运行环境直接执行。

```bash
conan create archives/r/rw/0.9 \
  -pr:h ohos-aarch64-linux-cross \
  -pr:b linux-x86_64 \
  --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Autotools 探针年代较旧 | 0.9 发布包中的 `config.guess`/`config.sub` 不识别 OHOS 三元组 | 使用上游 README 针对 exotic systems 明示的直接 C99 编译路径，不修改生成文件、不伪造平台 |
| 2 | 可选命令行程序引入 igraph | `simplerw.c` 负责多种图文件解析，库核心 `rw.c` 不依赖 igraph | 配方只打包目标库 `librw`；不混入可选 CLI，从而保持库依赖准确 |
| 3 | 上游发布包没有测试套件 | `make check` 实测输出 `Nothing to be done for 'check'` | 新增 8 项消费者/API 测试，共 28 个显式断言，覆盖已知图、分层计算、分解树和 OHOS ABI |

## 源码修改

无。0.9 源码按原样编译，不需要 HarmonyOS 补丁。

## 依赖版本

`librw` 无第三方编译或运行依赖。可选 CLI 所需的 igraph 不属于本库制品。

## 验证结果

```text
rw tests: 8/8 passed (28 assertions)
Conan package test: PASS
```

上游测试为 0 项，实测 0/0；新增测试 8/8 全部通过，测试数严格不少于上游。

## 交付物

| 文件 | 说明 |
|------|------|
| `include/rw.h` | rank-width 公共 C API |
| `lib/librw.a` | 默认静态库 |
| `licenses/COPYING` | GPL-2.0-or-later 许可证文本 |

## 注意事项

算法使用 32 位顶点子集位图，公共头文件将 `MAX_VERTICES` 定义为 32；较大图会被
`init_rw_dec()` 拒绝。计算复杂度随顶点数指数增长，这是上游算法设计边界。
---

**编译结束**: 2026-09-27 05:11
**最终状态**: built
