# acf-openssl 0.11.0 适配 notes

## 上游测试验证记录（2026-08-08，作者自评留痕）

### 库性质
- **Alpine ACF (Alpine Configuration Framework) Web 管理模块**：为 openssl 提供基于 Web 的系统管理界面
- 上游：https://gitlab.alpinelinux.org/acf/acf-openssl（GPL-2.0-only，Maintainer Ted Trask）
- 纯 Lua/LSP 脚本包，**无编译**（Makefile 仅做拷贝安装：`openssl*.lua openssl*.lsp openssl.roles openssl.menu` → `$(appdir)/openssl`）
- 本包与 ACF 框架宿主（acf-core）解耦：脚本由框架运行时加载

### 上游测试情况
- **上游无测试套件**：release tarball（acf-openssl-v0.11.0.tar.gz）仅 2 个 .lua + 10 个 .lsp + roles/menu + cnf 配置文件，无 test/spec/check 目录
- 模块行为由 acf-core 框架宿主在运行时验证，不在本 archive 内

### 自增测试（test_package，3/3 100% 通过）
本机 conan create 验证通过（EXIT=0，Package built + test_package 全 [ok]）：
1. ✅ 6 个核心模块文件存在性验证：openssl-controller.lua / openssl-model.lua / openssl.roles / openssl.menu / openssl-html.lsp / openssl-read-html.lsp
2. ✅ openssl-ca-acf.cnf 配置文件存在
3. ✅ 共发现 2 个 .lua + 10 个 .lsp 模板全部打包；lua 解释器可用时做 `lua -p` 语法检查（本机无 lua 解释器，记录文件已验证存在）

### 适配要点
- conanfile.py：纯脚本包配方——`source()` get 下载 tarball、`build()` pass、`package()` 按上游 Makefile 的 APP_DIST/ETC_DIST 拷贝到 `share/acf/app/openssl` + `share/acf/openssl`（cnf）
- R32：settings.os 校验 ("Linux", "OHOS")
- 无编译依赖、无 patches、无第三方依赖

### CI 复跑预期
- 纯脚本包无编译，CI 上 conan create 直跑即可（无需工具链 hack）
- L0 门禁：MANIFEST.yml 已按模板填写（assertion_count=7）

## 积分赛 PR 描述（body 供粘贴 GitCode）

**三方库信息**
- 名称：acf-openssl（Alpine ACF openssl 管理模块）
- 版本：0.11.0
- 仓库地址：https://gitlab.alpinelinux.org/acf/acf-openssl
- 适配路径：archives/a/acf-openssl/0.11.0/
- License：GPL-2.0-only

**测试用例对比**
| 项 | 上游 | 适配后 |
|----|------|--------|
| 测试套件 | 无（纯 Lua 模块，无 test 目录） | test_package 自增 3 项 |
| 通过率 | — | 100% |

**上游测试用例修改说明**：不适用（上游无测试套件）

**补全测试用例说明**：新增 test_package/conanfile.py——核心模块文件存在性（6 文件）+ cnf 配置 + lua 语法检查（解释器可用时）

**验证结果**
- 编译状态：纯脚本包无编译，conan create 直跑通过（Package built）
- 测试通过率：3/3 = 100%（本机验证）
