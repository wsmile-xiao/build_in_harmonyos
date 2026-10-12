# RetroArch 1.22.2 — OpenHarmony PC 适配笔记（路径 C · 高难度挑战）

## 1. 上游与版本

- 仓库：<https://github.com/libretro/RetroArch>
- tag：`v1.22.2`，commit `69a4f0ea1e8aaf442ae4858f2e7f2b31a1776576`
- 源码：`codeload.github.com` 官方 tarball，sha256
  `245ef18c8fa8fbd9fbb5eb25cf43e17c6aace2f95c1ed99873cbd794012bb232`
  （71,629,881 字节，自带 `libretro-common/` 与 `deps/`，无需 git 子模块）
- 规模：约 1763 个 `.c`/`.cpp` 翻译单元；自研 quickbuild（`configure` + `Makefile` +
  `qb/*.sh`）；内置第三方依赖 zlib / libFLAC / libchdr(lzma) / 7zip / rcheevos /
  glslang(SPIRV) / switchres / xxHash / zstd 等。

## 2. 为什么按路径 C 申报（逐条对照四条件）

1. **私有系统接口**：部分成立。OHOS 无桌面 Linux 的 X11/Wayland/ALSA/V4L2/DRM/Udev
   等接口，需按平台裁剪；但最终未新增私有 ioctl/syscall 改造，故标「部分成立」。
2. **私有编译工具链**：不满足。使用 OHOS SDK clang + 自带 lld 即可，未引入私有工具链。
3. **含汇编 / 闭源二进制 / 特殊调度等复杂架构**：**硬命中**。树内含 ARM NEON 与
   x86 SSE 汇编热点、自研 quickbuild 构建系统、`libretro-common` 运行时、glslang
   SPIRV 编译器、内存对齐/无锁数据结构等复杂架构；单文件不可行。
4. **依赖链庞大 / 全量测试成本极高**：**硬命中**。1763 个翻译单元 + 大量内置依赖，
   完整构建耗时长、平台裁剪项众多。

> 如实标注：1 部分成立、2 不满足、3/4 硬命中。仅申请纳入路径 C 候选清单，
> 分值以评审委员会复审/答辩为准。

**路径 C 硬门槛「上游测试全量跑通」**：上游在 `libretro-common/test/` 下提供 5 个
libcheck 单测套件（`test_hash` / `test_linked_list` / `test_generic_queue` /
`test_stdstring` / `test_utils`），由 `libretro-common/Makefile.test` 定义。本适配在
`build()` 内编译并**实际执行**全部 5 个套件：

```
test_hash         3 checks   0 failures
test_linked_list 89 checks   0 failures
test_generic_queue 16 checks 0 failures
test_stdstring   16 checks   0 failures
test_utils        3 checks   0 failures
--------------------------------------------
合计            127 checks   0 failures / 0 errors
```

## 3. OHOS 适配要点（5 个补丁）

### 0001 — quickbuild 把 HarmonyOS 识别为 Linux
`qb/qb.system.sh` 用 `uname -s` 判平台；OHOS 返回 `HarmonyOS`，不在 case 列表里，
落到 `*) OS="Win32"`，随后 `configure` 因缺 `windres` 报
`Error: Cannot proceed without windres.`。HarmonyOS PC 是 Linux/musl(bionic) 用户态，
并入 `Linux` 分支即可。

### 0002 — 守卫可选 IIO 光照传感器线程的 pthread 取消
OHOS bionic **没有** `pthread_cancel` / `pthread_setcancelstate` / `pthread_setcanceltype`。
`input/common/linux_common.c` 的可选 IIO 光照传感器线程用到它们。用
`HAVE_PTHREAD_CANCEL` 守卫：不可用时线程仍正常 `join`，靠自身 `done` 标志退出，
只损失「立即唤醒取消」的快路径，无功能回归。（与既有 E121 / mergerfs 同族。）

### 0003 — 内置 glslang 以特性宏走 DetachThread 清理路径
`deps/glslang/.../ossource.cpp` 的 `OS_CleanupThreadData()` 本就有 `#ifdef __ANDROID__`
跳过 pthread 取消清理的分支；按 R8（补丁不得引入 `__OHOS__` 平台宏，与 0002 的
特性宏写法统一），条件改为
`#if defined(__ANDROID__) || !defined(HAVE_PTHREAD_CANCEL)`：OHOS bionic 无
pthread 取消 → 宏未定义 → 走 `DetachThreadLinux` 清理（与原
`pthread_cleanup_push/pop` 路径功能等价，零行为风险）。

### 0004 — 回移 `string_hex_to_unsigned` 单字符缺陷修复
1.22.2 的实现里，当输入长度为 1（如 `"a"`）时走 `else return 0`，返回 0；而
`libretro-common/test/string/test_stdstring.c` 期望 `10`。上游在 1.22.2 **之后**
（master）已重写该函数修好。这里按 master 的实现回移，使上游测试与实现一致。

### 0005 — 让上游 libcheck 套件可编译、可运行（含 OHOS /tmp）
上游 `libretro-common/test/` 的套件**从未纳入任何构建**，已与代码脱节：
- `test_stdstring.c` 用陈旧的 **3 参** `string_replace_substring`（API 早已是 6 参）；
- `test_string_filter` / `test_string_replace` 向文档标注「必须非 NULL，否则 UB」的
  叶函数 `string_remove_all_chars` / `string_replace_all_chars` 传 NULL → 段错误；
- `test_hash.c` / `test_utils.c` 用 `tmpnam()`，而 bionic 的 `tmpnam()` 硬编码
  `P_tmpdir=/tmp`（忽略 TMPDIR/TEMP），OHOS `/tmp` 只读 → `fopen` 失败；
- 源码清单缺 `file/file_path_io.c`、`file/retro_dirent.c`、`compat/compat_strldup.c`
  等链接依赖。

本补丁按上游后续（PR #19292 等）**相同方式**修复：删掉 NULL 调用、改用 6 参 API、
补齐源文件，并把测试临时文件改走 `TEMP`/`TMPDIR`（回退 `.`）。仅测试侧改动，
不改变库行为（0004 除外，那是库缺陷修复）。

## 4. 构建 profile（无头 / 无 GPU 目标）

以 `./configure` 显式关闭全部桌面/GPU/音频/网络/成就后端（见 `manifest.yaml` 的
`configure_options`），保留无头核心运行路径。图形/音频后端由运行期加载的 libretro
核心按 `RETRO_ENVIRONMENT` 协商选择；本次交付聚焦「可构建、可运行、上游测试全绿」。
编译器由 OHOS conan profile 的 `tools.build:compiler_executables` 提供，profile 的
buildenv 把 SDK 的 `clang` 与 `ld.lld` 放入 PATH，链接步骤无需额外 `--ld-path`。

## 5. 产物

- `bin/retroarch`（ELF aarch64，`--version` / `--help` / `--features` 实测 rc=0）
- `licenses/COPYING`
- 软件级 `commands.json`（R38）

## 6. 已知边界（如实申报）

- 未启用 GPU（Vulkan/OpenGL/EGL）、音频（ALSA/Pulse 等）、视频输出（X11/Wayland/
  DRM/KMS）与网络（netplay/成就/在线更新）后端；这些需要 OHOS 上尚不具备的桌面栈
  或服务。属**平台不可行**级别，而非未做。
- 因此本次验证覆盖：编译链接、无头启动（version/help/features）、参数校验路径、
  以及上游 127 项单测。真正加载核心渲染画面需后续补 GPU 后端。
