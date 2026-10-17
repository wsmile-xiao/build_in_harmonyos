# 上游测试用例真机执行器(upstream_test_runner)

**用途**:在 HarmonyOS PC 真机上真实执行 libwebp 1.6.0 上游 `tests/fuzzer/` 的 12 个
fuzz 目标(上游测试源码**零改动**,md5 逐字节互证)。

## 背景与机制

上游 1.6.0 的 12 个 fuzz 目标已迁移到 **FuzzTest 框架**(`FUZZ_TEST(...).WithDomains(...)`
体系,非旧式 libFuzzer 入口)。FuzzTest 运行时(google/fuzztest,依赖 abseil)不在
OHOS 工具链可用范围,直接构建不可行。本执行器以两层替换**框架基础设施**、
保留**被测函数本体逐字执行**:

1. **编译期 shim**(`fuzztest/fuzztest.h`):把 `FUZZ_TEST` 注册宏与域构造
   (`String()/Arbitrary<T>()/InRange()/ElementOf()/Map()/FlatMap()/PairOf()/
   OptionalOf()/Just()/StructOf()/VectorOf()/ReadFilesFromDirectory()` 等)中性化
   为空壳——域对象只保证编译通过,永不参与运行期计算;
2. **driver**(`drv_*.cc`):`#include` 上游 `xxx_fuzzer.cc`(整体纳入同一编译单元,
   使其匿名命名空间内的被测函数可直接调用),以显式种子语料 + 显式参数组合
   **直接调用上游被测函数**(FuzzTest 随机域生成由显式选择替代)。

上游 12 个被测函数及其驱动参数:

| 上游目标 | 被测函数 | 驱动参数/种子 |
|---|---|---|
| simple_api_fuzzer | `SimpleApiTest(blob)` | 全部 9 种子 |
| dec_fuzzer | `DecodeWebP(blob)` | 全部 9 种子 |
| webp_info_fuzzer | `WebPInfoTest(blob)` | 全部 9 种子 |
| huffman_fuzzer | `HuffmanTest(blob)`(内部 VP8L 位流 API) | 全部 9 种子 |
| imageio_fuzzer | `Decode(blob, fmt, keep_alpha, use_argb)` | WebP/PNM/猜型三格式 |
| enc_fuzzer | `EncTest(blob, opt, use_argb, cfg, crop)` | 3 档 WebPConfig × use_argb × opt |
| enc_dec_fuzzer | `EncDecTest(use_argb, img, cfg, opt, crop)` | 3 内置源图 × 3 档 config × opt |
| advanced_api_fuzzer | `AdvancedApiTest(blob, factor, 8 选项, cs, incremental)` | 3 colorspace × 3 选项组采样 |
| animation_api_fuzzer | `AnimationApiTest(blob, threads, mode)` | 4 模式 × threads |
| animdecoder_fuzzer | `AnimDecoderTest(blob)` | 全部 9 种子 |
| animencoder_fuzzer | `AnimEncoderTest(blob, minimize, kmin/kmax, mixed, frames, opt)` | 3 帧序列 × 2×2 组合 × opt |
| mux_demux_api_fuzzer | `MuxDemuxApiTest(blob, use_mux_api)` | 双 API 路 × 全部 9 种子 |

种子语料(本机 PIL 独立构建生成):真实有损 q75/q100、无损 VP8L(RGBA,alpha 避 0)、
3 帧动画、1x1、RIFF 魔数损坏、随机字节、24 字节截断、PPM P6。每 driver 输出
`[sanity]` 行自证语料真实可解析(WebPGetFeatures/WebPDecodeRGBA)。

**种子以 base64 文本入库**(`seeds_b64/`):平台 PR diff 管线不携带二进制补丁数据
(GitCode `.diff` 对二进制文件只出 "Binary files differ" 头,checkout-pr 的
`git apply` 必报 missing binary patch data 而整体失败),故 9 个种子文件一律存为
base64 文本,`build_run.sh` 运行时用 python3 解码还原到 `seeds_bin/` 并打印 md5;
`seeds_md5.txt` 记录 9 个种子的字节数与 md5,与解码输出逐条互证字节一致。

## 构建与运行(真机)

```sh
# 前置:本目录 + libwebp-1.6.0 上游源码树(与 Debian orig 字节一致)解包到 ~/fuzzrun
sh build_run.sh   # 静态构建上游 libwebp + 12 目标(复用 1.6.0.1 包 generators 的
                  # conan_toolchain.cmake → OHOS SDK 26.0.0.18 ohos.toolchain.cmake,
                  # clang 15.0.4;含 seeds_b64 → seeds_bin 解码还原)
sh run_all.sh     # 逐目标执行,打印 PASS/FAIL 与汇总;任一 FAIL 则以非零退出传播(可作 CI 门禁)
```

注:`build_run.sh` 内的 conan 缓存路径指向适配验证机(华为 PC 真机);移植到其他
设备时改 `PKG` 即可。被测代码与 conan 包内 .so 同源:同一上游树(逐字节一致)+
同一 OHOS 工具链;huffman 等目标依赖的内部符号由同树静态库提供(内部符号不出现在
.so 导出表中,只能以静态构建驱动)。

## 零改动证明

设备侧执行副本与本仓库原始树逐字节一致(17/17 md5 全中,见 device-results.txt)。

## 真机执行结果(2026-09-28,华为 PC aarch64,clang 15.0.4)

12/12 目标 PASS,共 330 次上游被测函数执行,零崩溃零 abort;与 x86 本机(MinGW
g++ 13.2 独立构建)逐目标结果一致。2026-09-29 以最终提交版脚本(b64 入库 + 退出码
传播)真机复验:解码 9/9 md5 全中 + 12/12 PASS,exit 0。详见 device-results.txt。
