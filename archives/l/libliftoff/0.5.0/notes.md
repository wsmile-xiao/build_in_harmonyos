# libliftoff 0.5.0 适配笔记（HarmonyOS PC / aarch64）

## 编译环境

- 构建系统: **meson**（上游 `meson_version : '>=0.52.0'`，`c_std=c11`，`warning_level=3`，
  `werror=true`）
- 编译器: clang / clang++（OHOS SDK 26.0.0.18，`ohos-aarch64` profile）
- 依赖: libdrm/2.4.133（上游要求 `>= 2.4.108`，meson.build:30）
- 补丁: **0 个**（上游源码零改动）

## 版本选择说明

仓库此前只有 `archives/l/libliftoff/0.1.0`——那是**空占位**（仅 manifest.yaml 与 notes.md
模板，无 `conanfile.py`、sha256 为空）。而 wlroots 的 DRM 后端要求
`dependency('libliftoff', version: '>=0.4.0')`（`backend/drm/meson.build:18`），0.1.0 无法满足；
上游最新发布为 **0.5.0**，且 wlroots 对 `>=0.5.0` 有专门的特性分支
（`HAVE_LIBLIFTOFF_0_5`，`backend/drm/meson.build:52`），故本次适配 0.5.0。
0.1.0 占位目录保持原样未动。

## 编译步骤

```bash
conan create archives/l/libliftoff/0.5.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
```

配方内部：

```bash
meson setup <build> -Ddefault_library=shared -Dc_std=c11 \
  -Dwerror=false -Db_ndebug=false -Dwrap_mode=nodownload
meson configure <build> -Db_ndebug=false     # configure 后再钉一次 + 断言校验
ninja -C <build>
meson test -C <build>                        # 上游单测（mock libdrm）
meson install -C <build>
# 然后对包内 ELF 重新签名
```

## 上游测试结果（R51 如实申报）

**上游 0.5.0 含完整测试套件，共 58 项，本平台全部通过（58/58，100%）。**

清点（`test/meson.build`）：

| 测试组 | 子测试数 | 断言数（`assert(` 计数） |
|---|---|---|
| `alloc` | 26 | 18（test_alloc.c） |
| `dynamic` | 17 | 43（test_dynamic.c） |
| `priority` | 1 | 4（test_priority.c） |
| `prop` | 12 | 27（test_prop.c） |
| `candidate` | 1 | 7（test_candidate.c） |
| `check_ndebug` | 1 | —（哨兵） |
| **合计** | **58** | **99** |

未修改任何上游测试文件。

**为什么这套测试能在无 DRM 设备的机器上跑**：`test/libdrm_mock.c` 通过 meson 的
`override_dependency` 替换真实 libdrm，因此平面分配逻辑（`liftoff_output_apply`、
候选平面筛选、zpos 排序、动态更新等 57 个用例）完全不接触 `/dev/dri`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `TypeError: get() got an unexpected keyword argument 'tar_format'` | `conan.tools.files.get()` 不接受 `conandata.yml` 里的 `tar_format` 字段 | 显式传 `url`/`sha256`（仓内 accountsservice、dbus 等既有范式） |
| 2 | configure 报 `Run-time dependency libdrm found: NO` | libdrm 经 pkg-config 解析（`dependency('libdrm')`），但配方未生成 `libdrm.pc` | `generate()` 内加 `PkgConfigDeps(self)` |
| 3 | 上游 58 项中 `check_ndebug` 失败，其余 57 项"通过" | **"通过"是假的**：Release 构建定义 `NDEBUG`，而上游把每个断言及其副作用都写在 `assert(...)` 里（共 99 处），`assert` 被展开成 `((void)0)` 后测试实际什么都没执行。上游专门提供 `test/check_ndebug.c` 作哨兵来抓这种情况。**仅通过 `tc.project_options["b_ndebug"]="false"` 不够**：conan 还传 `--buildtype=release`，meson 据 buildtype 重新推导 `b_ndebug`，实测最终生效值仍是 `'true'` | 在 `meson.configure()` 之后执行 `meson configure -Db_ndebug=false`，再用 `meson introspect --buildoptions` **实测校验**生效值，不为 `false` 即 `raise`（仓内 jose 配方同一范式） |
| 4 | test_package 编译报 `'xf86drmMode.h' file not found` | 公开头 `include/libliftoff.h:8` 包含 `<xf86drmMode.h>`，即 libdrm 是 libliftoff **公开接口**的一部分（上游 `libliftoff.pc` 同样记 `Requires.private: libdrm >= 2.4.108`），但 Conan 默认不向消费者传递依赖的头文件 | `self.requires("libdrm/2.4.133", transitive_headers=True, transitive_libs=True)` |
| 5 | 上游默认 `werror=true` | 上游 CI 与本工具链（clang 15）告警集不同 | `-Dwerror=false`（告警仍完整打印） |
| 6 | 上游 wrap 会尝试联网下载 libdrm | meson fallback | `-Dwrap_mode=nodownload` |
| 7 | `meson install` 改写 RUNPATH 致签名失效 | OHOS 加载器拒绝映射签名不匹配的 ELF（`Error loading shared library`，原因字段为空） | `package()` 内对包内全部 ELF 剥 `.codesign` + `binary-sign-tool -selfSign 1` 重签 |

## 验证结果

```bash
$ conan create archives/l/libliftoff/0.5.0 -pr:h=ci/conan/profiles/ohos-aarch64 -r=ohpcd --build=missing
libliftoff/0.5.0: LIFTOFF_MESON_OPTION buildtype = 'release'
libliftoff/0.5.0: LIFTOFF_MESON_OPTION b_ndebug = 'false'     # ← 断言确实生效
libliftoff/0.5.0: LIFTOFF_MESON_OPTION werror = False
libliftoff/0.5.0: LIFTOFF_MESON_OPTION default_library = 'shared'
...
Ok:                58
Fail:              0
libliftoff/0.5.0: Package '90316e0ef973e885d9848e881f39209554928cc3' created
```

test_package（L1 消费者）：

```
ok   [api symbols]
ok   [create(-1)]
ok   [open(/dev/null)]
ok   [create(non-drm fd)]
ok   [caller fd still open]
skip [/dev/dri/card0] no DRM device node on this platform (errno=2)
OK: libliftoff links, and rejects non-DRM file descriptors
```

## 运行期能力（本机无 DRM/KMS）

本机 `/dev/dri` 不存在、设备亦无 `libgbm`/`libdrm.so`（OHOS 图形栈走 HDI display composer），
故 `liftoff_device_create()` 只能验证到「拒绝非 DRM 文件描述符」这一层；`output`/`layer`/
`plane` 对象需要真实 CRTC 与平面，本机无法构造。平面分配逻辑本身由上游 mock 测试覆盖
（58/58 通过），两者互补：

- 上游单测（mock libdrm）→ 覆盖**分配算法**
- test_package（真实 fd）→ 覆盖**链接、公开头可用性与设备创建契约**

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libliftoff.so.0.5.0`（+ `.so`/`.so.0` 软链） | 平面分配库 |
| `lib/pkgconfig/libliftoff.pc` | 上游自带（`Requires.private: libdrm >= 2.4.108`） |
| `include/libliftoff.h` | 公开头 |

## 注意事项

- 本配方**不含 patches/**：平台差异全部在配方侧解决，未改动上游源码。
- `b_ndebug=false` 的**后置钉正 + 实测校验**不可省略：否则 57 个用例会在断言被编译掉的情况下
  报"通过"，测试计数毫无意义（上游 `check_ndebug` 哨兵即为此设计）。
- 该包用于 wlroots 的 DRM 后端（`HAVE_LIBLIFTOFF_0_5`）；本机无 DRM 设备，故 wlroots 侧
  同样只能编译链接、运行期未验证。
---

**编译结束**: 2026-09-28 02:54
**最终状态**: built
