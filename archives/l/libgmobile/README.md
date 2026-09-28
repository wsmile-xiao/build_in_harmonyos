# libgmobile

gmobile 是 Phosh 项目下的一个 glib/GObject 基础库，提供移动设备相关的公共
功能：设备树 compatible 匹配、显示面板挖孔（cutout）几何、MCC → 国家码查表、
SVG path 解析、超时帮助函数等。Phosh 及其组件（如 phoc、phosh）依赖它。

- 上游: https://gitlab.gnome.org/World/Phosh/gmobile
- Conan 包名: `libgmobile`（上游项目名与 pkg-config 名均为 `gmobile`）
- 许可: LGPL-2.1-or-later

## 鸿蒙适配

- 构建系统: meson（`>= 0.56.1`，`c_std=gnu11`）
- 编译器: clang / musl / OHOS aarch64
- 补丁: **无**。上游 meson 项目在 OHOS 上可直接构建，两处平台相关耦合都在
  配方侧处理，不修改上游源码。
- 依赖: `glib/2.84.0.1`、`json-glib/1.10.6`；`tool_requires meson/1.11.0`

### 两处非显然的构建期耦合

1. **`json-stripblanks` 是子进程，不是链接。**
   `data/gmobile.gresources.xml` 的 34 个 JSON 文件都带
   `preprocess="json-stripblanks"`。glib 的 `glib-compile-resources`
   并不链接 libjson-glib，而是把 `json-glib-format` 当子进程执行（PATH
   查找，可被 `JSON_GLIB_FORMAT` 环境变量覆盖）。配方在构建环境里把 glib
   与 json-glib 制品的 `bin/` 前置进 PATH，并显式设置 `JSON_GLIB_FORMAT`。

2. **PkgConfigDeps 生成的 glib `.pc` 需要就地增补。**
   生成物里没有 `-lintl`（glib 在 OHOS 上与其 `proxy-libintl` 子项目一同
   构建，但 glib 配方的 `package_info` 未声明 `intl` 系统库），也没有
   `glib_mkenums` 一类工具变量。配方就地改生成物补上。

### 上游测试

`tests/meson.build` 注册 7 个测试程序、共 14 个 `g_test_add_func` 用例，
配方在 `build()` 内全量执行 `meson test` 并回读 `meson-logs/testlog.txt`
汇总块硬断言（不吃退出码）。详见 `0.7.2/notes.md` 的「验证结果」。

## 版本

| 版本 | 状态 | 补丁 | 说明 |
|------|------|------|------|
| 0.7.2 | built | 0 | 上游 master 与 v0.7.2 的 tests/ 一致（7 程序 / 14 用例） |
