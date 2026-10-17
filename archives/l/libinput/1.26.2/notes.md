# libinput 1.26.2 适配笔记（HarmonyOS PC / aarch64）

## 编译环境

- 构建系统: **meson**（上游 `meson_version : '>= 0.56.0'`，`c_std=gnu99`）
- 编译器: clang / clang++（OHOS SDK 26.0.0.18，`ohos-aarch64` profile）
- 依赖: libevdev/1.13.7、mtdev/1.1.7、eudev/3.2.14（提供 libudev）
- 补丁: **1 个** — `patches/0001-ohos-libc-portability.patch`（见下「源码修改」）

## 编译步骤

```bash
conan create archives/l/libinput/1.26.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方内部（`generate()` → `build()` → `package()`）：

```bash
meson setup <build> \
  -Ddefault_library=shared \
  -Dlibwacom=false -Ddebug-gui=false \
  -Dtests=false -Dinstall-tests=false -Ddocumentation=false \
  -Dlibexecdir=libexec          # 见问题 8，必须显式指定
ninja -C <build>
meson install -C <build>
# 然后对包内每个 ELF 重新签名（见问题 10）
```

## 依赖链（关键：libudev 从哪来）

上游 `meson.build:146` 是 **硬要求、无 fallback 分支**：

```meson
dep_udev = dependency('libudev')
dep_mtdev = dependency('mtdev', version : '>= 1.1.0')
dep_libevdev = dependency('libevdev')
```

而 ohpcd 里 **没有独立的 `libudev` 包**（实查 0 条）。可用的提供者有两个：

| 包 | ohpcd 版本 | 是否提供 libudev |
|---|---|---|
| `eudev` | 3.2.14 | ✅ 配方内 `set_property("pkg_config_name", "libudev")` |
| `systemd` | 261 | ✅ 同样提供 |

本配方选 **eudev**（轻量、专注 udev，不引入整个 systemd）。`PkgConfigDeps` 据其
`pkg_config_name` 生成 `libudev.pc`，meson 的 `dependency('libudev')` 即命中。

> **这条纠正了 main 上 1.26.0 的结论。** 软件级 `manifest.yaml` 当时记录
> 「libudev stub 不完整 / 需要 eudev 或完整的 libudev 实现」——方向是对的，
> 但当时的做法是自己写 stub 而没有使用 ohpcd 里已存在的 eudev，于是卡住。
> 改用 eudev 后该阻塞点不存在。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `src/util-strings.c` 链接期 `undefined symbol: rindex` | `rindex()` 是 strrchr() 的 BSD 别名，OHOS musl 不提供（实测 `nm -D libc.so` 只有 `strrchr`） | 补丁改为 POSIX 的 `strrchr()` |
| 2 | `tools/*.c` 编译期 `use of undeclared identifier 'program_invocation_short_name'` | 该标识符是 **glibc 扩展**，OHOS musl 不提供；musl 提供语义一致的 BSD `__progname` | 补丁内 `extern char *__progname;` + `#define program_invocation_short_name __progname`（与仓内 `elfutils 0.195` 的既有做法一致） |
| 3 | `dependency('libudev')` 找不到 | ohpcd 无独立 libudev 包 | `requires("eudev/3.2.14")`，靠其 `pkg_config_name=libudev` 生成 `.pc` |
| 4 | `dependency('libwacom')` 找不到 | ohpcd 无 libwacom | `-Dlibwacom=false`；上游对此有 no-op fallback（`meson.build:161-166`），功能损失仅限「数位板型号识别」 |
| 5 | `libinput debug-gui` 需要 GTK4 | 不需要该工具 | `-Ddebug-gui=false` |
| 6 | `/tmp` 只读（E002） | HarmonyOS `/tmp` 是只读 erofs | `_ensure_tmpdir()` 把 `TMPDIR` 指到可写目录 |
| 7 | meson 可能取到宿主 `ar`/`ranlib` | 未显式指定 | `_inject_ar_ranlib()` 从 profile 的 `compiler_executables` 注入 OHOS LLVM 的 `llvm-ar`/`llvm-ranlib` |
| 8 | **`meson install` 报 `Destination '.../bin/libinput' already exists and is not a file`** | Conan 的 `MesonToolchain` **把 `libexecdir` 硬编码成 `bindir`**（`conan/tools/meson/toolchain.py:358` `'libexecdir': bindir`）。于是上游两个安装目标撞在同一路径：主命令 `libinput` → `$prefix/bin/libinput`（**文件**），而 7 个子工具 → `$prefix/libexec/libinput/`（**目录**） | `tc.project_options["libexecdir"] = "libexec"`，还原 meson 默认值即还原上游意图（主命令在 `bin/`、子工具在 `libexec/libinput/`） |
| 9 | test_package 编译期 `fatal error: 'libudev.h' file not found` | ① 公开头 `src/libinput.h:35` 就 `#include <libudev.h>`，所以 libudev 头是 libinput 公开接口的一部分；② 更隐蔽的是 **eudev 声明了 `package_type = "application"`**（它同时装了 udevd 守护进程），Conan 因此把该依赖的 traits 默认成 `headers=False/libs=False`（`conan/internal/model/requires.py:217-221`），**丢弃 eudev 的 cpp_info** | 在 `requires()` 上**显式声明** `headers=True, libs=True, transitive_headers=True, transitive_libs=True`。该默认值只在 trait 未指定时生效（`set_if_none`），显式声明即覆盖，从而尊重 eudev 真实存在的 `include/libudev.h` 与 `lib/libudev.so` |
| 10 | **运行期 `Error loading shared library libinput.so.10: (needed by ./test_libinput)`**，原因字段为空 | `meson install` 会**原地改写每个被安装 ELF 的 RUNPATH**（把构建树的 RUNPATH 用等长 `XXX...` 覆盖），文件字节随之改变，**使链接期嵌入的 `.codesign` 签名失效**，加载器遂拒绝映射 | `package()` 内对包中所有 ELF（递归，因工具在 `bin/`+`libexec/libinput/`、callout 在 `lib/udev/`）执行 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 重新签名（与仓内 `accountsservice` 的 `_sign_installed_elfs()` 同法） |
| 11 | 上游测试套件无法运行 | litest 通过 `/dev/uinput` 创建虚拟设备，本环境 `os.stat('/dev/uinput')` → `EACCES` | `-Dtests=false`，**如实申报未运行**（不写成 skip/xfail 掩盖），另以 `test_package` 做消费者视角断言 |

### 问题 10 的定位过程（值得记下）

现象是「包能构建、消费者能编译能链接、一运行就加载失败」，且错误原因字段为空，很容易误判成依赖缺失或权限问题。决定性对照是**把构建树里刚链接出的同一文件拿来试**：

```
构建树 libinput.so.10.13.0  →  测试 4/4 全过，EXIT=0
包内   libinput.so.10.13.0  →  加载被拒（空原因）
sha256：7cee15c5…（构建树） vs 9c9ca4ba…（包内）   ← 同尺寸、不同内容
cmp -l：246 字节不同，全部落在 .codesign 段（文件偏移 339968）之前
差异内容：/storage/.../eudev…/p/lib:/storage/.../libevdev…/p/lib  →  XXXXX…（等长）
```

即：**重定位本身是对的**（RUNPATH 被清空，运行时靠 `LD_LIBRARY_PATH`），缺的只是把签名重算一遍。

## 源码修改

单个补丁 `patches/0001-ohos-libc-portability.patch`，两处**语义等价替换**（无平台 ifdef，同一份代码在 glibc 上同样成立）：

| 文件 | 改动 |
|---|---|
| `src/util-strings.c:249` | `rindex(base, '.')` → `strrchr(base, '.')` |
| `tools/libinput-record.c`（time.h 之后） | 新增 `extern char *__progname;` + `#define program_invocation_short_name __progname` |
| `tools/ptraccel-debug.c`（unistd.h 之后） | 同上 |

补丁已用 `patch -p1 --dry-run` 与实际应用双重验证。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| libevdev | 1.13.7 | evdev 事件封装（设备模型基础） |
| mtdev | 1.1.7 | 多点触控协议转换（`>= 1.1.0`）。注：ohpcd 该包只有 `libmtdev.a`，被静态链入，故 `DT_NEEDED` 中不含它 |
| eudev | 3.2.14 | 提供 `libudev`（设备发现）；见问题 9 的 traits 处理 |

## 验证结果

- **`conan create` 端到端通过**（`libinput/1.26.2@ohpcd/stable` 已生成）
- **test_package 4/4 通过**：`RESULT: PASS (4 checks, 0 failures)`
  - `libinput_path_create_context()` 返回可用 context
  - `libinput_log_set_priority()` 接受该 context
  - `libinput_path_add_device()` 对不存在设备返回 NULL（不崩溃）
  - `libinput_unref()` 引用计数契约成立
- **上游 litest 测试套件：未运行**（`-Dtests=false`）。原因是平台能力限制，非跳过：
  每个用例都经 `litest_create_uinput_device_from_description()` → `libevdev_uinput_*`
  创建虚拟输入设备，而本环境 `/dev/uinput` 实测 `EACCES` 不可访问。
  包内不含 `libinput-test-utils`（受 `install-tests` 门控），可佐证测试套件确未构建。
  > 注意：包里的 `libinput-test` **不是**测试套件，而是上游的一个工具
  > （`tools/libinput-test.c`，`install: true` 无条件安装）。
- 运行期加载已实测：包内 `libinput.so.10` 可被消费者正常加载（重签名后）。

## 交付物

| 路径 | 说明 |
|------|------|
| `bin/libinput` | 主命令（multiplexer CLI） |
| `lib/libinput.so.10.13.0` + `libinput.so.10` + `libinput.so` | 共享库与其 SONAME/dev 软链 |
| `lib/pkgconfig/libinput.pc` | pkg-config 元数据 |
| `lib/udev/libinput-device-group`、`libinput-fuzz-extract`、`libinput-fuzz-to-zero` | udev callout |
| `libexec/libinput/`（19 个） | 子工具：analyze*/debug-events/debug-tablet/list-devices/list-kernel-devices/measure*/quirks/record/replay/test |
| `include/libinput.h` | 公开头（**注意其 `#include <libudev.h>`**） |
| `share/libinput/*.quirks` | 设备 quirk 数据库 |
| `licenses/COPYING` | 许可证 |

## 注意事项

- **消费者必须能拿到 libudev 头**：`libinput.h` 直接 include `<libudev.h>`，故本配方把
  eudev 声明为 `transitive_headers=True`。若某消费方仍报 `libudev.h not found`，
  应检查其依赖图是否被其它规则削弱了该 traits。
- **libwacom 缺失的功能影响**：数位板型号/按键布局识别退化为内置表；对普通鼠标、
  键盘、触摸板、触摸屏无影响。
- **`libexecdir` 必须显式指定**：不指定时 Conan 会把它与 `bindir` 合并（问题 8），
  任何「主命令与子工具同名不同层」的上游包都会撞车。
- **ELF 重签名不可省**：任何在 `package()` 阶段用 meson/ninja install 落地 ELF 的
  配方都要留意这一点（问题 10）。
