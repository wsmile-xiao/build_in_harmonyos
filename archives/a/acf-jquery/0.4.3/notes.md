# acf-jquery 0.4.3 适配 notes

## 上游测试验证记录（2026-08-08，作者自评留痕）

### 库性质
- **Alpine ACF (Alpine Configuration Framework) jquery addon 包**：为 ACF Web 管理界面提供 jquery 静态资源（jquery-latest.js / jquery.flot.js / jquery.tablesorter.js 等 + tablesorter 主题）
- 上游：https://gitlab.alpinelinux.org/acf/acf-jquery（GPL-2.0-only，Maintainer Ted Trask）
- 纯静态 JS/CSS 资源包，**无编译**（Makefile 仅做拷贝安装）
- 安装路径（上游 Makefile/config.mk）：
  - APP_DIST（`*.js` + `widgets/*.js` + `parsers/*.js`）→ `$(appdir)` = `/usr/share/acf/app`
  - STATIC_DIST（`tablesorter/*` 主题 css/png）→ `$(staticdir)` = `/usr/share/acf/www/skins/static`

### 上游测试情况
- **上游无测试套件**：release tarball（acf-jquery-v0.4.3.tar.gz）仅 JS 库 + tablesorter 主题资源，无 test/spec/check 目录
- 资源由 ACF Web UI 运行时加载，不在本 archive 内做运行时验证

### 自增测试（test_package，9 断言 100% 通过）
本机 conan create 验证通过（EXIT=0，Package built + test_package 全 [ok]）：
1. ✅ jquery-latest.js
2. ✅ jquery.flot.js
3. ✅ jquery.flot.time.js
4. ✅ jquery.tablesorter.js
5. ✅ jquery.tablesorter.widgets.js
6. ✅ excanvas.js
7. ✅ widgets/ 子目录（1 个 js）
8. ✅ parsers/ 子目录（1 个 js）
9. ✅ tablesorter/ 主题资源（17 个 css/png）

### 适配要点
- conanfile.py：纯静态资源包配方——`source()` get 下载 tarball、`build()` pass、`package()` 按上游 Makefile APP_DIST/STATIC_DIST 安装：
  - `*.js` + `widgets/` + `parsers/` → `share/acf/app`
  - `tablesorter/` → `share/acf/www/skins/static/tablesorter`
- R32：settings.os 校验 ("Linux", "OHOS")
- 无编译依赖、无 patches、无第三方依赖

### CI 复跑预期
- 纯资源包无编译，CI 上 conan create 直跑即可（无需工具链 hack）
- L0 门禁：MANIFEST.yml 已按模板填写（assertion_count=6 组验证）
- W3 本地 CI 模拟已通过

## 积分赛 PR 描述（body 供粘贴 GitCode）

**三方库信息**
- 名称：acf-jquery（Alpine ACF jquery addon 包）
- 版本：0.4.3
- 仓库地址：https://gitlab.alpinelinux.org/acf/acf-jquery
- 适配路径：archives/a/acf-jquery/0.4.3/
- License：GPL-2.0-only

**测试用例对比**
| 项 | 上游 | 适配后 |
|----|------|--------|
| 测试套件 | 无（静态资源包，无 test 目录） | test_package 自增 9 项 |
| 通过率 | — | 100% |

**上游测试用例修改说明**：不适用（上游无测试套件）

**补全测试用例说明**：新增 test_package/conanfile.py——核心 JS 库存在性（6 文件）+ widgets/parsers 子目录 + tablesorter 主题资源验证

**验证结果**
- 编译状态：纯资源包无编译，conan create 直跑通过（Package built）
- 测试通过率：9 断言 = 100%（本机验证）
- W3 本地 CI 模拟通过
