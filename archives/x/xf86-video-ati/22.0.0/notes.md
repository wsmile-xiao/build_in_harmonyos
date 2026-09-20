# xf86-video-ati 22.0.0 适配笔记（第 3 次尝试，接续 PR #6349）

## 编译环境
- 构建系统: autotools（官方发布 tarball 自带全部生成文件）
- 编译日期: 2026-09-17（第 3 次）
- 编译器: clang（OHOS SDK）
- 状态: **built — 本地 conan create 全流程通过（含 test_package），已消除 xorg-server 依赖阻塞（SDK 改为配方内生成，见下）**

## 软件简介
xf86-video-ati 是 X.Org 的 ATI/Radeon 显卡驱动模块，产出两个 libtool 模块供 X 服务器 dlopen 加载：
- `ati_drv.so` — 传统 ATI 驱动（导出 `atiModuleData`，modname "ati"）
- `radeon_drv.so` — Radeon KMS 驱动（导出 `radeonModuleData`，modname "radeon"）

## 第 3 次尝试：消除 xorg-server 依赖阻塞（本轮核心变更）

### 背景与决策

第 2 次尝试的结论是"配方就绪、仅阻塞在 xorg-server 未发布（R36）"。第 3 次调研：

1. xorg-server 至今（2026-09-17）没有 conan 配方：`conan list "xorg-server/*" -r=ohpcd` → 0 条。
   `archives/x/xorg-server/` 里的 21.1.14/21.1.15 只是旧 HNP 流程（预编译 Xvfb 二进制）的记录，无 conanfile。
   注意：ci 上对未发布包探测报的 `registry_unreachable` 实为 cnb.cool 对匿名 404 的表现形式
   （`conan download <不存在的包>` 返回 `ERROR: error:system acceleration policy not enabled`），
   被 CI 的 not-found 模式匹配漏掉而误分类为"网络问题"——libdrm/2.4.121 当初同样报此错。
2. 若按拓扑序（R36）补齐 xorg-server conan 包，需先适配发布 libxfont2、xkbcomp（均未发布），
   再适配 xorg-server 本身（巨型包）——多包多 PR 多轮 CI/发布流水线，远超本任务单 PR 范围
   （W2 单包原子性也不允许捎带）。
3. **仓库已有合并先例**：`xf86-video-fbdev/0.5.1`（PR #4792，2026-09-04 合入）面对同一问题
   （"xorg-server is not available as a Conan package"）选择了配方内从官方 tarball 供给 SDK。

### 采用方案（fbdev 模式的加强版，保留完整 autotools 构建）

fbdev 的做法是手写 xorg-server.h/dix-config.h + 绕过构建系统直接 clang 编单文件 —— 对
ati 这种 ~40 个源文件、依赖 configure 多项 SDK 探测的驱动不可行/不可靠。本轮改为**驱动
xorg-server tarball 自己的 configure 生成真实 SDK 头**：

1. 下载 xorg-server 21.1.15 官方 tarball（conandata `xorg_server` 条目，sha256 锁定），
   in-recipe 打三处平台适配（与驱动自身补丁同源）：config.guess 加 HarmonyOS case、
   config.sub 三处 ohos 支持、configure 去 umask 077（E011）。
2. 写一个 `cpp` 包装器（`exec $CC -E -x c - "$@"`）前置到 PATH —— OHOS clang 不读 stdin
   （裸 `clang -E` 报 no input files），xserver 的 XORG_PROG_RAWCPP 探测（`${RAWCPP} < conftest`）
   会死在这里；有包装器后 clang 在 C 模式预定义 `unix`=1 的行为让 configure 正确选出
   `RAWCPPFLAGS=-undef`。
3. 跑 tarball 自带 configure，**全部 DDX 禁用**（--disable-xorg --disable-xvfb --disable-xnest
   --disable-xwin --disable-xephyr --disable-kdrive --disable-glx --disable-dri
   --disable-libunwind --with-sha1=libnettle）：
   - 依赖仅需已发布包：pixman、xorgproto（全部 proto pc）、xtrans、libxau、libxkbfile、
     libxshmfence、nettle（SHA1，AC_CHECK_LIB 需要 LDFLAGS=-L 注入 nettle libdir）
   - `xfont2`（REQUIRED_LIBS 无条件成员）用元数据桩 pc 满足 —— DDX 驱动 SDK 从不使用
     xfont2 头，也不链接它
   - config.status 由此生成**真实的** xorg-server.h/dix-config.h 等（含 RANDR/RENDER/XV/
     DPMSExtension/DRI2/DRI3/PRESENT/XvMCExtension=1 等驱动 configure 依赖的全部扩展宏，
     平台字节序、HAVE_* 等也都是真实探测结果）
4. 采集 SDK 头：从 xserver 源码树按 **meson install_data 清单**（含 build_xv/build_xace/
   build_xinerama/build_mitshm 的条件追加，共 152 个，扁平化到 sdkdir 基名 —— meson 语义）
   复制；再对生成的 xorg-server.h 补 5 个 XORG-DDX 宏（autotools 只在 XORG=yes 段 AC_DEFINE
   而 meson 无条件写入 SDK：XORG_VERSION_CURRENT、XSERVER_LIBPCIACCESS、XORGSERVER、
   XCONFIGFILE、__XSERVERNAME__，取自锁定 tarball 的真实值）。
   排除 glamor.h/vndserver.h/glx_extinit.h/glxvndabi.h（对应 --disable-glamor/--disable-glx）。
5. 合成 xorg-server.pc（sdkdir 指向组装目录、abi_* 取 xf86Module.h 的 SET_ABI_VERSION：
   videodrv 25.2、Requires.private: pixman-1）+ gbm.h 桩头（radeon_dri3.c 在 dri3.h 存在时
   无条件 include <gbm.h>，但 glamor 关闭后全部 gbm 符号引用都被 USE_GLAMOR 编译掉，
   无任何 gbm 链接）。
6. 之后驱动自身的完整 autotools 构建不变：configure 查到 xorg-server.pc → CFLAGS 拿到
   sdkdir → 全部 SDK 探测（RANDR/RENDER/XV/DPMSExtension defined、RegionDuplicate/fbGlyphs/
   xf86CursorResetCursor declared、misyncshm.h/present.h/dri3.h found）→ make -j1 → 双模块。

### 与"裁剪"的关系（R40 完整性说明）

驱动自身零裁剪：全部 ~40 个源文件照常编译，EXA/KMS/RANDR1.2/DRI2/DRI3 路径完整（DRI3 保留，
仅 glamor GL 加速路径按第 2 次尝试既定结论禁用 —— OHOS 无 mesa）。xserver 侧被禁用的是
DDX/服务器本体（与驱动构建无关）与 DRI1（上游 21.1 已弃用、驱动内引用处为注释掉的死代码）。

### 验证

- 本地 `conan create ... -pr:h ci/conan/profiles/ohos-aarch64 --build=missing` 全流程通过：
  SDK 生成 → 驱动 configure/make/install → test_package 双模块 PASS（ELF 层模块加载器校验）
- 产物：lib/xorg/modules/drivers/{ati_drv.so 47K, radeon_drv.so 606K}、share/man/man4/*.4、
  share/X11/xorg.conf.d/10-radeon.conf

## 历史修复记录（第 2 次尝试，相对第 1 次）

| # | 问题（AI 检视意见/CI 失败项） | 修复 |
|---|------|------|
| 1 | simdjson 4.6.3 混入本 PR（W2 单包原则 + L0n 分支名不匹配） | 从分支删除全部 simdjson 文件；main 已另有完整合入的 simdjson/4.6.3 配方 |
| 2 | test_package 空壳测试（R34，只 printf 返回 0） | 重写为 `check_module.c`：在 ELF 层复现 X server 模块加载器的识别校验 |
| 3 | 29 个补丁中大量为 configure 临时产物 | 源码切换为官方发布 tarball，补丁集缩减为 3 个真实可移植性补丁 |
| 4 | libdrm/2.4.121 未发布 | 改为已发布的 libdrm/2.4.133 |
| 5 | 缺 libpciaccess 依赖声明 | 增加 libpciaccess/0.19 |
| 6 | L0d: test() 无 self.run | test() 编译并实际运行 check_module 对两个模块逐一校验 |

## 源码与补丁

源码：`https://xorg.freedesktop.org/archive/individual/driver/xf86-video-ati-22.0.0.tar.xz`
（sha256 `c8c8bb56…`，R39 官方源；**不再使用** GitLab 自动生成 archive — 它不含生成文件，是第 1 次 29 个补丁乱象的根源）

3 个补丁（全部在本地对 pristine tarball 验证过 `git apply --check`）：
1. `0001-configure.patch` — E011：移除 config.status 临时目录创建中的 `umask 077`（HMDFS 上 0700 目录对所有者不可写）
2. `0002-config.guess.patch` — E007：uname -s 返回 "HarmonyOS"，新增 case 分支输出 `aarch64-unknown-linux-ohos`
3. `0003-config.sub.patch` — E007：ohos-linux 三元组 + ohos* OS 族 + `linux-ohos*` 内核-OS 组合校验（缺最后一项会报 "Kernel linux not known to work with OS ohos"）

补丁本地验证：`sh ./config.guess` → `aarch64-unknown-linux-ohos`；`sh ./config.sub aarch64-unknown-linux-ohos` → 原样通过。

## 依赖分析（2026-09-17 实测 `conan download -r=ohpcd`）

| 依赖 | 版本 | 用途 | 制品仓状态 |
|------|------|------|-----------|
| libdrm | 2.4.133 | 驱动链接（libdrm + libdrm_radeon） | ✅ |
| libpciaccess | 0.19 | 驱动链接/头文件 | ✅（pc 模块名 pciaccess 由配方别名合成） |
| pixman | 0.46.4.3 | SDK 头 compiler.h 的 include | ✅ |
| xorgproto | 2025.1 | 全部 proto pc（xproto/fontsproto/xf86driproto/randrproto/…） | ✅ |
| xtrans | 1.6.0 | SDK configure 输入（不打包） | ✅ |
| libxau | 1.0.11 | SDK configure 输入（不打包） | ✅（1.0.12 与 libxcb/1.16 冲突） |
| libxkbfile | 1.1.3 | SDK configure 输入（不打包） | ✅ |
| libxshmfence | 1.3.3 | SDK configure 输入（不打包） | ✅ |
| nettle | 3.10.2.1 | SDK configure 的 SHA1 探测（--with-sha1=libnettle，不打包） | ✅ |
| xorg-server | 21.1.15 | SDK 头 + xorg-server.pc — **配方内从官方 tarball 生成**（registry 无配方） | N/A |

xorg-server 说明：SDK 生成用到的 xserver configure 输入依赖（xtrans/libxau/libxkbfile/
libxshmfence/nettle）全部仅在构建期使用，**不进入驱动模块的链接与打包**；xorg-server conan
包一旦发布，改回 `self.requires("xorg-server/x.y.z")` + 删除 _setup_xorg_sdk 即可。

## 构建要点（CI 直读）

- `--disable-glamor`：glamor 硬性要求 `gbm >= 10.6`（mesa）— OHOS PC 无 mesa；禁用不影响 EXA/KMS 代码路径
- `--disable-static`：驱动模块只有 .so 形态
- conan libdrm 包把全部组件库合并进单个 `libdrm.pc`，而 configure 检查 `libdrm_radeon` 模块（`radeon_drv_la_LIBADD`）— 配方在 generate() 用包真实路径合成 `libdrm_radeon.pc`；同理合成 `pciaccess.pc`（conan 包名 libpciaccess）
- X server SDK 头（compiler.h）`#include <pixman.h>` — pixman 头路径显式注入 CFLAGS（同时经 xorg-server.pc Requires.private 传递）
- config.status（configure 生成物）内嵌同样的 `umask 077 && mktemp` — build() 在 configure 后原位修复，失败则修复后重跑（E011，与 abook 配方同法）；SDK 的 config.status 同样防御性处理
- `make -j1`（E074 HMDFS jobserver fifo EPERM）
- 产物路径：`lib/xorg/modules/drivers/{ati_drv.so,radeon_drv.so}`（configure 默认 moduledir=$libdir/xorg/modules，无需 --with-xorg-module-dir）

## test_package 设计（R34）

模块由 X server dlopen 并从 server 进程解析 xorg-server 符号；**OHOS/musl 的 dlopen 是急切绑定**
（本机实测：`.so` 含未定义符号时 `dlopen(..., RTLD_LAZY)` 直接报 `Error relocating ... symbol not found`），独立测试程序无法 dlopen 驱动模块。

`check_module.c` 因此在 ELF 层复现 X server 模块加载器（loader.c）的识别校验：
1. 文件是合法 ELF64/LSB/ET_DYN/EM_AARCH64
2. 导出定义态全局符号 `atiModuleData` / `radeonModuleData`
3. 符号指向的 XF86ModuleVersionInfo 记录：MODINFOSTRING1=0xef23fdc5、MODINFOSTRING2=0x10dc023a、modname="ati"/"radeon"、版本 22.0.0

PIC 模块内指针成员是 R_AARCH64_RELATIVE 重定位（文件内原始字节为 0），checker 从 .rela.dyn 解析（与运行时加载器一致）— 已用结构等价的合成模块在本机做正/反双向验证（错名/错版本/缺符号均 FAIL，正确数据 PASS）。

## 上游测试清点（R51）

源码树仅 `src/`、`man/`、`conf/` 三目录；`grep -n "^check\|TESTS" Makefile.am src/Makefile.am` 无结果 — 上游无独立测试套件（驱动模块只能由 X server 加载验证）。消费者侧验证见 test_package 一节。

---

**第 3 次尝试结束**: 2026-09-17
**最终状态**: built（xorg-server 依赖阻塞已消除：SDK 配方内生成；本地 conan create + test_package 全绿；待 CI 复验）
---

**编译结束**: 2026-09-17 16:41
**最终状态**: built
