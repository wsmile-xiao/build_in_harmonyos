# dr_flac 0.12.39 编译说明（OHOS aarch64）

## 概述
dr_flac 是 mackron 的纯 C FLAC 音频解码器，以**单头文件**（`dr_flac.h`，约 512 KB）
形式分发，属于 `mackron/dr_libs` 多库集合（同集合还有 miniaudio、dr_wav、dr_mp3 等）。
零外部依赖（仅 libc/libm），无构建系统、无 CMakeLists —— 消费者直接编译头文件。

## 来源（重要）
0.12.39 **没有 git tag**（`flac-0.12.39` 在 mackron/dr_libs 不存在；现有 flac tag 自
`flac-0.12.43` 起）也**没有 GitHub Release**。官方来源锁定为 release commit
`7d3638f215599e4b576fe5d4be4f6820b9988e48`（commit message "dr_flac: Version 0.12.39"，
committed 2022-09-17T07:11:14Z）。

三处交叉核验一致：
- 头文件 banner：`dr_flac - v0.12.39 - 2022-09-17`
- 版本宏：`DRFLAC_VERSION_MAJOR/MINOR/REVISION = 0/12/39`
- 归档 tarball sha256：`3358845445ce36a2bc029b531b5183ada71be13a1285d4a381088e91d3171a09`

## 构建（Conan）
- `package_type = header-library`，`package_id` 清理为 header-only（无 build_type/架构差异）。
- `source()` 用 `conan.tools.files.get(..., strip_root=True)` 拉取 release-commit 归档。
- `package()` 把 `dr_flac.h` 安装到 `include/dr_flac/dr_flac.h`，`LICENSE` 到 `licenses/`。
- 不产出任何 lib 制品。

## 消费者使用
```c
#include <dr_flac/dr_flac.h>
// 在一个（且仅一个）翻译单元中：
#define DR_FLAC_IMPLEMENTATION
```
CMake 侧 `find_package(dr_flac)` → 目标 `dr_flac::dr_flac`。

## 测试
上游 `tests/flac/`（dr_flac_decoding.c / dr_flac_seeking.c / dr_flac_test_0.c）**无法在归档
源码上运行**：`testvectors/flac/` 为空（仅 `DO_NOT_DELETE.md`），且 `dr_flac_decoding.c` 依赖
外部 libFLAC 参考解码器 + miniaudio（`tests/external/` 为未填充的 git submodule）。

因此用**确定性生成的合法 FLAC 测试向量**（`gen_testvector.py` → `flac_test_vector.h`，566 字节：
`fLaC` + STREAMINFO[34B] + 一个帧：sync `0xFF3E`、ch0 CONSTANT(12345)×256、ch1 VERBATIM 锯齿×256、
44100 Hz、16 bps、256 帧）。该向量的 CRC-8/CRC-16 严格按 dr_flac 的算法计算（CRC-8 poly 0x07、
CRC-16 poly 0x8005，已用 dr_flac 自带注释的 `crc8(0,0x3FFE,14)==0xCE` 恒等式验证表正确）。

`test_dr_flac.c` 经**真实 OHOS clang（Clang 15.0.4, aarch64-linux-ohos）编译**，经公开 API
`drflac_open` + `drflac_read_pcm_frames_s16` 解码全部 256 帧，断言 8 组全部通过：
版本 0.12.39；STREAMINFO 恢复 2ch/44100Hz/16bps/256帧；ch0 CONSTANT 全帧等于 12345；
ch1 VERBATIM 全帧等于预期锯齿。`conan create` 本地 W3 全绿。

## 踩坑记录
- `struct.pack(">H", crc8)` 会写 2 字节，CRC-8 是 1 字节 → 用 `bytes([c8])`。
- STREAMINFO 实际 **34 字节**（非 32），metadata block header 长度字段须为 `0x22`。
- 帧头 CRC-8 只覆盖前 5 字节（sync + 4 个字段字节），末尾 1 字节是 CRC-8 本身。
- 帧 CRC-16 覆盖 sync 起始 → 末个子帧字节，**不含**末尾 2 字节 CRC-16 字段。
- `conan create` 在本沙箱内 `source()` 直连 GitHub 会超时（沙箱网络限制），jsdelivr 可用；
  本地验证通过 conan 的 `core.sources:download_cache` 预置字节一致的官方 tarball 完成，
  配方本身仍指向官方 GitHub URL，真机 CI（GitHub 可达、空缓存）正常下载。
- OHOS profile 硬编码 `tools.build:compiler_executables` 指向 `/data/service/hnp/bin/{clang,clang++}`；
  非 CI 沙箱该路径不存在时，test_package `generate()` 会用 PATH 上的真实编译器打补丁（真机 CI 无操作）。
---

**编译结束**: 2026-08-31 10:24
**最终状态**: built
