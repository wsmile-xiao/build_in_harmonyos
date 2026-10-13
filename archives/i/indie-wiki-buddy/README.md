# indie-wiki-buddy

## 软件描述
**Indie Wiki Buddy** 是一个浏览器扩展：当用户点击 Fandom 等托管平台的 wiki 链接时，把它**重定向到对应的独立百科**（并给出提示），同时支持搜索结果的替换与站点黑白名单。纯静态资源（JS/CSS/HTML/图片/多语言），MIT 许可。

## 功能概述
| 内容 | 作用 |
|---|---|
| `background.js` | 扩展后台逻辑（拦截/重写导航、读取配置） |
| `data/` | 站点与 wiki 映射数据（主体数据，18 个文件） |
| `scripts/` | 内容脚本 / 页面注入逻辑（4 个文件） |
| `pages/` | 扩展的选项页与弹窗页（7 个文件） |
| `css/`、`images/`、`favicons/` | 样式、图标与站点图标（475 个 favicon） |
| `_locales/` | 多语言文案 |
| `manifest-chromium.json` / `manifest-firefox.json` | 两个浏览器的 manifest 模板（打包时按浏览器生成 `manifest.json`） |

## OHOS 适配

### 打包方式
- **Debian orig tarball** 作为源码；**不跑 dh**，照抄 `debian/*.install` 与 `debian/rules`
- 同一内容装**两棵浏览器树**：
  - `res/chromium/extensions/indie-wiki-buddy/`
  - `res/mozilla/extensions/{ec8030f7-c20a-464f-9b0e-13a3a9e97384}/{cb31ec5d-c49a-4e5a-b240-16c767444f62}/`
- `manifest.json` 由**按浏览器挑选的模板**生成（chromium → `manifest_version=3`；firefox → `manifest_version=2` 且带 gecko id）

### 关键攻坚点
1. **`manifest.json` 是生成物**：源码里只有两份模板；漏生成或两棵树用同一份都会出问题（后者会被 `manifest_version` 断言抓到）
2. **零依赖要三处都空**：Build-Depends / Depends / 发布物内的构建声明（本包 `package.json`、`Makefile` 都不存在）
3. **上游无测试**：如实记 N/A；验证改为"结构 + 配置语义 + 资源口径"三层断言（防"空目录装过去"）
4. **firefox 树目录名要与 gecko id 一致**：消费者校验里双向核对（路径与 manifest 字段）

### 与 Linux 的差异
- 纯静态数据，跨平台无差异；差异集中在**打包布局**（两棵浏览器树 + 生成 manifest）

## 依赖关系
- **Conan requires**：无
- **运行期**：无（扩展由浏览器加载）
- **构建期**：无（无编译、无 npm）

## 版本记录
| 版本 | 状态 | 打包日期 | 备注 |
|------|------|---------|------|
| 3.10.1 | built | 2026-10-08 | 纯静态扩展；两棵浏览器树 + 按浏览器生成 manifest.json；上游无测试记 N/A |

## 参考资料
- 上游仓库: https://github.com/KevinPayravi/indie-wiki-buddy
- Debian 包页: https://tracker.debian.org/pkg/indie-wiki-buddy
