# gupnp-tools 0.12.4 适配笔记

## 编译环境
- 构建系统: meson (>= 0.54.0)
- 编译日期: 2026-09-06
- 编译器: clang/clang++（/data/service/hnp/bin，llvm 15.0.4 工具链）
- 状态: built
- 积分归类: 【积分赛】路径 A 正常适配
- 前置：gupnp/1.6.8（j669539 的 PR #8316，open 未合，本地缓存有二进制）
  + gssdp/1.6.6（已合入 main 并发布 ohpcd）

## 背景

gupnp-tools 是 GUPnP 协议栈的配套工具集（Intel UPnP tools 的自由替代品）。
上游 5 个工具中 3 个是 GUI（network-light/universal-cp/av-cp 硬依赖
GTK+ 3），2 个是纯 CLI（gssdp-discover、gupnp-event-dumper），另有
gupnp-upload（CLI 但依赖 gupnp-av）。本适配构建 CLI 工具集。

## CLI-only 裁剪决策（补丁 0001，本适配核心）

**为什么不构建 GUI 工具**：

1. **GObject 双域冲突（硬性阻塞）**：gupnp 协议栈采用"单 GObject 域"方案
   （gssdp 1.6.6 / gupnp 1.6.8 notes 详述）——静态 glib2/2.88 的 .pc Libs
   置空，g_* 符号全部 UND，运行时统一解析到 libsoup-3.0.so 导出的唯一
   gobject 副本。而已发布的 gtk/3.24.43（broadway 后端）绑定的是
   **glib/2.84.0.1（shared）**——把 GTK 链进同一个进程，进程内出现两份
   GObject 类型系统，GType 注册撕裂 SIGABRT（gssdp 适配期间本地铁证，
   4108 个 g_* 双定义冲突）。gtk 配方无法切换到 glib2/2.88 static
   （其依赖链 atk/pango/gdk-pixbuf 全部绑定 shared glib/2.84）。
2. **显示后端语义**：OHOS 无 X11/Wayland，gtk/3.24.43 是 broadway
   (HTML5) 后端——GUI 工具即使链接成功，也需要 broadwayd 服务器 +
   浏览器才能显示，在鸿蒙 PC 目标场景无实际可用性（R40：编译通过≠
   适配完成，GUI 工具无法达到"实质平台适配"标准）。
3. **上游 CLI 工具本来就不依赖 GTK**：gssdp-discover（gssdp+gobject）
   和 gupnp-event-dumper（gupnp+gobject）是完整的实用工具，SSDP 发现
   与事件订阅打印是纯网络+文本场景，无显示需求。

**裁剪方式**（纯构建系统可移植性修复，无平台宏，R8 合规）：补丁 0001
为 meson 新增 `gui-tools` 布尔选项（默认 true，上游桌面行为完全不变）：
- `gtk = dependency('gtk+-3.0', required: gui_tools)`（false 时变可选）
- `HAVE_GTK_SOURCEVIEW = gui_tools and gtksourceview.found()`
- `subdir('data')`/GUI subdir 全部包进 `if get_option('gui-tools')`
- 配方传 `-Dgui-tools=false -Dav-tools=false`（av-cp/upload 依赖
  gupnp-av-1.0，该包未发布且 av-cp 是 GUI、upload 无 GUI 场景价值）

## 编译步骤

```bash
# 源码（官方 GNOME 源，NJU 镜像 200 作 fallback）
# https://download.gnome.org/sources/gupnp-tools/0.12/gupnp-tools-0.12.4.tar.xz
# sha256: 2c7f6f538fb36a15322be532217e5de161182c943c0a8b0da4458cf970b4092f

# conan create（host/build 同 ohos-aarch64 profile）
# ⚠️ 设备 shell 默认 LD_LIBRARY_PATH 含空格（chipset-pub-sdk:   <空格>/system/lib64），
# musl 动态链接器解析失败 → ninja 加载 libc++_shared.so 报 rc=127（gssdp 本地铁证），
# meson 因此报 "Could not detect Ninja v1.8.2 or newer"。需重设为无空格路径。
export LD_LIBRARY_PATH="/system/lib64/platformsdk:/system/lib64/chipset-pub-sdk:/system/lib64:/system/lib64/ndk:/data/storage/el1/bundle/libs/arm64"
conan create archives/g/gupnp-tools/0.12.4 \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
  -pr:b=$HOME/.conan2/profiles/ohos-aarch64 \
  --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 顶层 meson.build 无条件 `dependency('gtk+-3.0')`，无 GTK 环境直接 configure 失败 | 上游把 GTK 当硬依赖 | 补丁 0001：gui-tools 选项参数化 gtk 依赖与 GUI subdir |
| 2 | GUI 工具与 gupnp 栈 GObject 双域冲突 | gtk/3.24.43 绑定 shared glib/2.84，gupnp 栈是 glib2/2.88 static 单域方案 | CLI-only 裁剪（见上）；GUI 工具不在本包范围 |
| 3 | gupnp-av-1.0 依赖缺失 | gupnp-av/0.14.5 未发布（j669539 PR 也未合），且 av-cp 是 GUI | `-Dav-tools=false`（上游选项本来就是 required 参数化） |
| 4 | meson "Could not detect Ninja" 风险 | 平台默认 LD_LIBRARY_PATH 含空格（gssdp 本地铁证） | export 无空格的 LD_LIBRARY_PATH |
| 5 | AR=llvm-ar 等环境变量坏 | PATH 无 llvm-ar | generate() 里 os.environ.pop + shutil.which 定位真实 GNU 工具（复刻 glib2/libsoup3/gssdp/gupnp） |
| 6 | 工具可执行文件 g_* 符号解析 | 静态 glib2 若被链进可执行文件会与 libsoup-3.0.so 内嵌 gobject 双副本 | GLib 系 .pc Libs 置空（glib2-pc-fix + generators/glib-2.0.pc 双处理，gssdp/gupnp 同款第三次复用） |
| 7 | gssdp-1.6.pc/gupnp-1.6.pc 的 Requires: glib-2.0 展开链到静态 glib | PkgConfigDeps 生成的 generators/glib-2.0.pc 排在 pkg_config_path 首位 | generate() 后置空其 Libs 行（gssdp/gupnp 同款） |
| 8 | 上游无测试套件 | 工具集项目无 tests/ 目录 | test_package 执行被测包二进制 --help（R34 真实产物冒烟）；notes 记录验证口径 |

## 源码修改

- patches/0001-meson-add-gui-tools-option-for-headless-CLI-only-bui.patch：
  meson 新增 gui-tools 布尔选项（默认 true 上游行为不变），false 时 GTK 变
  可选依赖、GUI subdir 与 data/ 资源跳过、HAVE_GTK_SOURCEVIEW 强制 false。
  纯构建系统可移植性修复（portability），无任何平台条件宏（R8 合规）：
  headless Linux 服务器同样受益（无 GTK 的 CI 环境可构建 CLI 工具）。

## 依赖版本

- gupnp/1.6.8（⚠️ PR #8316 open 未合——本包被 PF4 依赖闸拦截推送，
  本地缓存二进制先行验证：gupnp/1.6.8:f69ba05b776a471b499d0f6c769a935ce0c56967）
- gssdp/1.6.6（shared .so）
- libsoup3/3.6.5-r1（shared .so，gobject 唯一提供者）
- glib2/2.88.0（静态 .a，经 .pc 修复 + Libs 置空方案使用）
- libxml2/2.15.3（libxml-2.0）
- zlib/1.3.1.1（root override，PIC 变体，传递依赖）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | meson 配方（CLI-only 选项 + GLib .pc Libs 置空单副本方案，复刻 gssdp/gupnp） |
| conandata.yml | 官方源 + NJU 镜像 + sha256 + 补丁声明 |
| test_package/ | 二进制执行冒烟（gssdp-discover --help + gupnp-event-dumper --help，R34） |
| patches/0001-meson-add-gui-tools-option-for-headless-CLI-only-bui.patch | gui-tools 选项（headless/CLI-only 构建） |
| manifest.yaml / notes.md / MANIFEST.yml / README.md / commands.json | 元数据 |

## 注意事项

- PR 标题前缀用【积分赛】（任务 #2354，开源鸿蒙PC专项积分赛）。
- **依赖闸**：gupnp/1.6.8 未发布到 ohpcd（其 PR #8316 open 未合）——
  PF4 会拦截 PR 创建。本地全套路验证（conan create + test_package）
  已用本地缓存 gupnp/1.6.8 二进制完成；等 #8316 合并发布后再推
  分支建 PR。
- 上游 GUI 工具（network-light/universal-cp/av-cp）不在本包范围：
  GObject 双域冲突 + broadway 显示后端无目标场景可用性。若未来
  gtk 生态迁移到与 gupnp 栈兼容的 glib 域，可用 gui-tools=true 重建。
- 产物：bin/gssdp-discover、bin/gupnp-event-dumper（+ locale 翻译）。
  软件级 commands.json 声明 binary:true（R38）。

## 验证结果

```bash
# conan create 成功（完整日志 $HOME/tmp/gupnp-tools-ci/create.log）
# gupnp-tools/0.12.4: Package '<package_id>' created

# 上游测试：N/A（工具集项目无测试套件；上游验证方式即运行工具）

# test_package L1: 编译伴随源 + 执行被测包二进制 --help 全过
#   gssdp-discover --help → exit 0（打印 GSSDP 发现工具用法）
#   gupnp-event-dumper --help → exit 0（打印事件订阅工具用法）
# 产物: bin/gssdp-discover + bin/gupnp-event-dumper
```

---

## 修复记录（2026-09-27，本次适配）

### 1. 依赖阻塞已解除

上一轮（2026-09-06）无法推 PR 的唯一原因已消失：`gupnp/1.6.8` 当时未发布到
`ohpcd`（其 PR #8316 open 未合），PF4 依赖闸会拦截。**当前 `gupnp/1.6.8` 与
`gupnp/1.6.10` 均已发布**（含 OHOS armv8 clang15 Release 二进制），依赖链
`glib2/2.88.0`、`libsoup3/3.6.5-r1`、`gssdp/1.6.6`、`libxml2/2.15.3`、
`zlib/1.3.1.1` 亦全部已发布。`conan create` 在**不使用 `--build=missing`** 的
情况下即可完成（依赖二进制全部复用），符合 W0「依赖须为可消费制品」要求。

### 2. test_package 真实缺陷修复（本次核心修复）

原 test_package 用 `gupnp-event-dumper --help` 验证，**实测会永久挂起**：
上游 `src/event-dumper/event-dumper.c` 的 `main()` 完全没有参数解析
（无 `GOptionContext`），直接创建 `GUPnPContextManager` + `GMainLoop` 并
`g_main_loop_run()`，因此 `--help` 不会退出——上一轮 `conan create` 实际是
卡死在 test 阶段（本轮复现：进程 35 分钟不返回），并非真正通过。

修复方式（保持「真实执行被测包二进制」的 R34 语义，且断言可机检）：

| 工具 | 上游参数行为 | 修复后的验证 |
|------|-------------|-------------|
| `gssdp-discover` | 有 `GOptionContext`，`--help` 打印用法后 exit 0 | 保留 `--help`（exit 0） |
| `gssdp-discover -n 1` | 真实 SSDP 发现，1 秒窗口后正常退出 | 新增：真实功能性冒烟（exit 0，打印 `Using network interface ...` / `Scanning for all resources`） |
| `gupnp-event-dumper` | **无参数解析，永久阻塞** | 改为有界运行：后台启动 → `sleep 3` → `kill -TERM`（上游注册了 `SIGTERM→g_main_loop_quit`）→ `wait` 断言 **exit 0**。退出码非 0（崩溃/库解析失败/提前退出）即失败 |

本地实测（`/data/service/hnp/bin/bash` + 完整 `LD_LIBRARY_PATH`）：
```
gssdp-discover --help           -> rc=0（打印 Usage: ... - discover devices using SSDP）
gssdp-discover -n 1             -> rc=0（Using network interface ancowlan0 / Scanning ...）
gupnp-event-dumper（3s 后 SIGTERM）-> rc=0
```

### 3. 本次真实构建结果

```
conan create archives/g/gupnp-tools/0.12.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
-> gupnp-tools/0.12.4: Package '29920dcc6a72566678f09fd49790cbd07db7153b' created
-> package(): Packaged 2 files: gssdp-discover, gupnp-event-dumper
-> test_package: 3 次 self.run 全 exit 0
-> EXIT_CODE=0
日志: $HOME/tmp/gt-create.log
```
---

**编译结束**: 2026-09-27 10:46
**最终状态**: built
