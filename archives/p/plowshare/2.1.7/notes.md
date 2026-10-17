# plowshare 2.1.7 适配笔记

## 编译环境
- 构建系统: custom（纯 Bash 脚本，无编译步骤；上游 Makefile 仅负责 install/打包）
- 编译日期: 2026-09-04
- 编译器: N/A
- 状态: built

## 编译/打包步骤
1. 下载上游源码包 `plowshare-2.1.7.tar.gz`（codeload GitHub tag v2.1.7）。
2. 校验 SHA256: `c17d0cc1b3323f72b2c1a5b183a9fcef04e8bfc53c9679a4e1523642310d22ad`。
3. build 阶段：`bash -n` 语法检查 7 个脚本（core.sh + 6 个 CLI），并将
   `declare -r VERSION='GIT-snapshot'` 替换为 `declare -r VERSION='2.1.7'` 注入版本。
4. package 阶段：flat 复制到 `bin/`（core.sh + plowdown/plowup/plowdel/plowlist/plowprobe/plowmod），
   同时安装 man 页、`share/plowshare/modules/config` 占位与 COPYING license。
5. test_package：逐一验证 6 个 CLI 存在、可执行、`bash -n` 通过、`--version` 输出 `2.1.7`、
   `--help` 输出 Usage。
6. requirements() 内对 `openssl/3.5.6.1.1` 使用 `override=True`，强制整条传递依赖链
   （curl → openssl）锁定到 CI 环境已编译通过的版本（R37 适配修复版，conan-verify + W3 通过）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 `make check` 或测试目录 | plowshare 是纯 Bash 脚本套件 | build 阶段做 Bash 语法检查与版本注入校验；test_package 真实执行安装后的 6 个 CLI 的 `--version`/`--help` |
| 2 | 上游 Makefile 在 `bin/` 创建 6 个符号链接 | HarmonyOS HMDFS/hmmac 对 symlink() 受限 | 不调用上游 Makefile，直接 flat 复制脚本到 `bin/`（脚本通过 `$(dirname $0)/core.sh` 定位 core.sh，同目录即可） |
| 3 | 上游 `patch_git_version` 需要 GNU sed 且依赖 git describe | OHOS toybox sed 能力受限；release tarball 无 .git | 配方内用 Python 直接替换 `declare -r VERSION='GIT-snapshot'` |
| 4 | 版本号未知（GIT-snapshot） | 上游未发布含版本的 tarball，需在安装期注入 | `_inject_version()` 将 6 个 CLI 的 VERSION 声明替换为 `2.1.7`，`--version` 输出可断言 |
| 5 | `conan create` 提示 `settings.os.version` 未定义 | 本地 OHOS profile 未设置 `os.version`，纯脚本包无需区分 OS 子版本 | 在 recipe 的 `configure()` 中 `rm_safe("os.version")`（同 prettyping） |
| 6 | codeload URL 解压格式误判 | 官方 codeload URL 末尾无 `.tar.gz` 后缀，Conan 可能按 zip 误判 | 在 `conandata.yml` 固定 `filename: plowshare-2.1.7.tar.gz`，保留官方 URL 与 sha256 |
| 7 | 运行时 bash 不在标准路径 | OHOS 无 `/bin/bash`，bash 位于 `/data/service/hnp/bin/bash` | bash 作为系统工具处理（不声明 Conan 依赖，同 prettyping 先例）：`_bash()` 探测 CONFIG_SHELL / `/data/service/hnp/bin/bash`，test_package 通过系统 bash + PATH 注入执行 |
| 8 | 真实下载/上传功能不可测 | 上游 2.1.7 起模块拆出到 `plowshare-modules-legacy`，核心包不含任何 host 模块 | 不伪造测试结果：仅验证 CLI 框架与 plowmod 管理机制；完整功能需联网 `plowmod --install` 后验证（见"阻塞项"） |
| 9 | curl 传递依赖链 openssl 版本在 CI 不保证可编译 | curl/8.15.0 依赖 openssl，上游传递链解析版本不稳 | `requirements()` 内 `self.requires("openssl/3.5.6.1.1", override=True)`，强制整条依赖链锁定到 R37 适配修复版（conan-verify + W3 通过） |

## 依赖版本
- 编译依赖: 无
- Conan 依赖: curl/8.15.0（built）；openssl/3.5.6.1.1（override=True，锁定传递链）
- 系统运行时: bash（PATH，如 /data/service/hnp/bin/bash）、curl、sed、grep、coreutils（GNU）；recode/perl+HTML::Entities、JS 解释器为可选

## 测试质量说明
- 上游测试: 无官方测试套件（无 test 目录、无 make check）。以 Bash 语法检查 + 版本/help 输出断言覆盖。
- 消费者测试: 真实执行安装后的 6 个 CLI，校验存在性、可执行位、`--version`=2.1.7、`--help` Usage 输出。
- 断言数: 约 30（6 CLI × 存在/可执行/语法/版本/帮助 五类）。

## 阻塞项 / 已知限制
1. **上游模块缺失（架构事实，非本配方缺陷）**：2.1.7 核心包不含任何网盘 host 模块，
   所有模块在独立仓库 `mcrapet/plowshare-modules-legacy`。离线/CI 非交互环境下
   `plowdown/plowup/plowdel/plowlist/plowprobe` 的真实网盘操作**无法验证**。
   本包交付的是完整可运行的 6 CLI + plowmod 模块管理框架。
2. 可选运行时依赖 recode 无 Conan 配方（仅影响部分站点的文件名编码转换，已声明为可选，
   不伪造为必需依赖）。
3. 若要完整功能验证，需额外在目标设备联网执行：
   `plowmod --install`（拉取模块仓库）后对真实网盘 URL 做一次 `plowprobe`/`plowdown`。

## 注意事项
1. 本包为纯脚本工具包，无静态/动态库，`cpp_info.libs = []`，无需 ELF 签名。
2. `settings` 为 `os`、`arch`、`compiler`、`build_type` 四项（PF8 配方静态闸要求），
   `configure()` 中 `rm_safe("os.version")`。
3. 软件级 `commands.json` 已创建，满足工具包 R38/L0k 要求。
4. 上游脚本已使用 `#!/usr/bin/env bash`，无需 shebang 补丁；运行时由 bash/5.3 依赖提供解释器。
5. 上游停滞维护（最后 commit 2021-06），后续版本无官方发行，本包锁 2.1.7。