# libgsystemservice

libgsystemservice 提供构建 **D-Bus 系统总线服务**所需的公共组件：

- **`GssService`** —— `GObject` 派生（`G_DECLARE_DERIVABLE_TYPE`）的服务基类：
  命令行解析、抢占总线名、polkit 授权、systemd 就绪通知（`sd_notify`）、
  空闲超时、`SIGINT`/`SIGTERM` 处理与优雅退出；
- **`GssPeerManager`** —— `GInterface`，按 D-Bus sender 查询对端进程凭据
  （argv0 / pidfd / uid）；
- **`GssConfigFile`** —— 多文件 + GResource 默认值的分层配置文件读取器。

accountsservice 一类的系统服务用它来省掉上述样板代码。

- 上游: https://gitlab.gnome.org/pwithnall/libgsystemservice （GNOME GitLab
  project id **1180**；注意 `GNOME/libgsystemservice` 这个路径不存在，会 404）
- Conan 包名: `libgsystemservice`（上游 pkg-config 名是 `gsystemservice-0`）
- 许可: LGPL-2.1-or-later

## 鸿蒙适配

- 构建系统: meson（`c_std=gnu11`）
- 编译器: clang / musl / OHOS aarch64
- 补丁: **无**。上游 meson 项目在 OHOS 上可直接构建，三处平台相关耦合都在
  配方侧处理，不修改上游源码。
- 依赖: `glib/2.84.0.1`（public）、`systemd/261` + `polkit/127`（private）；
  `tool_requires meson/1.11.0`

### 三处非显然的构建期耦合

1. **两个依赖的 pkg-config 名字对不上。**
   上游写 `dependency('libsystemd')` / `dependency('polkit-gobject-1')`，而
   `PkgConfigDeps` 按 **Conan 包名** 生成 `systemd.pc` / `polkit.pc`。配方把
   依赖包内自带的真实 `.pc` 复制进 `generators_folder`（meson
   `pkg_config_path` 首位）并把它的 `prefix=` 从 `/`（`--prefix=/` + DESTDIR
   装的）改写成实际包目录。同 `archives/a/accountsservice/26.27.3`。

2. **glib 的 `proxy-libintl`。** OHOS 上 glib 与子项目 `proxy-libintl`
   一起构建，`g_libintl_*` 就在 glib 包里，但 glib 配方的 `package_info`
   没声明 `intl` 系统库 → 生成的 `.pc` 缺 `-lintl` → 消费者
   `undefined reference to 'g_libintl_*'`。配方就地增补生成物。

3. **meson 机器文件缺 `ar`/`ranlib`/`pkg-config`。**
   `MesonToolchain` 生成的 `conan_meson_native.ini` 在 OHOS worker 上
   `[binaries]` 段缺这三项，配方补注入。

### 上游测试

`libgsystemservice/tests/meson.build` 注册 3 个测试程序、共 13 个
`g_test_add` 用例。配方在 `build()` 内全量执行 `meson test` 并回读
`meson-logs/testlog.txt` 汇总块做硬断言（不吃退出码）。

其中 **`peer-manager` 在 OHOS 上必然失败**：它的 fixture 要用
`g_test_dbus_up()` 拉起私有 `dbus-daemon`（AF_UNIX socket），而 OHOS 沙箱
拒绝 AF_UNIX bind、已发布的 dbus 包也不含 `dbus-daemon`。该程序**仍被构建
并执行**，配方按「失败数量 + 失败身份」硬核对后如实声明，不删也不 SKIP。
详见 `0.3.0/notes.md` 的「上游测试与验证结果」。

## 版本

| 版本 | 状态 | 补丁 | 上游测试 | 说明 |
|------|------|------|----------|------|
| 0.3.0 | built | 0 | 3 程序 / 13 用例（2 程序、11 用例通过） | main 与 0.3.0 的 tests/ 逐文件一致；`peer-manager` 受沙箱限制如实声明失败 |
