# dcadec 0.2.0 适配笔记

## 编译环境

- 目标系统：HarmonyOS/OpenHarmony 6.0，AArch64
- 构建系统：GNU Make
- 编译器：OpenHarmony SDK Clang 15.0.4
- Conan：2.29.1（OHOS 适配版）
- 状态：built

## 编译步骤

Conan 配方从 `tools.build:compiler_executables` 读取目标 C 编译器，并从同一 SDK 工具目录选择 `llvm-ar`。源码复制到构建目录后应用可移植性补丁，默认以 `CONFIG_SHARED=1` 构建共享库和 `dcadec` 命令行程序；`shared=False` 时构建静态库。构建阶段直接执行上游 `make check`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试素材未包含在发布压缩包中 | `test/samples` 是独立 Git 子模块 | 按 v0.2.0 的 gitlink 精确固定 `dcadec-samples` 提交并校验 SHA-256 |
| 2 | `ln -sf` 不符合目标文件系统的稳健链接创建要求 | 强制符号链接操作在部分文件系统上行为不一致 | 先显式删除目标，再用 `ln -s` 创建链接 |
| 3 | 原始 Makefile 会隐式使用宿主工具 | 交叉构建不能依赖环境中的默认 `cc`/`ar` | 从 Conan 配置注入 OHOS SDK 的 `CC` 与 `AR` |
| 4 | 真机 `sha1sum -c` 将清单中的 GNU 二进制标记 `*` 视为文件名字符 | 上游 `checksum.txt` 采用 GNU `sha1sum -b` 格式，OHOS 系统工具的检查模式解析语义不同 | 构建目录生成 POSIX shell 兼容入口，逐项剥离格式标记后仍调用系统 SHA-1 实现并对比全部原始预期值 |

## 源码修改

- `patches/0001-Makefile.patch`：调整 Makefile 的符号链接创建方式，并为共享构建的 CLI 设置包内相对运行路径；不修改解码算法、公开 API 或任何上游测试。
- `patches/0002-dcadec.c.patch`：为打包后的命令行工具补充常规 `--help` 长选项；不改变解码行为。

## 上游测试清点

| 项目 | 清点结果 |
|------|----------|
| 上游测试入口 | `test/test.sh`，由 `make check` 调用 |
| 官方测试样本 | 19 个 `.dtshd`，来自 v0.2.0 固定的 samples 提交 |
| 精确输出校验 | 118 项 SHA-1 |
| 有损输出校验 | 69 项 PCM 标准差 |
| 上游断言合计 | 187 项 |
| 上游测试修改 | 0 项 |
| OHOS/AArch64 实测 | 187/187 通过 |

## 依赖版本

- 无第三方 Conan 依赖。
- 系统库：`libm`。

## 验证结果

```text
OHOS/AArch64 shared conan create: PASS
OHOS/AArch64 static conan create: PASS
upstream make check: 187/187 PASS
consumer API assertions: 12/12 PASS
consumer CTest registration and execution: 1/1 PASS
dcadec --help packaged CLI smoke test: PASS
repository test suites: 11/11 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libdcadec.so.0.1.0` | 默认共享库，SONAME 为 `libdcadec.so.0` |
| `lib/libdcadec.a` | `shared=False` 变体的静态库 |
| `include/libdcadec/*.h` | 四个公开 C API 头文件 |
| `bin/dcadec` | DTS 解码命令行程序 |
| `lib/pkgconfig/dcadec.pc` | 可重定位 pkg-config 元数据 |

## 注意事项

- 共享库包同时提供常用链接名对应的常规文件，以兼容不支持符号链接的安装文件系统。
- 上游测试固定使用 v0.2.0 指向的样本提交，避免测试数据随分支变化。
- SHA-1 兼容入口只修正工具对 GNU 清单格式的解析，不修改上游测试脚本、样本、预期值或用例数量。
---

**编译结束**: 2026-09-10 03:30
**最终状态**: built
