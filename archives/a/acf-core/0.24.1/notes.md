# acf-core 0.24.1 适配笔记

## 1. 软件概要
- Alpine Configuration Framework（ACF）核心，Lua 5.4 Web 管理框架。
- 纯 Lua 项目：递归 Makefile（app/bin/lib/lua/www 五个子目录），无 C 编译，
  `make all` 为空操作，`make install DESTDIR=...` 仅复制文件。
- 上游官方源（aports APKBUILD 同款）：
  `https://gitlab.alpinelinux.org/acf/acf-core/-/archive/v0.24.1/acf-core-v0.24.1.tar.gz`
  sha256 `dbaec1253444702e5744016b61862c727e99efe012320fdbcac2067d450174bf`

## 2. 编译说明
- 无 configure 脚本；config.mk 硬编码 `prefix=/usr`、`luadir=share/lua/5.4/acf`（已是 5.4，无需 sed）。
- `make -j1`（递归 all，各子目录独立，均无实际编译）。
- `make install DESTDIR=<pkg>` 安装到 `usr/bin`、`usr/share/lua/5.4/acf`、
  `usr/share/acf/{app,lib,www}`、`etc/acf/acf.conf`、`etc/logrotate.d/acf`。
- **平台补丁（0001-bin-Makefile.patch）**：OHOS 无 coreutils `install` 命令（`install -Dm755` → rc127），
  将 bin/Makefile 的 `install -Dm755` 替换为 `cp` + `chmod 755`。

## 3. 外部 Lua 模块依赖分析（R18 流程）
acf-core 运行时 require 的外部模块及判定：

| 模块 | 加载位置 | 必需性 | 制品仓/cmd-pkgs 可用性 | 处理 |
|------|----------|--------|------------------------|------|
| `posix` | lua/mvc.lua L9（顶层）、lib/session.lua 等 | **运行时必需**（require acf.mvc 即触发） | ohpcd 有 luaposix/36.3 但要求 lua/5.5.0（本包为 lua 5.4，不兼容）；cmd-pkgs 无 | 需单独适配 lua5.4 版 luaposix 配方（后续 PR），测试期用纯 Lua 支撑 |
| `subprocess` | lua/mvc.lua L10（顶层）、lib/modelfunctions.lua | **运行时必需**（require acf.mvc 即触发） | 制品仓无配方；cmd-pkgs 无 | 需单独适配 lua-subprocess（后续 PR），测试期用 io.popen 支撑 |
| `md5` | lib/authenticator.lua（认证路径） | 必需（认证功能） | 制品仓无配方；cmd-pkgs 无 | 需单独适配 lua-md5（后续 PR），测试期用纯 Lua MD5（RFC1321，测试向量全过） |
| `acf.format/fs/html/processinfo` | lua/mvc.lua L11、lib/*.lua | 必需 | 来自 acf-lib 包（Alpine 未适配） | 后续 PR；测试期用 acf-lib 官方源码模块 |
| `json` | lua/mvc.lua L354（json viewtype） | 需要时 | 来自 lua-json4（未适配） | 后续 PR；测试期用纯 Lua JSON |

**结论**：上述模块均为 acf-core 运行时依赖，但属于独立第三方 Lua 包，
按 W2 原子性（每 PR 一个配方）应各自单独适配发布。本次 acf-core PR 的
conanfile requirements() 只声明已发布的 `lua/5.4.8`（R36：依赖先发布再构建下游）。
test_package 内提供纯 Lua 测试支撑（标为 TEST-HARNESS ONLY，不随包发布），
用于实质验证 acf-core 框架逻辑。

## 4. 上游测试
- 上游**无测试套件**：aports acf-core APKBUILD `options="!check" # no test suite`；
  源码 tarball 无 test/ 目录，无 `make check`/`make test` 目标。
- 验证采用自建功能测试（详见 reports/test-report.md）：框架加载 + welcome/read dispatch、
  全部 Lua 文件语法检查、acfpasswd 行为、MD5 测试向量等。

## 5. 运行约束
- acf-cli 脚本内 `read_config("acf")` 读 `/etc/acf/acf.conf`；OHOS /etc 只读（/system/etc），
  无法放置配置 → 二进制无法端到端 dispatch。等效逻辑由测试脚本（home 目录配置）完整覆盖。
- `acfpasswd` 依赖 `mkpasswd`/`awk`/`sed`/`grep`（系统工具），可离线验证 usage/错误分支。

## 6. 状态
- 编译：成功；功能测试：全部通过（40/40）；conan-verify：见 reports/conan-verify-report.md。
---

**编译结束**: 2026-08-06 17:01
**最终状态**: built
