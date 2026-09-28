# leaflet-markercluster 1.5.3-dfsg 适配笔记（HarmonyOS PC · 纯 JS 资产包）

## 版本口径
任务版本 **1.5.3-dfsg** = Debian 源包 `leaflet-markercluster 1.5.3~dfsg`（`~` 被平台归一化为 `-`，
同 net-tools 2.1 先例；dsc 见 deb.debian.org/pool/main/l/leaflet-markercluster/）。
**无需 R37 递增**：官方 main 无 leaflet-markercluster 归档，首次适配。

## 源码选择（关键取证）
- 上游 git 标签 v1.5.3 的 `dist/` **不含预编译 JS**——只有 2 个 CSS 与
  `WhereAreTheJavascriptFiles.txt`，其明示 *"We don't ship the .js files in the git master
  branch. They are only present in version tags and in npm."*（Debian orig 即此快照）。
- Debian 构建 JS 需 rollup+terser（Build-Depends 实证），目标环境无 node → 不可行。
- 因此源码取 **npm 官方发布包** `leaflet.markercluster-1.5.3.tgz`
  （sha256 fc6b0b1d…，dist/ 含 leaflet.markercluster.js、-src.js、MarkerCluster.css、
  MarkerCluster.Default.css + 2 sourcemap），与 Debian 构建产物同源（同 build/rollup-config.js）。
- 上游 js 头部横幅：`Leaflet.markercluster 1.5.3+master.e5124b2`。

## 适配
- 纯 JS/CSS **资产包**，无编译：`package_type = application`，build() 为空，
  package() 把 dist 7 件（4 主件 + 2 sourcemap + 说明）装入 `share/leaflet-markercluster/`，
  MIT-LICENCE.txt 与 README.md 进 `licenses/`；`resdirs` 指向 share 目录（acf-jquery 先例范式）。
- 运行时依赖 **Leaflet 1.x**（插件须在 Leaflet 之后加载）：制品仓暂无 leaflet，
  由消费方 Web 应用自行提供——README 与 MR 正文如实声明，不虚构 conan 依赖。

## test_package
- 上游 34 个 karma/jasmine spec 文件（**184 个 it() 用例**，审查员脚本实测口径；
  本地 grep it()=180 + xit=1，以审查员实测 184 为准）是**浏览器端**测试
  （真实 DOM + Leaflet 渲染），目标环境无浏览器 → 不执行，R51 清点如实记入 MANIFEST.yml。
- 替代验证 = 资产完整性断言（16 条核心）+ node 语法校验 + **完整消费者端到端用例**：
  dist 4 件套存在性；JS 工厂挂载点锚点（`L.MarkerClusterGroup`）、版本横幅锚点；
  CSS 类锚点（.leaflet-cluster-anim/.leaflet-cluster-spider-leg/.marker-cluster-small/large）；
  sourcemap 存在；MIT 许可证文本与 README；**安装产物与 npm dist 的 sha256 逐字节一致**。
- **消费者 E2E**（rule12，test_package/consumer/）：node --jitless + 最小 DOM 桩
  （dom-shim.js，Leaflet 渲染管线最小面；聚合算法纯 JS 与桩无关）+ 真实 Leaflet 1.9.4
  运行时（leaflet.min.js 作测试夹具，BSD-2-Clause，sha256 钉死，不进包产物），以浏览器
  `<script>` 语义加载被测包产物，走完 建图→加 100 标记→z0 聚成 1 簇（childCount=100）
  →z15 解散（100 标记各自可见）→removeLayer→整组摘除 全流程，14 个验证节点全走公共 API。
  本机 Windows node 24.16（含 --jitless 模式）与真机均实跑通过。
- sha256 比对用**纯字符串比对哈希列**（不依赖 diff/进程替换）：Windows GNU sha256sum
  带 `*` 前缀、OHOS 上 diff/进程替换机制不稳，均取 awk 哈希列后直接比较。
- node 检查：设备**有** node v24.13.0（/data/service/hnp/bin/node），但 V8 JIT
  在 OHOS 上直接 SIGTRAP（`Check failed: 12 == (*__errno_location())`，含 1 行探针文件也崩），
  **加 `--jitless` 即正常**（RC=0）。故用 `node --jitless` + 探针自检启用门槛。

## 真机验证（关键环境发现）
- **os.version 子设置坑**：设备 conan settings.yml 为 `OHOS` 定义 `version: ["5.0","6.0"]`
  子设置且无默认值；配方 settings 未声明 `os.version` 时 conan 计算 package_id 期间报
  `Invalid: 'settings.os.version' value not defined`（default profile 复现；官方
  ohos-aarch64 profile 自带 `os.version=6.0` 不触发）。**配方侧修复**（知识库
  DRAFT-glpk-4.65-ohos-conan-os-version-rm-safe 的官方范式）：主配方与 test_package
  conanfile 均在 configure() 以 hasattr 守卫 `rm_safe("os.version")`。acf-jquery 0.4.3
  先例无此守卫（其 CI 恒用 ohos-aarch64 故不触发）；本配方加守卫后**两种 profile 均实测通过**。
- **bash 进程替换在 OHOS 不可用**：`<(...)` 能展开为 /dev/fd/63，但**读取报
  Permission denied**（`cat <(echo hi)` 实测）——test.sh 首轮 sha256 比对用
  `diff <(printf ...)` 因此静默失败（Windows 本地同脚本却全过）。改为纯字符串比对哈希列。
- **node V8 JIT 崩溃**：设备 node v24.13.0 普通模式启动即 SIGTRAP
  （`Check failed: 12 == (*__errno_location())`，知识库 **E400** 已记录），`--jitless` 恢复；
  test.sh 按 E400 用 `--jitless --check` + 探针自检门。

## 状态
verified —— 真机（HarmonyOS PC 设备）+ 本机（Windows node 24.16，含 --jitless 模式）全绿：

| 步骤 | 结果 |
|---|---|
| `conan create` (-pr ohos-aarch64, --build=missing) | ✅ 17/17（16 核心 + node --jitless）|
| `conan test` (-pr ohos-aarch64) | ✅ 17/17 |
| `conan test` (-pr default) | ✅ 17/17（rm_safe 双 profile 健壮性证明）|
| `conan test` 复验（-pr ohos-aarch64，含消费者 E2E） | ✅ **18/18**（17 断言 + 消费者 E2E 14 节点），2026-09-27，日志 reports/conan-test-ohos-aarch64.log |
| `conan test` 复验（-pr default，含消费者 E2E） | ✅ **18/18**，2026-09-27，日志 reports/conan-test-default.log |
| 本机消费者 E2E（Windows node 24.16，普通 + --jitless） | ✅ 14/14（模拟包根 lmc-sim 实跑）|
| 缓存二进制 | `leaflet-markercluster/1.5.3-dfsg#2f6f1115…:876049f3…` |

审查整改（2026-09-27）：rule4 少报（实测 184 > 声明 34）→ 声明改 184；rule12
纯断言 → 新增完整消费者端到端用例 test_package/consumer/cluster_flow.js（14 节点）。

## 路径 B 知识库扩展（2 条草稿，随 MR 提交 knowledge/drafts/）
- DRAFT-leaflet-markercluster-1.5.3-dfsg-npm-dist-source-dfsg-no-prebuilt-js
  （git 标签无预构建 JS → npm 官方发布包作 dist 源码渠道，取证链完整）
- DRAFT-leaflet-markercluster-1.5.3-dfsg-ohos-bash-process-substitution-fd-denied
  （OHOS /dev/fd 高编号管道 fd 重开 Permission denied，修正
  operations/filesystem-analysis.md 的 "一致" 记录）
