# indie-wiki-buddy 3.10.1 适配笔记

## 打包环境
- **类型**: 浏览器扩展（**纯静态资源**：JS/CSS/HTML/图片/多语言），chromium 与 firefox 两棵树
- **打包日期**: 2026-10-08
- **平台**: arm64-ohos（OpenHarmony PC）
- **依赖**: **无**（无 Conan requires、无 npm 依赖、无运行期库、无编译）
- **状态**: built

## 打包步骤（conan create 全流程）

```bash
conan create archives/i/indie-wiki-buddy/3.10.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码（source()）
Debian orig tarball（与上游发布一致，541 个文件 / 约 4.9 MB）：
`indie-wiki-buddy_3.10.1.orig.tar.gz`（sha256 `2d648e32…`），`strip_root=True`。

### 2. 打包要点（照抄 Debian 的 install 映射与 rules）
| 项 | 处理 |
|---|---|
| 两棵浏览器树 | `res/chromium/extensions/indie-wiki-buddy/` 与 `res/mozilla/extensions/{ec8030f7-…}/{cb31ec5d-…}/`（后者沿用 Mozilla 扩展 ID，与 Debian 一致） |
| 内容 | `_locales/`、`css/`、`data/`、`favicons/`、`images/`、`pages/`、`scripts/`、`background.js`、`LICENSE`、`README.md` |
| **`manifest.json`** | **由模板按浏览器生成**：`manifest-chromium.json → <chromium>/manifest.json`（`manifest_version=3`）、`manifest-firefox.json → <firefox>/manifest.json`（`manifest_version=2`，带 `browser_specific_settings.gecko.id`）—— 与 `debian/rules` 的 `override_dh_auto_install` 同做法 |

> **易错点**：`manifest.json` 在源码里**并不存在**（只有两份模板）。直接照搬目录会漏掉它；
> 或者两棵树都塞同一份 → chromium 侧 `manifest_version` 会是 2（该用 3）而被消费者校验抓住。

### 3. 依赖为什么是"零"
三处都空才能算零依赖：①`Build-Depends` 仅 `debhelper-compat`（dh 版本声明）；②`Depends` 仅
`${misc:Depends}`；③发布物里**没有** `package.json`/`Makefile` 之类的构建声明 → 无编译、无 npm。

## 上游测试清点（R51）

| 项 | 值 |
|----|----|
| 上游测试 | **无**：包内无 `package.json` / `Makefile` / `test/`，Debian 侧亦无 `debian/tests` |
| 结论 | 上游通过率记 **N/A**（如实披露，不虚构） |
| 消费者验证 | `test_package/check_extension.py` 5 项：两棵树结构 → 两份 manifest 语义（version/manifest_version/gecko id）→ 资源口径（各目录文件数下限）→ 证据 |

## 实测结果（本地 conan create，2026-10-08）

```
indie-wiki-buddy/3.10.1: [build] 无需编译：静态扩展，547 个文件；两份 manifest 版本均 3.10.1
indie-wiki-buddy/3.10.1: [package] chromium 树 -> res/chromium/extensions/indie-wiki-buddy/
indie-wiki-buddy/3.10.1: [package] firefox 树 -> res/mozilla/extensions/{ec8030f7-…}/{cb31ec5d-…}/
[ok]   两棵浏览器树齐备（chromium + firefox，各含 manifest.json/background.js 与 7 个内容目录）
[ok]   chromium/manifest.json 合法：version=3.10.1、manifest_version=3
[ok]   firefox/manifest.json 合法：version=3.10.1、manifest_version=2
[ok]   firefox manifest 的 gecko id 与包内目录名一致（{cb31ec5d-c49a-4e5a-b240-16c767444f62}）
[ok]   资源口径达标（favicons/images/data/pages/scripts/css 均不低于下限，两棵树各一份）
[ok]   证据：chromium 树 538 个文件 / 0.8 MB
[ok]   证据：firefox 树 538 个文件 / 0.8 MB
checks=5 fails=0 skips=0
RESULT: PASS
```

- 上游通过率：**N/A**（无测试套件，清点证据见上节）
- 消费者校验：**5 项全部通过**

### 本库沉淀的适配范式（都已写进 version manifest 的 knowledge_gained 与知识草稿）

1. **`manifest.json` 是生成物**：源码只有 `manifest-chromium.json` / `manifest-firefox.json` 两份模板，
   必须**按浏览器**挑选生成——漏生成会缺文件，两棵树用同一份则 chromium 侧的
   `manifest_version` 会错（该 3 却是 2）→ 消费者校验用 `manifest_version` 断言兜住。
2. **零依赖要三处都空**：Build-Depends（仅 debhelper-compat）、Depends（仅 ${misc:Depends}）、
   发布物内的构建声明（本包无 `package.json`/`Makefile`）。
3. **纯数据包的消费者校验**应做"**结构 + 配置语义 + 资源口径**"三层：
   结构（两棵树与必需文件）、语义（version / manifest_version / gecko id）、
   资源下限（favicons≥400、images≥15、data≥10、pages≥5、scripts≥3、css≥5）——
   只数文件个数会被"空目录装过去"骗过。
4. **firefox 树目录名与 gecko id 双向核对**（路径 `{cb31ec5d-…}` 与 manifest 里的
   `browser_specific_settings.gecko.id` 必须一致）。

## 复用来源

- Debian native/数据包范式（不跑 dh、照抄 install 映射）沿用本会话的
  `archives/i/installation-report/2.98`、`archives/i/initramfs-tools/0.151`；
- "配置语义断言 + 资源口径断言"的做法为本包新增（见 version manifest 的 knowledge_gained）。
