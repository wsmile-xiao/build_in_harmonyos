# libexadrums 0.7.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15 (OHOS aarch64, libc++)
- 状态: published

## 编译步骤

1. `conan create` 触发 `source()` 下载并解压上游 tarball (`github.com/SpintroniK/libeXaDrums/0.7.0`)。
2. `generate()` 生成 AutotoolsDeps（注入 tinyxml2/minizip 的 -I/-L/-l）+ AutotoolsToolchain
   （额外 `-I<stub>/include`、`-L<stub>/lib -lasound`，并加
   `--build/--host aarch64-unknown-linux-ohos` + `--disable-dependency-tracking`）。
3. `build()` 先声明 `tool_requires`（automake/libtool）并用 `VirtualBuildEnv` 注入 PATH，再用
   OHOS clang 把内嵌的 `asound_stub.c` 编成 `libasound.a`，然后
   `autoreconf -fiv` → `./configure --build/--host=<ohos triplet> --prefix=<pkg>` → `make -j1`。
4. `package()` 执行 `make install`，把 stub 头 `alsa/asoundlib.h` 一并装进
   `include/`，删除 `*.la`，并把 SONAME 别名软链实体化。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游硬依赖 ALSA，OHOS 无 ALSA 且 ohpcd 无 alsa 包 | 音频后端缺失 | 内嵌静态 ALSA stub（libasound.a + 头），所有 snd_* 为 no-op；snd_pcm_open 成功、GetDevices 返回 1 个合成设备 |
| 2 | `PKG_CHECK_MODULES` 需要 pkg.m4，系统 aclocal 仅有 libtool.m4 | 缺 pkg-config 宏 | 删除 configure.ac 的 3 个 PKG_CHECK_MODULES，依赖改由 AutotoolsDeps 注入 |
| 3 | `-lstdc++fs -latomic` 在 clang/libc++ 下不存在 | 链接项不适用 | patch 移除 |
| 4 | `exadrums.pc` 的 `Requires.private: alsa tinyxml2` 会让下游消费者去找系统 alsa | alsa 是 stub，不应外泄 | patch 改为 `tinyxml2` |

## 源码修改

- `patches/0001-configure-drop-pkgconfig-and-werror.patch`：删除 PKG_CHECK_MODULES 三行、去掉 `-Werror`。
- `patches/0002-makefile-drop-stdcxxfs-latomic.patch`：LIBADD 移除 `-lstdc++fs -latomic`。
- `patches/0003-pc-drop-alsa.patch`：`Requires.private` 去掉 alsa。
- `patches/0004-cxx17-drop-ranges.patch`：libc++15 无 `<ranges>`；把 `std::ranges::transform` / `std::views::iota` / `std::views::transform` 改写为显式循环与 `std::find_if`。
- `patches/0005-chrono-system-clock.patch`：libc++ 下 `high_resolution_clock` 与 `system_clock` 非同类型；`Util/Time.h` 改用 `system_clock::time_point` 做 `to_time_t`。

## 依赖版本

- tinyxml2/11.0.0（ohpcd）
- minizip/1.3.1（ohpcd）

## 验证结果

```bash
# test_package（test.cpp，4 条 CHECK 断言；Release -DNDEBUG 下仍生效）
./test_libexadrums
# -> libexadrums version = 0.7.0
# -> ALSA playback devices = 1
# -> round-trip device = default sampleRate = 44100
# -> ALL libexadrums OHOS stub tests passed
```

## 注意事项

- ALSA 桩仅做编译/链接占位：真实音频播放为 no-op。如将来需要真实音频，需提供 OHOS 音频后端替换。
  本适配属**编译级适配**（构建/链接/API 可用），真实发声功能未在 OHOS 实现（R40）。
- 公共头 `Api/eXaDrums.h`、`Sound/Alsa/Alsa.h`、`Sound/Alsa/AlsaParams.h` 仍 `#include <alsa/asoundlib.h>`，
  因此 stub 头随包一起安装到 `include/alsa/`，保证下游消费者可编译。
- test_package 断言用自定义 `CHECK` 宏（非 `<cassert>`）：CI profile `build_type=Release` 带 `-DNDEBUG`，
  `assert()` 会被预处理剔除使测试退化为恒返回 0 的空壳；`CHECK` 在 Debug/Release 下均编译生效并影响退出码。
- `package()` 末尾把 `lib/` 下 SONAME 别名软链实体化（知识条目 E316/E492）：`libexadrums.so` /
  `libexadrums.so.2` 为三段式软链时，OHOS 加载器按 SONAME 打开会失败
  （`Error loading shared library libexadrums.so.2: (needed by ...)`）。

## 构建自举（autoreconf）

上游 GitHub archive 不含 `configure`（autoreconf 产物不进版本库），`build()` 必须先自举。
`configure.ac` 同时使用 `LT_INIT`（需 libtoolize）与 `AM_INIT_AUTOMAKE`（需 aclocal），
而 worker 的 `/data/service/hnp/bin` 只有 autoconf 家族（autoreconf/autoconf/autoheader/autom4te），
既无 `aclocal` 也无 `libtoolize`，CI 实测即在此失败：

```
autoreconf: running: aclocal --force -I m4
Can't exec "aclocal": No such file or directory
autoreconf: error: aclocal failed with exit status: 2
```

故按仓内既有惯例（`argp-standalone` / `abiword-plugin-*` / `audispd`）声明
`tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4.1")`，并由
`VirtualBuildEnv` 把两者 `bin/` 注入 conanbuild 环境的 PATH。

- libtool 必须 **≥ 2.5.4.1**：已发布的 `libtool/2.5.4` 包内 `share/libtool-conan/`
  （libtoolize 的 relocatable pkgdatadir）是**空目录**，会报
  `libtoolize: error: $pkgauxdir is not a directory`；2.5.4.1 为修复版（含三个有效软链）。
- `config.guess` 认不出 HarmonyOS（`uname -s` = HarmonyOS），显式传
  `--build/--host=aarch64-unknown-linux-ohos` 跳过探测，否则 configure 报
  `cannot guess build type; you must specify one`。

## 构建期临时目录（TMPDIR）

OHOS 的 `/tmp` 挂在**只读**分区上，构建期所有临时文件必须改道。`/system/bin/sh`
是 mksh，写 here-document 临时文件时**认 `TMPDIR`**，但当 `TMPDIR` 指向一个
**不存在的目录**时会**静默回退到只读的 `/tmp`**（既不报错也不提示），失败点因此
被推迟到 configure 的 conftest，伪装成编译器问题（CI #60094）：

```
./configure[1903]: can't create temporary file /tmp/shXXXXXX.tmp: Read-only file system
sed: conftest.cpp: No such file or directory
configure: error: C++ compiler cannot create executables
```

注意 `$HOME/tmp` **只存在于交互式 HOME**，CI 沙箱的 HOME 下没有该子目录，所以
「本地绿、CI 炸」正是这条。修法：`_ohos_tmpdir` 把临时目录钉在构建目录内
（`<build_folder>/.ohos-tmp`）并**预建**，`generate()` 里同时导出 `TMPDIR` 与
`TMPPREFIX`（后者供 zsh 的 here-doc 使用），`build()` / `package()` 的子 shell
里再各重复一遍（`install-sh`、`libtool` 都是 shell 脚本，各自需要临时目录）。

## config.status 的 mktemp 临时目录（知识条目 E114）

configure 全流程通过后，紧接着死在 `config.status` 上（CI #60712）：

```
configure: creating ./config.status
./config.status[1027]: can't create ./confkioDMa/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

根因是 **HMDFS 的文件系统限制**：`mktemp -d` 建出的目录权限是 `drwx--S---`
（2700 + setgid），**即使 owner 是当前用户也无法在其中创建文件**，且 `chmod`
也改不动。autoconf 把这个 `mktemp` 引导块烤进了生成的 `configure`，并**原样**
复制进它输出的 `config.status`，所以两条路径都会踩到。

修法（同 `archives/r/rsync`）：autoreconf 之后、运行 configure 之前，程序化改写
`./configure`，把 `tmp` 指向自己用 `os.makedirs` 预建的目录（普通 mkdir 目录，
**不是 mktemp**），并把 `mkdir "$tmp"` 兜底分支置为 `true`：

```python
for old, new in (
    ('`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`', fixed_dir),
    ("tmp=./conf$$-$RANDOM", f"tmp={fixed_dir}"),
    ('(umask 077 && mkdir "$tmp")', "true"),
):
    patched = patched.replace(old, new)
```

改写后 `config.status` 使用 `<build_folder>/.ohos-tmp/conf-tmp`（构建目录内、
预建、可写）。因为 `configure` 里的这段文本正是写 `config.status` 的 heredoc
模板，**只改 `configure` 一处即可同时修好两者**。

## 编译结束

- 适配完成，状态: published。已通过 `conan create` 全链路构建 + `test_package` 四条 CHECK 断言验证（W3 本地 CI 模拟通过）。
- 产物: `libexadrums.so.2.0.0`（动态库，内嵌 ALSA 静态桩）+ 头文件（`include/libexadrums/`、`include/alsa/`）。
