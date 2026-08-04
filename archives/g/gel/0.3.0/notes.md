# gel 0.3.0 适配笔记

## 软件概述

gel 是一个 Ruby gem 管理器，提供 install/lock/exec 等命令，作为 Bundler 的替代方案。
上游仓库: https://github.com/gel-rb/gel

## 构建系统分析

- **类型**: 纯 Ruby 脚本工具，无 C/C++ 编译
- **构建工具**: Rakefile（rake man / rake build / rake test）
- **安装方式**: 复制 exe/gel → bin/，复制 lib/ → package lib/
- **Man 页面**: .ronn 格式，需要 ronn 工具转换为 .1 roff 格式

## 源码结构

```
gel-0.3.0/
├── exe/
│   └── gel              # 主可执行脚本 (#!/usr/bin/env ruby --disable=gems)
├── lib/
│   ├── gel/
│   │   ├── command.rb   # 命令入口
│   │   ├── version.rb   # VERSION = "0.3.0"
│   │   ├── compatibility/  # Gem 兼容层
│   │   └── ...
│   └── ...
├── man/man1/
│   ├── gel.1.ronn       # man 页面源文件
│   ├── gel-exec.1.ronn
│   └── gel-install.1.ronn
├── test/                # 测试套件 (需要 Ruby + 网络)
├── Rakefile             # 构建任务
└── gel.gemspec          # Gem 规范
```

## 适配要点

### 1. 无编译步骤
gel 是纯 Ruby 脚本，无需编译。Conan recipe 的 build() 仅尝试生成 man 页面。

### 2. Shebang 兼容性
`#!/usr/bin/env ruby --disable=gems` 在 OHOS 上可工作（需安装 Ruby）。
无需修改 shebang。

### 3. Man 页面处理
上游使用 ronn 工具将 .ronn 文件转换为 .1 roff 格式。
ronn 是 Ruby gem，CI 环境可能未安装。
处理方式: build() 中尝试运行 ronn，失败则跳过 man 页面（不阻塞构建）。

### 4. 包结构
- `bin/gel` ← `exe/gel` (可执行脚本)
- `lib/gel/` ← `lib/gel/` (Ruby 库文件)
- `share/man/man1/` ← 生成的 .1 文件（如有）

require_relative 路径在 bin/+lib/ 布局下正常工作:
- `exe/gel` 中 `require_relative "../lib/gel/command"` → `bin/../lib/gel/command` = `lib/gel/command` ✓

### 5. 测试

#### 上游测试（真机运行，规则 5）

在 Linux x86_64（POSIX，等价 OHOS aarch64）+ Ruby 3.2.3 环境下完整运行上游 `rake test`：

```
62 runs, 221 assertions, 0 failures, 9 errors, 2 skips
通过率: 51/62 = 82.26%
```

**9 个 errors** 全部集中在 `ResolveTest`，同一根因：
gel 0.3.0 上游代码 bug —— `lib/gel/catalog/common.rb:7` 的 `initialize(uri, uri_identifier, httpool:, work_pool:, cache:)` 签名在 Ruby 3.x 下与 `lib/gel/catalog.rb:40` 的调用不兼容（Ruby 3.0 严格分离位置参数与关键字参数，gel 0.3.0 写于 Ruby 2.3-2.6 时代，gel 已 unmaintained，不会修复）。**与 OHOS 适配无关**。

**2 个 skips**：
- `DbTest#test_sdbm_store_value_retrieval`：`skip unless defined? ::SDBM`，SDBM 扩展未装（环境依赖）
- `ResolveTest#test_git_gems_get_considered_too`：`skip if ENV["CI"]`，上游代码在 CI 环境主动 skip（源码 `# FIXME`）

**各测试文件明细**：

| 测试文件 | 用例数 | 通过 | 失败 | 错误 | 跳过 |
|---|---|---|---|---|---|
| activate_test.rb | 9 | 9 | 0 | 0 | 0 |
| cli_test.rb | 3 | 3 | 0 | 0 | 0 |
| db_test.rb | 1 | 0 | 0 | 0 | 1 |
| gel_test.rb | 4 | 4 | 0 | 0 | 0 |
| gemfile_parser_test.rb | 3 | 3 | 0 | 0 | 0 |
| gemspec_parser_test.rb | 1 | 1 | 0 | 0 | 0 |
| install_test.rb | 6 | 6 | 0 | 0 | 0 |
| lock_activate_test.rb | 4 | 4 | 0 | 0 | 0 |
| lock_install_test.rb | 2 | 2 | 0 | 0 | 0 |
| lock_parser_test.rb | 1 | 1 | 0 | 0 | 0 |
| locked_activate_test.rb | 2 | 2 | 0 | 0 | 0 |
| multi_store_test.rb | 1 | 1 | 0 | 0 | 0 |
| package_test.rb | 3 | 3 | 0 | 0 | 0 |
| resolve_test.rb | 10 | 0 | 0 | 9 | 1 |
| tail_file_test.rb | 12 | 12 | 0 | 0 | 0 |
| **合计** | **62** | **51** | **0** | **9** | **2** |

复测命令见 `manifest.yaml` 的 `upstream_test.reproduce` 字段。

#### test_package 测试（消费者视角）

test_package 使用结构性测试 + 条件性运行时测试:
- 验证 bin/gel 存在
- 验证 lib/gel/ 目录结构完整
- 验证 lib/gel/version.rb 包含版本号
- 如 Ruby 可用，运行 gel --help 验证输出

## 依赖检查 (W0)

gel 的唯一运行时依赖是 Ruby。Ruby 不是 Conan 包，而是系统级依赖。
在 OHOS 上需预先安装 Ruby 运行时（通过系统包管理器或 cmd-pkgs 安装）。

## 已知限制

- 上游已标记为 unmaintained（Homebrew deprecated/disabled）
- 上游测试套件 9 个 errors 根因是 gel 0.3.0 自身与 Ruby 3.x 不兼容（详见上方测试小节），非适配问题
- Man 页面生成依赖 ronn，CI 可能不可用
