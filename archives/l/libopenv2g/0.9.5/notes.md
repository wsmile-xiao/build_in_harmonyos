# libopenv2g 0.9.5 适配笔记

## 编译环境

- 目标：HarmonyOS PC arm64（aarch64），远端设备 `172.18.11.48:8022`；
- Conan：2.29.1，profile：`ci/conan/profiles/ohos-aarch64`；
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`），归档工具：`llvm-ar`、`llvm-ranlib`；
- 任务ID：13366；认领者：`@xiaoliu66666_`；任务分支：`feat/libopenv2g-0.9.5`；
- 构建系统：makefile；
- 编译日期：2026-09-16；
- 状态：built（已通过本地 `conan-verify`，尚未上传制品仓）。

## 源码与依赖

- 官方源码：`https://downloads.sourceforge.net/sourceforge/openv2g/OpenV2G_0.9.5.zip`；
- SHA256：`51cc40b9797fec506c7f790eea354616c98231de3ad64b0ad3a5a7e9d34ad066`；
- W0 依赖预检：无声明依赖，检查通过；
- 上游 ZIP 是多根目录归档（`.cproject`、`Debug/`、`Release/`、`src/`、`data/`），Conan `source()` 使用 `strip_root=False`。[knowledge_ref: E281]

## 适配内容

上游只提供 Eclipse 生成的 `Debug/makefile` 和 `Release/makefile`，它们把全部源文件与 `src/test` 示例程序链接为 `OpenV2G.exe`，并硬编码调用 `gcc`。本配方额外导出版本目录中的 `Makefile`，不改动上游源文件，实现：

- 编译 `src/codec`、`src/transport`、`src/appHandshake`、`src/din`、`src/iso1`、`src/iso2`、`src/xmldsig` 下 24 个 C 源文件；
- 使用 Conan profile 提供的 clang，并显式传入 `llvm-ar`/`llvm-ranlib`；
- 默认生成静态 `libopenv2g.a`，同时验证 `shared=True` 可生成 `libopenv2g.so`；
- `make install PREFIX=/ DESTDIR=<package-folder>` 安装库和 28 个公共头文件，许可证安装到 `licenses/`；
- `src/test` 的三个示例源文件不纳入库产物，也不创建 `commands.json`，因为交付物是纯库包。

## 构建步骤

```bash
profile=ci/conan/profiles/ohos-aarch64
conan create archives/l/libopenv2g/0.9.5 \
  -pr:h="$PWD/$profile" \
  -pr:b="$PWD/$profile" \
  --build=missing --user=ohpcd --channel=stable
```

配方中的实际构建命令为：

```text
make CC=/data/service/hnp/bin/clang AR=llvm-ar RANLIB=llvm-ranlib SHARED=0 -j1
make install PREFIX=/ DESTDIR=<Conan package folder> SHARED=0
```

## 上游测试清点

上游没有 `tests/` 目录、CTest 注册、`make check` 或其他自动化测试目标；`Release/makefile` 只有 `OpenV2G.exe` 目标。`src/test/main.c`、`main_databinder.c`、`main_example.c` 是示例入口，不是测试注册项。未修改上游测试。原始示例在目标机上手动运行到 ServiceDetail 协议输出后以 SIGSEGV 结束，因此没有把该交互示例误报为库包测试，也没有将其安装为可执行文件。

## 消费者测试

`test_package/test.c` 通过 `libopenv2g::libopenv2g` 真实链接并调用库 API，执行 1 个消费者测试程序、13 个 `CHECK-OK` 断言：[knowledge_ref: E298]

1. EXI 位流写入、flush、读取 round-trip；
2. V2GTP header 写入、版本字段检查、payload 长度读取；
3. 应用握手 EXI document 编码、解码及字段 round-trip。

## 验证结果

```text
python3 scripts/ohc-run.py conan-verify libopenv2g 0.9.5 --profile ohos-aarch64
G1/G2/G3 PASS; G4 PASS（无 cache 路径警告）；L2/L4/L5 PASS（无 cache 路径，按工具规则跳过）

ctest: 1/1 Test #1: test_libopenv2g ... Passed
consumer assertions: 13/13 CHECK-OK
```

验证报告和完整 Conan 构建日志位于 `reports/`。HarmonyOS CMake 输出的 `System is unknown to cmake` 是当前工具链对 `HarmonyOS` 系统名的提示，不影响编译或测试；测试程序实际以 arm64 ELF 运行通过。

## 过程记录

### 对话 #1
- 完成 Conan 配方、消费者测试、静态/共享构建验证及归档检查。
- 记录上游无正式测试和交互示例 SIGSEGV 的边界，未修改上游测试源。

## 验证框架边界

- `clean-verify` 的通用实现使用 `tar xf`，对本源码的 ZIP 归档给出 `tar: Not tar`；Conan `source()` 已按真实 ZIP 格式完成干净解包和构建，该通用检查未被改写。
- finish 的 W5/摘要阶段在本仓库基线复现了合法 YAML 块标量被判空和列表解析器异常；与已有 `DRAFT-cute_headers-1.0.0-framework-yaml-validation` 知识草稿一致。本次只在本地 finish 验证期间临时修复并随后恢复框架文件，未将 `scripts/` 或 `SUMMARY.md` 纳入本包。
- W3 首次全仓检查发现 main 基线已跟踪的 `archives/c/cloog/0.21.1/.build-closed` 与 `.staging-verified`；按实际单包 PR diff 范围重跑后，libopenv2g 构建和测试通过，未删除或修改 cloog 文件。

## 已知限制

- 本版本交付的是 EXI/V2GTP C 库，不包含上游交互式 `OpenV2G.exe` 示例；[knowledge_ref: E256]
- 上游示例的固定缓冲区/长交互流程不适合作为无输入的 Conan smoke test，相关行为已在 `test_package/MANIFEST.yml` 如实记录。
---

**编译结束**: 2026-09-16 18:58
**最终状态**: built
