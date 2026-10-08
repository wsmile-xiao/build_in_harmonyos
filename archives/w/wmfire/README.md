# wmfire

`wmfire` is a Window Maker dockapp that renders CPU usage as an animated flame.
It samples the counters through `libgtop-2.0`, draws the flame with GDK (GTK+ 2)
and installs itself as an X11 dock window through Xlib.

## Versions

| Version | Status |
| --- | --- |
| 1.2.4 | built |

## 简介

CPU 占用率火焰 dockapp：周期性读取内核 CPU 计数（libgtop-2.0），用 GDK 把
user/nice/system/idle 比例画成一张 48x48 的火焰图，并以 X11 dock 窗口的形式停靠。

## OHOS 适配

- **移除硬编码 X11 路径**（补丁 `0001`）：上游 `src/Makefile.am` 写死
  `-L/usr/X11R6/lib -L/usr/local/lib` 及对应 `-I`，这些目录在 OHOS 上不存在且会
  覆盖 Conan 注入的搜索路径，改为完全由 `pkg-config` 决定。
- **`draw_fire` 链接修复**：`src/wmfire.c` 把 `draw_fire` 声明为 `inline` 而非
  `static inline`，clang -O3 不为非 static 的 inline 函数生成外部符号，链接报
  undefined symbol；构建期改写为 `static inline`。
- **autotools bootstrap**：tarball 只带 `configure.in` / `Makefile.am`，构建时
  生成 `configure` 并恢复辅助脚本可执行位 (ref: E490)。
- **安装产物**：`bin/wmfire` 归一化权限、移除 build RPATH（改由 LD_LIBRARY_PATH
  决定）、先删旧 `.codesign` 段再重新签名 (ref: E452)。

## 依赖

- `gtk2/2.24.33`（GDK/GTK+ 2，精确 pin `glib/2.84.0.1`）
- `libgtop/2.41.3`（libgtop-2.0 数据源）
- `libx11/6.4.0`、`libxext/6.4.0`
- `glib/2.84.0.1`（`force=True`，与 gtk2 同轨道）

**依赖轨道说明**：仓库把同一份上游 libgtop 源码打成了两个包——`libgtop/2.41.3`
在 glib 2.84 轨道，`libgtop2/2.41.3` 在 glib 2.88 轨道。由于 gtk2 精确 pin
glib/2.84.0.1，本配方必须选 `libgtop/2.41.3`；`libgtop2` 会被迫源码重建，且其
`cpp_info.libs` 缺少静态归档所需的 `intl`，链接必然失败 (ref: E508)。

## 功能验证

上游无测试套件（`Makefile.am` 未声明 `TESTS`，`make check` 是成功的空操作）。
本包提供鸿蒙具名端到端消费者用例 `test_package/src/hc_consumer.c`（HC-1..HC-4）：

- HC-1 `elf-contract`：已安装产物的 ELF 契约（ELF64/AArch64/PIE + `.codesign` + DT_NEEDED）
- HC-2 `loader-closure`：无 `DISPLAY` 下 exec 已安装的 `bin/wmfire`，要求加载器解析
  完整 DT_NEEDED 闭包且 `main()` 被执行到（`GDK init failed` + 退出码 255）
- HC-3 `x11-geometry-parse`：真实调用 `XParseGeometry()`（`-g` 选项同一入口）
- HC-4 `cpu-sample`：真实调用 `glibtop_init()` + `glibtop_get_cpu()`（在子进程中），
  用例写成与平台能力交叉校验的蕴含式：本进程可读 `/proc/stat` 时必须采到递增计数，
  被平台隐藏（鸿蒙 `/proc` 以 `hidepid=invisible,hmmac=genfs` 挂载）时必须按该错误
  明确拒绝而不是伪造计数

全部用例只走 exec-time DT_NEEDED 加载路径，不使用 `dlopen` (ref: E502)。
运行期闭包需做两处 OHOS 处理：依赖 soname 用 `cp -L` 摊平（E505），
平铺后的目录按 `LD_LIBRARY_PATH` 原有顺序以「先到先得」重建并注入工具链自带的
`libc++_shared.so`（`/data/storage/el1/bundle/libs/arm64` 下同名 7.5 MB 应用包运行库
在用户目录可执行文件上无法加载，会被平铺覆盖而误报缺库）。

## 参考

- 官网: https://www.improbability.net/wmfire/
