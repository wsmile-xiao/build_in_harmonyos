# libshumate 1.7.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-26
- 编译器: clang/clang++（/data/service/hnp/bin，llvm 15.0.4 工具链，aarch64-unknown-linux-ohos）
- 状态: built（本地 conan create 全绿）
- 任务: wave12 #14255（j669539）

## 背景

libshumate 是 GNOME 的 GTK4 地图组件库（libchamplain 继任者），为应用提供
瓦片地图渲染、矢量瓦片（Protobuf-based vector tiles）、图层/标记等能力。
GNOME Maps 等使用。

## 上游测试（rule4/N 口径 + 逐项定性）

上游 meson 注册测试目标 **16 个**（tests/meson.build 的 tests dict）。

**实测结果（本机 OHOS arm64 真跑）**：

| 类别 | 数量 | 明细 |
|------|------|------|
| 实跑全 PASS | 13 | 49 断言全过（见下） |
| 显示限制不可跑 | 3 | map、marker、marker-layer（gtk_init 需显示服务器） |

13 项 PASS 明细：coordinate(1)、data-source-request(2)、file-cache(2)、
location(1)、memory-cache(5)、vector-expression(17)、vector-index(3)、
vector-reader(3)、vector-renderer(2)、vector-sprite-sheet(3)、
vector-style(1)、vector-value(6)、viewport(4)。

3 项显示限制根因（实测确认）：调 `gtk_init()` → `Failed to open display`
（HarmonyOS PC 无窗口系统；Broadway unix socket bind 被 SELinux 拒绝，
与 gtksourceview5 同款平台限制，E471 分类）。

## 编译步骤

```bash
curl -fL -o libshumate-1.7.0.tar.xz \
  https://download.gnome.org/sources/libshumate/1.7/libshumate-1.7.0.tar.xz
sha256sum  # 3896cc4b6a7bf83141c27df23ce48cdd68467603bc6b764960307cdcbbef80e5

export PATH=/data/service/hnp/bin:~/.local/bin:/storage/Users/currentUser/usr/local/bin:$PATH
conan create archives/l/libshumate/1.7.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson `Dependency "sqlite3" not found` | override-only pin 不生成 .pc（PkgConfigDeps 只为直接依赖生成） | sqlite3 用普通 requires（非 override） |
| 2 | `Could not detect Ninja v1.8.2` | conanbuild 环境重写后 hnp ninja ELF 找不到 libc++_shared.so（OHOS musl loader 不搜 /system/lib64，SDK llvm/lib 里也没有） | build() 里向 conanbuildenv-*.sh 追加 `export NINJA=绝对路径` + `export LD_LIBRARY_PATH=/system/lib64:SDK/lib...`（generate() 里改无效：VirtualBuildEnv 在 generate 后才写文件，ConanFile.run 用 source conanbuild.sh 包装） |
| 3 | 测试全 rc=127 `Error loading libjson-glib-1.0.so.0` | 制品仓下载的 .so 带 CI worker 签名，本机 XPM 拒载 | build() 里 `_resign_dependency_libs()` 对全部依赖 .so 重签（llvm-objcopy 去 .codesign + binary-sign-tool -selfSign 1） |
| 4 | `cannot register existing type 'gchar'` SIGABRT | libsoup3/3.6.5-r1 静态内嵌 glib2 并导出 4110 个 g_* 符号，运行时与共享 glib/2.84 双 GObject 副本 | 换 libsoup3/3.6.5-r3（requires glib/2.84.0.1.1 shared=True，与 gtk4 链共用同一共享 glib——单副本） |
| 5 | 测试 LD 缺 json-glib 等 | cpp_info.components 的 libdirs 不进顶层收集 | 收集循环同时遍历 components |
| 6 | 编译 shumate-map.c 被 SIGKILL（exit 247） | 内存红线（MemAvailable 800MB 时 jobs=2 仍 OOM） | `-c tools.build:jobs=1`（内存红线纪律） |
| 7 | package_info includedirs 错 | meson 装到 include/shumate-1.0（非 libshumate-1.0） | 修正 includedirs |
| 8 | test.c `SHUMATE_MAP_SOURCE_OSM` 未定义 | 1.7.0 API 名是 OSM_MAPNIK | 修正为 SHUMATE_MAP_SOURCE_OSM_MAPNIK |

## 源码修改

- 无源码补丁（平台差异全部在配方层解决）

## 依赖版本

- gtk4/4.22.4（Broadway-only）
- glib/2.84.0.1.1（shared，override 对齐）
- cairo/1.18.4
- sqlite3/3.49.1（普通 requires，PkgConfigDeps 需要）
- libsoup3/3.6.5-r3（⚠️ 必须是 -r3：-r1/-r2 静态内嵌 GObject 导致双类型系统）
- json-glib/1.10.6
- protobuf-c/1.5.1
- zlib/1.3.1.1（override，PIC）

## 产物

- libshumate-1.0.so（含重签）
- include/shumate-1.0/*.h

## 注意事项（下游）

- 下游运行时 LD_LIBRARY_PATH 需含 libshumate/glib/gtk4/json-glib/libsoup3 的包 lib 目录 + /system/lib64
- **下游消费 libsoup3 必须用 3.6.5-r3**（单 GObject 副本），-r1/-r2 会双副本崩溃
- gir/vapi 关闭（OHOS 无交叉 g-ir-scanner）
- 上游 3 个 gtk_init 测试（map/marker/marker-layer）无显示环境恒失败，勿纳入下游 CI
---

**编译结束**: 2026-09-26 08:38
**最终状态**: built
