# wdq2wav 1.0.0 知识提炼证据

## 提取基线

| 字段 | 值 |
|---|---|
| 模式 | upgrade |
| 来源 PR | [#3798](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/3798) |
| PR 状态 | open |
| 原标题 | `【知识库扩展】feat(wdq2wav): 1.0.0 编译适配` |
| 原分支 | `feat/wdq2wav-1.0.0` -> `main` |
| 原 HEAD / validated_commit | `861e7b226bd6f43386f10b3fe29ee95d5f49f58a` |
| 上游源码 | `wdq2wav_1.0.0+dfsg.orig.tar.xz` |
| 上游 SHA256 | `6c99ee94e8e697f2cf41188c952f7ab90cba2d7deb04fd7dad24918fa9f0139d` |
| 原验证 | CI #24853；Conan test_package、L0、L1 通过；L2 非阻塞 skip |
| 审查 | 2026-08-14 AI 审查“未发现问题” |

PR 共包含 4 个提交：`27d8b57`（配方适配）、`cedca76`（消费者测试）、`be30022`（帮助断言修正）、`861e7b2`（真机验证记录）。本报告只提炼已有真实实现和验证，不重写历史。

## 原 PR 知识提取表

| 原 PR 事实与位置 | 可复用的知识命题 | 已有证据 | 还缺什么 | 最小补充动作 |
|---|---|---|---|---|
| L2 固定探测 `--help/--version` 后记录 skip；`notes.md` | 通用长选项探针失败不等于二进制或功能失败 | CI #24853；L0/L1/test_package 同次通过 | 上游真实接口 | 核对固定源码的 getopt 选项表和 man page |
| `test_package/test.cpp` 执行 `wdq2wav -h` | 应以安装产物实际支持的选项验证 CLI 契约 | 目标环境输出 `wdq2wav CLI help test: OK` | 转换功能 fixture | 收窄为帮助入口验证，不宣称转换通过 |
| Makefile 将硬编码 `g++` 和 root-owned `install` 改为变量及非特权 staging | 手写 Makefile 的编译器/安装边界可复用 | 补丁、成功构建 | 无 | 与既有 Makefile 草稿去重，留作应用案例 |

## 候选与去重

| 候选 | 触发前提 | 根因 | 修复机制 | 复验方式 | 最相近材料与实际增量 | 去向 |
|---|---|---|---|---|---|---|
| 通用长选项探针与上游短选项契约不匹配 | 上游只注册短选项；L2 尝试 GNU 长选项 | 探针假设超出上游接口 | 在消费者测试中运行受支持的 `-h`，将长选项记录为能力 skip | 检查退出码、usage 和参数占位文本 | E570 已覆盖补 `getopt_long`；本次新增“不要求长选项时不应为探针扩大接口”的选择边界 | 补充 E570 |
| raw Makefile 工具链与非特权安装 | Makefile 硬编码 g++、root owner/group | 交叉工具链与非 root 打包环境不满足宿主假设 | 使用 CXX/flags/DESTDIR 等变量 | Conan 单包构建及产物检查 | 命中 `DRAFT-ohos-makefile-explicit-toolchain-and-install-vars` 等已有材料，无独立增量 | 案例 |

检索范围：`knowledge/drafts/**`、`knowledge/graph/**`。关键词：`--help`、`--version`、`short option`、`短选项`、`L2 冒烟`、`install -o root`、`hardcoded g++`、`Makefile toolchain`。已实际阅读 E570 与 `DRAFT-ohos-makefile-explicit-toolchain-and-install-vars`。

## 一次性事实记录

### 上游库存与接口

2026-09-16 下载 PR 固定的 Debian tarball，SHA256 与 `conandata.yml` 一致。归档只含以下 5 个文件，不含测试目录、测试文件或 `check/test` 入口：

```text
Makefile
wdq2wav.1
wdq2wav.h
wdq2wav.html
wdq2wav.cpp
```

`wdq2wav.cpp` 使用：

```cpp
while ((c = getopt(argc, argv, "rqvzmndph")) != -1) {
    // case 'h': usage(progname); return 0;
}
```

man page 仅声明 `-h` 展示选项摘要、`-r` 展示版本，没有声明 `--help` 或 `--version`。

### 测试统计

| 层次 | 单位 | 库存 | 通过 | 失败 | 跳过 | 未执行 | 依据 |
|---|---|---:|---:|---:|---:|---:|---|
| 上游源码包 | 用例 | 0 | 0 | 0 | 0 | 0 | 固定 tarball 文件库存 |
| 已安装包消费者 | 测试程序 | 1 | 1 | 0 | 0 | 0 | CI #24853；`test_package/test.cpp` |
| 消费者内部 | 声明断言 | 4 | 4 | 0 | 0 | 0 | `test_package/MANIFEST.yml` |
| 通用 L2 | 探针 | 1 | 0 | 0 | 1 | 0 | `notes.md` 的 `L2_RESULT=skip` |

消费者 smoke 只覆盖 CLI 启动和帮助文本，未覆盖 WinDAQ 解析、WAV 输出、音频播放或交互输入。

### 验证记录

| 证据 | 类型 | 命令/入口 | 结果 | 绑定 |
|---|---|---|---|---|
| EVID-01 | static | SHA256 校验、tar 清单、源码/手册检索 | 哈希匹配；确认短选项契约与 0 个上游测试 | 上游 SHA256 `6c99...139d` |
| EVID-02 | target-executed | `test_package` -> `test_wdq2wav` -> `wdq2wav -h` | 通过；`wdq2wav CLI help test: OK` | `861e7b2`，CI #24853 |
| EVID-03 | historical | PR `/rebuild` | Conan test_package、L0、L1 通过；全部步骤成功 | CI #24853，PR HEAD 自验证后未改变 |
| EVID-04 | static | 知识检索与相似材料阅读 | 命中 E570 与 Makefile 既有草稿 | 2026-09-16 当前仓库 |

## 被验证文件与 blob

以下实现、补丁和测试文件来自 validated_commit `861e7b226bd6f43386f10b3fe29ee95d5f49f58a`；本次修订另外新增软件级 CLI 元数据和知识文档，不改变这些已验证输入。

| 路径 | Git blob |
|---|---|
| `archives/w/wdq2wav/1.0.0/conandata.yml` | `bc997c690a78f5301a01349a8d7c3361740355e1` |
| `archives/w/wdq2wav/1.0.0/conanfile.py` | `b147cb4ee9e66413f1209179f3d07da83a03f50e` |
| `archives/w/wdq2wav/1.0.0/manifest.yaml` | `d515a8bce6025d2688fe57672f3c5f6b59f5bc9e` |
| `archives/w/wdq2wav/1.0.0/notes.md` | `2b65d98a70c22e77b230cdd621df5837682f60e4` |
| `archives/w/wdq2wav/1.0.0/patches/0001-Makefile-use-toolchain-and-portable-install.patch` | `6c80d3606d218ee2d6f08692d8eee273ba6865dd` |
| `archives/w/wdq2wav/1.0.0/test_package/CMakeLists.txt` | `d9829e3af510ce7ea5115a3d42d3dba43f65a580` |
| `archives/w/wdq2wav/1.0.0/test_package/MANIFEST.yml` | `75427aa451b847ead001527432405fc968f3f096` |
| `archives/w/wdq2wav/1.0.0/test_package/conanfile.py` | `78537d3b2a3c9d6b047f93146281aa978fbd7fa3` |
| `archives/w/wdq2wav/1.0.0/test_package/test.cpp` | `670811a2b8393175c51f26157b94c252ea052f92` |

## P4 检查记录

| 检查 | 结果 |
|---|---|
| 内容与增量 | 通过：定位为 E570 补充，不重复申报 Makefile 模式 |
| 升级有效性 | 通过：完成提取表、成对草稿和证据报告 |
| 文件发现 | 通过：当前主线 `draft-review` 发现 1 份本任务草稿，`empty_drafts: 0` |
| 解析一致 | 通过：JSON 中 `has_signature`、`has_root_cause`、`has_rec` 均为 true |
| 引用与身份 | 通过：PR、提交、源码哈希、路径一致 |
| 证据与统计 | 通过：目标实跑、静态和历史证据分级；0/0 不写通过率 |
| 范围 | 本次修订新增 `archives/w/wdq2wav/commands.json`、知识 KV、知识 MD 和证据报告；未改动已验证实现 |
| 仓库检查 | 草稿预审通过；待运行本次暂存区 `git diff --check` 和提交范围检查 |

预审的正式图谱相似度结果为 `create`，最高分 0.16；该扫描未将 `knowledge/drafts/E570-draft-272F.*` 纳入正式图谱候选。人工去重已阅读 E570，因此采用更保守的“补充 E570”建议，不用自动建议覆盖实际材料比较。

## 结论边界

本次可申报的是“通用长选项探针与上游短选项契约之间的选择边界”，建议补充 E570。Makefile 修改是既有模式的应用案例，不计作新知识。CI 通过只能证明当前配方、打包和 `-h` 消费者 smoke；真实转换功能仍未验证。
