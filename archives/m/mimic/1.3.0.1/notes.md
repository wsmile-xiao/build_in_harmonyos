# mimic 1.3.0.1 — OHOS 适配笔记

## 上游概况

- 上游：https://github.com/MycroftAI/mimic1 （tag `1.3.0.1`）
- 语言：纯 C；Mycroft 的轻量级 TTS 引擎，CMU Flite 2016 年分支 + 内嵌
  HTS（隐马尔可夫）合成引擎
- 库：libttsmimic（公共 API 头安装到 include/ttsmimic/，mimic.h）
- 工具：mimic / mimic_time / mimicvox_info / t2p / compile_regexes
- 语音：默认构建编译进 8 个 CG voice（ap/awb/kal/kal16/rms/slt 等，
  .a 静态库形态）+ 安装 1 个 HTS voice 数据文件 cmu_us_slt_hts.htsvoice
  到 share/mimic/voices/（约 1.5MB）
- 许可：CMU 许可（MIT/X11 风格，见上游 COPYING）
- 硬依赖：pcre2（configure.ac:101 `PKG_CHECK_MODULES([PCRE2], [libpcre2-8])`）
- tarball 458MB（内嵌 flitevox 语音数据），解压约 768MB

## shared/static 判断

- 上游 `LT_INIT` 默认 **同时禁用** shared 和 static；libtool 仍会为每个
  LTLIBRARY 生成 .a 供链接，但 `make install` 不装库。
- 配方显式 `--enable-static --disable-shared`：以 .a 归档安装（与上游
  手动构建 `make check` 的链接形态一致）。无 shared 形态（源码无可见性
  控制，R26 不发明）。

## OHOS 适配要点（按踩坑顺序）

1. **无预生成 configure**：tarball 只有 configure.ac。`./autogen.sh`
   （= autoreconf -i）需要 pkg.m4（PKG_CHECK_MODULES 宏）。
   pkg.m4 在 pkgconf tool_require 包的 share/aclocal/。
   **ACLOCAL_PATH 必须在 run 命令行内联注入**——`buildenv_info
   .append_path("ACLOCAL_PATH", ...)` 在 CI 上不可靠（同 abiword-plugin
   -docbook 教训，实测 conanbuild env 文件中无该路径）。
2. **pcre2 .pc 陷阱**：ohpcd 的 pcre2 包 libpcre2-8.pc `prefix=/`（本机
   不存在的路径），pkg-config 产出 `-I/include -L/lib`。configure 碰巧
   通过（PCRE2_CFLAGS/LIBS 环境变量路径），make 时 pcre2.h 找不到。
   修法：从 `self.dependencies["pcre2"].cpp_info` 取绝对路径，显式传
   `PCRE2_CFLAGS=...`、`PCRE2_LIBS=...` configure 变量（缓存目录无关，
   CI 上同样成立；同 abiword-plugin-* 模式）。
3. **-Werror vs clang 包装器**：上游 CFLAGS 带 -Werror；OHOS clang
   包装器（/storage/Users/currentUser/usr/local/bin/clang，sh 脚本）向
   编译命令注入 `-Wl,--code-sign` → `-Werror=unused-command-line-argument`
   编译失败。用 `-Wno-error=unused-command-line-argument` 豁免（不动
   包装器/源码）。audio.c（--with-audio=none 路径）另有 set-but-unused
   变量，`-Wno-error=unused-but-set-variable` 豁免。
   **注意**：`tc.cflags` 是 property（返回新列表），append 会静默丢失；
   必须用 `tc.extra_cflags.append()`（实测：用错 API 时 CFLAGS=-fPIC -O3
   里完全没有豁免 flag）。
4. **config.guess 不认识 aarch64-linux-ohos**：显式 `--build=aarch64-linux
   --host=aarch64-linux-ohos`。
5. **musl 修复（源码补丁 0001）**：
   - HTS_misc.c：`fgetpos` + 手工访问 `fpos_t.__pos` → musl 的 fpos_t
     是不透明结构（无 __pos 成员）。改用 POSIX `ftello()`（Yocto 官方
     musl 补丁同思路，上游 commit 5282ff0750 拉取失败后自写最小修复）。
   - HTS_get_token_from_fp / _with_separator：`char c` → `int c`。
     HTS_fgetc 返回 int；AArch64 的 char 默认无符号，EOF(-1) 被截断成
     0xFF，token 死循环——真实 bug，非 OHOS 特有。
6. **-fno-common 重复符号（源码补丁 0002）**：cmu_indic_lang.h 里
   `const cst_regex * const cst_rx_not_indic;` 是无 extern 的临时定义，
   clang 11+ 默认 -fno-common，含该头的 3 个 TU 各生成强符号 → 链接
   失败。加 extern（声明），定义留在 .c。（us_regexes.h 是单 TU 包含的
   初始化定义，无此问题，不动。）
7. **HTS voice 定位**：`mimic_hts_get_voice_file()` 按 `.` / `voices` /
   `../voices` / PKGDATATADIR 探测，合成时按 **CWD** 解析。消费者要么
   chdir 到 voices 目录，要么把 .htsvoice 复制到 CWD/voices/ 下。
   （`mimic_voice_load()` 只支持 CG .flitevox；HTS voice 必须走
   `register_cmu_us_slt_hts()` 构造函数——同上游 main/mimic_voice_list.c。）

## 上游测试审计（R51 三步法）

上游正式测试 = **9 个 check_PROGRAMS 单元测试**（根 Makefile.am
`TESTS += $(myunittests)`，cutest.h 断言框架，make check 驱动）：
hrg_test / regex_test / string_test / token_test / voice_select_test /
wave_test / lex_test / lts_test / nums_test。

**OHOS aarch64 真机实测（2026-09-23）：TOTAL 9 / PASS 9 / FAIL 0 /
SKIP 0 / ERROR 0**。make check 已集成进 conanfile build()。
testsuite/* 是构建编排脚本（crosscompile_dependencies 等），非断言测试。
详见 test_package/MANIFEST.yml。

## test_package 设计

- **test.c**（17 条 CHECK）：chdir 到包内 voices/ → register_cmu_us
  _slt_hts() 注册 HTS voice → mimic_text_to_wave() 真实合成（文本→
  token→HTS→PCM）→ 断言样本数/采样率/单声道/非静音 → cst_wave_save
  _riff() 落盘并验证 RIFF/WAVE 魔数 → mimic_text_to_speech("none")
  （断言 rc==0 与时长 >0.1s）→ feature API round-trip → 幂等注册 →
  第二次合成 → mimic_exit()。全部为真实 API 调用，零 mock。
- **test_ohos.sh**（7 项 H 检查）：llvm-readelf 验证安装的全部 17 个
  libttsmimic*.a 是 ar 容器、180 个成员对象全部 ELF64/AArch64；测试
  二进制 ELF64/AArch64/PIE；NEEDED 仅 OHOS 系统库（实测 libc.so）；
  RPATH/RUNPATH 为空（静态链接）。

## 构建信息

- profile：ohos-aarch64（OHOS / armv8 / clang 15 / Release）
- 依赖：pcre2/10.40（ohpcd）；tool_requires：automake/1.18 +
  libtool/2.5.4 + pkgconf/3.0.5（pkg.m4 来源）
- 构建日期：2026-09-23；conan create 本地全绿（含 make check 与
  test_package 真机运行）
- 包体积约 297MB（静态库 + 语音数据，16 个 .a）

## 最终状态

- status: closed
- COMPLETED：ohos-aarch64 conan create 全绿（上游 make check 9/9 +
  test_package 17 检查 + OHOS 产物检查 7 项）；产物为 16 个静态库
  （libttsmimic*.a）+ 5 个工具 + HTS voice 数据；归档文件齐全
  （conanfile.py / conandata.yml / patches ×2 / test_package ×4 /
  manifest / notes / README / reports/test-report.md）。
