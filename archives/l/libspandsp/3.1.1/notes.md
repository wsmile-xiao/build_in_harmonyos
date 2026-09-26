# libspandsp 3.1.1 适配笔记

## 编译环境

- 构建系统: autotools（git archive 无预生成 configure，autoreconf -fi 自举）
- 编译日期: 2026-09-24
- 编译器: clang 15（OHOS SDK, aarch64-linux-ohos）
- 状态: published（conan create 全绿：包构建 + test_package 12 项消费者测试全 PASS）
- 任务: 平台任务 #13882（libspandsp 3.1.1，taskBranch=feat/libspandsp-3.1.1）

## 软件说明

SpanDSP 软传真/电话 DSP 库：T.30/T.38 传真、V.17/V.22bis/V.27ter/V.29/V.34
调制解调器、G.711/G.722/G.726/GSM0610/LPC10 编解码、DTMF/MFC/R2、回声消除。
任务名 libspandsp，与 main 已有 archives/s/spandsp/0.0.6（gcw_Pp8UzTBn，
2026-09 done，旧版 2008 tarball 含预生成 configure）为同一上游——3.1.1 是
GitHub tag v3.1.1 的 git archive，**无预生成 configure**，走 autoreconf 自举。

## 依赖（configure.ac 实证）

- libtiff/4.7.2（AC_CHECK_LIB(tiff, TIFFOpen)，硬依赖）
- libjpeg-turbo/3.2.0（AC_CHECK_LIB(jpeg, jpeg_start_compress)，硬依赖）

## 构建配置

- autoreconf -fi 自举：tool_requires automake/1.18 + libtool/2.5.4 + pkgconf/3.0.5
  （E6404 jbig2enc 同法；automake --add-missing 安装的新版 config.guess/config.sub
  原生识别 aarch64-unknown-linux-ohos，无需 0.0.6 时代的补丁）
- --build/--host=aarch64-unknown-linux-ohos（交叉编译标准姿势）
- --disable-doc（doc 需 doxygen）
- 不传 --enable-tests（需 sox/pbmtog3/fax2tiff 外部工具 + libsndfile/fftw/
  libxml2/libpcap/X11/fltk 全家桶，configure 硬失败 AC_MSG_ERROR）
- make -j1 / install -j1（E074 HMDFS jobserver fifo EPERM + 并行 install
  目录竞态，0.0.6 先例同款）
- configure umask 077 运行时替换（E011/E114，jbig2enc 同款）
- **CC_FOR_BUILD 运行时替换（本版特有）**：configure.ac 在 build==host 分支
  硬设 CC_FOR_BUILD="\$(CC)"（命令行/环境变量均被覆盖），而 src/Makefile 的
  13 个生成表工具（make_modem_filter/make_v34_probe_signals 等）规则不带
  $(CPPFLAGS)，且 include spandsp.h → tiffio.h + <spandsp/*.h> +
  meteor-engine.h（tools/）。对策：configure 后对生成的 src/Makefile 把
  CC_FOR_BUILD = $(CC) 替换为 "clang -I<源码树 src> -I<源码树 tools>
  -I<依赖 include...>"（_drop_umask_077 同款运行时替换模式）。

## R51 上游测试清点与结果申报（rule4 口径）

上游 tests/ 目录 **87 个测试二进制**（tests/Makefile.am 的 noinst_PROGRAMS：
85 个常规 + v32bis_tests/v34_tests 两个条件程序[COND_V32BIS/COND_V34 默认 off]），
手工运行形态（无 automake TESTS harness）。上游 CI（build-dispatch.yml）只
构建分发包不跑测试。

`--enable-tests` 的 configure 硬依赖（本机与 CI 环境均无，AC_MSG_ERROR）：
sox、pbmtog3（netpbm）、fax2tiff（libtiff-tools）外部程序 + libsndfile/
fftw/libxml2/libpcap/X11/fltk 库。因此 make test 整链不可用——环境限制如实申报。

**实测（自编译自跑，参考 spandsp 0.0.6 先例的纯算法子集方法）**：
上游测试源码 + conan 包产物（libspandsp.a）+ 构建树 config.h + conan 缓存
libsndfile/1.2.2 静态库，编译 22 个纯算法/低依赖测试并本机运行：

| 结果 | 数量 | 说明 |
|------|------|------|
| PASS | 21 | 全部纯算法测试通过 |
| 未跑 | 1 | r2_mf_rx_tests——需 spandsp-sim 完整构建链（make_line_models 生成表 + fftw + line_model 数据），本轮未构建 sim 库 |
| 环境阻断 | 65 | 依赖 ITU/贝尔科版权测试数据（test-data/ 需 unpack 脚本+外部数据包）、GUI（X11/fltk）、pcap/xml2 harness、需真实音频设备等 |

PASS 清单（21 个）：bit_operations_tests、crc_tests、complex_tests、
complex_vector_float_tests、complex_vector_int_tests、bitstream_tests、
hdlc_tests、t38_core_tests、t38_non_ecm_buffer_tests、v42_tests、
vector_float_tests、vector_int_tests、timezone_tests、logging_tests、
dc_restore_tests、queue_tests、awgn_tests、alloc_tests、async_tests、
bert_tests、t35_tests（后三个链 conan libsndfile 静态库编译）

## 消费者测试兜底（test_package，12 项全 PASS）

1. G.711 ulaw 编解码往返（长度 + 幅度容差 512 断言，实测 worst delta=68）
2. DTMF 生成（dtmf_tx 3 参数 API：init(NULL, NULL, NULL) + put('1') +
   样本产出 + 能量阈值断言，实测 320 样本 energy=52152838）
3. CRC-16 ITU 交叉验证（上游 tests/crc_tests.c 同款：块计算 vs 逐位计算
   一致性 + 固定输入确定性锚点 0x6F91）+ CRC-32 append/check 往返

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 生成表工具编译失败 tiffio.h not found | configure.ac build==host 分支硬设 CC_FOR_BUILD=$(CC)，命令行/环境变量被覆盖；生成规则不带 $(CPPFLAGS) | conanfile.py _fix_cc_for_build()：configure 后对 src/Makefile 做运行时替换注入依赖 include |
| 2 | 生成表工具编译失败 spandsp/telephony.h not found | 上游开发时 srcdir==builddir；分离构建时 <spandsp/*.h> 只在源码树 | _fix_cc_for_build 再加 -I<源码树 src> |
| 3 | make_v34_tx_pre_emphasis_filters 编译失败 meteor-engine.h not found | 同上，meteor-engine.h 在源码树 tools/ | _fix_cc_for_build 再加 -I<源码树 tools> |
| 4 | test_package 编译失败 bool 未定义 | 3.1.1 头文件用 C99 bool | test 源码首行加 #include <stdbool.h> |
| 5 | test_package 编译失败 dtmf_tx_init 参数不匹配 | 3.1.1 签名变 3 参数（s, callback, user_data） | dtmf_tx_init(NULL, NULL, NULL) |
| 6 | test_package 编译失败 span_tone_report_func_t 未定义 | dtmf.h 引用但类型定义在 super_tone_rx.h（伞头依赖） | 包含顺序加 super_tone_rx.h（0.0.6 先例同款经验） |
| 7 | CRC 锚点值断言失败 | 初值语义：crc_itu16_calc(buf, len, 0xFFFF) 对 "123456789" 实测 0x6F91（非网上常见的 0x31C3——那是初值 0 的 KERMIT 变体） | 本机实测锚点 0x6F91 + 上游同款块/逐位交叉验证双断言 |

## 源码修改

无源码补丁（umask 与 CC_FOR_BUILD 均为构建期运行时替换，非补丁）。
