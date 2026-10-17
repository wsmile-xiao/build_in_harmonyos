# polkit 124 适配笔记（libpolkit-gobject-1 客户端库，OHOS）

> **结论：可行，已发布。** polkit 124 通过上游 `-Dlibs-only=true` 构建
> `libpolkit-gobject-1` GObject 客户端库（**跳过 polkitd 守护进程**），完整满足
> 下游 accountsservice（meson.build:161 硬 REQUIRED `polkit-gobject-1`）的
> 构建依赖。OHOS 可行性结论见下文「OHOS 可行性评估」。

## 软件简介
polkit（PolicyKit）：D-Bus 授权策略框架。由三部分组成：
1. **polkitd** — D-Bus 系统服务守护进程（`org.freedesktop.PolicyKit1`），
   基于策略 JS 规则引擎（mozjs/duktape）与 PAM 做授权判定；
2. **libpolkit-gobject-1** — GObject 客户端库，应用/服务调用
   `polkit_authority_*` 向 polkitd 发起授权检查（**下游 accountsservice 只用这个**）；
3. **libpolkit-agent-1** + 命令行工具（pkcheck/pkaction/pkexec/pkttyagent）。
上游代码托管于 gitlab.freedesktop.org/polkit/polkit，**Meson** 构建。

## 上游版本确定
- 最新稳定 tag：**124**（gitlab API `repository/tags`，commit 82f0924d，
  release 2024-01-17；无更新 tag，accountsservice W0 报告提及的"约 124/125"即此）。
- 官方源码 tarball（实测可达、sha256 已核验）：
  `https://gitlab.freedesktop.org/polkit/polkit/-/archive/124/polkit-124.tar.gz`
  sha256=`72457d96a0538fd03a3ca96a6bf9b7faf82184d4d67c793eb759168e4fd49e20`

## W0 依赖发布检查（适配前第一步）

### 上游真实构建依赖（124，meson.build 实测）
```meson
gio_dep      = dependency('gio-2.0',      version: '>= 2.30.0')  # REQUIRED
gio_unix_dep = dependency('gio-unix-2.0', version: '>= 2.30.0')  # REQUIRED
glib_dep     = dependency('glib-2.0',     version: '>= 2.30.0')  # REQUIRED
gobject_dep  = dependency('gobject-2.0',  version: '>= 2.30.0')  # REQUIRED
expat_dep    = dependency('expat')                                # REQUIRED（无条件 assert）
dbus_dep     = dependency('dbus-1', required: false)              # 可选
js_dep       = (js_engine == 'duktape'|'mozjs')                   # libs-only 时置空，不需要
logind_dep   = (session_tracking != 'ConsoleKit')                 # 默认 ConsoleKit，不需要
systemd_dep  = (session_tracking == 'libsystemd-login')           # 默认不触发，不需要
pam_dep      = (authfw == 'pam')                                  # 需 -Dauthfw=shadow 规避
```

### 可用性核验（conan list + conan install 实测，2026-09-03）
| 上游模块 | Conan 包 | 核验 |
|---|---|---|
| glib/gobject/gio/gio-unix | `glib/2.84.0.1` | `conan list glib/* -r=ohpcd` 命中；prebuilt 安装成功；`gio-unix-2.0.pc` 在 glib 包 lib/pkgconfig |
| expat | `expat/2.8.2` | `conan list expat/* -r=ohpcd` 命中（2.8.2/2.8.2.1/2.8.2.1.1）；prebuilt 安装成功 |
| dbus（可选） | `dbus/1.14.10` | 命中；本配方不依赖（libs-only 下 dbus_dep 未找到即用默认布局） |
| mozjs（可选） | 无配方 | **libs-only 自动置空 js_engine，不需要** |
| systemd（可选） | 无配方 | **默认 ConsoleKit 会话跟踪，不需要** |

`meson setup` 实测（libs-only + authfw=shadow + 关闭 introspection/tests/docs）：
```text
Run-time dependency gio-2.0 found: YES 2.84.0.1
Run-time dependency gio-unix-2.0 found: YES 2.84.0
Run-time dependency glib-2.0 found: YES 2.84.0.1
Run-time dependency gobject-2.0 found: YES 2.84.0.1
Run-time dependency expat found: YES 2.8.2
Library crypt found: YES
...
```
全部解析成功，无阻塞依赖。

### 消费者集成验证（accountsservice 视角）
在 conan 消费者工程中 `conan install polkit/124 + glib/2.84.0.1`，PkgConfigDeps
生成 `polkit-gobject-1.pc`（Requires: glib-2.0 gobject-2.0 gio-2.0），然后
meson setup 实测：
```text
Run-time dependency glib-2.0 found: YES 2.84.0.1
Run-time dependency gio-2.0 found: YES 2.84.0.1
Run-time dependency gio-unix-2.0 found: YES 2.84.0
Run-time dependency polkit-gobject-1 found: YES 124
```
与 accountsservice meson.build:158-161 所需完全一致（gio/gio-unix/glib/polkit-gobject-1
全 YES）→ accountsservice 的 W0 阻塞解除，可回迁适配。

## OHOS 可行性评估（核心结论）

**libpolkit-gobject-1 可独立构建发布**（本任务已实现）。理由：
- 该库是纯 GObject 客户端库，meson 依赖仅 `gio-2.0/gio-unix-2.0/glib-2.0/gobject-2.0`
  （`src/polkit/meson.build` `common_deps`），全部由 ohpcd 已发布的
  `glib/2.84.0.1` 提供；
- 通过 `-Dlibs-only=true` **不构建 polkitd**，天然规避守护进程侧全部重依赖：
  JS 规则引擎（mozjs/duktape，OHOS 无）、PAM 鉴权框架（`-Dauthfw=shadow` 规避）、
  systemd/libelogind（默认 ConsoleKit 规避）；
- 产物 `.so` 用 OHOS `binary-sign-tool` 签名后动态链接器可加载（test_package
  实测运行通过）。

**但 polkitd（D-Bus 系统服务）在 OHOS 不可运行**，因：
- 已发布的 `dbus/1.14.10` conan 包**只含客户端库 libdbus-1，不含 dbus-daemon**
  （其配方注释明确"仅构建客户端库 dbus-1，跳过 dbus-daemon"）；
- 因此 OHOS 无 D-Bus 系统总线基础设施，polkitd 无处注册 `org.freedesktop.PolicyKit1`
  系统服务，运行期 `polkit_authority_*` 调用会失败。

**对 accountsservice 的影响**：构建期依赖完全满足（本库已发布，链接/头文件/.pc 齐备）；
运行期其 daemon 若调用 polkit 授权接口，需环境具备系统总线 + polkitd——这是
accountsservice 运行部署问题，非本库构建发布阻塞。若后续需完整授权链，应另立
polkitd 适配任务（含系统总线基础设施评估）。

## 编译步骤（conan create 验证通过）
```bash
conan create archives/p/polkit/124 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
- 配方：`conanfile.py`（Meson + PkgConfigDeps + MesonToolchain）
- 依赖：`glib/2.84.0.1`（transitive_headers/libs）+ `expat/2.8.2`（visible=False 私有）
- Meson 选项：`-Dlibs-only=true -Dauthfw=shadow -Dintrospection=false
  -Dtests=false -Dexamples=false -Dman=false -Dgtk_doc=false`
- 产物：`libpolkit-gobject-1.so.0.0.0`（+ .so.0/.so 软链）、
  `include/polkit-1/polkit/*.h`（22 个头含 polkitenumtypes.h）、
  `lib/pkgconfig/polkit-gobject-1.pc`、licenses/COPYING

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson setup` ERROR: `Unknown linker(s): llvm-ar` | meson 按裸名探测 ar，PATH 无 | 注入 `ar = 'llvm-ar'`（_inject_meson_tools，atk 模式） |
| 2 | `src/polkit/meson.build:44` ERROR: `Could not get pkg-config variable` | `gnome.mkenums_simple` 需 glib-2.0.pc 的 `glib_mkenums` 变量，PkgConfigDeps 不生成 | 增补 glib-2.0.pc/gobject-2.0.pc 的 `glib_mkenums`/`glib_genmarshal`/`gobject_query` 变量 |
| 3 | `meson setup` ERROR: `Unknown compiler(s): clang`（/data/service/hnp/bin 不在 PATH 前部） | 编译器探测 | 走 conan profile `tools.build:compiler_executables`，meson native 文件自动注入 |
| 4 | `conan create` ERROR: `direct dependency 'expat' is not used by cpp_info.requires` | expat 仅 configure 期 assert，库不链接 | `self.requires("expat/2.8.2", visible=False)` 私有依赖（at-spi2-core libxml2 同款） |
| 5 | 默认 `-Dauthfw=pam` 找不到 libpam | OHOS 无 PAM；顶层 meson 无条件检测 authfw | `-Dauthfw=shadow`，`cc.find_library('crypt')` 命中 sysroot libcrypt.a |
| 6 | `pkg-config: gio-unix-2.0 not found`（首次） | glib 包 gio-unix-2.0.pc 在 lib/pkgconfig 而非 PkgConfigDeps 生成 | `_append_dependency_pkg_config_paths` 把依赖包 lib/pkgconfig 追加进 meson pkg_config_path |

## 依赖版本
- glib/2.84.0.1（含 gobject-2.0/gio-2.0/gio-unix-2.0/gmodule-2.0/gthread-2.0）
- expat/2.8.2（构建期私有）
- 工具链：clang 15.0.4 (aarch64-linux-ohos)，meson 1.11.1，ninja 1.13.1

## 验证结果
```bash
$ conan create ...                    # EXIT=0
polkit/124 (test package): RUN: "./test_polkit"
polkit-gobject-1 OK: identity=unix-user:root subject=system-bus-name::1.42
```
- test_package 实测调用 `polkit_unix_user_new`/`polkit_identity_to_string`/
  `polkit_system_bus_name_new`/`polkit_subject_to_string`，输出身份/主题序列化，
  证明 .so 已签名可加载、头文件/链接无误。
- 消费者 meson 解析 `polkit-gobject-1`/`gio-unix-2.0` 全 YES，编译链接通过。

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Meson 配方（libs-only 客户端库） |
| conandata.yml | 上游 gitlab archive URL + sha256 |
| test_package/ | CMake 测试（调用真实 polkit API） |
| manifest.yaml | status: built |
| reports/w0-dependency-check.md | W0 依赖调查 + OHOS 可行性证据 |

## 注意事项
- **OHOS 无 D-Bus 系统总线**（dbus 包仅客户端库）：libpolkit-gobject-1 只做
  构建依赖发布；运行期授权需 polkitd + 系统总线（见上 OHOS 可行性评估）。
- `/tmp` 只读（E002）：中间产物用 `$HOME/tmp`。
- GitHub 沙箱不可达，上游源码用 gitlab.freedesktop.org 官方 archive（实测可达）。
- accountsservice 回迁时：requires 需加 `polkit/124`；其 meson `dependency('polkit-gobject-1')`
  由 PkgConfigDeps 生成的 polkit-gobject-1.pc 满足；注意 accountsservice 自身
  的 `_append_dependency_pkg_config_paths`（atk 模式）需把 glib 包 lib/pkgconfig
  追加进 pkg_config_path 以命中 gio-unix-2.0.pc（若未处理）。

---
**编译结束**: 2026-09-03
**最终状态**: built（本地缓存 + manifest；ohpcd 远端未推，按要求）
---
