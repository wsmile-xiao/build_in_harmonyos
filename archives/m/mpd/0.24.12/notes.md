# mpd 0.24.12 适配笔记

## 编译环境
- 构建系统: meson + ninja（源码 version '0.24.12'，meson_version >= 1.0；OHOS 交叉编译用 host_machine=linux 交叉文件 + wrap-mode=nodownload）
- 编译日期: 2026-09-27
- 编译器: clang/clang++（LLVM 15.0.4 OHOS 工具链）
- 状态: built
- 语言预检: lang-preflight 初判 mixed（exit 2）系误报——3×build.gradle.kts + 6×.java 全部位于 android/ 可选 Android 客户端目录（不在 meson 构建图内），主体 1671 个 cpp（99.4%）为 C++；指挥官 2026-09-27 确认改判 cpp 继续，终局 result 需 --force 覆盖该 env_unsupported 草稿并注明豁免

## 上游测试清点（R51 申报表，构建前）

- 清点日期: 2026-09-27
- 测试根目录: `test/`（86 .cxx + 8 .hxx + 3 .sh；子目录 util/net/time/tag/playlist/fs）
- 测试框架: GoogleTest（protocol: 'gtest'）+ meson test() 注册
- 门控开关: `-Dtest=true`（meson option `test`，默认 false，"Build the unit tests and debug programs"）
- test() 注册总数: **18**

| # | 测试目标 | 位置 | 注册条件 | 本配置状态 |
|---|----------|------|----------|------------|
| 1 | TestRewindInputStream | test/ | 无条件 | ✅ ON |
| 2 | test_protocol | test/ | 无条件 | ✅ ON |
| 3 | test_queue_priority | test/ | 无条件 | ✅ ON |
| 4 | TestIcu | test/ | 无条件注册（链 icu 特性；icu/76.1 已在制品仓，requires 需补） | ✅ ON（补 icu/76.1） |
| 5 | test_icy_parser | test/ | curl_dep found | ✅ ON（curl 8.15.0 共享缓存包 + libcurl shim，最终实测活跃） |
| 6 | test_translate_song | test/ | enable_database（默认 true） | ✅ ON |
| 7 | test_archive_iso9660 | test/ | libiso9660 + mkisofs 程序 | ❌ OFF（构建机无 mkisofs 程序，上游环境依赖） |
| 8 | test_archive_bzip2 | test/ | libbz2 + bzip2 程序 | ✅ ON（轮 B 2026-10-01：host bzip2/1.0.8 库 + tool bzip2/1.0.8.2 程序，15/18→16/18） |
| 9 | test_archive_zzip | test/ | libzzip + zip 程序 | ❌ OFF（本图无 zziplib） |
| 10 | TestSongFilter | test/ | 无条件 | ✅ ON |
| 11 | test_pcm | test/ | 无条件（9 个源文件） | ✅ ON |
| 12 | TestUtil | test/util/ | 无条件（17 个源文件，最大单测试） | ✅ ON |
| 13 | TestNet | test/net/ | 无条件注册（源文件按 tcp/ipv6/local_socket 裁剪） | ✅ ON |
| 14 | TestTime | test/time/ | 无条件（TestFileTime 仅 Windows） | ✅ ON |
| 15 | TestMixRamp | test/tag/ | 无条件 | ✅ ON |
| 16 | TestPlaylistPlugins | test/playlist/ | 无条件 | ✅ ON |
| 17 | TestFs | test/fs/ | 无条件 | ✅ ON |
| 18 | TestParsePath | test/fs/ | 无条件 | ✅ ON |

- 本配置预期启用: **15/18**（#7/#8/#9 为 OFF，全部因构建机程序/可选库缺失：mkisofs/libbz2/libzzip）——轮 B（2026-10-01）更新为 **16/18**：#8 经 host bzip2/1.0.8（库）+ tool bzip2/1.0.8.2（程序）点亮；#7/#9 维持 OFF（libiso9660/zip 未发布，上游环境依赖）
- 非注册调试可执行文件（run_input/run_decoder/dump_playlist/read_conf/run_inotify 等约 30 个）：手动调试工具，不计入通过率；其中 run_inotify 受 enable_inotify 门控（本配置 inotify=off 不构建）
- 关键条件宏（源码实证）: `is_linux = host_machine.system()=='linux'`（meson.build:245，交叉文件 host_machine=linux → true，历史补丁 0001/0005 预期不需要）；`enable_inotify = inotify and is_linux and database`（meson.build:326）；`enable_database = get_option('database')` 默认 true（meson.build:323）；`need_encoder` 随编码器输出启用（src/output/plugins/meson.build:12,40,96，vorbisenc 开 → true）
- 新增依赖发现: icu/76.1（TestIcu 需要，制品仓已有，requires 补充项，非指挥官 12 依赖清单内）

## 最终开关清单（步骤9：meson configure 自报核对，2026-09-27）

交叉编译参数（meson setup）：`--cross-file`（host_machine=linux/aarch64，绝对路径 HNP 编译器）+ `--native-file`（build machine 编译器，GenParseName 代码生成器用）+ `--wrap-mode=nodownload` + `--buildtype=release` + 23 个 -D 开关。setup rc=0。

### 背景 ON 清单核对（11 项）

| 背景项 | meson option | 自报值 | 核对结果 |
|--------|-------------|--------|----------|
| ALSA | alsa | enabled | ✓（构建层 ON；OHOS 运行时无 ALSA 设备 → 已知限制） |
| JACK | jack | enabled | ✓（注：`jack_set_info_function` 符号探测 = NO，JACK 运行时行为待真机验证） |
| PORTAUDIO | （无对应选项） | — | 0.24.12 输出插件无 portaudio，不被消费（步骤6 已确认） |
| SQLITE3 | sqlite | enabled | ✓（stickers） |
| FLAC | flac | enabled | ✓ |
| VORBIS | vorbis / vorbisenc | enabled / enabled | ✓（解码+编码） |
| MAD | mad | enabled | ✓（libmad.a 静态，-L 注入） |
| WAVPACK | wavpack | enabled | ✓ |
| CDIR（libcdio） | cdio_paranoia | auto → off | libcdio_paranoia 不在制品仓 → feature 自动降级 off（R36 不捎带适配，入已知限制） |
| OPUS | opus | enabled | ✓ |
| FFMPEG | ffmpeg | enabled | ✓（libavformat 60.16.101 / libavcodec 60.31.102 / libavutil 58.29.100，经 .pc Version 修正） |

### 背景 OFF 清单核对（9 项）

| 背景项 | meson option | 自报值 | 核对结果 |
|--------|-------------|--------|----------|
| shout | shout | disabled | ✓ |
| aac | faad | disabled | ✓（AAC 选项名 = faad） |
| wma | （无独立选项） | — | WMA 仅经 ffmpeg 插件解码，不可单独关闭（如实记录） |
| cddb | （无对应选项） | — | 0.24.12 已无 CDDB 相关选项（上游移除，无需关闭） |
| sndfile | sndfile | disabled | ✓ |
| pulse | pulse | disabled | ✓ |
| ao | ao | disabled | ✓ |
| oss | oss | disabled | ✓ |
| inotify（先关） | inotify | false | ✓（真机实测 OHOS 支持后再开 = 路径C 加分项） |

### 名单外开关（按默认值处理，自报值记录）

- **auto 且依赖在图内 → 默认策略启用（6 项）**：curl（libcurl 8.15.0，图内传递依赖 → HTTP 流媒体输入 + test_icy_parser 转活跃）；expat（2.8.2.1）；webdav（curl+expat → WebDAV 输入）；pcre（libpcre2-8 10.48 → 正则）；iso9660（libiso9660 2.3.0 → ISO9660 归档插件）；lame（libmp3lame → MP3 编码）；ipv6（AF_INET6 存在）
- **auto 无依赖 → 默认 off（34 项）**：adplug / audiofile / bzip2（bz2 库缺失）/ cdio_paranoia / chromaprint / dbus / fluidsynth / gme / id3tag / io_uring（liburing 不在仓）/ mikmod / mms / modplug / mpcdec / mpg123 / nfs / nlohmann_json / openal / openmpt / pipewire / qobuz / shine / sidplay / sndio / solaris_output / soxr / systemd / tremor / twolame / udisks / upnp / wildmidi / zeroconf / zzip；smbclient（默认 disabled）
- **boolean 默认 true 保留（16 项）**：cue / daemon / database / dsd / epoll / eventfd / fifo / httpd / local_socket / neighbor / pipe / recorder / signalfd / snapcast / tcp / wave_encoder
- **文档族（默认值，构建阶段实证）**：html_manual=true、manpages=true、documentation=auto、doxygen=false——若 doc 工具链缺失，步骤10 显式关闭并记录原因
- **Android 族（android_*，Linux/OHOS 路径不生效）；libfuzzer=true / fuzzer=false（互不生效）**

### 核心/编译参数自报值

- buildtype=release；**default_library=static**（Meson 1.12 默认 → 产物静态，R26 安全，conanfile 需 package_type 对齐）；cpp_std=c++20（MPD 硬性要求）；c_std=c11
- c_args/cpp_args 观测值：`-fPIC -O2 -I/storage/Users/currentUser/usr/local/include`（机器环境带入）
- 本配置 test() 注册测试 = 15/18 预期（test_icy_parser 因 curl 转活跃；test_archive_iso9660 另需构建机 mkisofs 程序；bzip2/zzip 仍 off）——轮 B 更新：16/18（bzip2 点亮，台账 #13）

## 困难度台账（路径C 高难度挑战，每处平台问题 1 条）

| # | 平台问题 | 根因 | 修复 | 可移植性 |
|---|----------|------|------|----------|
| 1 | `src/util/SpanCast.hxx:53` 编译错：`std::span` 无 range 构造（string_view→span 初始化无匹配构造） | OHOS libcxx-ohos 基于 LLVM 15.0.4，缺 C++23 P2652（span-from-range，libc++ 18 才并入）；上游 guard 仅覆盖 `__clang_major__ < 15`，本机恰为 clang 15.0.4 落在 guard 之外 | guard 改特征宏：`#if __cpp_lib_span < 202306L`（1 行）；两分支产生等价 span（data/size 与 range 构造同语义），全平台零行为差异；无平台宏（R8 合规）；W0b 比对：历史同类问题曾用 `defined(__OHOS__)`（R8 违规），本次不复用 | ✓ portable |
| 2 | `std::make_unique_for_overwrite` 全树 13 处编译错（10 文件：FileCommands.cxx / MadDecoderPlugin.cxx / SidplayDecoderPlugin.cxx×2 / io-uring ReadOperation.cxx / lib/icu Util.cxx / lib/icu Win32.cxx×2 / lib/nfs FileReader.cxx / Queue.cxx / ApeLoader.cxx / Id3Load.cxx×2） | 同上工具链缺 C++23 P2325R3（`make_unique_for_overwrite`，libc++ 19 才并入）；MPD 源码树无条件使用该 API，任何 option 组合都会命中 | 统一替换 `std::make_unique`（语义差异：值初始化多一次零填充——13 处使用点均在写后才读，零填充无副作用且开销可忽略）；本配置实际编译验证 6 文件（FileCommands/MadDecoder/icu-Util/Queue/ApeLoader/Id3Load），另 4 文件（Sidplay/io_uring/Win32/nfs，对应 option 本配置 off）同语义统一替换，保证任意 option 组合可构建；W0b 比对：历史 0002-0006 补丁覆盖 3/10 文件（FileCommands/Queue/ApeLoader），本次为全树补全 | ✓ portable |
| 3 | 29 文件用 `fmt::format`/`to_string`/`join` 编译错 `no member named 'format' in namespace 'fmt'`（首个命中 src/net/ToString.cxx:80/84） | fmt 11+ 将 `<fmt/core.h>` 改为精简布局（format/to_string/join/print 移入 `<fmt/format.h>`）；MPD 0.24.12 这 29 文件直接 include `<fmt/core.h>` 并使用 format.h 专属 API——依赖版本兼容问题（本图解析 fmt/12.2.0，制品仓可用版本）；推测：任何平台在 fmt≥11 下均会命中（非 OHOS 未实测） | 29 文件 `#include <fmt/core.h>` 统一替换 `#include <fmt/format.h>`（严格超集、幂等 include、零行为差异，fmt 9-12 全兼容）；含 1 个 win32 专属文件（本配置不编译，统一替换保任意平台可构建） | ✓ portable |
| 4 | `src/event/TimerList.hxx:22` 约束错：`regular_invocable<compare_three_way, time_point, time_point>` = false（round4 一次命中 6 个 TU） | libcxx-ohos（LLVM 15.0.4 基线）缺 `std::chrono::time_point::operator<=>`（C++20 起上游标准库提供），默认 `Compare=std::compare_three_way` 不可调用；W0b 历史同类问题（"chrono <=>"）预期命中 | TimerList.hxx 增加显式比较器 `CompareDue`（返回 `std::strong_ordering`，仅用 C++11 time_point 关系符 `<`/`>`）并作为第三个模板参数传入 `IntrusiveTreeSetOperators`；树逻辑以 `std::weak_ordering` 接收结果（strong→weak 标准隐式转换），语义与 compare_three_way 完全一致 | ✓ portable |
| 5 | 编译错 `fatal error: 'alsa/asoundlib.h' file not found`（input_plugins 目标）：同一 alsa_dep 对象在 libalsa/output_plugins 目标正常，input_plugins 漏掉 alsa 的 pkg-config cflags（可复现；直接 `pkg-config --cflags alsa` 输出正常；meson 1.12.0 内部机制未定） | meson 1.12.0 对同一 dep 对象在不同 executable 目标的 cflags 传递不一致（疑似 dep 对象共享/缓存问题），机制未完全定位但现象可复现 | 交叉文件 `[built-in options] c_args/cpp_args` 全局 `-I <alsa include>` 注入（workaround）；最终 conanfile build() 需复现 | OHOS/CI 同 meson 版本必现；全局 -I 为 workaround |
| 6 | 编译错 `mad.h`/`lame/lame.h` not found（decoder 目标）+ 链接缺 mad/lame：MPD 对 mad/lame 走 `compiler.find_library`（只给链接不给 include，上游依赖系统 /usr/include）；且 PkgConfigDeps 生成的 mad.pc/lame.pc 的 prefix 指向 recipe 槽的 p/（路径不存在，真实产物在另一 package_id 槽）——conan PkgConfigDeps 缺陷 | ①find_library 型依赖不携带 include 路径（上游设计）；②PkgConfigDeps .pc prefix 解析到 recipe 槽而非 package 槽（conan 2.29.1 缺陷）；③同类缺陷：gtest 包自带 4 个 .pc 硬编码原构建期 build-context 绝对路径（p/b/gtestddcd678b9dadc/p，本机不存在）、共享缓存遗留 curl 8.15.0 包的 libcurl.pc prefix 指向跨机不存在路径 | 交叉文件 c_args 全局 `-I <mad include> -I <lame include>` + c/cpp_link_args `-L <mad lib> -L <lame lib>`（find_library 只认 -L）；其余 .pc 缺陷用 SHIM 目录（PKG_CONFIG_PATH 最前）7 个 shim 收口：icu-uc/icu-i18n/libcurl/gtest/gtest_main/gmock/gmock_main（全部指向真实产物槽） | CI clean 环境同样必现（缺陷在 conan 侧）；conanfile build() 必须复现 shim+全局注入 |
| 7 | 链接错 `undefined symbol: icudt76_dat`（mpd 主可执行文件 + 4 个测试链接） | conan icu/76.1 为纯静态包（libicuuc.a/libicui18n.a/libicudata.a）；`icudt76_dat` 数据符号由 libicudata.a 提供，而 icu-uc 的 .pc Libs 若只写 -licuuc 则缺 -licudata；且 **meson 把 pkg-config 结果缓存进 coredata，`meson reconfigure` 复用缓存不重查**——改 .pc 后必须 `meson setup --reconfigure --clearcache` 才生效（实测踩坑：两次 reconfigure 后 build.ninja 仍无 -licudata） | shim icu-uc.pc 的 Libs 补 `-licudata`（顺序 -licuuc 在前 -licudata 在后）+ `--clearcache` 刷新 | 静态 ICU 包在任何 meson 项目必现；CI conan create 若 icu 为静态需同样处理 |
| 8 | `meson test` 15 个测试全部 SKIP（exit status 77、0.00s、无输出）：手动直接运行同一测试二进制 55/55 PASSED | meson 1.12 交叉构建语义：cross 构建产物运行测试必须经 `exe_wrapper`；交叉文件未定义 exe_wrapper → mtest.py `_get_test_cmd` 返回 None → `complete_skip()`（源码注释 "Can not run test on cross compiled executable because there is no execute wrapper"） | 交叉文件 `[binaries] exe_wrapper = ['<identity wrapper 脚本>']`：本机即目标机（aarch64 HarmonyOS 原生），wrapper 仅注入 LD_LIBRARY_PATH（conan 依赖库 + SDK llvm 库）后 `exec "$@"` 透传 | OHOS 目标机本地验证必用；CI worker（同为目标机）同理 |
| 9 | MPD 0.24 工具链/CLI 适配点（运行时验证阶段实测）：①主程序**无 --config 选项**（0.24 命令行仅 kill/no-config/no-daemon/systemd/stdout/stderr/verbose/version/help），配置文件路径是**位置参数**（src/CommandLine.cxx 首个非选项参数）；②新配置解析器（src/config/File.cxx + Tokenizer）**不接受 `name = "value"`**（`NextString` 要求值紧随名字，`=` 触发 `'"' expected`）——mpd.conf 必须 `name "value"` 格式；③`--decode-file` 选项已移除（0.24 无）；④测试工具 read_tags/run_decoder 的 URI 参数直接接受**绝对路径**（InputStream::Open 对 IsAbsolute 走本地打开，无需 file:// 前缀），DECODER 参数必须为具体插件名（mad/ffmpeg/opus 等，无 "all"） | MPD 0.22→0.24 命令行/配置解析重构（上游行为变化，非平台问题）；test 工具 URI 语义（本地路径直通） | 冒烟脚本按上述格式编写（`mpd --no-daemon <conf>`；conf 无 = 号）；R40 实质验证改用 test 工具 read_tags/run_decoder 替代 --decode-file | 上游通用行为；test_package 编写时遵循 |
| 10 | 共享 conan 缓存污染（.conan2 为本机共享，被并发任务清理/占用）：缓存出现空槽、跨机 prefix 的 .pc、build-context 遗留槽（p/b/ 消失）；曾导致 8.5.0 curl 解析指向已消失槽 | 本机 .conan2 缓存非 MPD 独占，其他 worker 任务会增删包 | 依赖存在性一律 `conan download -r=ohpcd`（W0/R36/R35）不信任本地缓存；.pc 消费一律经 SHIM 收口到**实测存在的**产物槽（不依赖 .pc 自带 prefix）；PKG_CONFIG_PATH = SHIM:deps-only（排除遗留槽 .pc 干扰） | 共享缓存环境必现；conanfile 侧 CI clean 环境无此问题（但 PkgConfigDeps prefix 缺陷 #6 仍在） |
| 11 | 配方 build() 遍历 `self.dependencies.values()` 时 `package_folder` 为 None → `os.path.join` TypeError（G2 conan create 首跑即挂）：传递依赖（bzip2/xz/openssl，Traits headers=False/libs=False）conan 2.29 不为其解包 → package_folder=None；且 values() 会遍历到全部传递依赖（非仅 16 个直接 requires） | ohpcd conan 2.29 对"消费者不可见"的传递依赖不解包（实测：直接依赖 16 个全有 folder，bzip2/xz/openssl 三个 None） | 遍历依赖取路径处一律先 `pf = d.package_folder; if not pf: continue`（conanfile _build_cross_files 已修）；只取特定依赖用 `self.dependencies[name]`（直接依赖均有 folder） | ohpcd conan 2.29 配方通用坑（任何遍历依赖的 meson/manual 配方都会踩）；知识图谱暂无对应 E 条目，待 graph add --draft |
| 12 | **OHOS 平台：已落盘 ELF 的任何 in-place 字节改动 = 不可执行**（两条独立证据链，2026-09-27 本机实测）：①`llvm-objcopy`（本机 llvm-strip 的别名，无独立 llvm-strip）输出（strip --strip-all 与零选项纯重序列化皆然，4.6KB hello 亦复现）exec 报 EACCES/EPERM；②`meson install` 对 builddir 产物剥 DT_RUNPATH 的 in-place patch（1195 字节，stage 哈希≠builddir 哈希、大小相同）→ 产物 exec 报 EPERM（stage 直接执行复现）。共性：文件 mode 770、ELF ehdr/phdr 内部一致、SELinux context 相同（hmdfs:s0）仍被拒；objcopy 非字节复制器（cmp 自第 7689 字节起与原件不同）；对照：clang/lld 原始产物可执行、全新拷贝（`cp`/`shutil.copy2`）可执行 | 推断：OHOS 内核/FS 对已落盘文件做完整性封印（与 lld 生成的 `.note.ohos.ident` 标识段相关，与 SKILL gotchas「ELF 签名：必须签名否则不可执行」同族机制）；落盘后任何字节改动（in-place patch 或重序列化写回）破坏封印 → exec 拒绝；全新文件写入不受影响 | package() **禁止 meson install / strip / objcopy 一切链接后重写**，一律对 builddir 原始产物做**全新拷贝**（conan copy = 新文件写入）；builddir 产物携带的 DT_RUNPATH（指向 conan build tree 目录）异地为死路径、无害，运行时库解析由 conanrunenv LD_LIBRARY_PATH 承担；需要瘦身走 CI sign.sh 签名链而非本地重写 | OHOS 平台硬约束（所有含可执行文件的配方）；aegisub 先例同为 builddir 直拷（未走 meson install）；已沉淀知识草稿 E430 |
| 13 | test_archive_bzip2 点亮三连坑（轮 B 2026-10-01）：①版本冲突——直接 `requires("bzip2/1.0.8.2")` vs ffmpeg 传递 `bzip2/1.0.8`，conan 2 图内直接报 `Version conflict`；②`ld.lld: unable to find library -lbz2`——MPD 对 bzip2 走 `cc.find_library('bz2')`（find_library 型只认 -L，交叉文件 c_link_args 此前仅 mad/lame）；③bzip2/1.0.8 包为纯库（package_info 无 bindirs），套件另需 bzip2 程序（1.0.8.2 包才声明 bindirs=bin，含 12 个程序） | ①conan 2 直接/传递同包不同版本 = 硬冲突，无隐式升级；②find_library 型依赖（mad/lame/bzip2 同族）的 -L 必须显式注入交叉文件（台账 #6 同手法）；③conan 包版本适配后缀（.2）可能伴随产物结构变化（补程序） | ①host 图维持 bzip2/1.0.8（与 ffmpeg 传递一致，冲突消除，mpd 链 libbz2.a）；②交叉文件 c_args 补 `-I <bzip2 include>`、c/cpp_link_args 补 `-L <bzip2 lib>`（meson-log 实证：补前链接测试缺 -L，补后 find_library 通过）；③`tool_requires("bzip2/1.0.8.2")` 仅提供程序（构建上下文，与 host 图版本互不冲突；PkgConfigDeps prefix 缺陷延伸至 bzip2.pc → 第 8 个 shim 收口）；程序入 PATH = conan buildenv 自动注入 + 配方 shutil.which 回退注入双保险 | conan 配方通用模式（版本冲突化解 + find_library -L 注入 + tool/host 同包异版本分工）；CI clean 环境同构必现 |

## 编译步骤

```bash
# 1. conan 依赖安装（17 requires + 1 tool_requires，profile ohos-aarch64，R36 全部已发布制品仓）
conan install --requires=mpd/0.24.12 ...   # 本地探索期：手动 conan install 各依赖 + PkgConfigDeps 输出 deps/

# 2. meson setup（交叉文件 cross-ohos.ini：[binaries] 绝对路径 HNP 编译器 + exe_wrapper；
#    [host_machine] system=linux/aarch64；[built-in options] 全局 c/cpp_args 与 c/cpp_link_args）
meson setup <builddir> <srcdir> \
  --cross-file cross-ohos.ini --native-file native-build.ini \
  --wrap-mode=nodownload --buildtype=release \
  -Dalsa=enabled -Djack=enabled -Dsqlite=enabled -Dzlib=enabled \
  -Dflac=enabled -Dvorbis=enabled -Dvorbisenc=enabled -Dmad=enabled \
  -Dwavpack=enabled -Dopus=enabled -Dbzip2=enabled -Dffmpeg=enabled -Dicu=enabled -Dtest=true \
  -Dshout=disabled -Dao=disabled -Doss=disabled -Dpulse=disabled \
  -Dsndfile=disabled -Dfaad=disabled -Dinotify=false
# 注：meson 1.12 位置参数序 = [builddir] [sourcedir]（builddir 在前）

# 3. 编译（737 目标，含 15 测试二进制）
meson compile -C <builddir> -j8     # rc=0

# 4. 测试（需 exe_wrapper，见台账 #8）
meson test -C <builddir> -j4 -t 10  # 15/15 Ok
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码编译错 4 类（span/make_unique_for_overwrite/fmt include/chrono <=>） | OHOS libcxx-ohos（LLVM 15.0.4）缺 C++23/20 部分标准库 + fmt 11+ 布局变化 | 台账 #1-#4，全部 portable 修法（特征宏/等价 API/显式比较器/头替换），零平台宏 |
| 2 | `alsa/asoundlib.h` not found（仅 input_plugins 目标） | 台账 #5（meson 1.12.0 cflags 传递不一致） | 交叉文件全局 -I alsa include |
| 3 | `mad.h`/`lame/lame.h` not found + 链接缺 mad/lame | 台账 #6（find_library 无 include + PkgConfigDeps prefix 缺陷） | 交叉文件 -I/-L 注入真实产物槽 |
| 4 | 15 个测试目标 `gtest/gtest.h` not found / 链接失败 | 台账 #6（gtest 包自带 .pc prefix 损坏 + deps 缺 gtest_main/gmock_main 模块） | 4 个 shim（gtest/gtest_main/gmock/gmock_main）指向 gtest 包真身（libgtest*.a/libgmock*.a 均在其中） |
| 5 | curl 依赖解析失败（webdav/http 输入） | 台账 #6/#10（遗留 curl 8.15.0 包 libcurl.pc prefix 跨机损坏） | libcurl shim（Name: libcurl，正确本地 prefix，无 Requires——deps 无 openssl .pc） |
| 6 | 链接错 `undefined symbol: icudt76_dat` | 台账 #7（静态 ICU 缺 -licudata + meson coredata 缓存 .pc 结果） | shim icu-uc Libs 补 -licudata + `meson setup --reconfigure --clearcache` |
| 7 | `meson test` 全 15 SKIP（exit 77） | 台账 #8（cross 构建无 exe_wrapper） | identity wrapper（LD_LIBRARY_PATH 注入 + 透传）入交叉文件 [binaries] |
| 8 | mpd 启动 `'"' expected` 配置解析错 | 台账 #9（0.24 配置格式无 = 号；且无 --config 选项） | conf 改 `name "value"`；`mpd --no-daemon <conf>`（位置参数） |
| 9 | GTest 解析回退到 bundled subproject | meson 对 pkg-config 查询模块名小写化 + main:true → 查询 `gtest_main`；deps 无该模块而 bundled 版 prefix 损坏 | shim 覆盖全部 4 模块（Name 字段小写匹配） |

## 源码修改

4 类 portable 修改，共 41 文件（与 .orig 基线 diff，patch 由 refresh-patch --auto 生成）：

| 类 | 文件 | 修改内容 |
|----|------|----------|
| 1. SpanCast 特征宏 | src/util/SpanCast.hxx | `__clang_major__ < 15` guard 改 `#if __cpp_lib_span < 202306L`（台账 #1） |
| 2. make_unique_for_overwrite | 10 文件 13 处：src/protocol/FileCommands.cxx、src/decoder/plugins/MadDecoderPlugin.cxx、src/decoder/plugins/SidplayDecoderPlugin.cxx×2、src/io/uring/ReadOperation.cxx、src/lib/icu/Util.cxx、src/lib/icu/Win32.cxx×2、src/lib/nfs/FileReader.cxx、src/queue/Queue.cxx、src/tag/loader/ApeLoader.cxx、src/tag/loader/Id3Load.cxx | `std::make_unique_for_overwrite` → `std::make_unique`（台账 #2） |
| 3. fmt 头替换 | 29 文件 | `#include <fmt/core.h>` → `#include <fmt/format.h>`（台账 #3） |
| 4. TimerList 比较器 | src/event/TimerList.hxx | 显式 `CompareDue`（strong_ordering）替代默认 compare_three_way（台账 #4） |

## 依赖版本

conan requires（16 项，W0 全部已发布 ohpcd 制品仓，2026-09-27 核验）：

| 依赖 | 版本 | 说明 |
|------|------|------|
| alsa-lib | 1.2.16.1 | 音频输出/混音器 |
| jack | 1.9.22 | jack 输出 |
| sqlite3 | 3.53.4 | 曲库 |
| zlib | 1.3.1.1 | ffmpeg 图冲突下唯一可解版本 |
| flac | 1.5.0 | flac 解码 |
| libvorbis | 1.3.7 | ogg/vorbis 解码+编码 |
| mad | 0.16.4 | mp3 解码（find_library 型，-L/-I 注入） |
| wavpack | 5.9.0 | wavpack 解码 |
| opus | 1.5.2.1 | opus 解码 |
| ffmpeg | 6.1.6 | 通用解码（.pc Version 修正：libavformat 60.16.101 等） |
| icu | 76.1 | Unicode/ICU（纯静态，-licudata 必链） |
| fmt | 12.2.0 | 格式化（29 文件需 format.h） |
| libcurl | 8.5.0 | http/webdav 输入——直连声明：MPD input 插件直接依赖，非 ffmpeg 传递（ffmpeg 图实测仅 bzip2/openssl/xz/zlib） |
| lame | 4.0 | mp3 编码（find_library 型，-L/-I 注入；deps/lame.pc Version: 4.0 实测） |
| gtest | 1.17.0 | 单元测试（gmock 图冲突下唯一可解版本） |
| gmock | 1.17.0 | 单元测试 |
| bzip2 | 1.0.8 | .bz2 档案解码（host 图版本，与 ffmpeg 传递一致避冲突；1.0.8 包为纯库 libbz2.a）——轮 B 新增 |
| bzip2 (tool) | 1.0.8.2 | tool_requires，提供 bzip2 程序（test_archive_bzip2 套件；1.0.8 包无 bindirs）——轮 B 新增 |

传递/共享缓存（不在 requires 主清单，图内解析）：expat 2.8.2.1（ffmpeg 传递）、libpcre2-8 10.48、libiso9660 2.3.0、ogg 1.1.1（libvorbis 传递）、fontconfig/freetype/harfbuzz/libxml2/xz（ffmpeg 传递）

## 验证结果

```bash
# 1. 全量上游测试（R51 三步法第二步，2026-09-27 真机运行）
meson test -C <builddir> -j4 -t 10
# → 15/15 Ok（0 Fail）：TestTime/TestUtil(55)/TestNet/TestMixRamp/TestRewindInputStream/
#   test_protocol/test_queue_priority/test_translate_song/TestPlaylistPlugins/TestIcu/
#   test_icy_parser/test_pcm/TestFs/TestParsePath/TestSongFilter
# 未注册 3/18：test_archive_iso9660（构建机无 mkisofs）、test_archive_bzip2（无 libbz2）、
#   test_archive_zzip（无 zziplib）——上游环境依赖缺失，非适配缺陷

# 2. R40 运行时实质验证（目标机原生执行）
# C1 版本信息：
mpd --version
# → Music Player Daemon 0.24.12 / MPD_HOST=https://www.musicpd.org/
# C2 配置解析+启动+曲库导入（本地冒烟 3 文件 wav/mp3/opus）：
mpd --no-daemon <conf>   # 0.24 绑定成功无日志（Listen.cxx 仅失败时抛 "Failed to listen on"）
#   → 实证监听：bash /dev/tcp 连 127.0.0.1:6601 读协议 greeting "OK MPD 0.24.0"
#     （协议 banner 为上游 GitVersion 烘焙值 0.24.0，与 --version 的 0.24.12 不同，断言仅取 "OK MPD" 前缀）
#   日志 update: added /sample.wav /sample.mp3 /sample.opus（3/3 导入）
# C3 解码后端初始化：
read_tags mad <mp3>      # → duration=0.548, audio_format=44100:24:1, 标签解析正常
read_tags ffmpeg <opus>  # → duration=0.507, audio_format=48000:f:1
run_decoder mad <mp3>    # → 解码帧正常（mad 后端全链路）
run_decoder opus <opus>  # → 解码帧正常（opus 后端全链路）
# C4 播放闭环（轮 B 2026-10-01 新增，null 输出 + 协议状态机，无音频设备需求）：
mpd --no-daemon <conf4>  # conf4: port 6602 + audio_output { type "null" name "NullOut" }（null 插件无条件编译）
#   → python3 socket 客户端：listall → add sample_c4.wav（3s，music_directory 相对路径）→ play 0 →
#     每 0.4s 轮询 status → 观测 state=play → stop（20 次 ≈ 8s 窗口）
#   协议坑：play N = 播放列表索引（空列表报 Bad song index）；add 用相对路径（0: 前缀报 No such directory）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| archives/m/mpd/0.24.12/conanfile.py | — | Conan 配方（手工 meson，无 MesonToolchain；build_folder 私有 prefix（R49）+ 7 shim .pc + ffmpeg .pc 修正 + cross/native 双交叉文件 + build() 内建 meson test + package() builddir 全新拷贝（禁 in-place 重写，台账 #12）） |
| archives/m/mpd/0.24.12/conandata.yml | — | 官方源（musicpd.org）+ sha256 |
| archives/m/mpd/0.24.12/test_package/ | — | 消费者测试 C1-C4（C4 = null 输出播放闭环状态机） |
| archives/m/mpd/commands.json | — | 命令行工具声明（mpd 可执行文件，R38） |
| archives/m/mpd/0.24.12/patches/ | — | refresh-patch --auto 生成（4 类 40 文件：fmt core.h→format.h 29 / make_unique_for_overwrite 10 文件 13 处 / SpanCast 特征宏 guard 1 / TimerList 显式比较器 1，0024 为双类文件） |

## 注意事项

- **conanfile build() 必须复现的本地探索期机制**（CI clean 环境等价实现；_fixup_pkgconfig 在 build() 内执行，generate() 仅 PkgConfigDeps）：①8 个 shim .pc（icu-uc/icu-i18n/libcurl/gtest/gtest_main/gmock/gmock_main/bzip2，icu-uc Libs 含 -licudata）；②ffmpeg .pc Version 修正（PkgConfigDeps 把 libav*.pc Version 写成 conan 包版本 6.1.6，MPD 要求 ≥58.12/58.18/56.14 语义不匹配，从包内 SONAME 取权威库版本）；③交叉选项等价物：mad/lame/bzip2 的 -L/-I（find_library 型）、alsa 的 -I（台账 #5）；④exe_wrapper 等价（test_package 运行时 LD_LIBRARY_PATH——conan 环境下由 conan 自身管理，预期 CI 无台账 #8 问题，实测为准）；⑤package() 对 builddir 原始产物**全新拷贝**（禁用 meson install/strip/objcopy——in-place 字节改动使已落盘 ELF 不可执行，台账 #12）
- PkgConfigDeps prefix 缺陷（台账 #6）为 conan 2.29.1 侧问题——conanfile 内用 build() 后处理覆盖（_fixup_pkgconfig），不依赖 .pc 自带 prefix
- 本机共享缓存污染（台账 #10）：.pc 消费一律实测产物槽，PKG_CONFIG_PATH 仅 SHIM:deps
- MPD 0.24 配置格式 `name "value"`（无 = 号）、主程序配置路径为位置参数（台账 #9）——test_package 启动类用例遵循
- 已知运行时限制：ALSA 输出（OHOS 无 ALSA 设备）、JACK（`jack_set_info_function` 探测 NO）、inotify 本配置关闭（路径C 加分项待真机实测后开）
- 语言预检豁免：mixed 初判系 android/ 客户端目录误报（指挥官确认 cpp），result 终态 --force 覆盖并注明
---

**编译结束**: 2026-09-27 22:18
**最终状态**: built
