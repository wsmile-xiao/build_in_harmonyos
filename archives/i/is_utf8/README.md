# is_utf8

is_utf8 是 simdutf 社区的高速 UTF-8 校验库：单一 C++ 源文件实现
`extern "C" bool is_utf8(const char *src, size_t len)`，对 ARM64 NEON /
x64 SSE/AVX2 做运行时 SIMD 分发，吞吐量可达每字节约 1 cycle。

## OHOS 适配

- 上游 `src/CMakeLists.txt` 固定 `add_library(is_utf8 STATIC)`，无共享库
  通道，Conan 按 `static-library` 交付（产物 `libis_utf8.a` + `is_utf8.h`）。
- 补丁 `0001-CMakeLists.txt.patch` 为 benchmarks 目录增加默认 OFF 的
  `IS_UTF8_BUILD_BENCHMARKS` 选项：上游在 configure 阶段用
  `file(DOWNLOAD)` 从 GitHub 拉取 simdutf 基准依赖，必须避免在干净 CI
  环境触发（详见 `1.4.1/notes.md` 与知识草稿
  `knowledge/drafts/DRAFT-isutf8-cmake-configure-download-benchmarks.*`）。
- Conan target：`is_utf8::is_utf8`（`cmake_file_name = is_utf8`）。
- OHOS settings 下按已合并同类配方先例设置
  `CMAKE_SYSTEM_NAME=Linux`/`CMAKE_SYSTEM_PROCESSOR=aarch64`。

## 验证

- 上游测试：`conan create` 内 `cmake.test()` 执行 ctest `unit`
  1/1 通过（42 条硬编码断言 + 10,010,000 条差分断言）。
- 消费者测试：test_package 65,820 条断言（1/2 字节全量差分 + 定向序列 +
  64KiB SIMD 路径），变异验证证明断言可真实失败。
- `ohc-run.py conan-verify`：G0–G3 PASS；G4 带「无法找到程序包 ID」告警，其 L2/L4/L5
  因该告警跳过；三道门禁的真实通过证据来自本地 W3（CI 同源脚本）：
  L0/L1/L4/L5=pass、L2=skip（库包无 bin/，合法）。详见 `1.4.1/notes.md`。

上游：https://github.com/simdutf/is_utf8
