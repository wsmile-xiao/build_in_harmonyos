# DRAFT — leaflet-markercluster：上游 git 标签无预构建 JS，npm 官方发布包作 dist 源码渠道

> 状态：草稿（来自 leaflet-markercluster 1.5.3-dfsg 真机适配，2026-09-26）

## 问题

上游 git 标签 v1.5.3 的 `dist/` 不含预编译 JS——只有 2 个 CSS 与
`WhereAreTheJavascriptFiles.txt`，该文件明示：

> We don't ship the .js files in the git master branch. They are only
> present in version tags and in npm.

Debian dfsg orig（= git 快照）同样不含 JS；Debian 构建 JS 依赖 rollup+terser
（dsc Build-Depends 实证）。OHOS 真机无浏览器、node V8 JIT 崩溃（E400）→
git 标签与 dfsg orig 两条路径都拿不到可分发 JS，且无法在目标环境复刻构建。

## 取证链

1. 上游 git 标签 dist/ 文件清单：2 CSS + WhereAreTheJavascriptFiles.txt（0 JS）；
2. Debian dsc Build-Depends：rollup、terser（JS 须现构建）；
3. 上游 npm 发布包 `leaflet.markercluster-1.5.3.tgz` 的 dist/ 含完整 4 件套
   （leaflet.markercluster.js / -src.js / MarkerCluster.css /
   MarkerCluster.Default.css）+ 2 sourcemap，与 Debian 构建产物同源
   （同 build/rollup-config.js）。

## 方案

- 源码取 **npm 官方发布包**（上游自有的 dist 渠道，非 dfsg repack），
  conandata.yml 钉死 URL + sha256；
- recipe 为 application 资产包（settings=os,arch、build()=pass、package() 拷贝
  dist 7 件到 share/leaflet-markercluster/、MIT-LICENCE.txt 与 README.md 进
  licenses/、resdirs 指向 share 目录）——acf-jquery 0.4.3 先例同款范式；
- 版本口径：任务版本 1.5.3-dfsg = Debian 1.5.3~dfsg 平台归一化（~→-，
  net-tools 2.1 先例），无需 R37 递增（制品仓无此包）。

## 验证

- 真机 `conan create` + `conan test`：17/17 全绿（16 核心断言 + node
  --jitless --check；ohos-aarch64 与 default 双 profile）；
- 16 核心断言含**安装产物与 npm dist 的 sha256 逐字节一致**（四文件逐一比对）。

## 适用边界

- 适用于「上游 git 无预构建资产 + 发行版 dfsg 同样剥离 + 目标环境无 node
  工具链」的前端库（Leaflet 生态插件、browserify/rollup 分发类项目）；
- npm 包本身是上游官方渠道，不构成对上游/发行版内容的改写；
- 若 npm 同样缺失 dist，须走 fallback（见 kv）。

## 查重差异

- E616（upstream-auto-tarball-vs-release-src-asset-submodules）：C/C++ 项目
  GitHub 自动 tarball 子模块空目录问题，forbid_2 禁止用 debian +dfsg repack
  **顶替上游源码**——本条目不顶替：源码渠道取上游官方 npm 发布包，与 E616
  原则（不采信改写过的 dfsg repack 为上游源码）一致但场景不同（JS 资产 vs
  C++ 子模块构建）。
- E552（lang-preflight 文档资产误报）：jquery.js 作为 doc/ 生成资产污染源码
  统计的处置，与本条「dist 资产来源选择」不同维度。
- acf-jquery 0.4.3（已合入先例）：其上游 tarball 自带 dist，无需 npm 渠道；
  本条填补「git 无预构建 JS」这一空白场景。
