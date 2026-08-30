# libxft 2.3.8 适配笔记

## 编译环境

- 构建系统: autotools（libtool + pkg-config）
- 编译日期: 2026-08-28
- 设备: HarmonyOS HongMeng Kernel 1.12.0 / aarch64（**设备端原生编译与运行验证**）
- 编译器: clang 15.0.4（`aarch64-unknown-linux-ohos`），libc 为 musl 系
- Profile: `ci/conan/profiles/ohos-aarch64`（`-pr:h` 与 `-pr:b` 同一份，与 CI 完全一致）
- 状态: built

## 为什么必须新写配方（不能沿用 2.3.9）

本仓库已有 `archives/l/libxft/2.3.9`，走的是上游 **Meson** 构建。
2.3.8 是**最后一个带 Autotools 的 libXft 发布**：解压后只有 `configure.ac` +
`Makefile.am`，没有 `meson.build`。因此 2.3.9 的 Meson 配方、其
`lib_man_suffix` 选项与 alias 处理都不可复用；本配方按仓库内已合并的
X.Org Autotools 先例（`libxext/1.3.7`、`libxrender/0.9.12`）重写构建段。

## 源码与官方性

| 项 | 值 |
| --- | --- |
| URL | `https://xorg.freedesktop.org/releases/individual/lib/libXft-2.3.8.tar.xz` |
| SHA-256 | `5e8c3c4bc2d4c0a40aef6b4b38ed2fb74301640da29f6528154b5009b1c6dd49` |
| 交叉验证 | `https://www.x.org/archive/individual/lib/libXft-2.3.8.tar.xz` 同一 SHA-256（两个官方主机一致，R39） |
| 文件数 | 127（2.3.9 为 129，差异来自构建系统替换） |

## 依赖

`preflight_check.sh libxft/2.3.8`：**5 个依赖全部已发布**，且 `libxft/2.3.8`
版本号未被占用（R36/R37）。除配方声明外，另用 `conan install --build=never`
实测过**二进制**命中（R35）：`libx11/libxrender/fontconfig/freetype/xorgproto`
及其传递闭包均从 `ohpcd` 下载成功。

| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| libx11 | 1.8.13 | `PKG_CHECK_MODULES(XRENDER, xrender >= 0.8.2 x11)` |
| libxrender | 0.9.12 | 渲染扩展 |
| fontconfig | 2.18.3 | `fontconfig >= 2.5.92` |
| freetype | 2.14.3 | `freetype2 >= 2.1.6` |
| xorgproto | 2025.1 | 协议头 |
| util-macros | 1.20.1 | `tool_requires`，见问题 #8 |

## 遇到的问题与解决方案

| # | 现象（原始错误） | 根因 | 解决方案 |
| --- | --- | --- | --- |
| 1 | `configure: error: cannot guess build type` / `config.guess: unable to guess system type`（E007） | `uname -s` = `HarmonyOS`、`uname -r` = `HongMeng Kernel 1.12.0`，上游 2022-09-17 版 `config.guess` 无该分支 | **源码补丁** `0001-config.guess.patch`：新增 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos` |
| 2 | `Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not recognized`（E072） | `config.sub` 的 OS 白名单不含 `ohos` | **源码补丁** `0002-config.sub.patch`：白名单加入 `ohos*` |
| 3 | `Kernel 'linux' not known to work with OS 'ohos'`（E122） | `case $kernel-$os` 组合表缺 `linux-ohos*` | 同一补丁追加 `\| linux-ohos*` |
| 4 | 先用 `scripts/patch-autotools-ohos.pl` 一键打补丁后仍失败 | 脚本插入的是 `ohos-linux`（方向反了），且对 `linux-ohos` 报 "already present" 假阳性（匹配到 `maybe_os` 的 `linux-*`）——这正是 E122 的成因 | 不用该脚本，改手工最小补丁；验证 `config.sub aarch64-unknown-linux-ohos` rc=0，并回归 `aarch64-unknown-linux-gnu`、`x86_64-unknown-linux-musl` 未受影响 |
| 5 | `config.status: error: could not setup config files machinery`（`./confe5Uvbn/subs1.awk: Permission denied`） | 上游 `configure` 创建 `config.status` 暂存目录前执行 `umask 077`；HMDFS 把它归一化成 owner 不可写的目录 | 在 **build 目录内的副本** `configure-ohos` 里把 `umask 077`→`umask 022`。`configure` 属生成文件，按 R6 不打源码补丁，导出的源码保持字节一致。仅作用于任务私有构建目录内的 autoconf 临时文件，不作为任何权限边界 |
| 6 | libtool 链接期消费过期 `.la`：`libX11.la` 的 `dependency_libs` 指向 `.cache/conan2` 与构建机的 `.conan2/p/b/...`；`libfreetype.la` 的 `libdir='//lib'` | 已发布包的 libtool 元数据带构建机绝对路径 | `generate()` 生成 **libtool shadow**：复制被引用的实体库、把 `libdir`/`dependency_libs` 重绑到任务目录，并将 `-L<shadow>` 置于 LDFLAGS 前。实测 `prepared 30 libtool shadows with 132 path replacements`。对指向**不存在目录**的 `-L` 采取丢弃而非硬失败（libxext 的 fail-closed 版本在 CI 干净环境下会因用户级前缀缺失而中断） |
| 7 | `checking whether we are cross compiling... configure: error: cannot run C compiled programs.`（rc=77） | 三重叠加，见"问题 #7 展开" | 见下 |
| 8 | configure 打印 `Package xorg-macros was not found ... No package 'xorg-macros' found` | `XORG_MACROS_VERSION(1.8)`/`XORG_DEFAULT_OPTIONS` 需要 `xorg-macros.pc`；缺失时 `macros_datadir` 为空，man/DOCUSER 替换退化 | `tool_requires("util-macros/1.20.1")`（该配方已发布，其 `package_info()` 主动暴露 `PKG_CONFIG_PATH` 与 `ACLOCAL_PATH`）；同时 `generate()` 把 `self.generators_folder` 追加进 `PKG_CONFIG_PATH`——`PkgConfigDeps` 只写 `.pc` 不改 `PKG_CONFIG_PATH`，否则上游 `PKG_CHECK_MODULES` 探测不到 Conan 生成的元数据 |
| 9 | 包内 `libXft.so.2` 别名实体化后，按 rpath 直接加载仍 `Permission denied` | `shutil.copyfile` 不保留 mode，别名落成 `rw-`（无 owner 可执行位），无法 `PROT_EXEC` 映射 | 实体化时补 `shutil.copymode(source, alias)`，并 fail-closed 断言别名带 `S_IXUSR`、与源字节一致；SONAME 从 `llvm-readelf -d` 读取而非拼字符串 |
| 10 | **CI worker 失败而本机通过**：`checking whether the C compiler works... no` → `C compiler cannot create executables`（rc=77），机器人日志无根因 | 我为问题 #7 导出的全局 `LD_LIBRARY_PATH=<视图>` 被子进程继承，视图里的 Conan `libxml2.so.16` 抢占了 OHOS SDK 链接器的解析：`Error relocating /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld: xmlFreeDoc: symbol not found`，`lld` 起不来即表现为"编译器不能产出可执行文件"。本机侥幸不复现（SDK 那份 libxml2 命中顺序不同） | 删除全局 `LD_LIBRARY_PATH`，只保留嵌入产物的 `DT_RPATH`（三组对照里 A 组本就 rc=0，证明该变量不需要）；并在 `_configure_ohos` 失败时回显 `config.log` 的失败标记与尾部，使 CI 能自报根因而非靠人猜 |

### 问题 #7 展开（本次最关键的平台结论）

`AutotoolsDeps` 会导出 `LIBS`，因此**连 autoconf 最早的 `AC_PROG_CC` 运行探测
也会链接整个依赖闭包**——程序必须真的能在本机关起来。逐层实测：

1. **签名（E135）**：`dlopen` 绝对路径 `libfontconfig.so.1` 报
   `Permission denied`，而同一视图目录里的 `libfreetype.so.6`、
   `libxml2.so.16` **OK**。两者都含 `.codesign` 段，差别是 fontconfig 那份
   签名在本机不被接受——即"已发布包的签名可能在消费端失效"。
2. **符号链接别名**：包目录里的 `libfontconfig.so.1` 是指向 `.so.1.17.0`
   的符号链接，加载器按该名解析失败（对应 AGENTS 中 E050/E073
   "别名必须做加载器实测"）。
3. **`LD_LIBRARY_PATH` 与 `DT_RPATH` 的优先级**（修正"OHOS 忽略
   `LD_LIBRARY_PATH`"的旧读法，见 AGENTS §知识库已知过期与冲突）：
   同一二进制三组对照——

   | 条件 | 结果 |
   | --- | --- |
   | 不设 `LD_LIBRARY_PATH`，仅嵌入 `-Wl,--disable-new-dtags,-rpath,<实体化视图>` | rc=0 |
   | `LD_LIBRARY_PATH=<依赖包目录>`（含符号链接别名）+ 同样 rpath | **rc=127** |
   | `LD_LIBRARY_PATH=<实体化视图>` + 同样 rpath | rc=0 |

   结论：本机加载器**认** `LD_LIBRARY_PATH`，且一旦设置就**压过** `DT_RPATH`；
   把 `LD_LIBRARY_PATH` 指向仍含符号链接别名的包目录，反而会让本可工作的
   rpath 查找失败。旧配方（`libxrender` 用 `--host=`、把 `cross_compiling`
   置为 yes）之所以"看起来没问题"，是因为那直接跳过了运行探测——R1 禁止。

**解法**：`generate()` 构建 `runtime-libs` **实体化 + 重签名视图**——遍历依赖
`cpp_info.libdirs`，`resolve` 后以真实文件名落盘为**普通文件**（越出包边界、
同名不同字节均 fail-closed），逐个 `llvm-objcopy --remove-section .codesign`
后 `binary-sign-tool -selfSign 1` 重签名并校验 `.codesign` 计数为 1；随后
LDFLAGS 只嵌入 `-Wl,--disable-new-dtags -Wl,-rpath,<view>`。**不设全局
`LD_LIBRARY_PATH`**——初版曾把它指向视图，CI worker 上被证明有害，见问题 #10。
依赖包本体只读、零改动。

**打包侧收口**：`package()` 用 `patchelf --remove-rpath` 去掉指向构建目录的
rpath（已发布依赖同样不带 rpath，避免把本机缓存路径写进产物），再实体化别名。
实测日志：`dropped the build rpath from 1 shared objects`、
`materialised 2 shared-library aliases as regular files`。

## 源码修改

只有 2 个补丁，均由 `ohc-run.py refresh-patch --auto libxft 2.3.8` 生成
（orig/work 哈希记录在版本级 `manifest.yaml` 的 `patch_generation`）：

| 补丁 | 规模 | 内容 | 平台专属 |
| --- | --- | --- | --- |
| `patches/0001-config.guess.patch` | +13/-0 | 新增 `*:HarmonyOS:*:*` 分支 | 是（纯新增分支，不改原逻辑流） |
| `patches/0002-config.sub.patch` | +3/-2 | OS 白名单加 `ohos*`；`kernel-$os` 组合加 `linux-ohos*` | 是 |

未修改任何生成文件（`configure`/`Makefile.in`/`Xft.h.in` 保持上游字节）。
未使用 `#ifdef __OHOS__`：平台差异全部落在平台描述文件里，源码逻辑零改动
（R8 禁止空壳 stub，这里连条件编译都不需要）。

## ABI 与元数据

- `src/Makefile.am` 的 `-version-number 2:3:8` 与 `-no-undefined` 保持上游，
  产物 `SONAME = libXft.so.2`，与 2.3.9 一致。
- `xft.pc` 的 `prefix` 改写为 `${pcfiledir}/../..` 以便重定位；
  `Requires: xproto` 与 `Requires.private` 保持上游原文；删除 libtool 的
  `libXft.la`，避免把本机路径外泄给下游。
- `package_info()`：`libs=["Xft"]`、`pkg_config_name="xft"`、
  `cmake_file_name="libxft"`、5 个 `cpp_info.requires`。
- `PkgConfigDeps.set_property` 把 `freetype→freetype2`、`xorgproto→xproto`
  对齐上游探测名（与 2.3.9 同处理）。
- 系统同名库检查：`/system/lib64` 下无 `libXft*`，不触发 R26 静态化，动态交付。

## 验证结果

```bash
# 与 CI 完全同参数（ci/conan/build_and_test.sh 的 CONAN_CREATE_ARGS）
conan create archives/l/libxft/2.3.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="libxft/*"          # → RC=0
```

- 上游测试：**0/0**。2.3.8 无 `test/` 目录，顶层 `Makefile.am` 只有
  `SUBDIRS = man src`，无 `TESTS`/`check_PROGRAMS`/`check-local`；
  `make -j1 check` 在 `build()` 中真实执行（L1c 有据）。
- 安装态消费者 **3/3**，合计 **137** 条断言：

  | 可执行文件 | 内容 | 结果 |
  | --- | --- | --- |
  | `libxft_api_surface` | 以带类型的重定位绑定安装头里全部 **77** 个公共函数，并执行版本与 FreeType 初始化契约 | `LIBXFT_API_SURFACE_PASS symbols=77 assertions=81` |
  | `libxft_name_contract` | `XftNameParse/Unparse` 往返、XLFD 字段映射（family/foundry/weight/slant/size/pixel size/原始名字保留）、5 个负例必须返回 NULL | `LIBXFT_NAME_CONTRACT_PASS assertions=28` |
  | `libxft_soname_contract` | **不链接** libXft，仅通过 `dlopen("libXft.so.2")` 与 `dlopen("libXft.so")` 解析并调用真实入口 | `LIBXFT_SONAME_CONTRACT_PASS libraries=2 assertions=28` |

- 静态变体：`-o libxft/*:shared=False` 独立构建并打包出 `libXft.a`，两个
  链接型消费者各通过 1 次；`soname_contract` 依产物实况打印显式 SKIP
  （包内不存在共享对象），不做无条件成功伪装。
- 交叉核对：从安装头正则抽出的公共函数集大小与 `api_surface.c` 绑定数均为
  **77**，与 2.3.9 一致。

## 交付物

| 文件 | 大小 | 说明 |
| --- | --- | --- |
| `lib/libXft.so.2.3.8` | 108864 | 真实共享库，SONAME `libXft.so.2`，已去构建 rpath |
| `lib/libXft.so.2`、`lib/libXft.so` | 108864 ×2 | 实体化普通文件（带 owner 可执行位） |
| `include/X11/Xft/Xft.h`、`XftCompat.h` | — | `Xft.h` 由 `Xft.h.in` 生成，版本号已展开 |
| `lib/pkgconfig/xft.pc` | — | prefix 已改为 `${pcfiledir}/../..` |
| `licenses/COPYING` | — | 上游 HPND-sell-variant 原文 |
| 78 个 man 页（`.3`） | — | 上游文档随包安装 |

## 未覆盖范围（如实记录）

本库绝大多数公共 API 的首参是 `Display *`。设备无 X server，`/dev/pts`
亦不可访问，因此**未执行**需要真实 X 连接的渲染路径（`XftFontOpen*`、
`XftDraw*`、`XftTextRender*`、`XftFontInfoCreate` 等——后者会经
`_XftDisplayInfoGet(dpy, True)` 解引用 `dpy`，传 NULL 即崩）。对这些函数的
覆盖方式是**链接期类型化绑定 + 运行期 dlsym 解析**，即"符号存在且签名可用"，
**不等于渲染结果正确**。这是 X.Org 客户端库在无 X server 环境下的固有边界；
未使用任何 stub 或空实现替代（R40）。

## 注意事项

1. OHOS 分支依赖 `/data/service/hnp/bin/bash`、`llvm-readelf`、`llvm-objcopy`、
   `binary-sign-tool`、`patchelf`；缺任一即 fail-closed，不降级为"看起来通过"。
2. `runtime-libs` 视图会重签名约 99 个共享对象（含别名），是构建期主要开销；
   依赖闭包变化时重签数量随之变化。
3. `umask 022` 与"重签名"两处都是**环境级 workaround**，触发条件与适用范围见
   问题 #5、#7；不改变其他软件的语义，也不放宽任何 DAC 边界。
4. 软件级 `archives/l/libxft/manifest.yaml` 的 `build_system: meson` 描述的是
   2.3.9；2.3.8 为 autotools，按 ARCHIVE-SPEC"可被版本级覆盖"在版本级单独声明。
## 决策记录

### 对话 #1 [2026-08-28]

- 问题: 本仓库已有 libxft 2.3.9，能否直接复用其配方
- 操作: 比对上游 tarball 文件清单，确认 2.3.8 无 `meson.build`，只有
  `configure.ac`/`Makefile.am`
- 结果: 判定构建系统不同，按 X.Org Autotools 先例（libxext 1.3.7）重写

### 对话 #2 [2026-08-28]

- 问题: configure 先报 `OS 'ohos' not recognized`，随后又报
  `Kernel 'linux' not known to work with OS 'ohos'`
- 操作: 先用 `scripts/patch-autotools-ohos.pl` 试打，发现它插入的是
  `ohos-linux` 且对 `linux-ohos` 误报已存在；改为手工最小补丁，并用
  `refresh-patch --auto` 固化为 2 个源码补丁
- 结果: `config.guess`/`config.sub` 均输出 `aarch64-unknown-linux-ohos`，
  未使用任何 `--build/--host/--target`（R1）

### 对话 #3 [2026-08-28]

- 问题: 三元组已正确，却连续三轮卡在 `cannot run C compiled programs`（rc=77）
- 操作: 停止调参（R43 口径），改读 `config.log` 第一条真实错误，再用
  dlopen / rpath / `LD_LIBRARY_PATH` 三组对照实验定位：依赖库签名在本机不被
  接受 + 符号链接别名不可解析 + `LD_LIBRARY_PATH` 压过 `DT_RPATH`
- 结果: 引入实体化且重签名的任务私有运行时视图，configure 真实通过；
  结论沉淀为知识草稿 E257/E321/E322/E323

### 对话 #4 [2026-08-28]

- 问题: 包内别名实体化后按 rpath 直接加载仍 `Permission denied`
- 操作: 对比 mode 发现 `shutil.copyfile` 未保留 owner 可执行位，补
  `copymode` 并加 fail-closed 断言；同时修掉上一版把 glob 拼成
  `libXft.so.so*` 导致实体化静默空转的缺陷
- 结果: `materialised 2 shared-library aliases as regular files`，
  `libxft_soname_contract` 以纯 dlopen 方式实测通过

### 对话 #5 [2026-08-28]

- 问题: PR #7080 的 CI 在 `conan-build-test` 失败（`C compiler cannot create
  executables`），而本机同参数共享/静态两变体均 RC=0；机器人只截 stdout，
  autoconf 把真实错误写进 `config.log`，第一轮完全看不到根因
- 操作: 不猜改（R43）；先给 `_configure_ohos` 加"失败即回显 `config.log`
  标记行 + 尾部"的诊断段并推给 CI，拿到证据后才定位：我为加载问题导出的全局
  `LD_LIBRARY_PATH=<视图>` 被子进程继承，把 SDK 链接器 `lld` 需要的 `libxml2`
  顶成了 Conan 那份，符号不匹配致 `lld` 崩溃
- 结果: 删除全局 `LD_LIBRARY_PATH`，仅保留嵌入产物的 `DT_RPATH`；本机复验
  两变体仍 RC=0（说明该变量本来就不必要）。结论回写 E257 草稿（含新 forbid_2）
---

**编译结束**: 2026-08-28 22:52
**最终状态**: built

状态: built
