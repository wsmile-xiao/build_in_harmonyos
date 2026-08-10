# acf-iproute2-qos 0.4.0 适配 notes

## 上游测试验证记录（2026-08-08，作者自评留痕）

### 库性质
- **Alpine ACF (Alpine Configuration Framework) Web 管理模块**：为 iproute2 的 QoS 流量控制提供基于 Web 的系统管理界面
- 上游：https://gitlab.alpinelinux.org/acf/acf-iproute2-qos（GPL-2.0-only，Maintainer Ted Trask）
- 纯 Lua/LSP 脚本包，**无编译**（Makefile 仅做拷贝安装：`qos*` → `$(appdir)/qos`）
- 本包与 ACF 框架宿主（acf-core）解耦：脚本由框架运行时加载

### 上游测试情况
- **上游无测试套件**：release tarball（acf-iproute2-qos-v0.4.0.tar.gz）仅 2 个 .lua + 3 个 .lsp + roles/menu，无 test/spec/check 目录
- 模块行为由 acf-core 框架宿主在运行时验证，不在本 archive 内

### 自增测试（test_package，7/7 100% 通过）
本机 conan create 验证通过（EXIT=0，Package built + test_package 全 [ok]）：
1. ✅ qos-controller.lua
2. ✅ qos-model.lua
3. ✅ qos.roles
4. ✅ qos.menu
5. ✅ qos-details-html.lsp（普通文件）
6. ✅ qos-expert-html.lsp（符号链接 → ../filedetails-html.lsp，目标由 acf-core 运行时提供）
7. ✅ qos-status-html.lsp（符号链接 → ../status-html.lsp，同上）

### 适配要点
- conanfile.py：纯脚本包配方——`source()` get 下载 tarball、`build()` pass、`package()` 按上游 Makefile APP_DIST 安装
- **符号链接处理**（关键坑）：上游 tarball 中 2 个 .lsp 是指向 acf-core 共享模板的**悬空符号链接**（`qos-expert-html.lsp -> ../filedetails-html.lsp`）。conan `copy()` 默认跳过符号链接 → 改用 python 逐文件复制：普通文件 `shutil.copy2`、符号链接 `os.symlink` 重建（保持相对目标）。test_package 用 `os.path.lexists` 检查（不解析链接目标，与上游 `cp -a` 复制链接本身的语义一致）
- R32：settings.os 校验 ("Linux", "OHOS")
- 无编译依赖、无 patches、无第三方依赖

### CI 复跑预期
- 纯脚本包无编译，CI 上 conan create 直跑即可（无需工具链 hack）
- L0 门禁：MANIFEST.yml 已按模板填写（assertion_count=7）
- W3 本地 CI 模拟已通过

## 积分赛 PR 描述（body 供粘贴 GitCode）

**三方库信息**
- 名称：acf-iproute2-qos（Alpine ACF iproute2 QoS 管理模块）
- 版本：0.4.0
- 仓库地址：https://gitlab.alpinelinux.org/acf/acf-iproute2-qos
- 适配路径：archives/a/acf-iproute2-qos/0.4.0/
- License：GPL-2.0-only

**测试用例对比**
| 项 | 上游 | 适配后 |
|----|------|--------|
| 测试套件 | 无（纯 Lua 模块，无 test 目录） | test_package 自增 7 项 |
| 通过率 | — | 100% |

**上游测试用例修改说明**：不适用（上游无测试套件）

**补全测试用例说明**：新增 test_package/conanfile.py——核心模块文件存在性（7 文件，含 2 个悬空符号链接用 lexists 验证）+ lua 语法检查（解释器可用时）

**验证结果**
- 编译状态：纯脚本包无编译，conan create 直跑通过（Package built）
- 测试通过率：7/7 = 100%（本机验证）
- W3 本地 CI 模拟通过
