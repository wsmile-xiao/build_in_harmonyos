# libmpcdec 0.1 — HarmonyOS PC (aarch64, os=OHOS) 适配笔记

## 基本信息

- 上游源: https://files.musepack.net/source/musepack_src_r475.tar.gz
- 实测 sha256: a4b1742f997f83e1056142d556a8c20845ba764b70365ff9ccf2e3f81c427b2b
- 版本口径: 上游 musepack SVN r475 快照没有自报版本号；发行版把它编成 0.1
  （Arch: libmpcdec 1:0.1+r475，Debian: libmpc 0.1~r495）。本包按平台任务卡
  取 `libmpcdec/0.1`，源码即 r475 快照。
- 构建系统: CMake（上游同为 2009 年快照，`CMakeLists.txt` 为权威；`configure.in`
  为 autotools 残留，构建不走它）
- 语言: 纯 C（R47 lang-preflight: task=cpp, detected=c，兼容族通过）
- 依赖: **无外部依赖**（libc 之外为空）。libcuefile/libreplaygain 只被同一 tarball 的
  mpcgain/mpcchap 工具使用，本包不构建这些工具，故不引入（W0 清单为 `none`）。

## 交付物（与 musepack/r475 的分工）

同一 tarball 里含解码库、SV7 编码器、心理声学模型和 7 个命令行工具。按平台任务卡
本包只交付**解码库**：

- `lib/libmpcdec.a`（`-o shared=True` 时为 `libmpcdec.so`）
- `include/mpc/*.h`（7 个头文件）

mpcenc/mpcdec/mpcgain/… 工具与 libmpcenc/libmpcpsy 归 `musepack/r475`（已发布），
本包不重复交付，也不声明 `commands.json`（库类型）。

## 编译结论（模式 B, CMake）

- 工具链: 本机 OHOS clang 15（`ci/conan/profiles/ohos-aarch64`），cmake 4.1.2
- `conan create` 干净构建 + `test_package` 全通过（W3 exit_code=0，日志见 PR 正文）
- 上游无测试目标: CMake 版无 `add_test()`/`enable_testing()`，`ctest -N` 为空集；
  autotools 版 `configure.in` 无 check 规则 → 上游用例数 N=0
- 库级执行验证由 `test_package` 承担（见下），本机可执行新生成 ELF，故 W3 与 CI
  都能真跑（2026-09-03 musepack 任务记录的 noexec 限制在本次环境已不存在）

## 源码修改清单（补丁由 `refresh-patch --auto` 生成）

1. `CMakeLists.txt`（补丁 0001）
   - `CMAKE_MINIMUM_REQUIRED 2.4 → 3.5`（CMake 4.x 移除 <3.5 兼容，不改则 configure 直接失败）
   - `set(CMAKE_C_FLAGS "-O3 …")` 改为**追加式** `"${CMAKE_C_FLAGS} -O3 … -fcommon"`
     - 覆盖式写法会丢弃 Conan toolchain 注入的 CFLAGS（R33）
     - `-fcommon`: `mpc_decoder.c`/`requant.c` 在多个 TU 定义同名 tentative
       definition（`Res_bit`/`__Cc`/`__Dc`），clang 默认 `-fno-common` 时
       最终链接报 `ld.lld duplicate symbol`（知识图谱 E322 同源）
   - `add_subdirectory` 只保留 `libmpcdec` 与 `include`（不构建编码器/工具）
2. `libmpcdec/CMakeLists.txt`（补丁 0003）
   - 规范化 `OUTPUT_NAME mpcdec`（静态目标原名 `mpcdec_static` 会产出
     `libmpcdec_static.a`），并补上游遗漏的 `install(TARGETS …)`
3. `include/CMakeLists.txt`（补丁 0002）
   - `INSTALL(DIRECTORY mpc … FILES_MATCHING PATTERN "*.h" PATTERN ".svn" EXCLUDE)`
   - 只装 `*.h` 以防上游 `include/mpc/.svn` 元数据进包；注意
     **`FILES_MATCHING PATTERN "*.h"` 本身仍会创建空的 `.svn/` 目录**，
     需再加 `PATTERN ".svn" EXCLUDE` 才能连目录一起排除（实测）

补丁均为通用可移植性/打包修复，无 `__OHOS__` 平台宏。

## 消费者测试设计（test_package）

上游 M 编解码器项目自带 mpcenc，但解码库包不交付编码器；断言"解码正确"需要
已知答案输入。做法：

1. 用**同版本参考编码器**（ohpcd 的 `musepack/r475` 的 `mpcenc`）把一段 0.15 s
   双声道 44.1 kHz 正弦 WAV 编成 SV8 流（4156 B，6615 样本）；
2. 把该流的字节以 **C 数组**内嵌进 `test_package/fixture_mpc.h`
   （sha256 见文件头；PR 因此不含二进制条目）；
3. `test_libmpcdec.c` 用内存 reader 调
   `mpc_demux_init → mpc_demux_get_info → mpc_demux_decode` 跑完整个流，断言：
   SV8 / 44100 Hz / 2 声道 / 6615 样本 / 7 帧、首 8 个样本与参考解码一致（±0.01）、
   RMS≈0.229、峰值≈0.366。

设备实测: `decoded 7 frames / 6615 samples, rms=0.228875 peak=0.366392` →
`libmpcdec decode test: OK`。该测试在 `conan create` 的 test 阶段自动执行。

## 验证结果

```bash
# W3（干净轮）:
python3 scripts/ohc-run.py conan-verify libmpcdec 0.1 --profile ci/conan/profiles/ohos-aarch64
# test_package:
stream: SV8 44100 Hz 2 ch 6615 samples
decoded 7 frames / 6615 samples, rms=0.228875 peak=0.366392
libmpcdec decode test: OK (SV8 header + 7 frames / 6615 samples verified)
```

## 注意事项

- 上游 CMake 把 `add_definitions(-DFAST_MATH -DCVD_FASTLOG)` 加在所有子目录上，
  保留即可（解码路径依赖 `FAST_MATH` 的近似实现）。
- `-o shared=True` 会构建 `libmpcdec.so`；默认静态交付，避免 HMDFS/RPATH 问题。
- 上游头文件目录带 `.svn/` 残留（2009 快照），补丁 0002 已处理。
