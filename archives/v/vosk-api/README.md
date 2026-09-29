# vosk-api

Vosk 是离线开源语音识别工具箱：20+ 语言的流式/批量语音转文字、可重构词表、
说话人识别。本仓交付其 **C API 核心库**（`libvosk.so` + `vosk_api.h`），
由 Kaldi（声学模型/解码）与 OpenFst（WFST 图/ngram 语言模型）驱动。

仓库内的 Python / Java / Kotlin / C# / Node.js / Rust / Go 目录只是各语言的
**绑定**，都是 libvosk.so 的消费者，不属于本包交付面。

## 版本列表

| 版本 | 状态 | 编译日期 | 测试状态 |
|------|------|----------|----------|
| 0.3.50 | built | 2026-09-28 | test_package 17/17 断言通过（10 消费者 + 7 鸿蒙专项），上游无自动化测试套件 |

## 鸿蒙平台适配（OHOS aarch64，设备原生）

构建系统 CMake，两个补丁：

1. `0001-CMakeLists.txt.patch`
   - 补入上游 CMake 路径漏写的 `src/postprocessor.cc`（`vosk_api.cc` 的
     `vosk_text_processor_new/itn` 引用其 `Processor` 符号）；
   - 链接目标由"发行版安装态 kaldi 假设"（`kaldi-base`/`kaldi-online2`/
     `kaldi-rnnlm`/裸 `fstngram`）改为 Conan 交付的 `kaldi::kaldi` /
     `libfstngram::libfstngram`。
2. `0002-src-recognizer.cc.patch`
   - `WordAlignLatticePartial` → `WordAlignLattice`（kaldi g20231112 已把
     partial 变体合并进同一入口，签名一致）。

产出 `lib/libvosk.so`（AArch64 ELF64）+ `include/vosk_api.h`，无命令行工具。

## 依赖关系

| 依赖 | 作用 |
|------|------|
| `kaldi/g20231112` | 静态库，解码器/online2/rnnlm/lat/feat 等模块 |
| `openfst/1.8.4` | 静态库，FST 核心（`fst/...` 头文件与 `libfst.a`） |
| `libfstngram/1.8.4` | 静态库，OpenFst NGramFst(LOUDS) 扩展；`src/model.cc` 注册 `NGramFst<StdArc>`，为硬依赖（openfst 本体默认不带 ngram 扩展） |
| `openblas/0.3.34` | shared-library，kaldi 的 BLAS/LAPACK 后端；libvosk.so 运行期 NEEDED `libopenblas.so.0` |

libc++_shared.so / libc.so 为平台运行时依赖。

## 参考资料

- 官网：https://alphacephei.com/vosk/
- 源码：https://github.com/alphacep/vosk-api
- C API：`src/vosk_api.h`
