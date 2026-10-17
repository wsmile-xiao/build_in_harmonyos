# libao-pulse 1.2.2 — HarmonyOS PC 适配笔记

## 1. 这个包是什么

上游 libao 是 Xiph 的跨平台音频输出库：`libao.so` 本身只带 `null/wav/raw/au` 等
文件类驱动，真正的硬件后端都是 `dlopen` 的插件模块，装在
`<libdir>/ao/plugins-4/lib*.so`。本任务（13044）只做 **PulseAudio 那一支**：
包名 `libao-pulse`，交付 `libao.so.4.1.1` + `lib/ao/plugins-4/libpulse.so`，
不打包 OSS 等其它驱动。

已归档的 `archives/l/libao/1.2.2` 是库本体（文档 + 生成物补丁，无配方）；
本目录是它的 PulseAudio 可构建变体。

## 2. 配方结构

- 源码：官方 git-archive `libao-1.2.2.tar.gz`，sha256
  `df8a6d0e…e2bf4d`（`conandata.yml` 校验）。
- 这个 tarball **没有 `configure`**，只有 `configure.ac`/`Makefile.am`，
  所以 `build()` 先跑 `autoreconf -fi`；`automake/1.18`、`libtool/2.5.4` 作为
  `tool_requires`（镜像里只有 hnp 的 autoconf 套件，且已安装的
  aclocal/automake 把 autoconf/autom4te/sed 的绝对路径写死，需要
  `_prepare_autotools_env()` 重新指向 PATH 上的实现）。
- `config.guess` 不认 HarmonyOS（`uname -s` = `HarmonyOS`），`--build`/`--host`
  显式给 `aarch64-unknown-linux-ohos`，libtool/2.5.4 的 `config.sub` 接受该三元组。
- 生成的 `configure` 里 `umask 077` 会被改写掉：HMDFS 强制 setgid，
  `umask 077 && mktemp -d` 得到的目录是 `drwx--S---`，属主自己也写不进去（E114）。
- `make` 固定 `-j1`（E074：HMDFS 的 jobserver fifo 返回 EPERM）。

## 3. 三个真正花时间的坑

### 3.1 configure 的「C 编译器可用吗」探针被依赖库拖死

`AutotoolsDeps` 会把每个依赖库都塞进 `LIBS`，而 configure 的每个探针程序都会
链接 `LIBS`。制品仓里发布的 `pulseaudio/17.0.1` 二进制**没有 `.codesign` 段**，
OHOS 加载器拒绝映射这类对象，于是最基础的探针直接：

    configure: error: cannot run C compiled programs
    ... Error loading shared library libpulse.so.0

处理：OHOS 分支给 configure 传 `LIBS=`（autoconf 的 precious variable，命令行
赋值合法且会 export）。探针不再链接任何外部库；插件自己的链接由
`src/plugins/pulse/Makefile` 里的 `$(PULSE_LIBS)` + `AutotoolsDeps` 提供的
`-L<abs libdir>` 完成。

### 3.2 pkg-config 看不见 pulseaudio 包（插件根本没被编译）

`configure.ac:455`：

    PKG_CHECK_MODULES(PULSE, [ libpulse-simple >= 0.9 ], [have_pulse=yes],[have_pulse=no])

而 `src/plugins/Makefile.am` / `src/plugins/pulse/Makefile.am` 都用
`if HAVE_PULSE` 决定是否产出 `libpulse.la`。第一次跑出来的是：

    PULSE live output: ........... no      # config.log 里 have_pulse=no
    package(): Packaged ... libao.so, liboss.so      # 没有 libpulse.so

关键细节：新版 pkg.m4 的 `_PKG_CONFIG` 会优先使用预置的 `PULSE_CFLAGS`/
`PULSE_LIBS`，但本镜像 autoconf-2.72 展开出来的是**老式分支**
（`if $PKG_CONFIG --exists " libpulse-simple >= 0.9 "`），预置变量完全不生效——所以「直接 define PULSE_CFLAGS/PULSE_LIBS」这条捷径无效，必须让
`pkg-config --exists` 真的成功。

-> 令 `PKG_CONFIG_PATH=<pulseaudio.package_folder>/lib/pkgconfig`。
但这样还有第二个问题：包里的 `.pc` 是 `prefix=/`（配方安装到 staging prefix），

    prefix=/ ; libdir=/lib ; includedir=/include
    Cflags: -I${includedir} -D_REENTRANT

只设 `PKG_CONFIG_PATH` 会得到 `-I/include -L/lib`。再补
`PKG_CONFIG_SYSROOT_DIR=<pulseaudio.package_folder>`，pkg-config 会把
`-I`/`-L` 重新挂到包目录上：

    checking for  libpulse-simple >= 0.9 ... yes
    checking PULSE_CFLAGS... -D_REENTRANT -I/data/…/pulseb0aa67ffdfbf2/p/include
    checking PULSE_LIBS... -lpulse-simple -pthread -lpulse -pthread

（`-L/lib` 被 pkg-config 当系统目录过滤掉了，链接时的 `-L` 由
`AutotoolsDeps` 的 `LDFLAGS` 提供。）

### 3.3 插件目录是 configure 时写死的，Conan 缓存里找不到

`src/audio_out.c` 里 `AO_PLUGIN_PATH` 由 `@plugindir@` 注入，而
`configure --prefix=/` 让它变成 **`/lib/ao/plugins-4`**。这对「并入根文件系统」
的安装是对的，但：

- 包还在 Conan 缓存里时，插件实际在 `<pkg>/lib/ao/plugins-4`；
- 设备上 `/lib` 是 `/system/lib` 的只读软链（`mkdir -p /lib/ao` ->
  `Read-only file system`），测试无法把插件摆到那个位置。

于是 `patches/0001-ao-plugin-path-env-override.patch` 让 `AO_PLUGIN_PATH`
环境变量可以覆盖该目录；**只接受绝对路径**，未设置、为空或相对路径时行为与
上游完全一致（评审建议的最小加固，见 §7）。测试脚本两次运行都把
`AO_PLUGIN_PATH` 指向被测包的 `lib/ao/plugins-4`。

## 4. 只留 PulseAudio 一个驱动

`--enable-pulse` 是显式请求；`esd/arts/nas/alsa` 默认 opt-out，直接
`--disable-*` 掉（日志里它们本来也都是 no），避免去探测宿主库。

容易忽略的是 **OSS**：它没有 `AC_ARG_ENABLE`，`configure.ac:268-271` 只要有
`<sys/soundcard.h>` 就 `have_oss=yes`——OHOS sysroot 里这个头文件是存在的，
于是第一版把 `liboss.so` 一起打了进去。处理办法是不动上游源码，用 autoconf
的 cache 变量：

    ac_cv_header_sys_soundcard_h=no ac_cv_header_machine_soundcard_h=no

（`AC_CHECK_HEADERS` 生成的探针遇到已设置的 cache 变量会直接复用，不会再编译。）
结果是 `OSS live output: no`、`PULSE live output: yes`，包里只剩
`libao.so` 与 `libpulse.so` 两个 `.so`。

## 5. 真机验证（conan create 全绿）

    PULSE live output: ........... yes
    OSS live output: ............. no
    package(): 2 '.so' files: libao.so, libpulse.so
    [test] libao-pulse test_package: 12 passed, 0 failed
    libao-pulse consumer checks: 8/8 passed
    CREATE_RC=0

test.sh 覆盖：安装布局（`lib/libao.so.4.*`、`lib/ao/plugins-4/libpulse.so`、
`lib/pkgconfig/ao.pc`）、ELF 契约（AArch64、SONAME `libao.so.4`、两个产物
都带 `.codesign`、插件 `DT_NEEDED` = `libpulse-simple.so.0` +
`libpulse.so.0` + `libc.so`），以及两次运行：
第一次用制品仓自己的 pulseaudio（预期加载失败，记录现状），第二次
`LD_LIBRARY_PATH` 指向已签名的平台客户端库
（`/system/lib64/libpulseaudio.z.so`、`libpulse-simple.z.so` 的软链）。

consumer 8 条断言里最关键的一条是 **pulse driver registered**：libao 必须真的
`dlopen` 插件并让驱动注册进驱动表（`driver[0] = pulse`，null/wav/raw/au 之后），
这同时证明了 `patches/0001` 生效。另一条有判别力的断言是
`ao_open_live(-1, ...) == NULL`（无效驱动 id 不得交出设备句柄），
以及「驱动已注册但无服务端」分支要求 pulse 驱动的 `ao_info->type == AO_TYPE_LIVE`。

## 6. 已知限制

- 真机上没有 PulseAudio 服务端，所以 `ao_open_live(pulse)` 返回 `NULL`；
  consumer 在「插件已注册但拿不到设备」这一分支断言 pulse 驱动的类型必须是
  `AO_TYPE_LIVE`（即确实是一个实时输出驱动，属预期）。
- 发布包里的 `pulseaudio/17.0.1` 缺 `.codesign`，OHOS 加载器不会映射它；
  真机运行插件需要平台自带的已签名客户端库（名字不同，需软链成
  `libpulse.so.0`/`libpulse-simple.so.0`）。这是依赖包的现状，不是本包的补丁能解决的。
- `docs/`（HTML 手册）与 `share/aclocal/ao.m4`、`lib/ckport/db/libao.ckport`
  一并安装，未做裁剪。

## 7. 评审意见处理（MR 12887）

MR 12887 的自动审查给了 1 条 P2 + 2 条 P3，全部已处理：

| 级别 | 意见 | 处理 |
|------|------|------|
| P2 | `libao_pulse_consumer.c` 的 `CHECK(pulse >= 0 \|\| device == NULL, ...)` 是恒真断言（`device` 只在 `pulse >= 0` 分支被赋值），虚增断言数、无法检出回归 | 删除该恒真断言，改为两条有判别力的断言：`ao_open_live(-1, ...) == NULL`（无效驱动 id 必须失败），以及按环境分支判定（无驱动 → 必须无设备；有驱动无服务端 → 驱动必须是 `AO_TYPE_LIVE`；有服务端 → `ao_play` 必须接受缓冲区） |
| P3 | `test.sh` 在 `set -euo pipefail` 下 `CORE=$(ls "$PKG"/lib/libao.so.4.* \| head -1)` 无匹配即中止，后面的 `bad "libao.so.4 missing"` 诊断分支不可达 | 命令替换加 `|| true`；并新增 `readelf_out()` 包装（内部 `|| true`）把 5 处 readelf 探针改为非致命，缺失产物时由 `check_contains` 报出明确的 FAIL 而不是让脚本静默中止 |
| P3 | `patches/0001` 允许环境变量覆盖 dlopen 插件目录，存在被劫持的加固空间 | `_ao_plugin_path()` 改为**只接受绝对路径**（`override[0] == '/'`），未设置/为空/相对路径都退回编译期路径；`conandata.yml` 的 `patch_description` 同步说明 |

修改后重新在真机跑了完整 `conan create`（见 §5），并已用 `git apply --check` 在
上游 `src/audio_out.c` 上验证新补丁可干净应用、结果与预期逐字节一致。
