# mkc (mk-configure 0.27.0)

基于 bmake（可移植 NetBSD make）的构建系统：安装 `mkcmake` 包装器、
`mkc_check_*`/`mkc_install` 辅助命令与 `mkc.*.mk`/`mkc_imp.*.mk` include 库。
上游：<https://github.com/cheusov/mk-configure>

本仓库提供鸿蒙 PC（OHOS aarch64）的 Conan 配方：`archives/m/mkc/0.27.0/`。
（同软件更新版本的配方以包名 `mk` 发布在 `archives/m/mk/0.40.0/`，本任务为
平台点名指定的 0.27.0 旧版。）

## 产物

- `bin/`：mkcmake、mkc_check_compiler/custom/decl/funclib/header/prog/sizeof/version、mkc_install、mkc_which
- `share/mkc-mk/*.mk`、`share/mk-configure/custom|features`
- man 页

软件级 `commands.json` 已登记全部命令。

## 依赖

bmake/20200710（tool_requires + requires）、bmkdep/20140112（tool_requires）。

## 鸿蒙适配要点

见软件级 `manifest.yaml` 的 `ohos_adaptation.key_points` 与版本目录内
`notes.md`（上游回归矩阵实跑口径与逐项归因）。
