# sdl_gfx 2.0.7 适配笔记

## 0. 版本选择说明（重要）

本任务原定目标为 **sdl_gfx 2.0.5**，但该版本**在上游从未产出分发物**：

- 官方站点 <https://www.ferzkopp.net/Software/SDL_gfx-2.0/SDL_gfx-2.0.5.tar.gz> → HTTP **300**（mod_speling：document could not be found），`.zip` 同；
- 上游 ChangeLog 中唯一无发布日期的条目：`Ver 2.0.5 - n/a`；
- GitHub `ferzkopp/SDL_gfx`：无 tag、无 release（master 为 `MICRO_VERSION=26`）；
- Debian（含 snapshot）最早版本为 `2.0.13-1`；6 个常见镜像（NetBSD/FreeBSD/libsdl.org/…）404；
- 制品仓：`conan download "sdl_gfx/2.0.5" -r=ohpcd --only-recipe` → exit 1（not found）。

经确认后**改用 2.0.7**（官方站点现存最早可用版本，`SDL_gfx-2.0.7.tar.gz` → HTTP 200），整个 2.0.x 线对 SDL 1.2 的依赖语义一致。

## 1. 编译环境

- 构建系统: autotools（2001 年代 autoconf/libtool 产物，configure 与 Makefile.in 均由上游预生成，无需 automake/autoconf）
- 编译日期: 2026-10-08
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）
- Conan: 2.29.1（OHOS 适配版），profile `ohos-aarch64`（os=OHOS / arch=armv8 / clang 15）
- 状态: built（静态库 `libSDL_gfx.a`）

## 2. 源码核验

```bash
curl -I https://www.ferzkopp.net/Software/SDL_gfx-2.0/SDL_gfx-2.0.7.tar.gz     # HTTP 200
sha256sum SDL_gfx-2.0.7.tar.gz   # 两次独立下载一致
# e2c1a74d9e22f5d84fbfe09ddf01c02cddbebcc9667bb77455b0b4d9e44b92e1
tar -xzOf SDL_gfx-2.0.7.tar.gz SDL_gfx-2.0.7/configure.in | grep -E "MAJOR_VERSION=|MINOR_VERSION=|MICRO_VERSION="
# MAJOR_VERSION=2 / MINOR_VERSION=0 / MICRO_VERSION=7  → 版本自证一致
```

## 3. 编译步骤（真实命令）

```bash
# ① configure（SDL_CONFIG 指向配方生成的 sdl-config shim；关闭 x86 MMX）
SDL_CONFIG=<shim> sh <src>/configure --prefix=$HOME/usr/local --disable-mmx
# ② 编译（libtool → llvm-ar/llvm-ranlib）
make -j1
# ③ 安装到 staging
make install DESTDIR=$TEST_PREFIX
```

产物：`libSDL_gfx.a`（静态库，72~80 KB）+ 5 个头文件 + `libSDL_gfx.la`。
`conan create` 走配方化路径（Autotools 助手，VPATH 构建），退出码 0。

## 4. 遇到的问题与解决方案（按真实发生顺序）

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|----------------------|------|----------|
| 1 | `config.guess: unable to guess system type`（exit 1） | 打包的 config.guess 为 2001-01-17 版，不认识 `uname -s = HarmonyOS`、`uname -m = aarch64` | 补丁 0001/0003：新增 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos` |
| 2 | `Invalid configuration 'aarch64-unknown-linux-ohos': machine 'aarch64-unknown' not recognized` | 2001-01-12 版 config.sub 既无 aarch64 CPU、也无 linux-ohos 内核-OS 对 | 补丁 0002/0004：CPUs 列表加 `aarch64`/`aarch64-*`，KERNEL-OS 与 os 归一化加 `-linux-ohos*` |
| 3 | `checking for sdl-config... no` → `configure: error: *** SDL version 1.2.0 not found!` | `AM_PATH_SDL` 只能从 **sdl-config 脚本**读取 cflags/libs，而 Conan `sdl/1.2.15` 包只含 `include/SDL/*.h` + `lib/libSDL.a`（无 sdl-config、无 SDL.pc） | `generate()` 生成 `sdl-config` shim（指向 `self.dependencies["sdl"].package_folder`），经 `Environment().vars(self, scope="build").save_script()` 注入 `SDL_CONFIG`（Autotools 助手以 `env="conanbuild"` 运行 configure） |
| 4 | `SDL_imageFilter.c:32: error: unrecognized instruction mnemonic`（20 个错误） | configure 默认 `--enable-mmx`，向 `CFLAGS` 注入 `-DUSE_MMX`，启用 x86 MMX 内联汇编；aarch64 无 MMX | 传 `--disable-mmx`（上游 README 明示非 x86 平台用此项，无需改源码） |
| 5 | `conan create` source() 阶段 `sha256 hash failed … Computed hash: ba81689d…` | 官方服务器（Apache `AddEncoding x-gzip`）对 `.tar.gz` 回 `Content-Encoding: x-gzip`；conan 的 requests/urllib3 下载器按 HTTP 语义**透明解压**，哈希对象变成解压后的 tar 流（`ba81689d… = sha256(gunzip(文件))` 已实测坐实） | `source()` 中 `get()` 失败后回退 `urllib.request` 原始字节下载 + `check_sha256` + `unzip`（先例：blepvco 0.1.0、irpas 0.10；知识库 DRAFT-conan-downloader-xgzip-content-encoding / E690） |
| 6 | `configure[3419]: …/sdl-config: can't execute: Permission denied` | 误用 `chmod(self, shim, 0o755)`——Conan 2.15+ 的 `chmod()` 签名是 `read/write/execute` 布尔参数，不是 mode | 改为 `chmod(self, shim, read=True, write=True, execute=True)` |
| 7 | test_package CMake 编译期 `'SDL/SDL.h' file not found` | Conan 对**静态**包的 traits 优化把下游 require 标成 `headers=False`，CMakeDeps 生成的 `sdl_INCLUDE_DIRS_RELEASE` 为空（直接 `--requires=sdl` 时正常，传递时丢失） | `self.requires("sdl/1.2.15", transitive_headers=True)`——SDL_gfx 公开头文件 `#include <SDL/SDL.h>`，下游必须拿到 SDL include 目录（先例：at-spi2-core 2.60.5） |
| 8 | CMakeDeps 报 `Library 'SDL_gfx' not found in package` | `package()` 只查 `self.source_folder/.libs`，而 Autotools 助手在本配方是 **VPATH（out-of-source）构建**，库落在 `build_folder/.libs` | `package()` 先查 `build_folder/.libs`，回退 `source_folder/.libs` |
| 9 | 自写 test_package 像素断言 4 条 FAIL（库返回成功但不绘制） | **不是库缺陷**：SDL_gfx 2.0.7 的 `___Color` 约定是 `0xRRGGBBAA`（`SDL_gfxPrimitives.h:44` 明示），alpha 是**低字节**；最初按 ARGB 传 `0xFFFF0000`（alpha=00）→ 透明即“静默不绘制” | 测试颜色改用 `0xFF0000FF`/`0x00FF00FF`，并补 alpha=00 无操作、alpha=FF 不透明两条断言固化该约定 |

## 5. 源码修改（补丁清单）

仅 4 个平台可移植性补丁，**无业务逻辑改动**：

| 补丁 | 目标文件 | 内容 |
|------|----------|------|
| `0001-Test-config.guess.patch` | `Test/config.guess` | 新增 HarmonyOS 分支（`aarch64-unknown-linux-ohos`），供上游测试程序 configure 使用 |
| `0002-Test-config.sub.patch` | `Test/config.sub` | 同上（Test/ 副本） |
| `0003-config.guess.patch` | `config.guess` | 新增 HarmonyOS 分支（`aarch64-unknown-linux-ohos`） |
| `0004-config.sub.patch` | `config.sub` | CPUs 列表加 `aarch64`/`aarch64-*`；KERNEL-OS 与 os 归一化加 `linux-ohos` |

补丁已实测可干净应用到原始源码（`patch -p1 --dry-run` 全部 exit 0，应用后 `config.guess`/`config.sub` 输出 `aarch64-unknown-linux-ohos`）。

## 6. 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| `sdl` | 1.2.15 | 直接强制（构建期 + 运行期） | `configure.in` `AM_PATH_SDL(SDL_VERSION=1.2.0, …, AC_MSG_ERROR)`；配方声明 `transitive_headers=True` |
| `alsa-lib` | 1.2.16 | 传递强制 | 由 `sdl` 配方默认 `alsa=True` 引入（conan download exit 0） |
| musl libc / libm / libdl / pthread | 系统 | 系统库 | `cpp_info.system_libs = ["m","dl","pthread"]` |

## 7. 上游测试申报表（R51 三步法）

**① 清点**：`Test/Makefile.am` 只声明 4 个 `bin_PROGRAMS`，**没有 `TESTS=` 注册**；主构建目录 `make check` 实测输出 `make: Nothing to be done for 'check'.`（exit 0）→ 上游**没有自动化测试套件**，只有 4 个手动演示程序（`assertion_count = 0`）。

**② 实际构建**（`Test/configure` + `make`，链接 staging 的 `libSDL_gfx.a`）：4/4 成功。

**③ 实际运行**（本机 aarch64，`SDL_VIDEODRIVER=dummy`）：

| 用例 | 类型 | 命令 | 结果 |
|------|------|------|------|
| `TestImageFilter` | 批量数组演示（自动退出） | `./TestImageFilter` | **exit=0**，输出 15 字节数组逐函数 MMX/C 路径对比 |
| `TestRotozoom` | 交互演示（需显示/键盘） | `timeout 8 ./TestRotozoom` | exit=124（超时终止）；已加载 `sample8.bmp`/`sample24.bmp` 并跑完 9 组 rotozoom/zoom，**无崩溃** |
| `TestFramerate` | 交互演示 | `timeout 8 ./TestFramerate` | exit=124（超时终止）；帧率循环正常输出 5~35 Hz，**无崩溃** |
| `TestGfxPrimitives` | 交互演示 | `timeout 8 ./TestGfxPrimitives` | exit=124（超时终止）；持续随机绘制，**无崩溃** |

统计：**总数 4 / 构建通过 4 / 运行成功启动 4 / 失败 0 / 跳过 0**；交互程序无法自然退出（无输入设备）属环境限制，已逐项给出技术原因，非“无环境”式豁免。

**④ 消费者断言**（`test_package/test_sdl_gfx.c`，20 条 `check()`）：`conan create` 中实际执行，**20 passed / 0 failed**（含像素级校验、alpha 约定、zoom/rotozoom、framerate、imageFilter）。

## 8. 验证结果

```bash
$ conan create archives/s/sdl_gfx/2.0.7 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
...
checking for SDL - version >= 1.2.0... yes
llvm-ar cru .libs/libSDL_gfx.a SDL_gfxPrimitives.o SDL_rotozoom.o SDL_framerate.o SDL_imageFilter.o
sdl_gfx/2.0.7: Package '04d565a5239a0675415f09ad1127648c8c70711f' created
[100%] Built target test_sdl_gfx
sdl_gfx/2.0.7 (test package): RUN: SDL_VIDEODRIVER=dummy "./test_sdl_gfx"
RESULT 20 passed, 0 failed
exit=0
```

## 9. 交付物

| 文件 | 说明 |
|------|------|
| `lib/libSDL_gfx.a` | 静态库（本平台唯一可行形态，见注意事项 1） |
| `include/SDL_gfxPrimitives.h`、`SDL_gfxPrimitives_font.h`、`SDL_rotozoom.h`、`SDL_framerate.h`、`SDL_imageFilter.h` | 5 个公开头文件 |
| `licenses/COPYING`、`licenses/LICENSE` | 上游 LGPL-2.1 许可证 |

## 10. 注意事项

1. **只支持静态库**：打包的 2001 年 libtool（ltconfig）动态链接器特性表无 OHOS 条目（configure 输出 `checking dynamic linker characteristics... no` → `supports shared libraries... no`），因此只能产出 `libSDL_gfx.a`；`shared=True` 在 `validate()` 中显式拒绝。
2. **颜色参数约定易踩坑**：2.0.7 的 `___Color` 系列是 `0xRRGGBBAA`（alpha 为低字节），`alpha=0x00` 时函数返回成功但**静默不绘制**。消费者写测试时勿按 ARGB 传参。
3. **SDL 头文件传播**：配方已用 `transitive_headers=True` 修复 Conan 静态包 traits 优化导致的 SDL include 目录丢失；若未来改写 `requirements()` 需保留该参数。
4. **sdl-config 缺口**：`sdl/1.2.15` 制品包不含 `sdl-config`，凡使用 `AM_PATH_SDL` 的上游项目都需要同款 shim（本配方已内置生成逻辑）。
5. **上游服务器 x-gzip**：任何指向 www.ferzkopp.net 的 `.tar.gz` URL 在 conan 中都会因 `Content-Encoding: x-gzip` 触发哈希错位，`source()` 的 urllib 回退不可删除。
6. **框架观察（非本库问题）**：`ohc-run.py init-build` 的归档脚手架（`scripts/ohc/init_archive.py`）按 `templates/conanfile-<system>.py`、`templates/conandata.yml`、`templates/test_package-conanfile-<system>.py` 查找模板，而仓库内实际文件名为 `*.tmpl`，因此 init-build 阶段会报“模板不可用”并跳过配方骨架（`conan-init` 子命令本身正常可用）。框架文件未改动（W2 要求单独 PR）。

## 11. 对话记录（关键决策与实测回执）

### 对话 #1 — 目标版本不可得，确认改用 2.0.7

- 提问方：适配任务（目标 `sdl_gfx 2.0.5`）。执行方复核后回报：官方 tarball/zip 均 HTTP 300、ChangeLog `Ver 2.0.5 - n/a`、GitHub 无 tag/release、Debian snapshot 最早 2.0.13、6 镜像 404、ohpcd 无 recipe（conan download exit 1）。
- 决策：**改用 2.0.7**（官方现存最早可用版本）。理由：2.0.x 全系 SDL 1.2 依赖语义一致，且 conandata 的 source URL 必须真实可下载（否则 W3/CI 的 `conan get()` 必 404）。

### 对话 #2 — 首个真实错误：config.guess 不识别 HarmonyOS

- 实测：`sh config.guess` → `config.guess: unable to guess system type`（timestamp 2001-01-17），exit 1；`sh config.sub aarch64-unknown-linux-ohos` → `machine 'aarch64-unknown' not recognized`，exit 1。
- 处置：新增 4 个平台补丁（顶层 + Test/ 各 config.guess/config.sub），补齐 HarmonyOS 分支、aarch64 CPU、aarch64-* 通配、linux-ohos 内核-OS 与 os 归一化。复验：`config.guess` → `aarch64-unknown-linux-ohos`（exit 0）。

### 对话 #3 — 第二个真实错误：SDL 找不到（sdl-config 缺口）

- 实测：`checking for sdl-config... no` → `configure: error: *** SDL version 1.2.0 not found!`，exit 1。
- 根因：`AM_PATH_SDL` 只认 sdl-config 脚本；`sdl/1.2.15` 包内只有 41 个头文件 + `libSDL.a`。
- 处置：配方 `generate()` 生成 sdl-config shim 并注入 `SDL_CONFIG`。复验：`checking for SDL - version >= 1.2.0... yes`，configure exit 0。

### 对话 #4 — 第三个真实错误：x86 MMX 内联汇编

- 实测：`SDL_imageFilter.c:32: error: unrecognized instruction mnemonic`（20 errors），make exit 2。
- 处置：`--disable-mmx`（上游 README 明确指引）。复验：`llvm-ar cru .libs/libSDL_gfx.a ...`，make exit 0。

### 对话 #5 — conan create 连环 4 个错误

1. `sha256 hash failed … Computed hash: ba81689d…` → 服务器 `Content-Encoding: x-gzip` 被 conan 下载器透明解压（`ba81689d…=sha256(gunzip(文件))` 实测坐实）→ `source()` 加 urllib 原始字节回退。
2. `sdl-config: can't execute: Permission denied` → 误用 `chmod(path, 0o755)`（该 API 是 read/write/execute 布尔参数）→ 改为 `chmod(read=True, write=True, execute=True)`。
3. test_package `'SDL/SDL.h' file not found` → 静态包 traits 优化使 `require.headers=False`，CMakeDeps 的 SDL include 目录为空 → `requires("sdl/1.2.15", transitive_headers=True)`。
4. CMakeDeps `Library 'SDL_gfx' not found in package` → `package()` 查错目录（VPATH 构建库在 `build_folder/.libs`）→ 改为 build_folder 优先、source_folder 回退。
- 复验：`conan create` exit 0，`RESULT 20 passed, 0 failed`。

### 对话 #6 — 测试作者侧误判与最终口径

- 现象：首版消费者断言 4 条 FAIL（库返回成功却无像素变化）。
- 结论：**非库缺陷**——2.0.7 的 `___Color` 约定为 `0xRRGGBBAA`（alpha 低字节），alpha=00 静默不绘制；文档依据 `SDL_gfxPrimitives.h:44`。修正测试后 20/20 通过。

### 对话 #7 — finish 阶段：补丁命名与 JC 作用域

- 现象 A：finish Step1 `refresh-patch --auto` 以规范名重建补丁并把旧补丁移入 `patches/.patch-backup-<ts>/`，导致 conandata 引用的自定义补丁名不存在 → G2 报 `Patch file does not exist`。
- 处置 A：改用 refresh-patch 规范名（0001-Test-config.guess.patch …）+ 条目显式 `strip: 1`（E515），删除备份目录。
- 现象 B：本地 W3 的 junk_check 在 `full` 模式（整仓 `git ls-files`）下命中**他人归档**中已提交的既有标记文件（cloog/kics/libbfio/thc 的 `.staging-verified`、`.build-closed`），与本档案无关。
- 处置 B：按 CI 的 PR 作用域复跑（`JUNK_PR_DIFF=<本档案 14 文件清单>`，junk_check 官方 prdiff 模式）→ JC 通过；未触碰他人归档，未提交任何 commit。

---
**编译结束**: 2026-10-08 19:17
**最终状态**: built
