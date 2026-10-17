# patches/

**本配方不携带任何源码补丁。**

上游 qtcharts-everywhere-src-5.15.2 源码在 OHOS aarch64 下无需修改即可编译，
`conandata.yml` 的 `patches` 为空，`manifest.yaml` 声明 `patches: none`。

## 为什么这个目录是空的

`ohc finish` 的补丁生成器（`refresh_patch.py`，per-file-difflib 比对 `.orig`
与 `.work` 快照）会把构建目录里的 **qmake 生成物**误判为源码修改，产出 8 个
「补丁」：

| 生成物 | 说明 |
|---|---|
| `src/charts/QtCharts.version{,.in}` | qmake 生成的链接器版本脚本 |
| `src/charts/qdoc_wrapper.sh`、`src/charts/uic_wrapper.sh` | qmake 生成的工具包装脚本，**硬编码本机前缀** `/storage/Users/currentUser/tmp/qt5charts-prefix` |
| `src/chartsqml2/qmlplugindump_wrapper.sh`、`src/chartsqml2/uic_wrapper.sh` | 同上 |
| `.qmake.stash` | qmake 配置缓存，**冻结了特定 SDK（ohos-sdk_26.0.0.18）与 clang 15.0.4 版本** |
| `include/QtCharts/QtChartsDepends` | syncqt 生成的依赖声明 |

经核对，这 8 个目标文件**全部不存在于上游 tarball**（`tar tJf` 逐项验证），
因此它们不是源码修改，作为补丁交付会把本机路径与 SDK 版本泄漏进制品仓，
且 `apply_conandata_patches` 因 `patches: {}` 始终是 no-op —— 它们从未参与构建。

已于 W4 审计打回后删除。**若再次运行 `ohc finish`，该生成器会重新产出这 8 个
文件，需手工清理**（`refresh_patch.py` 是框架脚本，不在软件适配任务的可改范围内）。
