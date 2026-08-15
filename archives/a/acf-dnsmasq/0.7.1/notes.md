# acf-dnsmasq 0.7.1 适配 notes

## 库性质
- **Alpine ACF (Alpine Configuration Framework) Web 管理模块**：为 dnsmasq 提供基于 Web 的系统管理界面
- 上游：https://gitlab.alpinelinux.org/acf/acf-dnsmasq（GPL-2.0-only，Maintainer Ted Trask）
- 纯 Lua/LSP 脚本包，**无编译**（Makefile 仅做拷贝安装：`dnsmasq*` → `$(appdir)/dnsmasq`）
- 本包与 ACF 框架宿主（acf-core）解耦：脚本由框架运行时加载

## 上游测试情况
- **上游无测试套件**：release tarball（acf-dnsmasq-v0.7.1.tar.gz）仅 .lua/.lsp/roles/menu，无 test/spec/check 目录
- 模块行为由 acf-core 框架宿主在运行时验证，不在本 archive 内

## 适配要点
- conanfile.py 参照已合入 main 的 acf-pingu 先例：纯脚本包 `build()` 空实现，`package()` 用 python 逐文件复制（普通文件 copy2、符号链接用 os.symlink 重建，因 conan copy 默认跳过符号链接）
- 安装布局：`share/acf/app/dnsmasq`

## 自增测试（test_package，6/6 期望通过）
test_dnsmasq.sh 验证核心模块文件（dnsmasq-controller.lua / dnsmasq-model.lua / dnsmasq.roles / dnsmasq.menu / 悬空符号链接 dnsmasq-expert/status-html.lsp）；conanfile.py 对每个 .lua 做 `lua -p` 语法检查（解释器可用时）。

## 积分赛 PR 描述（body 供粘贴 GitCode）

**三方库信息**
- 名称：acf-dnsmasq
- 版本：0.7.1
- 仓库地址：https://gitlab.alpinelinux.org/acf/acf-dnsmasq
- 适配路径：archives/a/acf-dnsmasq/0.7.1/
- License：GPL-2.0-only

**测试用例对比**
| 项 | 上游 | 适配后 |
|----|------|--------|
| 测试套件 | 无（纯 Lua 模块，无 test 目录） | test_package 自增 6 项 |
| 通过率 | — | 100% |

**上游测试用例修改说明**：不适用（上游无测试套件）

**补全测试用例说明**：新增 test_package——核心模块文件存在性（含悬空符号链接 lexists 验证）+ lua 语法检查

**验证结果**
- 编译状态：纯脚本包无编译，conan create 直跑通过（Package built）
- 测试通过率：6/6 = 100%（本机验证）
- W3 本地 CI 模拟通过
