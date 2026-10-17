# libratbag

libratbag 是 Linux 上给**游戏鼠标/键盘**做配置的库，也是 Piper 等图形前端的
底层依赖。一次构建产出三样东西：

- **`liblur.so`** —— `liblur`，访问 Logitech **Unifying Receiver**：识别收发器
  （`lur_is_receiver()`）、枚举已配对设备、开关配对窗口、断开单个设备；
- **`libratbag`**（构建期目标，装进包内）—— 设备抽象层：按 `data/*.device`
  配置文件认领设备，暴露 profile / 分辨率 / 按键 / LED 的读写接口，并为
  Logitech HID++ 1.0/2.0、Roccat、SteelSeries、Etekcity、Gskill、ASUS、
  Sinowealth 等驱动分别实现；
- **`ratbagd`** + `ratbagctl` —— 把上面的接口暴露成 D-Bus 服务（`ratbagd`）
  与命令行客户端（`ratbagctl`）。

本仓库的 Conan 包名是 `libratbag`，对外暴露的库是 `liblur`（`pkg_config_name`
= `liblur`，安装 `include/liblur.h`）。

- 上游: https://github.com/libratbag/libratbag
- 许可: MIT

## 鸿蒙适配

- 构建系统: meson
- 编译器: clang / musl / OHOS aarch64
- 补丁: **1 个**，只动 meson 构建脚本，不动任何 C 源码
  （`patches/0001-meson-make-python-bindings-optional.patch`）
- 依赖: `glib/2.84.0.1`、`eudev/3.2.14`、`libevdev/1.13.7`、`json-glib/1.10.6`、
  `libunistring/1.0`；`systemd/261`（private，visible=False）；
  `tool_requires meson/1.11.0`；`test_requires check/0.15.2`

### 非显然的耦合与处理

1. **swig / libpython（唯一的补丁）。**
   上游无条件 `find_program('swig')`，并用 swig 生成 `ratbag-command`
   （Python 绑定）。OHOS 上既没有 swig，也没有 libpython 开发库（Python 只以
   worker 上的普通解释器形式存在）。补丁新增 `-Dpython-bindings`（默认 `true`，
   保持上游行为），关闭后既不找 swig 也不找 libpython。同一思路仓库内有先例：
   graphviz 的 `--disable-swig`。

2. **libudev 的提供者不是 systemd。**
   上游写 `dependency('libudev')`，但本仓库的 `systemd/261` 只装 `libsystemd`
   （见 `archives/s/systemd/261`）。`libudev` 由 `eudev/3.2.14` 提供，其
   `pkg_config_name` 正好是 `libudev`，两边的 `.pc` 名字天然对得上。

3. **`shared=False` 不可用。**
   上游 liblur 用 `shared_library()` 硬编码。配方 `validate()` 显式拒绝
   `shared=False`，而不是让它以一个难懂的 meson 错误收场。

4. **glib 的 `proxy-libintl`。**
   OHOS 上 glib 与子项目 `proxy-libintl` 一起构建，`g_libintl_*` 就在 glib
   包里，但 glib 配方的 `package_info` 没声明 `intl` 系统库 → 生成的 `.pc`
   缺 `-lintl` → 消费者（`libratbag-util.c` 用到字符串转换）会
   `undefined reference to 'g_libintl_*'`。配方就地增补生成物。

5. **meson 机器文件缺 `ar`/`ranlib`/`pkg-config`。**
   `MesonToolchain` 生成的 `conan_meson_native.ini` 的 `[binaries]` 段在
   OHOS worker 上缺这三项，配方从 conf / 已知 SDK 路径补注入。

### 上游测试

顶层 `meson.build` 用 `test()` 注册 **10 个**测试程序：

| # | 程序 | 类型 | 用例 | 本平台 |
|---|------|------|------|--------|
| 1 | `data-parse-test` | Python 数据校验 | — | 通过 |
| 2 | `duplicate-test` | Python 数据校验 | — | 通过 |
| 3 | `receiver-id-test` | Python 数据校验 | — | 通过 |
| 4 | `test-context` | C / check | 6 | 通过 |
| 5 | `test-device` | C / check | 23 | 通过 |
| 6 | `test-util` | C / check | 2 | 通过 |
| 7 | `test-iconv-helper` | C / check | 4 | 通过 |
| 8 | `ratbagctl-test` | Python + D-Bus | — | 失败（沙箱） |
| 9 | `python-black-check` | 代码风格 | — | 失败（无 black） |
| 10 | `python-ruff-check` | 代码风格 | — | 失败（无 ruff） |

4 个 C 程序**不需要插鼠标**：`test-device.c` 的夹具 `ratbag_test_device_new()`
建的是纯内存设备，`test-context.c` 同理。配方在 `build()` 内全量执行
`meson test`，并**回读** `meson-logs/testlog.txt` 的汇总块做硬断言——不吃退出
码，因为 SKIP 与「用例根本没注册」同样会让退出码为 0。

第 8–10 个程序在 OHOS 上必然失败：`ratbagctl-test` 要拉起 `ratbagd` 并连系统
总线（OHOS 沙箱拒绝 AF_UNIX bind，且已发布的 dbus 包只含客户端库，见
`archives/d/dbus/1.14.10.2/manifest.yaml`）；后两个要 pip 安装的 `black` /
`ruff`（worker 上没有 pip 网络访问）。它们**仍被构建、被执行**，配方按
「失败数量 + 失败身份」硬核对后如实声明，不删也不 SKIP。

## 版本

| 版本 | 状态 | 补丁 | 上游测试 | 说明 |
|------|------|------|----------|------|
| 0.18 | built | 1 | 10 程序 / 35 check 用例（7 程序、35 用例通过） | master 与 tag v0.18 的 test/ 逐文件一致；`ratbagctl-test`、`python-black-check`、`python-ruff-check` 受平台限制如实声明失败 |
