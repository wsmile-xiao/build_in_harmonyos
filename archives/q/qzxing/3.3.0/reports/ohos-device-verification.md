# qzxing 3.3.0 真机验证报告

- 日期: 2026-09-30
- 设备: OpenHarmony PC 真机（aarch64，relay 通道 8）
- 工具链: conan 2.29.1 + ohos-aarch64.profile（clang 15 / libc++ / OHOS 6.0）
- 流程: `QZXING_RESOURCES_DIR=<语料 checkout> conan create ./3.3.0 --user ohpcd --channel stable -pr ohos-aarch64.profile -b missing`
- 结果: 全链路通过（构建 → 上游测试 → 打包 → 消费测试），日志 create15.log

## 1. 上游测试（build() 内生成式 CMake harness 编译同一批未修改测试源）

```
Upstream tests verified: decode total=1110 successful=851 failed=237
inconsistencies=22; encoder suites clean (no Exception: marker)
```

- 解码: 1110 次 PNG 语料尝试（qzxing-test-resources 子模块，52 目录/1192 图），
  Total/successful/failed/inconsistencies 与上游自己提交的参考日志
  qzxing_decode_3_0_alpha_0_3_test_results.log 在 12/17 格式上逐字一致，
  其余 5 个格式差异全部是 3.0-alpha→3.3.0 代码演进（见 notes.md）。
- 编码: 7 套件 46 单元方法全部执行，输出无 `Exception:` 标记（0002 补丁
  修正上游 testEncode 坏夹具后 46/46 全部执行，任何平台都无法通过的断言
  已真机字节级实证，见 notes.md）。
- 失败/不一致并非异常：失败文件按目录成簇（upca-6 整目录等），属上游
  已知难例，非适配引入。

## 2. 打包产物

```
package(): Packaged 1 file: LICENSE
package(): Packaged 2 '.h' files: QZXing.h, QZXing_global.h
package(): Packaged 1 '.0' file: libqzxing.so.3.3.0
package(): Packaged 1 '.3' file: libqzxing.so.3
package(): Packaged 1 '.so' file: libqzxing.so
```

共享库 SONAME libqzxing.so.3（与 Debian libqzxing3 对齐）。

## 3. 消费侧测试（test_package/qzxing_probe，8 项断言）

```
PASS: independent QR fixture decoded successfully
PASS: independent QR fixture payload matches
PASS: encoder produced a non-trivial QR image
PASS: round-trip QR decoded successfully
PASS: round-trip payload matches encoded data
PASS: encoder default-argument overload produces an image
PASS: setDecoder/getEnabledFormats round-trip
PASS: decoderFormatToString maps both formats
SUMMARY: 8 checks, 0 failures
```

- 独立夹具: python-qrcode 8.x 离线生成的 29 模块 QR（纠错 M、2 模块静区、
  载荷 https://atomgit.com/OpenHarmonyPCDeveloper），纯代码矩阵无二进制
  夹具依赖，与本库实现完全独立。
- 往返: encodeData → decodeImage 载荷逐字节一致。

## 4. 关键缺陷定位（真机实证）

- **解码器注册**: MultiFormatReader.cpp 的注册被 ENABLE_DECODER_* 宏门控，
  上游 CMake 构建默认全关 → 打包库零解码器、消费侧解码全灭（真机复现:
  打包库 decodeImage 全部失败，同一批源码按 .pro 宏编译的 harness
  1110 图 851 成功）。配方在 generate() 显式开启 5 个
  QZXING_USE_DECODER_* 选项后 8/8 通过。
- **上游 API 缺陷**: `QZXing(DecoderFormat)` 构造函数不初始化
  tryHarderType（真机实测垃圾值 126），setTryHarder(true) 失效；消费侧
  须用默认构造 + setDecoder + setTryHarder（上游 DecodeValidator 模式，
  探针即按此书写）。
