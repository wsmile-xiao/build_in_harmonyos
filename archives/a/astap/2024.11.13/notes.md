# astap 2024.11.13 适配笔记

## 编译环境

- 构建系统：custom（Free Pascal Compiler）
- 编译日期：2026-09-04
- 目标平台：HarmonyOS PC arm64（`os=OHOS`，`arch=armv8`）
- 编译器：Free Pascal Compiler 3.2.2 AArch64
- Conan：2.29.1
- 状态：built

## 编译步骤

1. 下载上游 `v2024.11.13` 提交（CanardConfit/ASTAP 镜像 commit `bb22250d`）的 ASTAP 源码并校验 SHA-256。
   （Debian salsa 的 `upstream/2024.11.13` 导入不含 `command-line_version/` 目录，CLI 以 GitHub
   镜像为准。）
2. 下载官方 FPC 3.2.2 AArch64 发行包并仅解压构建所需组件。
3. 为 `ppca64` 和 `fpcres` 添加 HarmonyOS ELF 签名。
4. 在 `command-line_version/` 中直接编译 `astap_command_line.lpr`，避免误选源码根目录的 GUI 单元。
5. 为生成的静态 `astap_cli` 添加 HarmonyOS ELF 签名并安装到 Conan 包的 `bin/`。

核心验证命令：

```bash
conan create archives/a/astap/2024.11.13 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=astap/*

python3 scripts/ohc-run.py conan-verify astap 2024.11.13
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | 初始化工具将项目误判为 Autotools | ASTAP 实际为 Lazarus/Object Pascal 项目 | 使用 custom Conan 构建并直接调用 `ppca64` |
| 2 | 下载的 FPC 工具无法直接执行 | HarmonyOS 要求 ELF 签名 | 构建时使用 `binary-sign-tool` 签名 `ppca64` 和 `fpcres` |
| 3 | 编译缺少 `crc`、`JPEGLib` 等单元 | 官方基础包未包含全部 FCL 图像依赖 | 解压 rtl-objpas、rtl-extra、fcl-base、fcl-image、paszlib、hash、pasjpeg 组件 |
| 4 | 编译器错误引入 `dialogs` | 从源码根目录构建时优先解析到 GUI 版 `unit_tiff.pas` | 将工作目录切换到 `command-line_version/`，使用 CLI 专用单元 |
| 5 | 缺失输入文件返回码为 0 | 上游 CLI 捕获异常并打印错误，但不设置非零退出码 | 消费者测试按真实行为断言两条错误文本 |

## 源码修改

无上游源码补丁。本次适配仅新增 Conan 配方、应用元数据和消费者测试。

## 构建依赖

- 官方 FPC 3.2.2 AArch64 静态发行包（构建时下载并校验）
- FPC 单元：rtl、rtl-objpas、rtl-extra、fcl-base、fcl-image、paszlib、hash、pasjpeg
- HarmonyOS `binary-sign-tool` 与 `llvm-objcopy`

## 验证结果

- `conan create`：通过
- `conan-verify` G1–G4：通过
- 消费者测试：9/9（100%），含真实 FITS 图像分析（`HFD_MEDIAN=3.7`、`STARS=23`）
- W3 本地 CI：通过
- 独立终审：PASS，无 P0/P1
- 产物：64 位 arm64 静态 `astap_cli`，已签名并可运行

## 交付边界

本次仅交付 ASTAP 命令行求解器。GUI 依赖 Lazarus LCL/GTK/Qt，外部星表数据库体积较大，均不纳入 Conan 制品。

## 结束

**编译结束**：2026-08-23  
**最终状态**：built
---

**编译结束**: 2026-08-23 01:57
**最终状态**: built
