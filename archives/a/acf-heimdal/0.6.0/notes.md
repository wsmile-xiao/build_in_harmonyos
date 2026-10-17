# acf-heimdal 0.6.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-19
- 编译器: clang/clang++
- 状态: built（本机前置验证完成，真机/shadow CI 待跑）

## 编译步骤

纯 Lua ACF 模块，无 C 编译。上游 Makefile 包含：
1. `make -C <src> -j1 all` — `all:` 为空操作，仅校验 Makefile 语法
2. `make -C <src> install DESTDIR=<pkg>` — `mkdir -p` + `cp -a heimdal*`，简单可用（不引用 acflibdir，与 acf-mariadb 不同）
3. Recipe 在 `package()` 中把 `usr/` 前缀规范化为 Conan 标准布局，并把两个悬空 symlink 物化为从 acf-core 复制的常规文件

## 源码分析

acf-heimdal 是 Alpine Configuration Framework 的 Heimdal Kerberos 管理界面模块，纯 Lua 实现：

| 文件 | 类型 | 说明 |
|------|------|------|
| heimdal-controller.lua | Lua | 分发控制器（status/expert/klist/kinit/kdestroy 五个动作） |
| heimdal-model.lua | Lua | 配置模型：读/写 /etc/krb5.conf，调用 kinit/klist/kdestroy |
| heimdal.menu / heimdal.roles | 文本 | ACF 菜单与角色定义 |
| heimdal-klist-html.lsp | 视图 | 票据列表视图（真实文件） |
| heimdal-expert-html.lsp | symlink | -> ../expert-html.lsp（acf-core 共享视图，悬空） |
| heimdal-status-html.lsp | symlink | -> ../status-html.lsp（acf-core 共享视图，悬空） |

## 依赖分析

`heimdal-model.lua` 的 require：
- `modelfunctions` → acf-core（getstatus/getfiledetails/setfiledetails/run_executable）
- `acf.fs` → acf-lib-lua5.4（fs.write_file 写 kinit 密码临时文件）

`heimdal-klist-html.lsp` 的 require：
- `htmlviewfunctions` → acf-core
- `acf.html` → acf-lib-lua5.4（html.html_escape）

共享视图模板（expert-html.lsp / status-html.lsp）→ acf-core 的 share/acf/app/

因此 recipe 声明两个依赖：
- `acf-core/0.24.1`（框架 + modelfunctions/htmlviewfunctions/cfe + 共享视图）
- `acf-lib-lua5.4/0.11.1`（acf.fs/acf.html）

> 注：acf.fs / acf.html 属于 acf-lib-lua5.4 而非 acf-core（acf-core 只提供 mvc.lua/modelfunctions 等框架脚本与 acf/lib 下的模块）。这比 acf-mariadb 只声明 acf-core 更完整——acf-mariadb 的模型 require("acf.db") 其实也依赖 acf-lib，但其 test_package 未做运行时 require 校验所以未暴露。

运行时还需 heimdal 客户端二进制（kinit/klist/kdestroy），由 `modelfunctions.run_executable` 通过 PATH 调用，属于运行环境依赖（对应 archives/h/heimdal/7.8.0），不在本模块的 Conan 依赖中声明（与 acf-mariadb 不声明 mariadb 服务端同理）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tarball 含两个悬空相对 symlink（expert/status -> ../*.lsp） | 上游视图引用 acf-core 的共享模板，跨 Conan 包相对路径无法解析 | `package()` 中从 acf-core 的 share/acf/app/ 复制 expert-html.lsp/status-html.lsp 并重命名为 heimdal-expert/status-html.lsp（功能等价，物化为常规文件） |
| 2 | HMDFS 拒绝 symlink 创建 | 真机文件系统对 symlink 支持受限（见避坑指南 §15） | 同上，no-link 布局，物化后产物全部为常规文件 |
| 3 | `usr/` 前缀规范化顺序 | `make install` 落盘到 `<pkg>/usr/...`，需先规范化再做视图物化，否则相对路径失效 | 先 `make install`，再 `usr/` → 根目录规范化，最后物化两个视图 |

## 源码修改

无（recipe 通过 `package()` 方法中的物化逻辑处理 OHOS 兼容性，不修改上游源码，无需 patch）

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| acf-core | 0.24.1 | 运行时框架（mvc.lua 分发 + modelfunctions/htmlviewfunctions/cfe + 共享视图），已发布 ohpcd 制品仓 |
| acf-lib-lua5.4 | 0.11.1 | 运行时 Lua 库（acf.fs/acf.html），已发布 ohpcd 制品仓 |
| lua | 5.4.8 | acf-core 与 acf-lib-lua5.4 的运行时依赖（传递） |

## 验证结果

### 本机前置验证（已完成）
```
源码 URL 校验:      PASS（distfiles.alpinelinux.org 可下载，2116 bytes）
sha256 校验:        PASS（1c4b2961fdc2e74d18ba6e5a0f9c06606579fc42687a73378bf536e2239e0e05）
构建系统识别:       PASS（纯 Makefile，pure-Lua 模块，install = mkdir + cp -a）
依赖检查:           PASS（acf-core/0.24.1 + acf-lib-lua5.4/0.11.1 均已发布 ohpcd）
配方静态检查:       PASS（conanfile.py/conandata.yml/MANIFEST.yml/test_package 完整，Python/YAML/JSON/sh 语法通过）
源码物化模拟:       PASS（本地模拟 package() 复制+物化，产物 7 文件全为常规文件）
```

### 真机验证（已完成 ✅）
```
RUN_ID:              claude-acf-heimdal-build-0.6.0-v2-20260819-193410-19537
conan create:        PASS（构建 + 测试全部通过，耗时 8 秒）
test_package:        PASS=11 FAIL=0（luac 未装于真机，2 语法检查有据跳过）
共享视图物化:        PASS（expert/status 常规文件，与 acf-core 逐字节一致）
L0: pass（依赖 ohpcd 可用、版本不冲突、commands.json 有效）
L1: pass（test_package 已执行，L1e 破坏性验证有据跳过）
L2: skip（无 bin/，有据跳过）
L4: pass（无 patch）
L5: warn（无 bin/lib 产物——纯 Lua 模块预期行为）
ci-metadata:         已写入
```

## 下一步真机/shadow CI 命令

```sh
# 单包 shadow CI（在隔离 job 内）
. "$HOME/ohos-users/<user>/acf-heimdal-pr<id>/env.sh"
cd "$CI_REPO_ROOT"
CI_PACKAGES="archives/a/acf-heimdal/0.6.0" zsh ci/conan/build_and_test.sh
# 或
sh "$HOME/bin/run-ohos-shadow-ci.sh" archives/a/acf-heimdal/0.6.0
```

## 注意事项

- 纯 Lua 模块：无 bin/、无 lib 库，L2 smoke test 按规则跳过
- 运行时需 acf-core + acf-lib-lua5.4；运行时还需 Heimdal Kerberos 客户端（kinit/klist/kdestroy）
- `heimdal-model.lua` 的 set_kinit 用 fs.write_file 写 `/tmp/k<timestamp>` 密码临时文件，真机需确认 /tmp 或 TMPDIR 可写（见避坑指南 §13）
- 两个共享视图（expert/status）来自 acf-core，若 acf-core 版本更新可能需要同步检查视图文件是否变化

---

**编译结束**: 2026-08-19
**最终状态**: built（前置完成，真机待验证）
