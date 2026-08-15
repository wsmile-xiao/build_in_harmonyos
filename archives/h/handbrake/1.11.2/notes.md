# handbrake 1.11.2 适配笔记（HandBrakeCLI）

## 编译环境

- 构建系统: HandBrake 自定义 make（`./configure` 为 Python 驱动 → 生成 `build/GNUmakefile` → `make`），非 Autotools
- 准备日期: 2026-08-12
- 编译器: clang/clang++ 15（新端口设备路径 `/storage/Users/currentUser/usr/local/bin/clang`），AR/RANLIB/NM 用同目录 `llvm-ar`、`llvm-ranlib`、`llvm-nm`
- 状态: built（r45 真机 `conan create` exit 0；`test_package` 已验证 `HandBrakeCLI --version` / `--help` 2/2 通过）
- 目标: OpenHarmony PC aarch64（aarch64-unknown-linux-ohos）

## 构建方式（conanfile.py build() 复现）

```bash
# 1. 配置（源码根目录执行）
sh configure --force \
  --prefix=/usr/local \
  --disable-gtk --disable-numa \
  --disable-nvenc --disable-nvdec --disable-qsv --disable-vce \
  --disable-mf --disable-libdovi \
  --cc=/storage/Users/currentUser/usr/local/bin/clang \
  --patch=/path/to/_host_gnu_patch_src/install/bin/patch

# 2. 构建（configure 生成的 build/ 目录内）
cd build && make -j2      # 产出 build/HandBrakeCLI

# 3. 打包
# package() 复制 HandBrakeCLI 到 bin/，并用 binary-sign-tool 自签名（ELF codesign）
```

- configure 需 `--force`（build/ 目录已存在时）；`--cc`/`--patch` 显式传路径（R33）
- 33 个 contrib（ffmpeg/x264/x265/libvpx/libass/dav1d/svt-av1/...）全部在树内构建，contrib 产物在 `build/contrib/lib` 下
- 本地验证加速：conanfile `_seed_local_cache()` 复用 `/storage/Users/currentUser/builds/handbrake-1.11.2.work` 的
  `download/`（distfile 缓存，115MB）与 `build/contrib|libhb|test`（已构建产物），并将产物统一 touch 到
  未来时间戳使 make 判定"已最新"，仅重链 HandBrakeCLI（约 3 分钟）。CI/其他机器无此缓存时走完整自包含构建。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 build tuple 非 aarch64-unknown-linux-ohos | HandBrake `make/config.guess` 不认识 HarmonyOS（E007） | 补 `*:HarmonyOS:*:*` case，输出 `$machine-linux-ohos`（0001 补丁） |
| 2 | 各 contrib（freetype/lame/libass/...）configure 报 invalid host | contrib 自带 config.guess 无 OHOS 分支 | 逐个打 A01-config-guess-ohos.patch（0009-0018；libiconv/xz 打 `build-aux/config.guess`，HandBrake 自动应用 A??-*.patch） |
| 3 | ffmpeg contrib configure 报 target_os=harmonyos unknown | OHOS `uname -s` 返回 HarmonyOS，ffmpeg 不支持 | module.defs 强制 `--target-os=linux`，并 `--disable-vulkan`（OHOS sysroot 缺 vulkan_beta.h） |
| 4 | x264 链接报 R_AARCH64_ABS64 against local symbols | OHOS clang 默认 PIE，x264 asm 非 PIC | x264 module.defs 加 `--enable-pic` |
| 5 | x265 构建产物对象后缀错误 | OHOS cmake 产物为 .obj | x265 module.defs `X265.O.ext = .obj` |
| 6 | libass 无法定位 freetype/harfbuzz | 平台过滤不含 HarmonyOS | main.defs/libass module.defs 过滤加 `$(HOST.systemf)=HarmonyOS`，并禁 require-system-font-provider |
| 7 | configure probe repo info 失败 | GitHub tag archive 无 .git/version metadata | 本轮改用官方 `HandBrake-1.11.2-source.tar.bz2`，该 release source asset 自带 `version.txt`，不再需要补丁 |
| 8 | make 报 jobserver mkfifo Operation not permitted | HMDFS 不支持 mkfifo | 无害警告，make 自动退化为串行，继续构建 |
| 9 | 生成的 HandBrakeCLI 无法执行（Operation not permitted） | OHOS 要求 ELF codesign | `binary-sign-tool sign -inFile ... -outFile ... -selfSign 1 -signAlg SHA256withECDSA` 自签名 |
| 10 | 后台 make/进程被杀 | 平台限制 | 前台 + timeout 分块执行；长任务用 nohup 持久化 |
| 11 | tar 解包后 make 时间戳级联重建 contrib | 拷贝产物 mtime 不一致，contrib stamp 依赖链触发重建且部分失败 | 统一 `touch -d '2030-01-02 03:04:05'` 所有已构建产物，使 make 判定最新 |
| 12 | /tmp 只读（E002） | 平台限制 | 临时文件用 `$TMPDIR`（= $HOME） |
| 13 | toybox patch 兼容性 | PATCH.exe 必须 GNU patch | 先解析 PATH/编译器目录/`$HOME/usr/local/bin`；失败时从官方 GNU patch 2.8 源码构建 host tool 并传 `--patch=<build>/_host_gnu_patch_src/install/bin/patch` |
| 14 | GNU patch 2.8 `config.status` 报 `subs1.awk: Permission denied` | OHOS/HMDFS 对 Autoconf `mktemp -d` + 内层 `umask 077` 目录写入异常 | 仅在 host GNU patch 自举源码中把 `configure` 的 `./confXXXXXX` 临时目录创建放宽为 `umask 022` |
| 15 | 顶层 configure 调旧路径 `/data/service/hnp/bin/bash` | 新端口设备没有旧 HNP bash，仅有 `/usr/bin/zsh`、`/bin/sh` | recipe/test_package 使用 `_host_shell()` 选择实际存在的 `CONFIG_SHELL`/`SHELL`/bash/zsh/sh |
| 16 | 顶层 configure `find: ar...(fail) not found` | 新端口设备只有 `llvm-ar`/`llvm-ranlib`/`llvm-nm`/`llvm-strip`，没有裸 `ar` 等命令 | recipe 在 build folder 生成私有 `ar`/`ranlib`/`nm`/`strip` shell wrapper，前置 PATH 并设置对应环境变量 |
| 17 | 顶层 configure `find: gm4...(fail) not found` | 新端口设备无系统 `gm4`/`m4` | 新增 `m4/1.4.19` build requirement，并把 Conan m4 `bin/` 注入 PATH |
| 18 | 顶层 configure `find: autoconf...(fail) not found` | 新端口设备无系统 autoconf，HandBrake 要求 `autoconf >= 2.71` | 新增 `autoconf/2.72` build requirement 并注入 PATH |
| 19 | 顶层 configure 后续会强制探测 `pkg-config` | 新端口设备无 `pkg-config/pkgconf`，ohpcd 无对应包 | recipe 从官方 pkgconf 2.5.1 源码构建 host tool，生成私有 `pkg-config`/`pkgconf` wrapper 并前置 PATH |
| 20 | pkgconf 自举 configure `no acceptable ld found in $PATH` | 新端口设备有 `ld.lld` 但无裸 `ld` | 私有 toolchain wrapper 新增 `ld -> ld.lld`，pkgconf configure 显式传 `LD=<wrapper>` |
| 21 | Conan autoconf 包脚本调用裸 `perl` | 新端口设备无系统 Perl；`autoconf` wrapper 直接执行会报 `perl: inaccessible or not found` | 扩展 `_host_autotools/bin`，用 Conan Perl 包装 `autoconf`/`autoheader`/`autoreconf`/`autom4te` 等 |
| 22 | contrib 预取阶段长时间无进展 | 旧逻辑对每个镜像可等待 300s 且还尝试 urllib；慢镜像会在真正 configure 前消耗大量时间 | `_download_one()` 增加可调超时/候选数/方法，并优先 curl |
| 23 | `make` 阶段补下载 `libvpx`/`bzip2` 失败 | HandBrake 自带 Python urllib 下载器在新端口证书/直连/慢源上不可靠；r17 已证明让 make 兜底联网不可行 | contrib distfile 预取改为构建前强依赖：同名 tarball 去重、最多 4 路、纳入非 GitHub fallback；实际构建依赖下载失败则在 make 前显式停止 |
| 24 | r21 强制预取仍有 7 个 required distfile 下载失败 | recipe hash 变化会创建新的 Conan build folder；distfile cache 是 build-folder-local，而新端口 GitHub 代理/直连偶发 22/超时 | `_download_one()` 在联网前扫描同一 `CONAN_HOME` 内既有 HandBrake `download/`，仅复制 SHA256 匹配的 distfile 作为迭代兜底 |
| 25 | r22 make 仍补下载 `SVT-AV1-v4.1.0.tar.gz` | 预取/URL 改写正则只允许 `[A-Z0-9_]`，漏掉变量名 `SVT-AV1.FETCH.*` | FETCH 正则扩展为 `[A-Z0-9_-]+`；远端已验证 GitLab fallback 可下载且 SHA256 匹配 |
| 26 | r23 解包 `ffmpeg-8.0.2.tar.bz2` 失败：`toybox: Unknown command toybox` | HandBrake configure 探测到 `/usr/bin/tar`，它是 toybox tar；处理 `.tar.bz2` 时会间接调用坏的 toybox/bunzip2 路径 | 在 recipe 私有 `_host_archive_tools/bin` 生成 `tar`/`gtar` Python wrapper，覆盖 `tar xfC <archive> <dir>` 并前置 PATH，使 configure 写入 wrapper 路径 |
| 27 | r24 `contrib/libvpx` configure 报 `perl: inaccessible or not found` | libvpx configure 自身调用裸 `perl`；此前只包装 autoconf/automake 命令，PATH 中仍没有可执行的 `perl` | 在 `_host_autotools/bin` 额外生成 `perl` wrapper，指向 Conan `perl/5.42.2` 并注入 `PERL5LIB` |
| 28 | r25 `contrib/libvpx` configure 报 `Toolchain is unable to link executables` | libvpx 把环境变量 `LD` 当最终链接 driver 调用；recipe 此前导出 `LD=<build>/_host_toolchain/bin/ld -> ld.lld`，但 HandBrake 传入的 `LDFLAGS` 含 `-fstack-protector-strong` 等 compiler-driver 选项，`ld.lld` 不接受 | 仍在 PATH 提供裸 `ld` wrapper 供 configure/pkgconf 探测，但环境变量 `LD` 改为 clang driver |
| 29 | r26 `contrib/libiconv` configure 报 `expected an absolute directory name for --prefix`，prefix 前缀出现乱码 | 新端口 `/bin/sh` 运行 Autoconf 脚本时会尝试写只读 `/tmp/sh*.tmp` 并污染后续参数处理；远端探针显示同一 libiconv configure 在 `CONFIG_SHELL=/usr/bin/zsh` 下返回 0 | recipe 构建开始导出 `CONFIG_SHELL=/usr/bin/zsh`，但 `SHELL` 保持 `/bin/sh`；host 自举 make/install 用命令行 `SHELL=/bin/sh` 覆盖，contrib 需额外在 `module.defs` 注入 `CONFIG_SHELL` |
| 30 | r26 `contrib/libdav1d` Meson 报 `Atomics not supported` | OHOS clang launcher 在 compile-only 探测中注入 `-Wl,--code-sign`，Meson 同时加 `-Werror=unused-command-line-argument`，导致 `stdatomic.h`/GCC atomics 编译探测假失败 | recipe 生成私有 `clang`/`clang++` wrapper，加 `-Qunused-arguments`；`CC`/`CXX`、`--cc` 与 PATH 中裸 `clang` 均指向 wrapper |
| 31 | r27 host GNU patch 自举 `make` 报 `zsh:cd:21: no such file or directory: lib src tests` | GNU Autotools 生成的 Makefile 假设 POSIX sh 的变量拆分语义；r27 把 `SHELL` 全局设为 zsh 后，递归目录列表未按预期拆分 | 只把 `CONFIG_SHELL` 设为 zsh 供 Autoconf configure re-exec，`SHELL` 保持 `/bin/sh`；GNU patch/pkgconf 自举的 configure 用 zsh，make/install 显式用 `/bin/sh` |
| 32 | r28 仍在 host GNU patch `make` 报同一 `zsh:cd` | Autoconf configure 已把 `SHELL=/usr/bin/zsh` 写入 Makefile；GNU make 环境变量 `SHELL=/bin/sh` 不会覆盖 Makefile 内变量 | host GNU patch/pkgconf 自举执行 `make`/`make install` 时用命令行变量 `SHELL=/bin/sh` 覆盖 Makefile |
| 33 | r29 顶层 HandBrake configure 报 `ERROR: no suitable version of python found` | HandBrake 顶层 `configure` 是 POSIX sh launcher，`inpath()` 依赖 `IFS=:` 后的 `$PATH` 分词；用 zsh 启动时不会按 POSIX sh 语义拆分 PATH | 顶层 `_configure()` 固定用 `/bin/sh` 启动；`CONFIG_SHELL=/usr/bin/zsh` 仍保留给后续 Autoconf contrib configure |
| 34 | r30 `contrib/libiconv` 仍用裸 `./configure`，未继承 `CONFIG_SHELL` | HandBrake 顶层 configure 会把 contrib 命令生成进 `build/GNUmakefile`；仅在 recipe 环境中导出 `CONFIG_SHELL` 不会自动进入 `LIBICONV.CONFIGURE.env` | recipe 在顶层 configure 前改写 `contrib/libiconv/module.defs`：追加 `LIBICONV.CONFIGURE.env.CONFIG_SHELL`/`SHELL` 和 `CONFIGURE.env.args`，并给 build/install 追加 `SHELL=/bin/sh` |
| 35 | r31 `libiconv` 命令已带 `CONFIG_SHELL=/usr/bin/zsh SHELL=/bin/sh` 但 prefix 乱码仍复现 | 根因是 Autoconf 去掉 `--prefix` 尾斜杠时调用 `/bin/expr` 的 alternation 表达式；OHOS `/bin/expr` 在长路径上输出随机前缀。另一个边界是 `/bin/sh` 启动 libiconv configure 会因只读 `/tmp` 失败 | recipe 对 `LIBICONV` 同时设置 `CONFIGURE.exe=/usr/bin/zsh ./configure`，并把 `CONFIGURE.prefix` 改成去尾斜杠的 `$(patsubst %/,%,$(call fn.ABSOLUTE,$(CONTRIB.build/)))`；build/install 继续 `SHELL=/bin/sh` |
| 36 | r32 `libiconv` configure 已越过 prefix 解析，但 `config.status` 报 `./conf*/subs1.awk: permission denied` | libiconv Autoconf 2.72 生成的 `config.status` 与 GNU patch 自举同类：`mktemp -d "./confXXXXXX"` 使用 `umask 077`，OHOS/HMDFS 上目录 owner/权限行为导致后续写 `subs1.awk` 被拒 | 新增 HandBrake contrib `A02-config-status-umask-ohos.patch`，把 libiconv `configure` 与 `libcharset/configure` 中 config.status 临时目录创建从 `umask 077` 放宽为 `umask 022` |
| 37 | r33 `A02-config-status-umask-ohos.patch` 应用时报 `unexpected end of file in patch` | 外层 `0020` patch 声明 `@@ -0,0 +1,28 @@`，但生成的内层 A02 实际为 33 行，HandBrake source patch 生成文件时被截断 | 修正外层 hunk 计数为 `+1,33`；两层 patch 需 dry-run 通过后再跑 r34 |
| 38 | r34 `libopus` configure 执行 `autoreconf -fiv` 时失败于 Conan automake 包原始 `aclocal` 包装脚本：`.aclocal-real: No such file or directory` | 我们的 `autoreconf` wrapper 只用 Conan Perl 执行 `.autoreconf-real`，但未向递归 Autotools 调用导出 `ACLOCAL/AUTOMAKE/AUTOCONF/AUTOM4TE` 和 wrapper-first `PATH`；Autoconf Perl 脚本因此按环境/包脚本解析到 Conan automake 公开包装脚本 | 私有 `_host_autotools/bin` wrapper 统一导出 wrapper-first `PATH`、`PERL`、`M4`、`ACLOCAL`、`AUTOMAKE`、`AUTOCONF`、`AUTOHEADER`、`AUTOM4TE`、`AUTORECONF` 等，`_prepare_autotools_env()` 同步设置这些变量；等待 r35 验证 `libopus` 是否越过 `autoreconf` |
| 39 | r35 `libopus` 已越过 `autoreconf` wrapper 问题，但随后 `./configure --prefix=<长路径/>` 报 prefix 前缀乱码 | `libopus` regenerated configure 与 libiconv 同属 Autoconf 长 prefix + OHOS `/bin/expr` 污染问题；且现场 generated `configure` 同样包含 `umask 077` 的 `config.status` 临时目录逻辑 | 将 `_patch_contrib_autoconf_rules()` 扩展到 `LIBOPUS`：configure 用 zsh 直接执行、prefix 去尾斜杠、build/install 显式 `SHELL=/bin/sh`；在 `LIBOPUS.CONFIGURE.bootstrap` 的 `autoreconf -fiv` 后追加 Python one-liner 把 generated `configure` 中 `umask 077` 改为 `umask 022` |
| 40 | r36 `LIBOPUS` zsh/无尾斜杠/umask 修复生效后，configure 失败于 `./config.guess: unable to guess system type` | `autoreconf` 从 automake 安装了新的 `config.guess`，覆盖了 HandBrake A01 patch；该脚本在 runner tmp 下创建 `dummy.c` 被拒。远端探针确认 `./config.sub aarch64-unknown-linux-ohos` 可接受目标三元组 | 对 `LIBOPUS.CONFIGURE.extra` 显式追加 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`，绕开 regenerated `config.guess` 探针；等待 r37 验证 |
| 41 | r37 `libopus` 已越过 `config.guess` 并写入 `.stamp.libopus.configure`，随后 `libogg` configure 报同类 `--prefix` 乱码 | `libogg` 走 HandBrake 默认 Autoconf contrib 规则，默认 `CONFIGURE.prefix=$(call fn.ABSOLUTE,$(CONTRIB.build/))` 带尾斜杠；它也在 `autoreconf` 后使用 generated configure，暴露与 libiconv/libopus 相同的 zsh/prefix/umask/build-host 问题 | 将 `_patch_contrib_autoconf_rules()` 扩展为 OHOS-only 的 Autoconf contrib 列表：FDKAAC/FREETYPE/FRIBIDI/JANSSON/LAME/LIBASS/LIBGNURX/LIBICONV/LIBOGG/LIBOPUS/LIBSPEEX/LIBTHEORA/LIBVORBIS/XZ/ZIMG 统一注入 zsh configure、无尾斜杠 prefix、`SHELL=/bin/sh` build/install、generated configure `umask 077 -> 022` 和显式 `--build/--host`；等待 r38 验证 |
| 42 | r38 统一 Autoconf 注入生效，`libogg`/`zimg`/`fribidi` 等越过 configure；新失败为 `x264` configure `Error 126`，`/bin/sh: ./configure: No such file or directory` | x264 不是 Autoconf，`configure` 存在但 shebang 为 `#!/bin/bash`，新端口无 `/bin/bash`；直接用 `/bin/sh ./configure` 后又因 x264 `config.sub` 不接受 `aarch64-unknown-linux-ohos`。远端探针确认 `/bin/sh ./configure --host=aarch64-unknown-linux-gnu` 可生成 `config.mak`，走 `SYS=LINUX`/`AARCH64` 路径 | 新增 `_patch_x264_rules()` 并扩展 `0006`：OHOS 下 `X264.CONFIGURE.exe=/bin/sh ./configure`、`X264.CONFIGURE.host=aarch64-unknown-linux-gnu`、prefix 去尾斜杠，build/install 显式 `SHELL=/bin/sh`；等待 r39 验证 |
| 43 | r39 x264 修复生效，x264 configure/build 与 x265 8-bit build 均通过；随后 `freetype` configure 停在 `./config.status: permission denied: ./conf*/subs1.awk` | FreeType 入口先执行源码根 `configure`，再 `cd builds/unix && ./configure`；此前 bootstrap 只改当前目录 `configure` 的 Autoconf `umask 077`，未覆盖嵌套 `builds/unix/configure`，因此内层 `config.status` 仍创建不可写临时目录 | 将 `_patch_contrib_autoconf_rules()` 的 bootstrap Python 片段扩展为扫描当前 contrib 源树下所有 `configure`，统一把 `umask 077` 改为 `umask 022`；等待 r40 验证 |
| 44 | r40 提前停在 `contrib/freetype/module.defs:34: *** missing separator` | r40 的递归 Python bootstrap 片段含真实换行，追加进 `module.defs` 后破坏 GNU make 变量语法；这是 recipe 生成问题，尚未验证 FreeType 内层 umask 修复 | 将 Python 片段改为 `python -c 'exec(\"...\")'` 单行命令文本，内部换行只以 `\n` 转义保留；等待 r41 验证 |
| 45 | r41 越过 `missing separator`，但 `libiconv` bootstrap 的 Python 片段报 `IndentationError` | GNU make/recipe 命令展开后把 `python -c exec(...)` 内部缩进压缩成单空格，块语句失去有效缩进；这仍是 recipe 生成问题，未形成平台新边界 | 改为无换行、无缩进、无块语句的 Python 单行列表推导：遍历当前源树所有 `configure` 并替换 `umask 077`；等待 r42 验证 |
| 46 | r42 验证无块 Python bootstrap 生效，`freetype` 已写入 `.stamp.freetype.configure`；随后 `lame` configure 报 `/usr/bin/zsh ./config.sub aarch64-unknown-linux-ohos failed` | LAME 3.100 自带旧 `config.sub` 拒绝 `aarch64-unknown-linux-ohos`，远端探针确认接受 `aarch64-unknown-linux-gnu` 和 `aarch64-unknown-linux-musl` | 对通用 Autoconf 注入中的 `LAME` 单独使用 `--build/--host=aarch64-unknown-linux-gnu`，保留其它 Autoconf contrib 的 OHOS tuple；等待 r43 验证 |
| 47 | r43 验证 LAME GNU tuple 生效，`contrib/lame/.stamp.lame.configure` 已写入；随后 `libspeex` configure 报 `/usr/bin/zsh ./config.sub aarch64-unknown-linux-ohos failed` | Speex 1.2.1 自带旧 `config.sub` 同样拒绝 OHOS tuple。远端按已解压源码逐项探测确认：当前通用 Autoconf 模块中仅 `LAME` 和 `LIBSPEEX` 拒绝 OHOS tuple，且二者均接受 `aarch64-unknown-linux-gnu`；`libvorbis/freetype/fribidi/jansson/libass/libiconv/libogg/libopus/xz/zimg` 均接受 OHOS tuple | 将通用 Autoconf 注入中的 `LIBSPEEX` 与 `LAME` 一并使用 `--build/--host=aarch64-unknown-linux-gnu`；等待 r44 验证 |
| 48 | r44 验证 `LIBSPEEX` GNU tuple 生效，并越过全部关键 contrib、`libhb` 编译、`HandBrakeCLI` 链接/strip、`package()` 和 Conan package revision 创建；失败发生在 `test_package` 执行 `/usr/bin/zsh test.sh`，报 `command not found: ^M` | Windows checkout/overlay 让 `test_package/test.sh` 在真机端带 CRLF，zsh 将 CR 当作命令文本的一部分；主包构建与打包已被本轮确认通过 | `test_package/conanfile.py` 在执行前把 `test.sh` 复制到 build folder 并归一化为 LF，再运行这份副本；r45 已验证 `HandBrakeCLI --version`/`--help` 2/2 通过 |

## 依赖版本（contrib 全部在树内）

ffmpeg 8.0.2、x264 snapshot-20250729、x265 snapshot-20260216、libvpx 1.16.0、libass 0.17.4、
libdav1d 1.5.3、SVT-AV1 4.1.0、zlib 1.3.2、bzip2 1.0.8、libiconv 1.18、freetype 2.14.1、
harfbuzz 12.2.0、fribidi 1.0.16、lame 3.100、libopus 1.6.1、libvorbis 1.3.7、libtheora 1.2.0、
libspeex 1.2.1、jansson 2.15.0、libjpeg-turbo 3.1.3、libbluray 1.4.0、libdvdnav 7.0.0、
libdvdread 7.0.1、libgnurx 2.5.1、xz 5.8.2、zimg snapshot-20250624

## 验证结果

已在新端口 `33332` 使用隔离 job `/storage/Users/currentUser/ohos-users/codex-a/handbrake-1.11.2-20260812-r1` 推进真机 `conan create`。
r11 已通过依赖解析、Conan Perl 包装 automake/aclocal、官方 GNU patch 2.8 源码自举、`config.status`、`make install`，并确认 `_host_gnu_patch_src/install/bin/patch --version` 为 `GNU patch 2.8`。r11 后续在 contrib 预下载阶段出现 1 个网络 timeout（`libiconv-1.18.tar.gz`），随后暴露旧 bash 路径问题；已修。
r12 已重走到顶层 configure，旧 shell 路径问题修复生效，失败于裸 `ar` 缺失；已通过私有 LLVM binutils wrapper 修复。
r13 已确认 wrapper 生效：顶层 configure `find: ar...(pass) <build>/_host_toolchain/bin/ar`；随后失败于缺少 `gm4/m4`。已补 `m4/1.4.19` build requirement，待 r14 真机验证。
r14 已确认 `gm4/m4`、`ar`、`ranlib`、`strip` 均通过，随后失败于 `autoconf` 缺失。远端预检确认 ohpcd 提供 `autoconf/2.72` OHOS armv8 binary；同时预检官方 pkgconf 2.5.1 tarball SHA256 匹配，已补 pkg-config 自举以避免下一轮停在 `PKGCONFIG.exe`。
r15 已确认 `autoconf/2.72` 可下载，GNU patch 自举仍稳定；pkgconf 2.5.1 源码自举进入 configure 后失败于裸 `ld` 缺失。已新增 `ld -> ld.lld` wrapper，并发现 Conan autoconf 包本身调用裸 `perl`，已改为 recipe 私有 Perl wrapper。
r16 已确认 `ld -> ld.lld` wrapper 生效，pkgconf 2.5.1 configure/build/install 完成并生成 `pkg-config` wrapper；随后旧 contrib 预取逻辑在可选下载阶段长时间无进展，人工终止，runner 记录 `rc=143`。已将 contrib 预取改为有界加速项：不直连 GitHub、只试少量镜像 curl、单候选短超时，预取失败仍交给构建期改写后的 `module.defs` URL。
r17 已确认有界预取不再静默挂住，顶层 configure 全部通过：`autoconf`、`automake`、`libtool`、`pkg-config`、`meson`、`ninja`、`cmake` 等探测均通过，`nasm`/`cargo` 仍为非致命缺失；`make --jobserver-style=pipe -j2` 已启动。新失败点为 make 阶段补下载 `libvpx-1.16.0.tar.gz` 和 `bzip2-1.0.8.tar.gz`，HandBrake urllib 下载器因证书/超时失败。已改为 recipe 必须在 make 前补齐实际构建 contrib distfile；若仍下载失败，失败会停在 recipe 预取阶段并给出具体文件/URL。
r18 在强制预取重构后提前失败于 recipe bug：部分 `contrib/*/module.defs` 无 `FETCH.url`，新去重逻辑访问 `urls[0]` 导致 `IndexError`。已补 `if not urls: continue`，该轮未形成新的平台边界。
r19 提前失败于 recipe 下载排序回归：为 contrib 预取新增的“非 GitHub fallback 优先”影响了官方 HandBrake source asset 下载，导致先走 GitHub 直连/urllib 并触发证书失败。已把该排序限制为 contrib 预取专用，源码包/GNU patch/pkgconf 保持原候选顺序。
r20 仍在官方 source asset 下载处失败，说明当前设备到 GitHub/mirror 偶发不可用；已把 required source 下载改为 curl-only，并在同一 `CONAN_HOME` 内复用已解包过的 HandBrake 官方源码缓存作为迭代兜底。若复用的是已补丁源码，会跳过二次 `apply_conandata_patches()`。
r21 已确认 source cache 兜底可进入 build 阶段，GNU patch/pkgconf 自举仍稳定；强制 contrib 预取完成 `19 downloaded, 0 cached, 11 failed`，其中 required 失败为 `fribidi`、`harfbuzz`、`jansson`、`libass`、`libjpeg-turbo`、`x265`、`zimg`。同一 `CONAN_HOME` 内已有这些文件的多轮历史 cache 且大小完整，已补 SHA256 校验后的 distfile cache 复用，等待 r22 验证能否重新进入顶层 configure/make。
r22 已确认 30 个 contrib distfile 均通过 SHA256 cache 复用并进入顶层 configure/make；新失败点为 make 补下载 `SVT-AV1-v4.1.0.tar.gz`，原因是 `SVT-AV1.FETCH.url` 中模块名前缀带连字符，预取正则未捕获。远端短探测确认 GitLab fallback `https://gitlab.com/AOMediaCodec/SVT-AV1/-/archive/v4.1.0/SVT-AV1-v4.1.0.tar.gz` 可下载，大小 `10904647`，SHA256 `6c4c0c44ff0ba3d136d6f57f3a707f9de8e9c866f50f809c1d22a43f0d8c9583`。已修正 FETCH 正则，等待 r23 验证。
r23 已确认 `prefetch 31 contrib distfiles`，`SVT-AV1-v4.1.0.tar.gz` 通过 GitLab fallback 下载并 SHA256 校验；随后顶层 configure 通过，make 进入 distfile 校验/解包。新失败点为 `TAR.exe=/usr/bin/tar` 解包 `.tar.bz2` 时 `toybox: Unknown command toybox`，`ffmpeg` extract 失败。远端验证 `/usr/bin/tar -> ../../bin/toybox`，`.tar.gz` 可解，`.tar.bz2` 失败；已新增 Python tar wrapper 并在 `_configure()` 前前置 PATH。
r24 `codex-a-handbrake-conan-create-1.11.2-r24-20260813-022643...` 已确认 Python `tar`/`gtar` wrapper 生效，生成的 `build/GNUmakefile` 使用 `_host_archive_tools/bin/gtar`，make 已越过 `.tar.bz2` 解包并继续到 contrib configure/patch 阶段；`SVT-AV1` CMake configure 已成功。新失败点为 `contrib/libvpx` configure 调用裸 `perl`，设备报 `perl: inaccessible or not found` / `Perl is required to build`；已新增 build-folder 私有 `perl` wrapper，等待 r25 验证。
r25 `codex-a-handbrake-conan-create-1.11.2-r25-20260813-024214...` 已确认 `perl` wrapper 生效，r24 的 `Perl is required to build` 消失；31 个 contrib distfile SHA256 均通过，tar/gtar wrapper 继续生效，SVT-AV1 CMake configure 仍可通过。新失败点为 `contrib/libvpx` configure 的 `Toolchain is unable to link executables`；`config.log` 显示 `check_ld` 直接调用 `_host_toolchain/bin/ld`，并把 `-fstack-protector-strong` 传给 `ld.lld`，导致 `ld.lld: error: unknown argument '-fstack-protector-strong'`。已改为仅在 PATH 提供裸 `ld` wrapper，环境变量 `LD` 导出为 clang driver，等待 r26 验证。
r26 `codex-a-handbrake-conan-create-1.11.2-r26-20260813-025453...` 已确认 `LD=clang` 修复生效：`contrib/libvpx` configure 已越过链接探测并写入 `.stamp.libvpx.configure`。新失败点并行出现在 `libiconv` 与 `libdav1d`：libiconv under `/bin/sh` 报 prefix 乱码，远端探针确认 `CONFIG_SHELL=/usr/bin/zsh` 可通过同一 configure；dav1d Meson 的 atomics 探测失败实际是 clang compile-only 被 `-Wl,--code-sign` unused diagnostic 卡住，远端探针确认 `-Qunused-arguments` 可通过。当前 r27 修复为优先 zsh + clang/clang++ wrapper，等待真机验证。
r27 `codex-a-handbrake-conan-create-1.11.2-r27-20260813-032044...` 已确认 zsh 与 clang wrapper 在 recipe 开始阶段生效，且 `LD` 指向 clang wrapper；但失败提前发生在 host GNU patch 自举 make 阶段：configure under zsh 已完成，`make all-recursive` 因 `SHELL=/usr/bin/zsh` 处理 `lib src tests` 递归目录失败。当前 r28 修复为拆分 shell：`CONFIG_SHELL=/usr/bin/zsh`，`SHELL=/bin/sh`，host GNU patch/pkgconf 的 make/install 显式用 POSIX sh。
r28 `codex-a-handbrake-conan-create-1.11.2-r28-20260813-032902...` 已确认 `CONFIG_SHELL=/usr/bin/zsh SHELL=/bin/sh` 进入 recipe，GNU patch configure 仍成功，但 Makefile 内的 `SHELL=/usr/bin/zsh` 未被环境变量覆盖，`make all-recursive` 仍报 `zsh:cd:21`。当前 r29 修复为在 host GNU patch/pkgconf 的 `make` 命令行显式传 `SHELL=/bin/sh`。
r29 `codex-a-handbrake-conan-create-1.11.2-r29-20260813-033432...` 已越过 GNU patch 与 pkgconf 源码自举：`make SHELL=/bin/sh` 生效，`patch` 与 `pkg-config` wrapper 生成；31 个 contrib distfile 全部 SHA cache 复用，随后顶层 HandBrake configure 因用 zsh 启动 shell launcher 报 `ERROR: no suitable version of python found`。当前 r30 修复为顶层 configure 固定 `/bin/sh`，而 contrib Autoconf 继续通过 `CONFIG_SHELL=/usr/bin/zsh`。
r30 `codex-a-handbrake-conan-create-1.11.2-r30-20260813-034234...` 已确认顶层 configure 用 `/bin/sh` 后通过；`libvpx`、`zlib`、`SVT-AV1` 与 `libdav1d` 均写入 configure stamp，其中 dav1d Meson 已显示 `stdatomic.h` 可用，说明 clang wrapper 的 `-Qunused-arguments` 生效。当前唯一新失败为 `libiconv` contrib 生成规则仍直接执行 `./configure`，未带 `CONFIG_SHELL=/usr/bin/zsh`，再次出现 prefix 乱码。当前 r31 修复为在生成 `build/GNUmakefile` 前向 `LIBICONV.CONFIGURE.env.args` 注入 `CONFIG_SHELL`/`SHELL`，并给 libiconv build/install 追加 `SHELL=/bin/sh`。
r31 `codex-a-handbrake-conan-create-1.11.2-r31-20260813-035729...` 已确认 `LIBICONV.CONFIGURE.env` 注入进入生成规则，命令显示 `CONFIG_SHELL=/usr/bin/zsh SHELL=/bin/sh ./configure ...`；但失败仍为 `expected an absolute directory name for --prefix`。远端探针确认：短 prefix 可过，长 prefix 带尾斜杠会在 Autoconf 的 `expr "X$ac_val" : 'X\(.*[^/]\)' \| ...` 去尾斜杠步骤被 OHOS `/bin/expr` 污染；长 prefix 去尾斜杠后用 zsh 执行 `--help` 可通过，而 `/bin/sh` 仍因 `/tmp` 只读失败。当前 r32 修复为 `LIBICONV.CONFIGURE.exe=/usr/bin/zsh ./configure`，并把 `LIBICONV.CONFIGURE.prefix` 改为无尾斜杠。
r32 `codex-a-handbrake-conan-create-1.11.2-r32-20260813-041120...` 已确认 libiconv configure 命令变为 `CONFIG_SHELL=/usr/bin/zsh SHELL=/bin/sh /usr/bin/zsh ./configure --prefix=<无尾斜杠路径>`，并越过 prefix 乱码与大部分探测，最后停在 `config.status: error: could not setup config files machinery`，具体为 `./conf*/subs1.awk permission denied`。当前 r33 修复为新增 libiconv contrib `A02` patch，复用 GNU patch 自举已验证的 `umask 077 -> 022` 方案。
r33 `codex-a-handbrake-conan-create-1.11.2-r33-20260813-042410...` 已确认 `0020` 在 source 阶段应用并生成 `contrib/libiconv/A02-config-status-umask-ohos.patch`，但内层 A02 应用时报 `unexpected end of file in patch`。根因是外层 hunk 行数声明过小，生成文件被截断到 28 行；当前 r34 修正 hunk 计数为 33 行。
r34 `codex-a-handbrake-conan-create-1.11.2-r34-20260813-043505...` 已确认完整 A02 生效：`libiconv` inner patch 成功应用，`CONFIG_SHELL=/usr/bin/zsh SHELL=/bin/sh /usr/bin/zsh ./configure --prefix=<无尾斜杠路径>` 跑完，并写入 `contrib/libiconv/.stamp.libiconv.configure`。新失败点为 `libopus` 执行 `autoreconf -fiv` 时递归调用到 Conan automake 包原始 `aclocal` 包装脚本，随后找不到 `.aclocal-real` 并以 Error 126 停止。当前 r35 修复为让私有 Autotools wrapper 自身和 recipe 环境都导出 `ACLOCAL/AUTOMAKE/AUTOCONF/AUTOM4TE/AUTORECONF` 指向 `_host_autotools/bin`，并把 wrapper 目录放回递归 PATH 首位。
r35 `codex-a-handbrake-conan-create-1.11.2-r35-20260813-045402...` 已确认 `libopus` 的 `autoreconf -fiv` 改走私有 wrapper：日志显示 `.autoreconf-real: running: <build>/_host_autotools/bin/aclocal/autoconf/autoheader/automake`，r34 的 `.aclocal-real` Error 126 消失。新失败点为 `libopus` 后续 configure 报 `expected an absolute directory name for --prefix`，乱码形态与 r31 libiconv 相同；现场 `configure` 还包含 `umask 077` 的 `config.status` 片段。当前 r36 修复为把 `LIBOPUS` 纳入 `_patch_contrib_autoconf_rules()`，并在 bootstrap 后补丁 generated `configure` 的 `umask`。
r36 `codex-a-handbrake-conan-create-1.11.2-r36-20260813-050857...` 已确认 `LIBOPUS` 规则扩展进入生成命令：`autoreconf -fiv; python3 -c ... replace(umask 077, umask 022); CONFIG_SHELL=/usr/bin/zsh SHELL=/bin/sh /usr/bin/zsh ./configure --prefix=<无尾斜杠路径>`。prefix 乱码消失，但 `autoreconf` 新装的 `config.guess` 在 runner tmp 写 `dummy.c` 被拒，最终 `unable to guess system type`。远端探针确认 `config.sub aarch64-unknown-linux-ohos` 可接受目标；当前 r37 修复为给 `LIBOPUS.CONFIGURE.extra` 追加显式 `--build/--host`。
r37 `codex-a-handbrake-conan-create-1.11.2-r37-20260813-052202...` 已确认 `LIBOPUS.CONFIGURE.extra += --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos` 生效，libopus configure 生成 `config.status` 并写入 `contrib/libopus/.stamp.libopus.configure`。新失败点为 `libogg` 的默认 Autoconf configure 规则同样触发长 prefix 乱码。当前 r38 修复为把同类 Autoconf contrib 统一纳入 `_patch_contrib_autoconf_rules()`，避免后续 vorbis/theora/speex/lame/xz/freetype/libass/jansson/fribidi/fdk-aac/zimg 逐个复现同类问题。
r38 `codex-a-handbrake-conan-create-1.11.2-r38-20260813-054011...` 已确认统一 Autoconf 注入生效：日志显示 `patched Autoconf rules for 15 contrib module.defs`，并写入 `contrib/libogg/.stamp.libogg.configure`、`contrib/zimg/.stamp.zimg.configure`、`contrib/fribidi/.stamp.fribidi.configure`，r37 的 libogg prefix 乱码消失。新失败点为 x264：`configure` 文件存在但 shebang 为 `/bin/bash`，设备无 bash，默认 `./configure` 报 126；探针确认 `/bin/sh ./configure --host=aarch64-unknown-linux-gnu` 可通过。当前 r39 修复为专门 patch x264 configure 规则，不把 x264 混入 Autoconf 通用规则。
r39 `codex-a-handbrake-conan-create-1.11.2-r39-20260813-055755...` 已确认 x264 专用规则生效：实际命令为 `/bin/sh ./configure --host=aarch64-unknown-linux-gnu --prefix=<无尾斜杠路径> ... --enable-pic`，并写入 `contrib/x264/.stamp.x264.configure` 与 `.stamp.x264.build`；`x265` 8-bit 也写入 `.stamp.x265_8.build`，多项 contrib 已进入 install。新失败点为 `freetype` 内层 `builds/unix/configure` 的 Autoconf `config.status` 临时目录仍由 `umask 077` 创建，导致 `./conf*/subs1.awk` permission denied。当前 r40 修复为让通用 Autoconf bootstrap 扫描当前 contrib 源树所有 `configure` 并统一放宽 umask。
r40 `codex-a-handbrake-conan-create-1.11.2-r40-20260813-062042...` 提前失败于 Makefile 解析：`contrib/freetype/module.defs:34: *** missing separator`。根因是上轮递归 Python 片段把真实换行写进了 `FREETYPE.CONFIGURE.bootstrap += ...`。当前 r41 修复为用 `exec(<repr>)` 生成无真实换行的 `python -c` 单行命令，保留内部 `\n` 语义。
r41 `codex-a-handbrake-conan-create-1.11.2-r41-20260813-062952...` 已越过 r40 的 Makefile `missing separator`，但 `libiconv` bootstrap 立即因 Python `IndentationError` 失败：命令展开后的 `exec(...)` 字符串缩进被 make 压缩。当前 r42 修复为不再生成任何块语句，改用纯单行 Python 表达式完成所有 `configure` 的 `umask` 替换。
r42 `codex-a-handbrake-conan-create-1.11.2-r42-20260813-063920...` 已确认单行 Python bootstrap 生效：日志反复出现 `patched configure umask entries`，`libiconv/libopus/libogg/zimg` 等越过 configure，且 r39 的 FreeType 内层 `config.status` 问题消失并写入 `contrib/freetype/.stamp.freetype.configure`。本轮推进到 install/build 阶段后新失败为 `lame` 旧 `config.sub` 拒绝 `aarch64-unknown-linux-ohos`；远端探针确认 `aarch64-unknown-linux-gnu` 可接受。r43 修复为仅对 `LAME` 追加 Linux aarch64 build/host tuple。
r43 `codex-a-handbrake-conan-create-1.11.2-r43-20260813-070250...` 已确认 LAME 使用 `--build/--host=aarch64-unknown-linux-gnu` 并写入 `contrib/lame/.stamp.lame.configure`。新边界转移到 `libspeex`：Speex 1.2.1 的旧 `config.sub` 拒绝 `aarch64-unknown-linux-ohos`。远端对已解压源码逐项探测确认，当前通用 Autoconf 列表中只有 `LAME` 与 `LIBSPEEX` 拒绝 OHOS tuple，二者都接受 `aarch64-unknown-linux-gnu`。r44 修复为把 `LIBSPEEX` 加入同一 GNU aarch64 tuple 覆盖。
r44 `codex-a-handbrake-conan-create-1.11.2-r44-20260813-072432...` 已确认 `LIBSPEEX` 覆盖生效，`contrib/libspeex/.stamp.libspeex.configure/build/install` 写入；ffmpeg、x265 8/10/12-bit、harfbuzz、libass、libtheora 等关键 contrib 均完成 build/install，随后 `libhb/libhandbrake.a` 与 `HandBrakeCLI` 链接/strip 成功，`package()` 打包 `bin/HandBrakeCLI` 并生成 package revision `04d0c806f28e6dd5046cb0282d98db6e`。新边界在 test_package：`/usr/bin/zsh test.sh` 因 CRLF 报 `command not found: ^M`。当前 r45 修复为 test recipe 执行前复制 LF-only 脚本。
r45 `codex-a-handbrake-conan-create-1.11.2-r45-20260813-080352-20260813-080356-9649` 已完成真机 `conan create`，runner exit code 0。`test_package` 运行 build folder 内 LF-only `test-lf.sh`，真实执行 `HandBrakeCLI --version` 与 `HandBrakeCLI --help`，2/2 通过。full package reference: `handbrake/1.11.2#33e6f859fc99fbfd7ea87dc7a166e9be:6b129b068851896169fae42d399fa922d239ce8a#2e4735def1793535bc91373e7c47d793`。

## 推进路线

1. 已在新端口 `33332` 的隔离 job/runroot 完成真机 `conan create`，本轮不需要继续启动 r46。
2. 当前收尾重点是保持 `manifest.yaml`、`reports/test-report.md` 与 PR 交付口径一致：上游自动化用例 0，消费侧验证 2/2 通过。
3. 若后续需要真实媒体转码 smoke，应另设输入文件、运行时长与超时口径，不混入本轮 `test_package` 统计。
4. 如 CI/维护者反馈出现新日志边界，再基于最近失败点继续修复。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| build/HandBrakeCLI（conan 包内 bin/HandBrakeCLI） | r45 已确认产出并打包 | `package()` 已复制并移除 `.codesign` section，Conan package revision `2e4735def1793535bc91373e7c47d793`；full ref `handbrake/1.11.2#33e6f859fc99fbfd7ea87dc7a166e9be:6b129b068851896169fae42d399fa922d239ce8a#2e4735def1793535bc91373e7c47d793` |

## 注意事项

- 历史探索中本地 conan create 复用构建缓存会快很多；正式验证不能依赖该缓存，需干净 OHOS 构建。
- **Rule 21 / P0**：本 PR **不修改** `ci/`（含 `build_timeouts.txt`、`build_and_test.sh`）；超时与 CI 预下载修复改由维护者框架 PR 处理
- CI #14768/#15352：`$HOME/usr/local/bin/automake` 坏桩 + Conan automake（perl 脚本）shebang 不可直接 exec → 隔离坏桩，在 build 目录生成 `perl` 包装的 automake/aclocal 并前置 PATH（不改 `ci/`）
- 配方侧：`_prefetch_contribs` 并行预取 + 构建期改写 contrib `module.defs` 的 GitHub URL 走镜像；`conandata.yml` 保持官方 URL；`TMPDIR=/data/local/tmp` + `make --jobserver-style=pipe` 规避 HMDFS mkfifo 导致的串行退化
- CI #12716/#12753/#12777：worker 无 GNU patch（仅 toybox）。从 PATH/clang 同目录/`$HOME/usr/local/bin` 解析；否则先尝试带 SHA 校验的 cmd-pkgs 预编译包；若不可达，再从官方 GNU patch 2.8 源码构建 native host tool。GNU patch 自举要修 Autoconf `umask 077` 临时目录。绝不回退 toybox。ELF 自签名仅 OHOS。
- 新端口设备缺少裸 `ar`/`ranlib`/`nm`/`strip`/`ld`、`m4`、`autoconf`、`pkg-config`；这些 host tool 必须由 recipe 的 build requirements/wrapper/源码自举封装，不能依赖全局环境。
- CI #12993：libiconv/xz 的 A01 打 `build-aux/config.guess`（非源码根）；0014 元补丁 `@@` 行数必须与正文一致，否则 `patch stream is incomplete`
- HandBrakeCLI 静态链接了全部 contrib，运行无需额外依赖
- 该版本只产出 CLI；GTK GUI 已禁用（无图形界面适配）
- 后续如需 x265 8/10/12bit 全深度需确认 x265 变体构建，当前默认 8bit

## AI review 闭环（R41）

针对 2026-08-04 16:42 审查：

| # | 意见 | 处置 | 防回退 |
|---|------|------|--------|
| 1 | `test.sh`：`if !` 后 `$?` 恒为 0 | **已改**：`set +e` → 跑 CLI → `ret=$?` → `set -e` 再判断 | 仍失败即 `exit 1`，不影响 R34 |
| 2 | cmd-pkgs GNU patch 预编译包未校验完整性 | **已改**：下载后按固定 sha256 校验，失败则换下一个镜像包 | 仍拒绝 toybox；HMDFS chmod 拷贝到自有 `bin/` |
| 3 | 协作者改 `ci/config/build_timeouts.txt`（§21 / CONTRIBUTING） | **已移除**：PR 不再改 `ci/`，与 main 严格一致 | 超时由维护者框架 PR 配置 |
| — | 人工审查规则 1/4：旧 PR 曾误写测试统计 | **本轮口径**：上游自动化测试为 0；消费侧验证待真机执行后再填实际结果 | 不沿用旧 PR 通过率 |
| 4 | nasm 全局非致命（前轮） | **已收紧**：仅 `aarch64-*`/`arm64-*` | OHOS CI 无 nasm 仍可 configure |

其它已防历史失败：libiconv&xz `build-aux/config.guess`、0014 元补丁行数完整、OHOS-only ELF 签名、`_CACHE_ROOT` 空守卫、main.defs 不重复加 xz、并行预取/构建期镜像重写。
---


**本轮准备时间**: 2026-08-12
**当前状态**: built；r45 真机 `conan create` exit 0，`test_package` 已用 LF-only 脚本副本真实验证 `HandBrakeCLI --version` / `--help` 2/2 通过；full ref `handbrake/1.11.2#33e6f859fc99fbfd7ea87dc7a166e9be:6b129b068851896169fae42d399fa922d239ce8a#2e4735def1793535bc91373e7c47d793`
