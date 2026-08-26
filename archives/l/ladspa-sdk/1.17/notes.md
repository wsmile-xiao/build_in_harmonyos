# ladspa-sdk 1.17 适配笔记

## 编译环境
- 构建系统: makefile（上游 `src/Makefile`，未重写）
- 编译日期: 2026-08-25
- 编译器: clang 15.0.4 (OHOS 工具链) / clang++
- 状态: built
- 目标平台: OpenHarmony / HarmonyOS PC aarch64 (armv8)

## 上游信息

- 官方源码: https://www.ladspa.org/download/ladspa_sdk_1.17.tgz
- SHA256: `27d24f279e4b81bd17ecbdcc38e4c42991bb388826c0b200067ce0eb59d3da5b`
  - 与 FreeBSD ports (`audio/ladspa` distinfo)、Solus packages、ix pkgsrc 一致。
- 许可证: LGPL-2.1-or-later（见 `doc/COPYING`）
- 压缩包大小: 71053 字节

## 源码结构

```
ladspa_sdk_1.17/
├── README
├── doc/          # HTML 文档 + COPYING (LGPL-2.1)
├── snd/noise.wav # 示例音频（交互式 demo 用）
└── src/
    ├── Makefile           # 上游构建系统（install/test/targets）
    ├── ladspa.h           # ★ 核心 API 头文件（LADSPA_Descriptor 等全部 ABI）
    ├── gcc_exports.map     # 插件 .so 版本脚本（仅导出 ladspa_descriptor）
    ├── utils.h            # host 侧辅助函数声明（load.c/search.c/default.c）
    ├── load.c / search.c / default.c   # host 工具共享代码
    ├── applyplugin.c / analyseplugin.c / listplugins.c  # 三个 host 工具
    └── plugins/
        ├── amp.c / delay.c / filter.c / noise.c  # 4 个 C 示例插件
        └── sine.cpp                               # 1 个 C++ 示例插件
```

## 真正需要打包的核心内容

1. **`ladspa.h`** — LADSPA 插件 API 头文件，是 SDK 的核心产物。定义
   `LADSPA_Data`、`LADSPA_Properties`、`LADSPA_PortDescriptor`、
   `LADSPA_PortRangeHintDescriptor`、`LADSPA_PortRangeHint`、
   `LADSPA_Descriptor`（含 `UniqueID`/`Label`/`Properties`/`Name`/`Maker`/
   `Copyright`/`PortCount`/`PortDescriptors`/`PortNames`/`PortRangeHints`/
   `ImplementationData` 及 `instantiate`/`connect_port`/`activate`/`run`/
   `run_adding`/`set_run_adding_gain`/`deactivate`/`cleanup` 函数指针），
   以及 `ladspa_descriptor()` 入口点 typedef
   `LADSPA_Descriptor_Function`。
2. **5 个示例插件 `.so`**（amp/delay/filter/noise/sine）— 上游 `install`
   目标确实安装这些插件到 `$(INSTALL_PLUGINS_DIR)`，是 SDK 的参考实现，
   供 host 程序 dlopen 加载，故一并打包到 `lib/ladspa/`。
3. **3 个 host 工具**（analyseplugin/applyplugin/listplugins）— 上游 `install`
   目标确实安装到 `$(INSTALL_BINARY_DIR)`，是 SDK 的实用工具，打包到
   `bin/`。这些工具链接 libsndfile（wave I/O）和 libdl/libm。

> 未把 demo 当核心库：`snd/noise.wav` 与交互式 `test` 目标仅是演示，不打包。

## 上游测试分析

上游**无正式测试套件**。Makefile 的 `test` 目标是一个交互式音频演示：

- 依赖 `/tmp/test.wav`（由 `/tmp/test.wav` recipe 生成）和 `../snd/noise.wav`；
- 调用 `sndfile-play` 播放白噪声和插件输出（需要音频设备）；
- `/tmp/test.wav` recipe 实际运行 `listplugins`、`analyseplugin`、`applyplugin`
  三个工具生成一个 wave 文件，但**没有任何断言**，仅产出文件供人耳试听。

因此：
- 上游测试数: **0**（无断言型测试）
- 实际执行数: **0**（交互式 demo 不可在 CI 运行）
- 通过数: **N/A**

按任务要求，不因上游测试少就虚构"单元测试"；新增的 test_package consumer
检查统一算作**集成测试**（共 18 条断言）。

## 编译步骤

复用上游 `src/Makefile`，通过 make 变量覆盖完成 OHOS 适配，**不打补丁**：

```bash
# 在 src/ 目录
make -j1 install \
  CC=$CC CPP=$CXX \
  CFLAGS="-I. <sndfile-include> -Wall -Werror -O2 -fPIC \
          -Wno-error=unused-command-line-argument \
          -DDEFAULT_LADSPA_PATH=<pkg>/lib/ladspa" \
  CXXFLAGS="<同 CFLAGS>" \
  LIBRARIES="-ldl -lm <sndfile-lib> -lsndfile" \
  INSTALL_PLUGINS_DIR=<stage>/lib/ladspa \
  INSTALL_INCLUDE_DIR=<stage>/include \
  INSTALL_BINARY_DIR=<stage>/bin
```

`install` 依赖 `targets`，故一次 `make install` 即构建全部插件+工具并拷贝到
stage 目录，再由 Conan `package()` 拷入包目录。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 插件编译失败：`-Wl,--code-sign: 'linker' input unused [-Werror,-Wunused-command-line-argument]` | OHOS clang 包装器在编译(`-c`)阶段也注入 `-Wl,--code-sign`、`-fuse-ld=lld`、sysroot `-L` 等链接器参数；上游 `-Werror` 将其升级为致命错误 | CFLAGS/CXXFLAGS 增加 `-Wno-error=unused-command-line-argument`，**仅降级此一条警告**，不修改源码/Makefile |
| 2 | 工具链接失败：`unable to find library -lsndfile` | 三个 host 工具需要 libsndfile（wave 读写） | recipe `requires libsndfile/1.2.2`（已在 ohpcd 制品仓发布 OHOS aarch64 二进制），并通过 `LIBRARIES` 注入其 include/lib 路径 |
| 3 | 安装目录默认 `/usr/...` | 上游 Makefile 硬编码系统目录 | 覆盖 `INSTALL_PLUGINS_DIR`/`INSTALL_INCLUDE_DIR`/`INSTALL_BINARY_DIR` 为 stage 目录 |

> 以上 3 项均通过**编译参数/recipe**解决，未使用任何 patch（符合 R8）。
> 上游 `-ldl` 在 OHOS 工具链可用（musl 提供弱符号 `dlopen`），无需删除。

## 源码修改

无。未应用任何补丁（`patches: []`）。

## 依赖版本

- libsndfile/1.2.2（OHOS aarch64，ohpcd 制品仓，静态链接）
- libdl、libm（系统库，OHOS 自带）
- 无其他外部依赖

## 验证结果

```bash
# conan create（见 task #7 实际输出）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → 5 插件 + 3 工具 + ladspa.h 打包成功

# test_package（见 task #7 实际输出）
# → consumer 构建 test_minplugin.so，dlopen 自建插件与安装的 amp.so，
#   18 条 ABI 断言全部通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| include/ladspa.h | 核心 API 头文件 |
| lib/ladspa/amp.so, delay.so, filter.so, noise.so, sine.so | 5 个示例插件 |
| bin/analyseplugin, applyplugin, listplugins | 3 个 host 工具 |
| licenses/COPYING, licenses/README | 许可证与说明 |

## 注意事项

- LADSPA 插件通过 `dlopen()`/`ladspa_descriptor()` 动态加载，**不链接**为
  库；`cpp_info.libs` 为空，仅声明 `system_libs=["dl"]` 供 host 程序使用。
- `LADSPA_PATH` 环境变量由 `package_info` 注入，指向包内 `lib/ladspa/`，
  便于 host 工具与 consumer 发现插件。
- 本目录为 `archives/l/ladspa-sdk/1.17`（匹配上游 SDK 名称）；仓库已存在的
  `archives/l/ladspa/` 为另一独立归档，不在本次改动范围。

---

**编译结束**: 2026-08-25
**最终状态**: built
