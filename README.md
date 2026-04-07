# build_in_harmonyos

> 鸿蒙系统开源软件编译知识库与预编译包发布平台

## 一句话

**让任何开源软件在 HarmonyOS PC 上可编译、可安装、可运行。**

## 项目定位

```
源码编译 → 知识沉淀 → 预编译包 → 一键安装
```

| 维度 | 说明 |
|------|------|
| **知识库** | 29 篇文档覆盖环境特性、构建系统、错误模式（67+ 条）、打包规范 |
| **编译档案** | 30 款软件、33 个版本的完整记录，含补丁、配置和测试报告 |
| **预编译包** | 已发布 sed 4.9、pkg-config 0.29.2，持续增加中 |
| **AI 工作流** | SKILL.md v4.0 定义五步走编译流程，可复现、可分发 |

## 快速使用

### 安装预编译包

```bash
# sed
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/sed/install.sh | sh -s -- 4.9

# pkg-config
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkg-config/install.sh | sh -s -- 0.29.2
```

### 从源码编译新软件

详见 [SKILL.md](SKILL.md)（AI 编译智能体技能定义，v4.0）。

## 编译成果

### 已发布预编译包

| 软件 | 版本 | 大小 | 状态 |
|------|------|------|------|
| sed | 4.9 | 410K (release) + 50K (debug) | ✅ 完全可用 |
| pkg-config | 0.29.2 | 687K (release) + 88K (debug) | ✅ 完全可用 |

> 更多预编译包制作中，见 [PREBUILD_TODOLIST.md](PREBUILD_TODOLIST.md)

### 历史编译档案（30 款 / 33 版本）

| 状态 | 数量 | 代表软件 |
|------|------|----------|
| ✅ 完全成功 | 23 | bash, gawk, openssl, ncurses, jq, file, ... |
| ⚠️ 部分成功 | 8（含 🧪 已测试 1 款，详见 SUMMARY.md） | coreutils, htop, patch, wget, rsync, strace, ... |
| ❌ 失败 | 0 | — |

完整兼容性总览见 [SUMMARY.md](SUMMARY.md)。

## 知识库

### 核心文档（必读）

| 文档 | 内容 |
|------|------|
| [SKILL.md](SKILL.md) | AI 编译流程定义（五步走 + 十条铁律）v4.0 |
| [KNOW_YOUR_WHY.md](KNOW_YOUR_WHY.md) | 核心目的、约束分级、知识分层原则 |
| [packaging.md](knowledge/packaging.md) | 可移植打包指南 v2.3（10步流程+扁平结构） |
| [error-patterns.md](knowledge/error-patterns.md) | 错误模式库 E001-E067+ |
| [environment.md](knowledge/environment.md) | 环境变量、工具链、系统限制 |
| [harmonyos-specifics.md](knowledge/harmonyos-specifics.md) | ELF签名、SELinux、软链接限制 |

### 专题文档

| 文档 | 内容 |
|------|------|
| [build-systems.md](knowledge/build-systems.md) | Autotools/CMake/Custom-Perl 适配策略 |
| [dependencies.md](knowledge/dependencies.md) | 编译依赖关系与推荐顺序 |
| [autotools-patterns.md](knowledge/autotools-patterns.md) | Autotools 通用适配模式 |
| [musl-compat.md](knowledge/musl-compat.md) | musl vs glibc 兼容方案 |
| [best-practices.md](knowledge/best-practices.md) | 编译最佳实践 |
| [troubleshooting.md](knowledge/troubleshooting.md) | 问题排查指南 |
| [FAQ.md](knowledge/FAQ.md) | 常见问题解答 |

### 深度分析

| 文档 | 内容 |
|------|------|
| [filesystem-analysis.md](knowledge/filesystem-analysis.md) | HMFS/HMDFS/EROFS 架构分析 |
| [python-extensions.md](knowledge/python-extensions.md) | Python C 扩展模块编译方法 |
| [ptrace-alternatives.md](knowledge/ptrace-alternatives.md) | ptrace 替代调试方案 |

## 项目结构

```
build_in_harmonyos/
├── SKILL.md                     # AI 编译流程定义（v4.0）
├── KNOW_YOUR_WHY.md             # 核心目的与约束
├── PREBUILD_TODOLIST.md         # 预编译进度跟踪
├── SUMMARY.md                   # 兼容性总览（自动生成）
│
├── knowledge/                   # 知识库（29 篇）
│   ├── packaging.md             # 打包规范
│   ├── error-patterns.md        # 错误模式库
│   └── ...                      # 27 篇更多文档
│
├── scripts/                     # 辅助脚本
│   ├── init-build.sh            # Step 1: 编译初始化
│   ├── finish-build.sh          # Step 3: 收尾管线（4步）
│   ├── refresh-patch.sh         # 补丁生成
│   ├── verify-build.sh          # 质量门禁（G1-G4）
│   ├── finalize-archive.sh      # 归档收口（5阶段）
│   ├── init-archive.sh          # 归档骨架创建
│   └── install-template.sh      # install.sh 模板（33行）
│
├── archives/                    # 编译档案（双层结构）
│   ├── s/sed/                   # 软件级
│   │   ├── README.md            # 编译说明
│   │   ├── RELEASENOTE.md       # 发布说明
│   │   ├── install.sh           # 安装脚本
│   │   └── 4.9/                 # 版本级
│   │       ├── manifest.yaml    # 元数据
│   │       ├── PROGRESS.md      # 进展记录
│   │       ├── patches/         # 补丁
│   │       ├── reports/         # 报告
│   │       └── packaging/       # 预编译包 tar.gz
│   └── p/pkg-config/           # 同上结构
│
└── .opendesk/                   # AI 智能体配置
```

## 目标平台

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS (OpenHarmony) |
| 架构 | aarch64 |
| C 库 | musl libc |
| 编译器 | Clang 15.0.4 (LLVM) |
| Shell | toybox ash (HiShell) |
| 终端 | DevBox (VS Code Remote SSH) |

## 鸿蒙 vs Linux 关键差异

| 差异点 | Linux | HarmonyOS | 影响 |
|--------|-------|-----------|------|
| C 库 | glibc | musl libc | iconv、FILE 结构差异 |
| Shell | bash | toybox ash | 无数组、无 `${BASH_SOURCE}` |
| /tmp | 可写 | **只读** | 必须用 `$HOME/tmp` |
| SELinux | 通常禁用 | **强制启用** | 软链接/子进程/ptrace 受限 |
| ELF 执行 | 无需签名 | **adhoc 签名** | 改 ELF 后必须重签名 |
| 并行构建 | `make -jN` | **`make -j1`** | FIFO 被 SELinux 限制 |

## 发布渠道

预编译包发布于 gitcode releases：

```
https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases
```

URL 格式：`cmd-pkgs/{name}/{name}-{ver}-ohos-aarch64.tar.gz`

## 相关项目

| 项目 | 说明 |
|------|------|
| [ohos-python-release](https://gitcode.com/OpenHarmonyPCDeveloper/ohos-python-release) | Python 预编译包 |

## 许可证

MIT License

Copyright (c) 2024-2026 OpenHarmony PC Developer 社区
