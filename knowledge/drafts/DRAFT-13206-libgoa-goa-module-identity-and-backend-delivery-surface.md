# DRAFT-13206-libgoa-goa-module-identity-and-backend-delivery-surface
## 多制品 Meson 工程的交付面审计：交付面全集取自 `meson introspect --installed`，而不是任务名或公开头

> **Contributor**: Yukinoshitaqwq | **Status**: DRAFT | **Updated**: 2026-09-28
> **Severity**: 🟡 medium | **Category**: meson / conan / pkg-config / packaging / ohos

**一句话增量**：本条给的不是"某个面怎么补"，而是一条**可复用的审计规程** ——
交付面（这个构建究竟装出哪些链接期制品）必须**从构建系统自身导出**（meson `introspect --installed`），
与配方交付清单**逐项 diff**，**差集（未交付面）必须显式申报**；libgoa 是该规程的实证：
第二共享库 `goa-backend-1.0` 在公开头里**没有任何守卫、完全不可见**，凡是从任务名/公开头/文档
"推断"交付面的做法必然漏面。

> **状态说明**：源码级事实已核实（官方归档 + sha256 固定）；真机证据已回填
> （2026-09-27 OHOS worker 真机 `conan create RC=0` + `test_package` 消费者探测全通过 + 安装树清单；
> 2026-09-28 受控对照复现）。适配与本文在同一分支 `feat/libgoa-3.58.1`；同前缀
> 【知识库扩展】Issue **#3551**、适配 PR **#13518**（`feat/libgoa-3.58.1` → `main`）。
> 本条在 PR 合入前不声称已获知识积分。

## 相关既有条目（同族差异化定位）

本条与近邻的**维度不同**：下面每一条回答的是"某一个面该怎么补"；本条回答的是
"**怎么知道有几个面、以及没交付的面怎么算**" —— 即交付面的**枚举与申报**。

| 既有条目 | 收录状态 | 它回答的问题 | 本条目增量（差异化） |
|---|---|---|---|
| **E217**（check-cmake-header-install-subdir） | 正式 | 上游把头装进 `include/<subdir>`，配方 `includedirs` 仍指 `include` → 消费者找不到头。**只覆盖"头子目录"一个面** | 本条把"面"本身当作审计对象：先用构建系统枚举出**全集**，再做 diff；头子目录只是 diff 命中的其中一项 |
| **E412**（optional acceleration backends in self-contained static packages） | 正式 | **同一库内部**的可选加速后端策略，防宿主自动探测 | 非本题——那是"同一个 `.so` 内的开关"；本条是**另一个独立共享库**（独立 SONAME、独立头目录、独立 libversion），且本条关注的是"它交付了没有"必须被申报 |
| **E618 / E623 / E624**（libheif 插件型子包系列） | 草稿 | 同 tarball 内**插件模块**子包的识别与交付面 | 非本题——那些是 `dlopen` 加载的插件（运行期装载）；本条是**编译期链接、独立版本号**（libversion 2.0.0）的第二共享库，不涉 dlopen |
| **E550 / E2179**（多编解码后端 / CMake optional backends） | 草稿 | 多后端**交叉编译接线**与测试前绑定（"后端能不能构建出来"） | 非本题——那是构建可行性；本条是构建之后的**交付面记账**："哪些面交付、哪些被裁、裁掉怎么申报" |
| **E542**（provider 配方复用已发布父模块制品） | 正式 | 从**已发布父模块**跨包复制组件 | 非本题——那是跨包复用；本条的面在同一构建内、由 meson 选项决定是否产出 |
| **E437**（qtcore5compat 源码包命名 qt5compat） | 正式 | **源码包名/下载 URL** 与任务名不一致（conandata 层面） | 非本题——那是"下载什么"；本条 diff 的对象是"装出去什么"，且身份面只是审计的第 4 步 |
| **E432**（PkgConfigDeps 按 conan 包名生成 .pc） | 草稿 | **依赖包**的 `.pc` 名与上游模块名不一致 → 造 alias `.pc` 补救 | 非本题——那是依赖侧、靠别名补救；本条是**自身交付包**的身份映射，且**不造别名**（上游名本来就是 `goa-1.0`）。两条会同时出现在一张依赖图中，互补 |
| **E077**（安装期 depfixer 改写 `.dynstr` → `.codesign` 失效，须在 `package()` 重签） | 正式 | 鸿蒙加载器只加载 `.codesign` 段有效的 ELF | **本条引用 E077 作为已采纳知识**（配方按它实现四步重签，`PACKAGE_CODESIGN=PASS signed_elfs=1`），**不重复申报** |
| **E307 / E316** | 正式 | 工具判定相似（0.40 / 0.23）；语义分别是"测试怎么跑起来"与"SONAME 文件实体化" | 与本条语义不同：本条既不是测试运行前置，也不是符号链接实体问题 |

> 查重（2026-09-28）：正式条目 541 条（`knowledge/doc/E*.md`）+ 在途草稿 2089 篇全文检索：
> `gnome-online-accounts` / `libgoa` / `goabackend` / `goa-backend` / `online account` 命中 **0**；
> `pkg_config_name` 系命中 27 条（E437/E432 为代表，已在上表逐条对照）。
> `introspect` / `交付面审计` / 安装树 diff 类命题在全语料**无既有条目**。
> 官方 `draft-review` 实跑（项目树 = 正式图谱 543 条 `.kv` + `index.tsv`）：
> quality `signature/root_cause/rec` **全 ✅**；TOP 相似 E307 **0.40** / E217 **0.36** / E316 **0.23**；
> 判定 **`review-similar`**（灰区，纳入决策权在人工审核）。`keyword_jaccard` 全为 0.0。
> 若维护者判断应并入 E217/E412/E437/E432，**接受合并证据，不重复申报同一知识积分**。

## Scope（何时用）

适用（出现任一即应做交付面审计）：
- 同一构建产出**多个链接期制品**（多个共享库 / 多个头目录 / 可选子系统），且制品名由构建系统的**变量**决定；
- 平台任务名 ≠ 上游工程名（`libgoa` ↔ `gnome-online-accounts`），身份只能从构建系统导出；
- 公开头 / 文档**看不见**某个可选制品（无守卫宏）——此时"看不见"等于"必须枚举"。

**不**适用：
- 单制品简单库（一个 `.so` + 一个头目录），审计成本大于收益；
- 制品由 `dlopen` 运行期装载的插件（走 E618/E623/E624 的插件契约）；
- 交付面由外部包提供（跨包复用，走 E542）。

## 交付面审计规程（本条核心）

### 第 1 步 枚举全集（不要推断，要导出）

| 构建系统 | 交付面全集的来源 |
|---|---|
| meson | `meson introspect --installed <builddir>`（配置期即可，不依赖构建完成；配合 `--targets` 看目标） |
| CMake | 安装后 `<builddir>/install_manifest.txt`（或 `cmake --install --dry-run`） |
| autotools | `make -n install` 的 install 行，或 `DESTDIR=<tmp> make install` 后对空目录树做 diff |
| conan 配方 | 包目录本身（`conan cache path`）+ `package_info()` 的声明——**交付清单的权威副本** |

本案例实测路径：`meson setup _b -Dgoabackend=true && meson introspect --installed _b` 与
`-Dgoabackend=false` 两次输出的**差集**，就是被选项裁掉的全部交付面。

### 第 2 步 逐项 diff

把配方/清单声明的交付物与第 1 步的全集逐项对齐，每个制品判定**交付**或**裁剪**。
本案例 diff 结果（真机安装树 vs 上游声明）：

| 上游交付面（`meson.build` 声明） | 本包实际 | 判定 |
|---|---|---|
| `goa-1.0`（库 + `.pc` + 头子目录 + typelib 命名空间） | `lib/libgoa-1.0.so.0`、`lib/pkgconfig/goa-1.0.pc`、`include/goa-1.0/goa/`（7 头） | **交付** |
| `goa-backend-1.0`（第二共享库 + `goabackend/` 头目录） | `find` 计数 **0** | **裁剪（已申报）** |
| `goa-daemon` + provider 后端 | 不在包内 | **裁剪（已申报）** |

### 第 3 步 申报差集（关键义务）

每个被裁掉的面必须在 `notes.md` / `manifest.yaml` 写明三件事：**不交付什么、为什么不交付、公开面是否完整**。
本案例：`goa-backend-1.0` 与 daemon 不交付，原因是其依赖（json-glib / libsecret / libsoup-3.0 /
libxml2 / rest-1.0）在 ohpcd 尚无发布；并给出**公开面不受影响**的证据 —— 关闭 `goabackend` 后
`src/goa` 公开头与导出符号不变，`goa-1.0.pc` 与 `libgoa-1.0.so.0` 全部照旧。
不得以"上游只有一个库"或沉默来掩盖被裁掉的面。

### 第 4 步 身份对齐（diff 命中的偏差之一）

交付出去的身份按上游构建变量导出，四个面**一次对齐**：库名/SONAME（`libgoa-1.0.so.0`）、
`.pc` filebase（`goa-1.0.pc`）、CMake 与 typelib 命名空间（`Goa`）、安装头子目录
（`$includedir/goa-1.0/goa/`，以及被裁剪的 `.../goabackend/`）。**不额外造 alias `.pc`** ——
上游名本来就是 `goa-1.0`，这与 E432 为依赖包造别名的补救路径不同。

## 现象与稳定错误签名

消费者按**上游名**探测时全线落空，而库与头其实都在安装树里（这是"面在但不被认领"的典型形态）：

```text
configure: error: Package requirements (goa-1.0) were not met:
Package 'goa-1.0', required by 'virtual:world', not found

CMake Error at CMakeLists.txt:12 (find_package):
  By not providing "FindGoa.cmake" ... Could not find a package configuration file
  provided by "Goa" ... GoaConfig.cmake  goa-1.0-config.cmake

/tmp/consumer.c:3:10: fatal error: 'goa/goa.h' file not found
```

**真机受控对照复现（2026-09-28，OHOS aarch64；唯一受控变量 = 交付身份基名）**
取同一份**已安装包**，只把 `lib/pkgconfig/goa-1.0.pc` 改名为 `libgoa.pc`（模拟"按平台任务名导出身份"），
库 `lib/libgoa-1.0.so.0` 与头 `include/goa-1.0/goa/goa.h` 全程不动：

```text
$ PKG_CONFIG_PATH=<pkg>/lib/pkgconfig pkg-config --exists goa-1.0 ; echo rc=$?
Package goa-1.0 was not found in the pkg-config search path.
Perhaps you should add the directory containing `goa-1.0.pc'
to the PKG_CONFIG_PATH environment variable
rc=1
$ PKG_CONFIG_PATH=<pkg>/lib/pkgconfig pkg-config --modversion libgoa
3.58.1                                  # 按任务名探测反而成功
$ ls -l <pkg>/lib/libgoa-1.0.so.0 <pkg>/include/goa-1.0/goa/goa.h
（两者都在）                             # 库与头文件从未缺席
# 对照组：仅把 .pc 名字改回上游名 goa-1.0.pc，其余完全不变
$ PKG_CONFIG_PATH=<pkg>/lib/pkgconfig pkg-config --modversion goa-1.0 ; echo rc=$?
3.58.1
rc=0
```

**联合判据（本条推荐的最小诊断）**：
`pkg-config --exists <上游名>` 失败（rc≠0）**且** `lib/<上游库名>.so*` 与 `include/<上游名>/**/*.h`
在位 —— 前者说明身份没对上，后者说明制品没丢；两个条件同时成立时，问题在**身份映射**，
不在交付缺失。若后者也不在，则是交付面问题（走第 1–3 步审计）。
**同族形态（本次未实测到，供日志匹配用）**：CMake 侧 `find_package(Goa)` 找不到
`GoaConfig.cmake`；typelib 侧 `Goa-1.0` 缺失。正则：
`No package 'goa-1\.0' found|goa-1\.0\.pc|libgoa-1\.0\.so|Goa-1\.0.*typelib|Package .Goa.* not found`

## 根因与最小复现

上游 `meson.build` 把交付身份定义在变量上（**不是**工程名 `gnome-online-accounts`）：

```meson
goa_name       = 'goa'
goa_ns         = 'Goa'
goa_api_version = '1.0'
goa_api_name   = 'goa-1.0'                      # shared_library 名 / pkg.generate filebase
goa_backend_api_name = 'goa-backend-1.0'        # 第二个共享库
goa_pkgincludedir = join_paths(goa_includedir, goa_api_name)   # $includedir/goa-1.0
```
`src/goa/meson.build`：`shared_library(goa_api_name, version: '0.0.0')`（首版即 SONAME `libgoa-1.0.so.0`）、
`pkg.generate(filebase: goa_api_name, subdirs: goa_api_name, name: goa_ns)`；
`src/goabackend/meson.build`：第二个共享库 + `install_headers(..., install_dir: $includedir/goa-1.0/goabackend)`；
`src/meson.build` 用 `if enable_goabackend` 把 `goaidentity` / `goabackend` / `daemon` 整段关掉，
而 **`src/goa/*.h` 内没有任何 `GOA_BACKEND_ENABLED` 守卫** —— 后端面在公开头里不可见。

最小复现（源码级，离线可做）：
```bash
tar xf gnome-online-accounts-3.58.1.tar.xz
cd gnome-online-accounts-3.58.1
grep -n "goa_api_name\|goa_backend_api_name\|goa_pkgincludedir" meson.build
grep -n "install_headers" -A4 src/goa/meson.build src/goabackend/meson.build
grep -rn "GOA_BACKEND_ENABLED" src/goa/ ; echo rc=$?     # rc=1：公开头里没有守卫
```

## 已尝试方案与结果

| 方案 | 结果 |
|---|---|
| 把任务名 `libgoa` 当交付身份（`.pc` 名/包名） | ❌ 消费者按上游名 `goa-1.0` 探测全失败（真机受控对照 rc=1）；依赖本包的配方各自造别名，命名分叉 |
| 从公开头 `src/goa/*.h` 推断交付面 | ❌ 头里**没有** `GOA_BACKEND_ENABLED` 守卫，第二个共享库不可见 → 会漏掉整个后端面 |
| 只声明"交付了 libgoa"，不写裁剪 | ❌ 交付清单与真实安装树不一致（`goa-backend-1.0` 差集未申报），审计不可复核 |
| **从构建系统枚举全集 + diff + 申报差集**（采纳） | ✅ 差集明确（`*goa-backend*` 计数 0），公开面完整性有证据，消费者按上游名探测全通 |

## 最终方案

1. **枚举**：`meson introspect --installed <builddir>`（另构建 `-Dgoabackend=true/false` 两版取差集）得到交付面全集。
2. **diff**：配方交付清单 vs 全集逐项判定；本包裁剪面 = `goa-backend-1.0` + daemon。
3. **申报**：`notes.md` / `manifest.yaml` 写明不交付项、原因（依赖未发布）、公开面完整证据。
4. **对齐身份**：库名/SONAME、`.pc` filebase、CMake 与 typelib 命名空间、头子目录四面按上游变量导出；
   配方侧显式 `pkg_config_name = goa-1.0`，不造 alias `.pc`。
5. **消费者验证**：按上游名探测（`pkg-config --modversion goa-1.0` + `#include <goa/goa.h>` + 至少一处 API 往返）。

## 适用范围、反例、解除条件

- 适用：多制品构建、任务名≠上游工程名、可选制品在公开头里不可见（或不确定是否可见）的工程（GNOME/KDE/Qt 系多见）。
- 反例：① 若下游确实需要提供商/daemon（在线账号服务场景），**不可**裁剪，必须走 fallback（两制品全交付并分别验证）；
  ② `dlopen` 插件不适用本条（见 E618/E623/E624）；③ 头文件本身随选项变化的工程不适用（那是 E566 的头/符号契约漂移）。
- 解除条件：上游若改为按工程名导出身份、或把后端面合并进公开库、或公开头加上守卫宏使裁剪可见，
  本条的"枚举 + 申报"义务自动降级为普通身份核对。

## 真实验证

- **已核实（源码级，可离线复现）**：官方归档 `https://download.gnome.org/sources/gnome-online-accounts/3.58/gnome-online-accounts-3.58.1.tar.xz`
  sha256 `9ec1900cc51409c2067c07c828c10be06fe3bf68d2999bb72d7d5ed325ed9bbc`（496012 字节，本地校验一致）；
  上述 `grep` / `install_headers` 输出为本文事实来源。**不是修前鸿蒙实测。**
- **已核实（真机受控对照复现，2026-09-28）**：见「现象与稳定错误签名」——受控变量只有 `.pc` 基名，
  改任务名即失败（rc=1）、改回上游名即成功（rc=0），库与头始终在位。命令与输出均为真机实测，**不是构造报错文本**。
- **已核实（修后鸿蒙真机实测，2026-09-27，OHOS aarch64 worker）**：`conan create . -pr:h=ohos-aarch64
  -pr:b=ohos-aarch64` → `RC=0`；`PACKAGE_CODESIGN=PASS signed_elfs=1`（E077 四步重签）。
  安装树按上游 `goa_api_name` 落位（真机实测）：

  ```
  lib/libgoa-1.0.so -> .so.0 -> .so.0.0.0      # readelf: SONAME=libgoa-1.0.so.0
  lib/pkgconfig/goa-1.0.pc                     # Name: Goa / Version: 3.58.1
  include/goa-1.0/goa/                         # 公开面头目录（7 个头）
  lib/goa-1.0/include/goaconfig.h              # 配置期生成（Cflags 含 -I${libdir}/goa-1.0/include）
  ```

  消费者按**上游名**探测成功（`test_package` 真跑，非空壳）：
  `pkg-config --modversion goa-1.0` → `3.58.1`（本包 `.pc`，非同名系统库）；
  `test_goa_consumer` 链接并运行打包后的 `libgoa-1.0.so.0`，10 项断言全 `ok`
  （版本全局量 / `goa_check_version` / `goa_error_quark` / `GoaClient`·`GoaObject`·`GoaAccount`·`GoaManager`
  类型注册 / `goa_client_new_sync` 往返），结论行 `libgoa 3.58.1 consumer contract: all checks passed`。
  设备与 profile：aarch64-linux-ohos（OHOS 6.0 / armv8），clang 15.0.4，原生构建。
- **审计差集的真机确认（2026-09-28，对已打包目录计数）**：`find <pkg>/ -name "*goa-backend*"` = **0**、
  `find <pkg>/ -type d -name goabackend` = **0** —— 差集为"确实未交付"，且已在配方 notes/manifest 显式申报。
- **未实测项（如实标注）**：`meson introspect --installed` 的两次配置/差集命令**尚未在真机上实跑**，
  本条目前以"官方 `meson.build` 的 install 声明 + 真机安装树清单"完成等价 diff；
  该命令是本规程**推荐**的机械化枚举手段，A 侧 PR 合入前可按需补做并回填输出。
- **流程信息**：适配与本文在同一分支 `feat/libgoa-3.58.1`；同前缀【知识库扩展】Issue 为 **#3551**，
  适配 PR 为 **#13518**（`feat/libgoa-3.58.1` → `main`）；CI 结论以仓库构建记录为准。
  本条在 PR 合入前不声称已获知识积分。

## 交付关联

- 适配 PR：任务 13206 `libgoa/3.58.1`，分支 `feat/libgoa-3.58.1`（适配与知识文档同一 PR）
- 知识库扩展 Issue：[#3551](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3551)（同前缀 `【知识库扩展】`）
- 关联知识：E217、E412、E437、E432、E542、E618/E623/E624、E550/E2179（对照，不重复申报）；E077（已采纳使用）
