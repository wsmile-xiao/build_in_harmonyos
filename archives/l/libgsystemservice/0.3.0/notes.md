# libgsystemservice 0.3.0 适配笔记

> 状态：**built**（Meson，OHOS clang，aarch64）。上游源码零补丁，四处平台耦合
> 全部在配方侧解决。上游 3 个测试程序 / 13 个用例全量执行；其中 2 个程序通过，
> 1 个（`peer-manager`）因 OHOS 沙箱不允许 AF_UNIX bind 而**如实声明失败**
> （不删、不 SKIP）。

## 软件简介

libgsystemservice 提供构建 **D-Bus 系统总线服务**所需的公共组件：

- `GssService`：`GObject` 派生（`G_DECLARE_DERIVABLE_TYPE`）的服务基类，
  负责命令行解析、抢占总线名、polkit 授权、systemd 就绪通知（`sd_notify`）、
  空闲超时、`SIGINT`/`SIGTERM` 处理与优雅退出；
- `GssPeerManager`：`GInterface`，按 D-Bus sender 查询对端进程的凭据
  （argv0 / pidfd / uid）；
- `GssConfigFile`：多文件 + GResource 默认值的分层配置文件读取器。

上游：`https://gitlab.gnome.org/pwithnall/libgsystemservice`（GNOME GitLab
project id 1180）。产物为共享库 `libgsystemservice.so.0`（soname 里的
"gsystemservice-0" 是上游 `libgsystemservice_api_name`），头文件装在
`include/gsystemservice-0/libgsystemservice/`。

> 路径坑：`GNOME/libgsystemservice` 这个 GitLab 路径**不存在**（API 404），
> 只有 `pwithnall/libgsystemservice` 命名空间下这一份。找 tag / 比对
> 默认分支时要认准 project id 1180。

## 上游版本确定

- 最新 tag：**0.3.0**，默认分支 `main`。
- 官方 tarball（实测可达，sha256 已实测核对）：
  `https://gitlab.gnome.org/pwithnall/libgsystemservice/-/archive/0.3.0/libgsystemservice-0.3.0.tar.gz`
  sha256 = `06dc0f8533fdfd6fa6acd96c76e2782a97ebbea9bb55fb7b82356dc065a21dcb`
  （43132 字节）
- 解出目录 `libgsystemservice-0.3.0/`，配方 `strip_root=True` 拉平。

## 依赖解析

| 上游 meson dependency | Conan 包 | 可见性 | 说明 |
|---|---|---|---|
| `gio-2.0 >= 2.71` / `glib-2.0 >= 2.44` / `gobject-2.0 >= 2.44` | `glib/2.84.0.1` | **public** | 三个头文件都 `#include <gio/gio.h>`，是唯一传给下游的依赖 |
| `libsystemd` | `systemd/261` | private | `service.c` 用 `sd_notify()` 做 READY=1/STOPPING=1 就绪通知 |
| `polkit-gobject-1` | `polkit/127` | private | `service.c` 用 `polkit_authority_check_authorization_sync()` 做授权 |

三个包均已发布到制品仓且状态 `built`。`meson/1.11.0` 作为 `tool_requires`
（仓库内 45 个 Meson 配方统一锚定的版本；1.11.0.1 无预编译二进制）。

## 适配点（五处，全在配方侧，**零补丁**）

### 1. 两个「名字对不上」的 pkg-config 依赖

上游私有依赖写的是 `dependency('libsystemd')` 与
`dependency('polkit-gobject-1')`，而 `PkgConfigDeps` 是按 **Conan 包名**
生成 `.pc` 的——生成出来的是 `systemd.pc` / `polkit.pc`，meson 找不到。

真正要找的东西是这两个**依赖包里自带的** `.pc`：`libsystemd.pc`、
`polkit-gobject-1.pc`。但它们的配方是用 `--prefix=/` + `DESTDIR` 装的，
`prefix=` 指向 `/`，照搬过去会让 `-I${includedir}/polkit-1` 解析到 `/polkit-1`。

配方（`_alias_dependency_pc()`）的做法：从依赖包里把这两份 `.pc` 找出来
（依次找 `lib/pkgconfig`、`share/pkgconfig`），把 `prefix=` 改写成实际包目录，
写到 `generators_folder`——它排在 meson `pkg_config_path` 的第一位，必然优先命中。
同一套路见 `archives/a/accountsservice/26.27.3`（那里是 polkit 的同一份 `.pc`）。

**但 `systemd/261` 是特例：已发布的二进制包里 `lib/pkgconfig/` 是空的。**
`polkit/127` 自带 `polkit-gobject-1.pc`，能按上面的路走；systemd 那份没有，
所以 CI 里先是

```
libgsystemservice/0.3.0: WARN: libsystemd.pc not found in the systemd package
../libgsystemservice/meson.build:26:2: ERROR: Dependency "libsystemd" not found (tried pkg-config and cmake)
```

**为什么缺**：systemd 配方的 `build()` 只构建 `libsystemd` 目标、刻意不走
`meson.install()`（全量 install 会触发 1281 个目标而超时），而 meson 的
`pkg.generate()` 产物只有当对应目标被构建时才落到 `<build>/libsystemd.pc`；
配方 `package()` 里

```python
pc_src = os.path.join(self.build_folder, "libsystemd.pc")
if os.path.isfile(pc_src):   # ← 没生成就静默跳过
```

因此悄悄没装上。这不是本包能改的（改它属于"动别人的包"），所以由消费者兜底：
配方在复制失败时改走 `_synthesize_libsystemd_pc()`，按包内真实布局
（`include/systemd/sd-*.h` + `lib/libsystemd.so`）合成一份最小 `.pc`——
`Version` 取自依赖自身的 `ref.version`（满足上游 `>=227`），
`Cflags: -I${includedir} -I${includedir}/systemd`
（上游以 `#include <systemd/sd-daemon.h>` 引用，故 `-I${includedir}` 必需；
后一项与 systemd 自己那份 `.pc` 的 `subdirs` 行为一致）。
同一处坑在 `archives/l/libratbag/0.18` 也踩到过，用的是同一套做法。

### 2. glib 的 proxy-libintl

OHOS 上 glib 与它的 `proxy-libintl` 子项目一起构建，`g_libintl_*` 符号就在
glib 包里，而 glib 配方的 `package_info` 没有声明 `intl` 系统库。于是
`PkgConfigDeps` 生成的 `glib-2.0.pc` 里没有 `-lintl`，消费者会
`undefined reference to 'g_libintl_*'`。配方 `_augment_glib_pkg_config()`
就地增补生成的 `.pc`（补 `-lintl` 与 glib 工具变量），`_glib_libintl_link_args()`
再把 libintl 的绝对路径加进 `c_link_args`。

### 3. meson 机器文件里的 `ar` / `ranlib` / `pkg-config`

`MesonToolchain` 生成的 `conan_meson_native.ini` 在 OHOS worker 上
`[binaries]` 段缺这三项，配方 `_inject_meson_tools()` 从 `conf` 与已知 SDK
路径补注入。

另外两处「不装/不测」的开关：`gtk_doc=false`（上游默认 true，需要 gtk-doc
工具链，OHOS 没有）与 `installed_tests=false`（上游默认即 false；它只门控
`*.test` 元数据是否安装，**不影响测试是否执行**，见下）。

### 4. `gnome.compile_resources()` 要的工具变量不在生成的 `gio-2.0.pc` 里

上游 `tests/meson.build:16` 用

```meson
config_file_resources = gnome.compile_resources(
  'config-file-resources', 'config-file.gresource.xml',
  c_name : 'config_file_resources')
```

meson 1.11.0 的 `gnome` 模块在 `_find_tool()`（`mesonbuild/modules/gnome.py`）
里把工具名映射到它所归属的 pkg-config 模块：

```python
tool_map = {
    'gio-querymodules': 'gio-2.0',
    'glib-compile-schemas': 'gio-2.0',
    'glib-compile-resources': 'gio-2.0',
    'gdbus-codegen': 'gio-2.0',
    'glib-genmarshal': 'glib-2.0',
    'glib-mkenums': 'glib-2.0',
}
depname = tool_map[tool]
varname = tool.replace('-', '_')
return state.find_tool(tool, depname, varname, native=...)
```

（注意映射与直觉相反：`glib-*` 里只有 `glib-mkenums` / `glib-genmarshal`
挂 `glib-2.0`，其余四个都挂 `gio-2.0`。）

`ModuleState.find_tool()`（`mesonbuild/modules/__init__.py`）的查找顺序是：

1. 子项目 overrides；
2. **机器文件 `[binaries]` 段的同名条目**（`environment.lookup_binary_entry`）；
3. **`dep.get_variable(pkgconfig=varname)` —— 没有 default 参数**；
4. `find_program()`。

第 3 步就是失败点。`PkgConfigDeps` 生成的 `.pc` 只写 `Cflags` / `Libs`，
**不带任何工具变量**（这正是上游 glib 自己 `glib-2.0.pc.in` 里
`glib_mkenums=…` / `glib_genmarshal=…` 那一类行），于是 meson 直接抛：

```
../libgsystemservice/tests/meson.build:16:30: ERROR: Could not get pkg-config
variable and no default provided for <PkgConfigDependency gio-2.0: True ['>= 2.71']>
```

（`True` 是 `native=True`——`_find_tool` 对非 gobject-introspection 的工具
一律按 build 机器查依赖，所以命中的是 native 机器文件的 `pkg_config_path`。）

修法沿用第 2 节已有的思路：`_augment_glib_pkg_config()` 本来就是往
`generators_folder` 里那几份生成的 `.pc` 尾部追加 `工具名=staging路径`
（值取 `_prepare_glib_build_tools()` 拷出来并重签的副本，因为 glib 包缓存
里的原件在 HMFS 上不可执行）。这里只需把 `gio-2.0.pc` 补进映射表：

```python
entries = {
    "glib-2.0.pc":    ["glib_mkenums", "glib_genmarshal", "gobject_query"],
    "gobject-2.0.pc": ["glib_mkenums"],
    "gio-2.0.pc":     ["glib_compile_resources", "glib_compile_schemas",
                       "gio_querymodules", "gdbus_codegen"],
}
```

`-lintl` 的增补同时收窄为只作用于 `glib-2.0.pc` / `gobject-2.0.pc`——`gio`
本身不引用 `g_libintl_*`，给它挂上只会让每个消费者的 gio 链接行多一个
无谓的 `-lintl`。

### 5. 测试运行环境要挂 `/system/lib64`（polkit 的 `libz.so` 只能来自系统）

CI #62298（PR #11565）三个 meson 测试程序**全部** `exit status 127`：

```
1/3 libgsystemservice:config-file  FAIL  0.07s  exit status 127
Error loading shared library libpolkit-gobject-1.so.0:
    (needed by .../build-release/libgsystemservice/libgsystemservice-0.so.0)
Error relocating .../libgsystemservice-0.so.0: polkit_authority_get_sync: symbol not found
Error relocating .../libgsystemservice-0.so.0: polkit_system_bus_name_new: symbol not found
…（polkit_authority_check_authorization_sync / polkit_authorization_result_get_is_authorized 同）
```

链路是：`libgsystemservice-0.so.0` → NEEDED `libpolkit-gobject-1.so.0` →
（该库自己 NEEDED）**`libz.so`** + `libc.so`。判据是**实测包内容**而不是猜：

* `polkit/127` 的 `lib/libpolkit-gobject-1.so.0` 是合法 aarch64 ELF，
  `SONAME=libpolkit-gobject-1.so.0`，`DT_NEEDED` 只有 `libz.so`、`libc.so`
  （glib / expat / duktape 都静态链进去了），无 `RPATH`/`RUNPATH`；
* 而 ohpcd 上 `zlib/1.3.1(\.1)` 的**唯一**二进制包 `lib/` 下只有 `libz.a`
  ——**没有任何 `libz.so`**；CI 日志里 zlib 也进了 `Skipped binaries`
  （本依赖图不带它的二进制），所以 meson test 的 `LD_LIBRARY_PATH`
  （清一色是 conan 依赖的 `lib/`）里没有 `libz.so` 的任何来源；
* OHOS 上 conan-run 的库路径**默认不含系统库目录**（`avahi-ui/0.8`
  为 `libc++_shared.so` 补 `/system/lib64`、`alkimia/8.2.1` 同款），
  `libz.so` 只能从 `/system/lib64` 来。

于是 `_build_environment()` 在 OHOS 上追加系统库目录：

```python
if self.settings.os == "OHOS":
    environment.append_path("LD_LIBRARY_PATH", "/system/lib64")
```

两个细节：

1. **append 而不是 prepend**。`/system/lib64` 排在所有 conan 依赖之后，
   避免系统里的同名库（glib / expat / …）顶掉 conan 的那份——
   conan 图的 glib 是 2.84.0.1，与系统 glib 不是同一 ABI 代际
   （`baloo/26.04.3` 对系统 Qt 用了同一条理由）。
2. loader 报的是**"正在解析的那个直接依赖"**（`libpolkit-gobject-1.so.0`，
   parent 为 `libgsystemservice-0.so.0`），被它拖住的 `libz.so` 不会单独
   点名——所以不能只看被点名的库名去归因，"缺的是谁"要从
   `DT_NEEDED` + 实际包内容反推。

> ⚠️ **这一节的结论是错的，只保留推理过程供对照**：挂上 `/system/lib64`
> 之后 CI 仍报**一模一样**的错（见下一节）。真因不是缺 `libz.so`，而是
> `libpolkit-gobject-1.so.0` 是个**符号链接**（E073）。`/system/lib64`
> 这一行保留，但它服务的是另一个（真实存在的）`libz.so` 依赖，**不是**
> 本条报错的解药。

### 5.1 真因：依赖包里的 SONAME 是符号链接（E073）

补上第 5 节之后，CI #62306（PR #11565）的三个测试程序依旧全挂、
`exit status 127`，报错与 #62298 **逐字相同**：

```
Error loading shared library libpolkit-gobject-1.so.0:
    (needed by .../build-release/libgsystemservice/libgsystemservice-0.so.0)
Error relocating .../libgsystemservice-0.so.0: polkit_authority_get_sync: symbol not found
```

`LD_LIBRARY_PATH` 里明明已经有 `.../p/polki5512206552703/p/lib`（含
`/system/lib64`），同一个错误却一字未变 —— 说明不是「找不到」，而是
「找到了但加载不了」。三种 errno 文本的鉴别：

| 现象 | 含义 |
| --- | --- |
| `... : No such file or directory` | 搜索路径上没有 |
| `... : Permission denied` | 有，但 ELF 没有有效 `.codesign` 段（E077 未签名） |
| `... : `（strerror 为空） | **有，但加载器解析不到实际库文件** —— 符号链接（E073） |

**判据是 `conanmanifest.txt` 的 md5**：Conan 对符号链接记的是**目标字符串**
的 md5，所以

```
lib/libpolkit-gobject-1.so:   77d3b7c8b176bbbfff1f5100a0ee4314 == md5("libpolkit-gobject-1.so.0")
lib/libpolkit-gobject-1.so.0: d2edb620a9e0d008e76e1d70d9f0a201 == md5("libpolkit-gobject-1.so.0.0.0")
lib/libpolkit-gobject-1.so.0.0.0: b341322b6efc149c9d4dcf00138d4ae1   ← 唯一的真文件
```

前两条一眼可判是链接；而 `libgsystemservice-0.so.0` 的 `DT_NEEDED` 用的正是
**链接名** `libpolkit-gobject-1.so.0`。`libpolkit-agent-1.so.0` 同款。
`json-glib-1.8.0`（libgmobile 的依赖）也是这个布局
（`libjson-glib-1.0.so.0 == md5("libjson-glib-1.0.so.0.1000.6")`）。

修法：`_stage_symlinked_sonames()` 把各依赖 libdir 顶层的符号链接展开成真文件
副本，放进 `<build>/conan-staged-soname-libs/`，并 **prepend 到
`LD_LIBRARY_PATH` 最前**（副本按字节复制，自带原签名）。依赖包在 Conan 缓存里
只读且被其它包引用，改不得，所以只能在消费侧补 —— 与 `libsigc/2.12.1`、
`fluidsynth/2.5.7`、`libxft/2.3.8` 的处置同属 E073。

**通用教训**：`Error loading shared library X: (needed by Y)` 里，`X` 是
loader 正在解析的那个**直接依赖**；不要顺着 `DT_NEEDED` 往下猜"缺的是谁"，
先看冒号后面那截 strerror **有没有内容** —— 空的就是 E073。

## 上游测试与验证结果（rule4 口径）

`libgsystemservice/tests/meson.build` 的 `test_programs` 列表注册 3 个
`test()` 程序：

| 程序 | 用例数（`g_test_add`） | OHOS 上结果 |
|---|---|---|
| `config-file` | 9 | **通过** |
| `peer-manager` | 2 | **失败**（沙箱限制，见下） |
| `service` | 2 | **通过** |
| 合计 | **13** | 11/13 用例、2/3 程序 |

**上游默认分支 `main` 与 tag `0.3.0` 的 `libgsystemservice/tests/` 逐文件一致**
（GitLab API 比对四个文件的行数 / `g_test_add` 数完全一致），因此不存在
「main 比 tag 多几个用例」的差额需要解释。

### 为什么 `peer-manager` 在 OHOS 上必然失败（如实声明，不是跳过）

它的 fixture 调 `g_test_dbus_new (G_TEST_DBUS_NONE)` + `g_test_dbus_up ()`，
也就是要拉起一个**私有 `dbus-daemon` 在 AF_UNIX socket 上监听**。两条路都断了：

1. OHOS 沙箱**拒绝 AF_UNIX bind**（`Operation not permitted`），已记录在
   `archives/d/dbus/1.14.10.2/manifest.yaml`；
2. 已发布的 `dbus/1.14.10` 只构建客户端库，**不含 `dbus-daemon` 二进制**
   （`dbus/1.14.10.1` 才加 `bin/dbus-daemon`，但那个版本没有随本包引入）。

所以该程序**仍然被构建、被执行**（不是 SKIP、也没有从 `tests` 列表里删），
失败在配方里是「**允许但必须核对身份**」：

- 硬判据：`Fail` 数不得超过「已声明的受阻程序数」（=1），且失败的那个程序名
  必须就是 `peer-manager`；`Timeout` / `Unexpected Pass` 必须为 0；
  `Ok` 必须 ≥ 2 且 `config-file`、`service` 必须出现在测试日志里；
- 软判据：失败文本若命中已知的「无 session bus」标记（`dbus-daemon`、
  `Failed to execute child process` …）记一条 info，否则只 `warning`。

失败文本之所以只当诊断、不当门禁：读 GLib 2.84 的 `gio/gtestdbus.c`
`start_daemon()` 可知，它在 `g_spawn_async_with_pipes_and_fds()` 之后直接
`g_assert_no_error (error)`——**没有 dbus-daemon 时进程直接 abort**（消息为
`Failed to execute child process “dbus-daemon” (No such file or directory)`），
而**有 dbus-daemon 但 bind 被拒时**会走另一条未加防护的路径（读取地址失败后
可能解引用空指针）。两条路给不出稳定的错误文本，把文本当硬门禁会产生假阴性。
真正的保护是「**失败数量 + 失败身份**」，这一条是硬的。

### 判据：回读汇总块，不吃退出码

`meson test` 的退出码 0 只说明「没有失败」——用例被 SKIP、或 `test()`
根本没注册，退出码同样是 0。配方在 `build()` 里跑完套件后**回读**
`meson-logs/testlog.txt` 的汇总块（`Ok:` / `Expected Fail:` / `Fail:` /
`Unexpected Pass:` / `Skipped:` / `Timeout:`）并硬断言；汇总块读不到
（文件缺失或格式变更）也抛异常——「读不到结论」不等于「结论是好」。

### 适配后测试统计

- **上游**：3 个 meson 测试程序 / 13 个 `g_test_add` 用例
- **本平台实测**：3 个程序全部被构建并执行（执行集 3/3 = 100%），
  其中 2/3 程序通过、11/13 用例通过
- **通过率**：程序口径 **66.7%**，用例口径 **84.6%**（均 > 50%）
- **test_package（消费者视角）**：`test.c` 47 个 `CHECK` 断言，覆盖
  GObject 类型注册、两个 error domain 与退出码映射、`GssConfigFile` 的
  路径列表优先于 resource 默认值（含 strv/boolean/string/uint 取值、越界
  校验反向对照、非法文件解析错误反向对照、组去重排序）、继承 `GssService`
  的 derivable class 并做属性往返与「未运行态」检查。

`peer-manager` 的通过率缺口是**平台沙箱限制**导致，不是适配缺陷：同样的
配方在允许 AF_UNIX 且 PATH 里有 `dbus-daemon` 的 Linux 主机上，该程序
即可通过（其失败路径与 OHOS 无关）。

## 验证命令

```bash
# 库与头文件
ls $PKG/include/gsystemservice-0/libgsystemservice/{config-file.h,peer-manager.h,service.h}
ls $PKG/lib/libgsystemservice.so.0

# 上游测试汇总块（build() 内自动断言）
sed -n '/^Ok:/,/^Timeout:/p' <builddir>/meson-logs/testlog.txt
#   → Ok:                    2
#     Fail:                  1        (peer-manager，已声明)
#     Timeout / Unexpected Pass / Expected Fail: 0

# 消费者视角
./test_libgsystemservice      # → "…: 47 checks, 0 failed"
```

## 已知限制

1. **`peer-manager` 无法在 OHOS 上执行**：需要私有 session bus（AF_UNIX
   bind + `dbus-daemon`），沙箱不允许且 OHOS 侧没有 `dbus-daemon`。
   影响面：该包本身只是**库**，运行时依赖总线的是使用它的服务
   （如 accountsservice/26.27.3 那类 daemon）；库的编译、链接、符号导出
   与无总线的 API 路径均已在本平台实测通过。
2. **`gss_service_run()` 未在 OHOS 上做真机端到端验证**：它要抢占系统总线名，
   需要真实 system bus 与 polkit authority，本环境不具备。配方只验证到
   「服务对象可构造、属性可读写、未运行态 getter 返回值正确」。
3. **权限相关用例可能自跳过**：`config-file` 的 `unreadable` 用例在
   有 `CAP_DAC_OVERRIDE`（如以 root 运行）时会自行 SKIP。配方不要求
   `Skipped == 0`，因此该跳过不会造成假通过，也不会造成误报失败。
