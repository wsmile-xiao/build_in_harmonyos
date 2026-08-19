# abiword-plugin-openwriter

## 简介

abiword-plugin-openwriter 是 AbiWord 文字处理器的 OpenDocument Text (.odt) 读写插件。
AbiWord 是 GNOME 桌面环境的开源文字处理软件，对标 Microsoft Word；.odt 是 OASIS 主导的
OpenDocument 格式国际标准（ISO/IEC 26300）。

本归档通过 conan 配方把 AbiWord 主仓库 `plugins/openwriter/` 子目录单独抽出打包，
适配 HarmonyOS PC（arm64 / Linux-like 行为）。

- **官网**：https://www.abisource.com/
- **源码**：https://gitlab.gnome.org/World/AbiWord（subpath `plugins/openwriter/`）
- **镜像**：https://github.com/AbiWord/abiword
- **许可证**：GPL-2.0-or-later
- **构建系统**：autotools（上游 plugin.m4 + Makefile.am）

## OHOS 适配

- **基础信息**：上游 AbiWord 3.0.8 release-3.0.8（2026-02-18 发布），源码位于 `plugins/openwriter/` 子目录，非独立仓库
- **依赖策略**：通过 conan `requires("libgsf/1.14.53")` 声明强依赖，libgsf 是 openwriter 读/写 .odt zip 容器 + 文档元数据必需
- **辅助依赖**：`requires("glib/2.84.0")`（GObject 类型 gsf_off_t / GsfInput* 显式声明，便于下游 abiword 消费者解析）
- **构建路径**：source-recipe（`conanfile.source()` 抽 `plugins/openwriter/` 子目录到 build root），手动 `make -C xp libxp.la` + `make openwriter.la` 跳过 abiword parent configure
- **OHOS 关键决策**：
  - `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`（绕过 config.guess 不识别 OHOS）
  - `_drop_umask_077_in_place()` 模块化替换 `umask 077 && mktemp -d` 模式（HMDFS E114）
  - OHOS 强制 `make -j1`（HMDFS E074 jobserver fifo EPERM）
  - `package()` 复制 `.deps/` 目录（libtool transitive dep stubs 必需）
  - `tool_requires("automake/1.18") + tool_requires("libtool/2.5.4")`（OHOS HNP image 仅含 autoconf suite）
- **ABI surface 验证**：`test_package/test_openwriter.c` R34 测试覆盖 openwriter 实际调用的 11 个 libgsf symbol
- **真业务依赖**：openwriter 还需要 libabiword 主库（IE_Imp/PD_Document/XAP_Module 等 ~20 个符号），属于 Path B 贡献创新范畴

## 依赖

- `libgsf/1.14.53` — 强依赖（upstream `feat/libgsf-1.14.53` 分支，未合并 main）
- `glib/2.84.0` — GObject 类型强依赖
- (间接通过 libgsf) `libxml2` / `zlib` / `glib`

## 功能验证

```bash
# L0 静态验证（无依赖）
python -c "import ast; ast.parse(open('archives/a/abiword-plugin-openwriter/3.0.8/conanfile.py').read())"

# L1 conan create（依赖 libgsf/1.14.53 合并到 main 后）
conan create archives/a/abiword-plugin-openwriter/3.0.8 \
    -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing

# L2 qemu-aarch64-static（OHOS user-mode）
qemu-aarch64-static -L /usr/aarch64-linux-gnu ./test_openwriter.aarch64
```