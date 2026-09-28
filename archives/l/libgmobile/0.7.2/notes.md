# libgmobile 0.7.2 适配笔记

## 基本信息

| 项 | 值 |
|---|---|
| 上游 | https://gitlab.gnome.org/World/Phosh/gmobile （Phosh 项目） |
| 归档 | `gmobile-v0.7.2.tar.gz`（GitLab `/-/archive/v0.7.2/`） |
| sha256 | `2566187fbd0974d1b1e8ee417935db526c8f65dad28807ab3a5244a5fa757c92` |
| 构建系统 | meson（>= 0.56.1） |
| 语言/标准 | C，`c_std=gnu11` |
| 许可 | LGPL-2.1-or-later |
| 构建日期 | 2026-09-20 |

## 依赖

| 组件 | 版本 | 说明 |
|---|---|---|
| glib | 2.84.0.1 | `glib-2.0 >= 2.78`、`gio-2.0 >= 2.78`；OHOS 上自带 proxy-libintl |
| json-glib | 1.10.6 | `json-glib-1.0 >= 1.6.2`；**运行期**依赖（面板 JSON 解析），不是构建期依赖 |
| meson | 1.11.0 | `tool_requires` |

`epoll-shim` 在 meson.build 里是 `required: false` 的可选项（给非 Linux 平台用），
OHOS 走原生 epoll，不引入。

## OHOS 上的三个非显然耦合

### 0.5 依赖包里的 SONAME 是符号链接（E073）

`meson test` 的 7 个程序**全部** `exit status 127`：

```
1/7 gmobile:cutout  FAIL  0.11s  exit status 127
Error loading shared library libjson-glib-1.0.so.0:
    (needed by .../build-release/src/libgmobile.so.0)
Error relocating .../libgmobile.so.0: json_from_string: symbol not found
Error relocating .../libgmobile.so.0: json_serializable_get_type: symbol not found
…（十几条 json_* 同理）
```

而 `LD_LIBRARY_PATH` 里**已经有** `.../p/json-01fc8e37bde89/p/lib`：

```
LD_LIBRARY_PATH=.../build-release/src:.../llvm/lib:.../mesonc731ddfc5b264/p/lib:
                .../glibcad7259522c98/p/lib:.../json-01fc8e37bde89/p/lib:...
```

所以不是「找不到」而是「找到了加载不了」。三种 errno 文本的鉴别：

| 现象 | 含义 |
| --- | --- |
| `... : No such file or directory` | 搜索路径上没有 |
| `... : Permission denied` | 有，但 ELF 没有有效 `.codesign` 段（E077 未签名） |
| `... : `（strerror 为空） | **有，但加载器解析不到实际库文件** —— 符号链接（E073） |

`json-glib/1.8.0` 包内三个名字只有一个是真的，**判据是
`conanmanifest.txt` 的 md5** —— Conan 对符号链接记的是**目标字符串**的 md5：

```
lib/libjson-glib-1.0.so:            884317035739cf2533e5d6d81d09ff44 == md5("libjson-glib-1.0.so.0")
lib/libjson-glib-1.0.so.0:          3fb7976d243736fd69a6c01702d8505a == md5("libjson-glib-1.0.so.0.1000.6")
lib/libjson-glib-1.0.so.0.1000.6:   e41b0e5d27417294c9a360e545e38a5d   ← 唯一的真文件
```

而 `libgmobile.so.0` 的 `DT_NEEDED` 用的正是**链接名** `libjson-glib-1.0.so.0`。
HMDFS 解析不了这类链接（E073）。

修法：`_stage_symlinked_sonames()` 把各依赖 libdir 顶层的符号链接展开成真文件
副本，放进 `<build>/conan-staged-soname-libs/`，**prepend 到 LD_LIBRARY_PATH
最前**（副本按字节复制，自带原签名）。依赖包在 Conan 缓存里只读且被其它包
引用，改不得，只能在消费侧补 —— 与 `libsigc/2.12.1`（E050/E073）、
`fluidsynth/2.5.7`、`libxft/2.3.8` 同属 E073 处置；同一依赖图里
`libgsystemservice` 的 polkit 也是同一处坑。

**通用教训**：`Error loading shared library X: (needed by Y)` 里 `X` 是 loader
正在解析的那个**直接依赖**；先看冒号后面那截 strerror **有没有内容**，空的
就是 E073，再去查该包的 `conanmanifest.txt`。

### 0. glib 的构建期 ELF 不能直接从包缓存里 exec

`glib/2.84.0.1` 把 `glib-compile-resources` 作为 **OHOS ELF** 装在包缓存的
`bin/` 下，但 HMFS 不允许从包缓存直接 exec 它：ninja 报

```
FAILED: data/gm-resources.h ...
/bin/sh: .../bin/glib-compile-resources: Operation not permitted
[code=126]
```

即 **EPERM，被 ninja 折成退出码 126**——不是找不到文件、也不是缺动态库
（缺库会报 `error while loading shared libraries`），更不是配方里 PATH 没配。
注意 126 与「命令存在但不可执行」同码，容易误判成权限位问题；实际 `chmod`
没用，需要**换一个可执行的位置 + 重签名**。

配方按仓库内 `glade/3.40.0`、`gnumeric/1.12.57` 的既有做法处理：
`_stage_glib_build_tools()` 把工具从包缓存拷到 `build_folder/conan-native-tools/`，
`chmod 755`，再
`llvm-objcopy --remove-section .codesign` 去掉旧签名段、用
`/data/service/hnp/bin/binary-sign-tool sign -selfSign 1` 就地自签名；
因为该 ELF 链接的是 conan glib 的 `.so`，再用一个 `sh` 包装脚本注入
`LD_LIBRARY_PATH` 并 `exec` 真身，pkg-config 变量指向**包装脚本**。

包装脚本注入的 `LD_LIBRARY_PATH` 用 `_dependency_libdirs()` 取**全部** host
依赖的 `lib`（glib 自己的 `lib` 排在最前），这样 glib-compile-resources 及
其一切继承环境的子进程都能解析到 conan 库。

上游只用到 `gnome.compile_resources()` 这一个 glib 工具
（`data/meson.build:1`，全树 `grep mkenums|genmarshal|compile_schemas` 无命中），
所以 glib 侧只需 staging `glib-compile-resources` 一个。

这里还踩过一个**看起来对、实际不通**的坑，详见「耦合 1」：一开始也给
`json-glib/1.10.6` 的 `bin/json-glib-format` 做了同样的 staging + 重签名，
并把 `JSON_GLIB_FORMAT` 指向重签后的真身 ELF。重签名确实让它通过了 HMFS 的
EPERM 检查，但**子进程自己的动态装载仍然失败**，最终放弃该路线、改由补丁
关闭 `json-stripblanks` 预处理。

### 1. json-stripblanks 走的是外部子进程，不是链接

`data/gmobile.gresources.xml` 里 34 个文件全部写了
`preprocess="json-stripblanks"`。常见的误判是「glib-compile-resources 链接了
json-glib」；实际检查 ohpcd 的 `glib/2.84.0.1` 制品：

```
bin/glib-compile-resources
  DT_NEEDED: libc.so libgio-2.0.so libgobject-2.0.so libglib-2.0.so libintl.so
  strings:   JSON_GLIB_FORMAT, json-stripblanks, json-glib-format
```

即 glib 是**把 `json-glib-format` 当子进程执行**的，二进制靠 PATH 查找
（可被环境变量 `JSON_GLIB_FORMAT` 覆盖）。这条链路在 OHOS 构建机上有两层障碍，
第二层在配方侧无解，最终只能让子进程**不再需要存在**。

**第一层**：`json-glib/1.10.6` 包缓存里的那份也是 OHOS ELF，HMFS 拒绝 exec。
CI 上实际挂掉的形态（PR #11556）：

```
FAILED: [code=1] data/gm-resources.h
../data/gmobile.gresources.xml: Failed to execute child process
".../json-01fc8e37bde89/p/bin/json-glib-format" (Operation not permitted).
```

注意它与「耦合 0」的 `[code=126]` 长得不一样（这里是 `code=1`），因为失败
发生在 glib-compile-resources 内部 `g_spawn` 的**子进程**里，由 glib 自己
报错退出，而不是 shell 报 `Operation not permitted`。

**第二层**（做了第一层的补救之后才暴露出来）：把工具拷到 build 目录重签名、
用 `JSON_GLIB_FORMAT` 指向这个已签的真身 ELF，EPERM 消失了，但换成装载期失败：

```
Error loading shared library libjson-glib-1.0.so.0:
  (needed by .../conan-native-tools/json-glib-format)
Error relocating .../json-glib-format: json_generator_new: symbol not found
../data/gmobile.gresources.xml: Child process exited with code 127.
```

`exit 127` 是 loader 找不到这个二进制的依赖库。给包装脚本/环境注入**全部**
依赖 `lib` 也没能解决——`g_spawn_sync` 派生方是 glib 内部 helper，
`LD_LIBRARY_PATH` 传不到那个位置，而 `glib-compile-resources` 是别人发布的
二进制，配方不该也无法改它。

**结论：不修补通道，而是取消需求。** 补丁
`patches/0001-gmobile-gresources-drop-json-stripblanks.patch` 把
`data/gmobile.gresources.xml` 里 34 个 `<file>` 上的
`preprocess="json-stripblanks"` 全部删掉。gmobile 在**运行期**用 JsonParser
解析这些 JSON（见 test_package 的第 2、3 号用例），空白与语义无关；该预处理
只是把内嵌资源压小一点的体积优化，去掉属于**行为等价**的取舍，换来构建链
不再依赖一个在本平台上跑不起来的子进程。

顺带说明另两个**看似可行、实际走不通**的方向：

- 给 glib 打补丁让它链接 libjson-glib：`json-stripblanks` 是上游 glib 的
  `--internal` 预处理约定，改它等于把 json-glib 变成 glib 的依赖，
  牵动依赖层，远超本包范围。
- 关掉 `data` 子目录：资源是 gmobile 的**核心交付物**
  （`gm_display_panel_new_from_resource()`、`gm_list_devices()` 全靠它），
  不能省。


### 2. PkgConfigDeps 生成的 glib .pc 需要就地增补

PkgConfigDeps 生成的 `.pc` 是简化版：没有 `glib_mkenums` / `glib_genmarshal`
之类的工具变量，也没有 `-lintl`。glib 在 OHOS 上带 proxy-libintl，但 glib
配方的 `package_info` 并未声明 `intl` 系统库，所以消费者侧会出现
`undefined reference to 'g_libintl_*'`。配方按 json-glib 的既有做法就地改
生成物（不碰制品）：补 `-lintl` 到 `Libs:`，并按 `glib-mkenums` 的实际位置
补工具变量。

其中 `gio-2.0.pc` 的 `glib_compile_resources` 是**必需的**，不是锦上添花：
meson 的 gnome 模块解析 `gnome.compile_resources()`（`data/meson.build:1`）
时走 `find_tool('glib-compile-resources', 'gio-2.0', 'glib_compile_resources')`，
其顺序是「overrides → machine file `[binaries]` → **pkg-config 变量** → 裸名
PATH 查找」。因为 pkg-config 变量这一档排在 PATH 之前，缺变量时 configure 会
直接以 `Could not get pkg-config variable and no default provided for
<PkgConfigDependency gio-2.0 ...>` 中止——**哪怕 `glib-compile-resources`
就在 glib 包的 `bin/` 里、也确实在 PATH 上**。这正是 `PkgConfigDeps` 生成的
简化 `.pc` 抢先于 glib 自带 `.pc`（`_append_dependency_pkg_config_paths()`
把 `generators_folder` 排在 `pkg_config_path` 首位）所掩盖的坑。

因为 meson 正是**从这个变量取值当命令**，它必须指向上面「耦合 0」里的
**包装脚本**而不是包缓存里的原 ELF——否则 configure 能过、build 期照样
`Operation not permitted`。两处修改（补变量 + 变量值指向 staging 脚本）
缺一不可。

## 补丁

| 补丁 | 目标 | 类型 | 说明 |
|---|---|---|---|
| `patches/0001-gmobile-gresources-drop-json-stripblanks.patch` | `data/gmobile.gresources.xml` | portability | 删去 34 个 `<file>` 的 `preprocess="json-stripblanks"`，使 `glib-compile-resources` 不再派生 `json-glib-format`（该子进程在本平台装载不了 libjson-glib）。JSON 由运行期 JsonParser 解析，空白无语义，属体积优化损失 |

## 打包边界

- `examples=false`：上游 `examples/meson.build` 里 3 个示例程序
  （`gm-timeout`、`gm-display-panel-preview`、`gm-display-panel-run-phosh`）都带
  `install: true`，默认会把可执行文件装进 `bin/`。它们是需要显示栈的演示程序，
  不是本包的交付物；关掉后包内容只剩 `lib/`（含 `libgmobile.so.0`）、
  `include/gmobile/`、`lib/pkgconfig/gmobile.pc` 与 udev/hwdb 数据文件。
- `hwdb=true`（上游默认）：`61-gmobile-wakeup.hwdb` / `61-gmobile-torch.hwdb` /
  `61-gmobile.rules` 装到 `lib/udev/`。纯数据文件，保留。
- `installed_tests=false`（上游默认）：不安装 `.test` 元数据（这是上游默认，
  与本包无关；`not_installed` 只在该选项为真时才起作用，见「测试」一节）。
- `introspection=false` / `vapi=false` / `gtk_doc=false` / `man=false`：分别
  需要 gobject-introspection、vala、gi-docgen、rst2man，OHOS 上均不提供，
  也不影响交付物（库 + 头文件 + .pc）。

## 测试

上游 `tests/meson.build` 注册 7 个测试程序、共 14 个 `g_test_add_func` 用例：

| 程序 | 用例数 | 说明 |
|---|---|---|
| test-cutout | 1 | 裁剪区路径/边界解析 |
| test-device-tree | 1 | 设备树 compatible 匹配（用 `tests/data/compatibles1|2` 夹具，不读 `/proc/device-tree`） |
| test-display-panel | 2 | 面板 JSON 解析 + corner-radii |
| test-mcc-mnc | 1 | MCC → ISO 国家码 |
| test-svg-path | 4 | SVG path 解析 |
| test-timeout | 2 | `gm_timeout_*` |
| test-utils | 3 | 断言宏 + `gm_list_devices()` |

配方在 `build()` 内执行 `meson test`，随后**回读** `meson-logs/testlog.txt`
的汇总块硬断言：`Fail` / `Timeout` / `Unexpected Pass` 必须为 0，`Ok` 必须
>= 7（`UPSTREAM_TEST_PROGRAMS`）。

为什么不只看退出码：automake/meson 的退出码 0 只说明「没有失败的用例」，
而 `Skipped`、以及「用例根本没被注册进 suite」同样会得到退出码 0。

## 验证结果

### 上游测试（`meson test`，build() 内全量执行）

- 7 个测试程序全部构建并执行，14 个用例全绿（7 Ok / 0 Fail / 0 Timeout /
  0 Unexpected Pass / 0 Skipped）。
- 汇总块由配方回读断言，不是依赖退出码。

### test_package（消费者视角，OHOS aarch64 真机运行）

`test.c` 覆盖三条互不重叠的路径，每条都配了反向对照：

| # | 测什么 | 断言 | 反向对照 |
|---|---|---|---|
| 1 | `gm_mcc_to_iso()` 编译进库的 MCC 表 | `"460"` → `"CN"`；IMSI 前缀 `"460001234567890"` → `"CN"` | `"abc"` 与 `"46"` 必须返回 NULL 且设置 GError |
| 2 | GResource 真的被编进去了 | `gm_list_devices()` >= 34 条且含 `purism,librem5`；`gm_display_panel_new_from_resource("/mobi/phosh/gmobile/devices/display-panels/purism,librem5.json")` → 名字 `Purism Librem 5`、720x1440 | 若资源未嵌入则 lookup 失败 |
| 3 | 传递依赖 json-glib 真的链上了 | 内联 JSON 解析出 68x145、corner-radii `[10,11,12,13]`、1 个 cutout | `"{ not json"` 必须返回 NULL 且设置 GError |

三号之所以有意义：`gm_display_panel_new_from_data()` 内部走
`json_from_string()`/`json_gobject_deserialize()`（libjson-glib），如果
打包时把 json-glib 的传递链接弄丢，正例会直接崩在符号解析上。
