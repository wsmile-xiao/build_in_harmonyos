# mimic 1.3.0.1 功能测试报告

**日期**: 2026-09-23
**平台**: HarmonyOS (OHOS, arm64)
**构建方式**: Conan 2.29.1 (OHOS adapted) + Autotools（autogen + configure + make）
**Profile**: ohos-aarch64 (os=OHOS, os.version=6.0, arch=armv8, compiler=clang 15)
**依赖**: pcre2/10.40 (ohpcd)；tool_requires: automake/1.18 + libtool/2.5.4 + pkgconf/3.0.5
**补丁**: 2 个（HTS_misc.c musl fpos_t/EOF 修复；cmu_indic_lang.h extern 声明）

## 测试摘要

### 上游测试（make check，集成在 conanfile build()）

| # | 测试 | 描述 | 结果 |
|---|------|------|------|
| 1 | hrg_test | 语篇表示结构（HRG）单元测试 | ✅ PASS |
| 2 | regex_test | 正则引擎单元测试（cst_regex / pcre2） | ✅ PASS |
| 3 | string_test | 字符串 API 单元测试 | ✅ PASS |
| 4 | token_test | 分词器（tokenstream）单元测试 | ✅ PASS |
| 5 | voice_select_test | voice 注册/选择单元测试 | ✅ PASS |
| 6 | wave_test | 波形（cst_wave）单元测试 | ✅ PASS |
| 7 | lex_test | 词典查找单元测试（cmulex） | ✅ PASS |
| 8 | lts_test | 字母转音（LTS）单元测试 | ✅ PASS |
| 9 | nums_test | 数字展开（usenglish nums）单元测试 | ✅ PASS |

**上游测试**: 9/9 PASS（TOTAL 9, PASS 9, FAIL 0, SKIP 0, ERROR 0）

### 消费者测试（test_package，真机端到端）

| # | 测试 | 描述 | 结果 |
|---|------|------|------|
| 1 | mimic_init | 引擎初始化返回 0 | ✅ PASS |
| 2 | chdir voices | 进入包内语音数据目录 | ✅ PASS |
| 3 | register_cmu_us_slt_hts | 注册 HTS voice（上游调用序列） | ✅ PASS |
| 4 | voice name | voice 名称为 slt_hts | ✅ PASS |
| 5 | mimic_text_to_wave | 文本→波形合成成功 | ✅ PASS |
| 6 | samples > 1000 | 合成样本数真实（>1000） | ✅ PASS |
| 7 | sample_rate sane | 采样率在 8k–48k 之间（实测 32000） | ✅ PASS |
| 8 | mono | 单声道 | ✅ PASS |
| 9 | not silence | 波形非静音（非零样本 > 100） | ✅ PASS |
| 10 | cst_wave_save_riff | RIFF 落盘 rc==0 | ✅ PASS |
| 11 | RIFF/WAVE magic | 文件头 12 字节魔数正确 | ✅ PASS |
| 12 | text_to_speech none | outtype=none 合成 rc==0 | ✅ PASS |
| 13 | duration > 0.1s | 合成时长有效（实测 1.65s） | ✅ PASS |
| 14 | feat set/get | feature API round-trip | ✅ PASS |
| 15 | idempotent register | 二次注册返回同一 voice | ✅ PASS |
| 16 | second synthesis | 第二次合成产出样本 | ✅ PASS |
| 17 | mimic_exit | 引擎关闭返回 0 | ✅ PASS |

**消费者测试**: 17/17 PASS

### HarmonyOS 产物检查（test_ohos.sh，llvm-readelf）

| # | 检查 | 结果 |
|---|------|------|
| H1 | 16 个 libttsmimic*.a 均为 ar 容器 | ✅ PASS |
| H2 | 归档成员对象（180 个）全部 ELF64 | ✅ PASS |
| H3 | 归档成员对象全部 AArch64 | ✅ PASS |
| H5a/b | 测试二进制 ELF64 + AArch64 | ✅ PASS |
| H6 | NEEDED 仅 OHOS 系统库（libc.so） | ✅ PASS |
| H7 | RPATH/RUNPATH 为空（静态链接） | ✅ PASS |

**产物检查**: 全部 PASS

**总计**: 上游 9 + 消费者 17 + 产物 7 = 33 项全 PASS，0 FAIL

## 测试环境

- **Conan 版本**: 2.29.1 (OHOS 适配版)
- **Profile**: ohos-aarch64（本机即 OHOS aarch64 目标机，原生执行）
- **工具链**: /storage/Users/currentUser/usr/local/bin/clang（aarch64-
  unknown-linux-ohos, musl, clang 15）

## 验证命令

```bash
conan create archives/m/mimic/1.3.0.1 \
  -pr:h=ohos-aarch64 \
  -pr:b=ohos-aarch64 \
  --build=missing
```

## 测试数据与结果摘录

test_package 真实运行输出（节选）：

```
PASS mimic_init() == 0
PASS register_cmu_us_slt_hts() built the voice
PASS mimic_text_to_wave() produced a wave
PASS wave has real samples (>1000)
PASS wave sample rate sane
PASS wave is not silence
PASS cst_wave_save_riff() wrote the wav (rc==0)
PASS wav file has RIFF/WAVE magic
PASS mimic_text_to_speech('none') rc==0
PASS mimic_text_to_speech reported duration > 0.1s
  second synthesis: 0 samples, 1.65s
PASS mimic_feat_set_int/get_param_int round-trip
PASS second register_cmu_us_slt_hts() is idempotent
PASS second synthesis produced samples
PASS mimic_exit() == 0
ALL PASS
```

make check 摘要（conanfile build() 内执行）：

```
PASS: unittests/hrg_test
PASS: unittests/regex_test
PASS: unittests/string_test
PASS: unittests/token_test
PASS: unittests/voice_select_test
PASS: unittests/wave_test
PASS: unittests/lex_test
PASS: unittests/lts_test
PASS: unittests/nums_test
============================================================================
Testsuite summary for mimic 1.3.0.1
============================================================================
# TOTAL: 9
# PASS:  9
# FAIL:  0
# SKIP:  0
# XFAIL: 0
# XPASS: 0
# ERROR: 0
```

## 结论

mimic 1.3.0.1 在 HarmonyOS PC（aarch64, musl, clang 15）上：上游
9 个单元测试、消费者 17 项端到端检查（含真实 TTS 合成）、HarmonyOS
产物 7 项检查全部通过。库以 16 个静态归档 + HTS voice 数据发布，
API（mimic_init / register_cmu_us_slt_hts / mimic_text_to_wave /
cst_wave_save_riff / mimic_text_to_speech / feature 系列 /
mimic_exit）全部真实可用。
