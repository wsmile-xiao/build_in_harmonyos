# lcrq 0.4.1 适配笔记

## 状态

前置适配完成（配方 + test_package + 4 补丁 dry-run 验证通过）。真机构建与 librecast
联调见 `reports/W0-report.md` 更新记录。

## 上游概况

- 项目：Librecast Project 的 RaptorQ (RFC6330) FEC 库
- 官方仓库：https://codeberg.org/librecast/lcrq（tag v0.4.1，2026 年发布）
- 许可证：GPL-2.0-only OR GPL-3.0-only
- 构建系统：autotools（configure.ac 2.71 + 手写 Makefile.in 层级：顶层 → src/doc/examples/test）
- 产物：仅共享库 `liblcrq.so`（SONAME `liblcrq.so.0.0`，ABIVERS 0.0）
- 依赖：纯 C，无外部依赖（configure 仅探测 libc 族函数）
- aarch64：上游按 CPU 分派 `matrix_neon.o`（NEON 内联函数）+ `gf256_simd.o`，无需补丁

## 为什么必须先行适配

librecast 0.11.2 的 `src/Makefile.in:41` 无条件 `LIBS += -llcrq`，即使 configure 探测
失败也无法完成 librecast.so 链接。lcrq 是 librecast 的**硬链接依赖**，按"一库一分支"
原则独立适配、独立 PR，librecast PR 声明依赖本 PR。

## 源码

- 上游无独立 release tarball，取官方 Codeberg `v0.4.1` tag 归档：
  `https://codeberg.org/librecast/lcrq/archive/v0.4.1.tar.gz`
- sha256：`f342fbcd1b4617cd14149d428cb6b596aa4cf57b1dbc2f954320dce2acd42e1f`

## 补丁（4 个，全部 dry-run 验证）

| 补丁 | 内容 | 依据 |
|------|------|------|
| 0001/0002 | config.guess/sub 加 HarmonyOS 识别（aarch64-unknown-linux-ohos） | scripts/patch-autotools-ohos.pl，libfec/librecast 先例 |
| 0003 | 顶层 `install: all doc` → `install: all`（去掉 doc/man 页，裸 install 不可依赖） | librecast 0003 同型 |
| 0004 | src/Makefile.in soname 别名 `ln -sf` → `cp -f`（3 处） | 避坑指南 #15，librecast 0004 同型 |

## 配方关键决策

- `basic_layout(build_folder=".")` 强制 in-tree（上游 Makefile 非 VPATH 感知）
- `options = {"shared": [True]}`（上游无静态目标）
- `build()` 末尾全量 `make test`：20 个用例纯算法（0000-* RaptorQ、0001-* q 队列），
  无网络依赖，真机可直接全量跑（预计 1-2 分钟）

## 上游测试

- 20 个独立用例，断言 ≈146（grep 统计）
- runner：maketest；退出码 0=PASS / 1=WARN / ≥2=FAIL
- 无需裁剪预案（无网络/权限依赖）

## 真机构建记录（2026-09-20）

- 设备：HarmonyOS PC aarch64（HongMeng Kernel 1.12.0，kernel 2026-03-23 构建，8 核）
- 入口：conan create -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... （-j1，监控内存）
- 结果：见下文更新
