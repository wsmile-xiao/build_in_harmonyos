# pianobar 2024.12.21 适配笔记

## 编译环境

- 构建系统: makefile（raw Makefile，无 configure/CMake）
- 上游版本: 2024.12.21（官方发布包，55 个文件）
- 上游仓库: <https://6xq.net/projects/pianobar/>（镜像 <https://github.com/PromyLOPh/pianobar>）
- 源码包: <https://6xq.net/pianobar/pianobar-2024.12.21.tar.bz2>
- sha256: `16f4dd2d64da38690946a9670e59bc72a789cf6a323f792e159bb3a39cf4a7f5`
- 编译器: clang/clang++（Conan `tools.build:compiler_executables`）
- 状态: built（本轮仅完成未提交工作树，真机预检由 HMBS 后台执行）

## 依赖版本

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| libao | 内置垫片（ao 1.2.2 API 兼容） | 上游 `pkg-config ao` 硬依赖；仓库内无其 Conan 配方、ohpcd 远端缺失，配方在构建目录自带 raw+null 垫片并静态链接（见 conanfile `_compile_ao_shim`），不声明外部 requires |
| curl | 8.15.0 | HTTPS 接入 Pandora（含 OpenSSL TLS） |
| json-c | 0.18 | JSON 解析（`pkg-config json-c`） |
| libgcrypt | 1.12.2 | Blowfish 加解密（partner 登录密钥） |
| ffmpeg | 7.1.5 | mov 解复用/aac 解码/http 协议/volume 滤镜；上游 INSTALL 要求 >= 5.1，`src/config.h` 已按版本宏兼容 7.x |
| pkgconf | 3.0.5 | tool_requires，提供 `pkgconf` 二进制 |

## 编译步骤

上游 INSTALL 流程（`gmake clean && gmake && gmake install`），配方内等价实现：

1. `PkgConfigDeps` 生成全部依赖 `.pc`，`PKG_CONFIG_PATH` 指向 generators 目录；
2. `make -j1 PKG_CONFIG=pkgconf CC=<conan clang>`（源码树内构建）；
3. 手工 `llvm-ar rcs libpiano.a src/libpiano/*.o`（DYNLINK=0 默认不产出该归档）；
4. `make install PREFIX=/ DESTDIR=<package_folder>` 安装 `bin/pianobar` 与 man 页；
5. 拷贝 `libpiano.a` 到 `lib/`、`piano.h` 到 `include/`、`COPYING` 到 `licenses/`；
6. OHOS 下对最终 `bin/pianobar` 做 `binary-sign-tool` 自签名（工具缺失时仅警告，不中断）。

## 上游测试审计

- 解包核查：顶层 Makefile 仅有 `all/clean/install/install-libpiano/uninstall/test`
  目标（`test` 为无规则的 `.PHONY`），无 `check` 目标；全源码树无 `tests/` 目录、
  无 `*test*` 文件、无 ctest/gtest/pytest 注册。
- 上游 CI（`.github/workflows/build.yml`）仅执行 `make` 编译，不运行任何测试。
- 结论：上游确无测试（`upstream_tests_exist: false`），以 18 个
  test_package 消费者断言补位（14 个 libpiano C API + 4 个 CLI 行为）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
| --- | --- | --- | --- |
| 1 | 真机 `conan create` 在解析依赖图时报 `Package 'libao/1.2.2' not resolved` | 配方曾声明 `requires("libao/1.2.2")`，但该包无 Conan 配方、ohpcd 远端也不存在 | 删掉该外部 requires，改为配方内自带 ao 兼容垫片：构建时在 `build_folder/ao-shim` 生成 `ao/ao.h`、`ao/os_types.h`、`ao_shim.c` 与 `ao.pc`（Version 1.2.2），用 Conan 传入的 CC/AR 编成静态 `libao.a`，`PKG_CONFIG_PATH` 优先指向垫片，实现 raw 文件驱动真实写文件、live 走 null 丢弃（OHOS 无 OSS/ALSA/Pulse，保持单库原子性） |
| 2 | 默认构建不产出 `libpiano.a`，C API 无法交付/测试 | 上游仅在 `DYNLINK=1` 分支归档该静态库（含创建 symlink，不适合 HMDFS） | 构建后手工 `ar rcs`，不创建任何 symlink |
| 3 | `pianobar` 无 `--help/--version`，交互式启动需 Pandora 账号 | main 函数直接进入登录流程，且 `BarReadline` 在 EOF stdin 下 `select` 空集无限阻塞（见 #12），`< /dev/null` 不可作为冒烟测试 | CLI 测试改为静态交付检查：不断言执行退出码，只断言可执行位、二进制内 welcome/version 字符串与 man 页（详见 #12） |
| 5 | graph Version conflict openssl 3.5.6 vs 3.5.6.1 from ffmpeg/7.1.5 | curl needs openssl/3.5.6.1 (OHOS FD_SET fix), ffmpeg pins 3.5.6 | requirements() add self.requires("openssl/3.5.6.1", override=True) unify to higher patch version |
| 6 | build fails src/libpiano/request.c:27 fatal error json.h not found | json-c headers installed under include/json-c/ but repo json-c recipe exposes only top include/ via PkgConfigDeps, so upstream #include <json.h> gets no -I include/json-c | build() passes command-line CFLAGS with -I<json-c include> -I<json-c include>/json-c to make; json-c recipe untouched (single-library PR) |
| 7 | test_package build fails test_libpiano.c:11 fatal error gcrypt.h not found | package_info set libs but no cpp_info.requires, so CMakeDeps consumers of pianobar::piano got no transitive includes; test TU includes <gcrypt.h> directly | package_info adds cpp_info.requires (curl/json-c/libgcrypt/ffmpeg avformat+avcodec+avfilter+avutil); test CMakeLists also find_package(libgcrypt)+explicit link as belt and suspenders |
| 8 | 上轮生产者侧透传后仍缺头，且 `piano.h` 透出 `../config.h`（又拉 libav 头） | 上游 `src/libpiano/piano.h` 自身 `#include <gcrypt.h>`（`gcry_cipher_hd_t`）和 `"../config.h"`（后者再 `#include <libavfilter/version.h>`/`<libavformat/version.h>`）；test_package 图中纯传递依赖的头路径不可靠，且包内从未交付 `config.h`（下一错必是 `config.h` 缺失） | 改走消费者侧直连：test_package 显式 requires libgcrypt/1.12.2 + ffmpeg/7.1.5（与主配方同版本）并显式链接 `libgcrypt::libgcrypt`/`ffmpeg::avformat`/`ffmpeg::avfilter`；主配方 `package()` 增发上游 `src/config.h` 到包根目录（即 `include/../config.h`）；`test()` 补 HMBS 双标记（test_package 18 断言以 exit 0 门控，上游诚实 `no_tests`） |
| 9 | 直连后 `gcrypt.h` 已通，`piano.h` 仍缺（test_libpiano.c:12） | 初判为 `cpp_info.requires` 中 `curl::curl` 与本仓 curl 配方的 `CURL::libcurl` 目标名不符，另加消费者头路径结构性兜底 | requires 改 `CURL::libcurl` 正名（后被真机证伪，见 #10）；test_package `generate()` 经 CMakeToolchain 注入 `PIANOBAR_INCLUDE_DIR=<包>/include`，CMake 以 `target_include_directories` 绝对路径直含；`package()` 对 piano.h/config.h 加存在性 fail-fast 校验（这两项保留） |
| 10 | `package_info(): requires includes package 'CURL::', but not a direct requirement` | `cpp_info.requires` 的 `::` 前是 Conan 包引用名（小写 `curl`），不是 CMake 目标名（`CURL`）；#9 的"正名"方向反了，真机校验器逐字匹配直接依赖名 | 回退为 `"curl::curl"` 并加 NOTE 注释固化规则；其余 #9 改动（绝对头路径注入、fail-fast）保留，`piano.h` 缺失改由结构性兜底解决 |
| 11 | test_package link fails with every Piano* symbol undefined (PianoErrorToStr/PianoListCount/PianoFindStationById/PianoInit/PianoDestroy/PianoDestroyPlaylist) while transitive deps resolve | package_type application makes CMakeDeps drop cpp_info.libs, so pianobar::piano carries no -lpiano; archive itself is complete (upstream src/libpiano has exactly crypt/list/piano/request/response .c, matching the 5-object ar) | package_type application -> library (bin+lib mixed package, precedent a52dec/0.7.4); test_package unchanged |
| 4 | OHOS 可执行文件需 `.codesign` 签名才能运行 | 内核拒绝加载无签名段的 package cache ELF | `package()` 内自签名；签名工具缺失时警告不断流（真机/CI 实证后再收紧） |
| 12 | test_package 在 `test_pianobar.sh` 处 `Signal 9`/`conan create` 退出码 137（2026-09-14 预检：`PASS: pianobar binary exists` 后即被 kill；libpiano 14/14 已过） | 上游 `src/ui_readline.c:BarReadline` 在 stdin EOF（`< /dev/null`）时 `read==0` 仅 `FD_CLR(STDIN)` 后 `continue`，下一轮 `select(maxfd, 空集, NULL)` 无限阻塞；`src/main.c` 无 `--help/--version` 分支且登录需 Pandora 网络，执行式冒烟测试在真机必然 hang 住被收割（Signal 9）。另 `test_pianobar.sh` 用 bash-only `pipefail` 而预检以 `/bin/sh` 执行 | `test_pianobar.sh` 改为 POSIX `sh` 静态交付检查（4 断言：可执行位、`strings/grep -a` 查二进制内 `Welcome to pianobar` 与 `2024.12.21`、man 页存在），不执行交互式二进制；`HOME/XDG_CONFIG_HOME` 隔离到 `${TMPDIR:-${TMP:-/tmp}}` 下 `mktemp -d`，`trap` 清理，不写只读 `/tmp`，不断言退出码、不删测试 |

## 验证结果

- 本轮：工作树已完成，未提交；等待 HMBS 后台真机预检（`conan create` + test_package）。
- `test_libpiano` 预期 14/14 通过（全离线断言，无网络）。
- CLI 侧不再执行交互式二进制：预期 `test_pianobar.sh` 4/4 通过（可执行位、二进制内 welcome/version 字符串、man 页），合计 18/18 断言。

## 交付物

| 文件 | 说明 |
| --- | --- |
| `bin/pianobar` | Pandora 命令行客户端 |
| `lib/libpiano.a` | libpiano 静态库（Pandora 协议 C API） |
| `include/piano.h` | libpiano 公开头文件 |
| `share/man/man1/pianobar.1` | 上游 man 页 |

## 注意事项

- `test_pianobar.sh` 为 POSIX `sh`（预检以 `/bin/sh` 执行），临时目录一律经 `${TMPDIR:-${TMP:-/tmp}}`+`mktemp -d` 创建并 `trap` 清理，不硬编码 `/tmp`；`build()`/`package()` 的 `TMPDIR/TMP/TEMP` 重定向保留。
- 上游链接 `-lpthread -lm` 保持原样（路径 A 最小改动）；若真机链接报缺 `pthread`，再以 OHOS 专用补丁剔除（musl libc 内建 pthread）。
- PR 正文测试数字待真机 evidence 轮回填，本轮不猜测。
