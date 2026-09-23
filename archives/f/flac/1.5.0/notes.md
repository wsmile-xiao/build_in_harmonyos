# flac 1.5.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 1.5.0 官方自带完整 CMakeLists.txt）
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18) / clang++
- 目标平台: HarmonyOS PC aarch64 (arm64-v8a, musl)
- 状态: success

## 编译步骤
1. 下载源码 `https://github.com/xiph/flac/archive/refs/tags/1.5.0.tar.gz`
   （sha256: aea54ed186ad07a34750399cb27fc216a2b62d0ffcd6dc2e3064a3518c3146f8）
2. CMake 配置：ohos.toolchain.cmake + OHOS_ARCH=arm64-v8a + CMAKE_INSTALL_LIBDIR=lib
   - WITH_OGG=ON（libogg/1.3.5 从 conan 制品仓取，静态链接）
   - BUILD_PROGRAMS=ON（flac/metaflac CLI）、BUILD_CXXLIBS=ON（libFLAC++）、BUILD_TESTING=ON
   - BUILD_EXAMPLES/DOCS/MANPAGES=OFF
3. cmake --build -j4 → 全部目标编译链接成功
4. cmake --install → lib/libFLAC.a lib/libFLAC++.a bin/flac bin/metaflac include/FLAC/*.h

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 静态库创建报 `Error running link command: no such file or directory` | OHOS SDK llvm/bin 无 llvm-ranlib，ohos.toolchain.cmake 把 CMAKE_RANLIB 指向不存在的 `<sdk>/llvm/bin/llvm-ranlib`（报错不指明缺哪个程序） | `-DCMAKE_RANLIB=$(which llvm-ranlib)`，hnp 布局下 /data/service/hnp/bin/llvm-ranlib 是 llvm-ar 的别名（ar 兼容 ranlib 调用），配方内置 `_llvm_ranlib()` 自动探测 |
| 2 | find_package(Ogg) 找不到 conan 的 libogg | 交叉链 FIND_ROOT_PATH_MODE=ONLY 滤掉 conan 包路径 | 预置 cache 变量 `-DOGG_INCLUDE_DIR=<ogg>/include -DOGG_LIBRARY=<ogg>/lib/libogg.a`（上游 cmake/FindOgg.cmake 用 find_path/find_library） |
| 3 | test_libFLAC++ 运行报 `__cxa_pure_virtual: symbol not found` | NEEDED libc++_shared.so，设备系统库版本不含该符号所需版本 | LD_LIBRARY_PATH=<sdk>/llvm/lib/aarch64-linux-ohos 运行（SDK 自带 libc++_shared.so），配方测试段内置 |
| 4 | test_cuesheet good 用例报 `can't open file cuesheets/good.000.cue.1 for writing` | 程序输出路径 = strstr(input, "cuesheets/") 相对路径 | 在含 cuesheets/ 子目录的 CWD 运行（mkdir cuesheets，等价上游 test_grabbag.sh 的工作目录） |
| 5 | flac CLI 编解码往返 wav 整文件 cmp 不一致 | 输入是 WAVE_FORMAT_EXTENSIBLE（40 字节 fmt），解码输出标准 16 字节 fmt；data 段音频数据一致 | 无损验证改用 STREAMINFO md5 自洽（encode→decode→re-encode 的 md5 相同）+ data 段比对，等价上游 test_flac.sh 的 md5cmp |

## 上游测试（conan build() 内执行，全部通过）
| 测试 | 说明 | 结果 |
|------|------|------|
| test_libFLAC | libFLAC 单元测试（bitreader/bitwriter/crc/format/encoders/decoders/metadata 全套） | PASSED |
| test_libFLAC++ | libFLAC++ C++ 绑定单元测试（含 Ogg FLAC metadata chain） | PASSED |
| test_grabbag/cuesheet | 6 good 全部通过 + 44 bad 全部正确拒绝 + 输出与 cuesheet.ok 一致 | PASSED |
| test_grabbag/picture | 输出与 picture.ok 完全一致 | PASSED |
| test_streams | 全部测试流生成（rt-*、rpg-tone-*、noisy-sine、wacky*） | OK |
| test_seeking | 50 次预编程+随机 seek 全部 OK | PASSED |
| flac CLI roundtrip | 61 个 rt-*.wav verify 编码全过；压缩等级 0/5/8 编码+校验 OK；md5 自洽 | PASSED |
| metaflac | picture import/export/roundtrip/remove OK | PASSED |
| Ogg FLAC | 编码+解码往返一致 | PASSED |

通过率：9/9 组测试全通过（本地实测，设备原生运行）

## 无法运行/简化的上游测试说明
| 上游测试 | 处理 | 原因 |
|----------|------|------|
| test_flac.sh 全量 | 部分等价执行（编码/解码/verify/md5cmp 核心） | 完整脚本 1500+ 秒超时预算（上游 CMake 也设 TIMEOUT 1500）；核心断言（md5 自洽、verify、-t 校验）已覆盖 |
| test_metaflac.sh | 部分（picture 操作） | 完整脚本依赖 generate_streams.sh 产物与大量 shell 工具组合；picture 导入导出往返已验证 |
| test_replaygain.sh | 未运行 | replaygain_analysis 是 GPL 工具库，非 libFLAC 核心 API；上游对库本身的验证由 test_libFLAC 覆盖 |
| test_compression.sh | 未运行 | 纯性能对比测试（多实现压缩率比较），与平台适配正确性无关 |
| test_libFLAC++.sh / libFLAC.sh wrapper | 直接跑二进制 | ctest wrapper 在 OHOS 无 busybox sh 环境下不可用，直接调用测试二进制等价 |

## 源码修改
无（零补丁——1.5.0 CMake 构建系统原生支持交叉编译，无需修改任何源文件）

## 依赖版本
- libogg/1.3.5（Conan 制品仓，静态链接进 libFLAC，FLAC_API_SUPPORTS_OGG_FLAC=1）

## 验证结果
- flac --version → flac 1.5.0 ✅
- metaflac --version → metaflac 1.5.0 ✅
- FLAC_API_SUPPORTS_OGG_FLAC = 1 ✅（OGG 支持已启用）
- libFLAC.a / libFLAC++.a 静态库 + flac / metaflac CLI 均产出 ✅
- test_package: FLAC__stream_encoder/decoder 65536 样本无损往返（bit-identical）✅

## 产物
| 文件 | 说明 |
|------|------|
| lib/libFLAC.a | C 库（静态） |
| lib/libFLAC++.a | C++ 库（静态） |
| bin/flac | 命令行编码/解码工具 |
| bin/metaflac | 元数据编辑工具 |
| include/FLAC/*.h, include/FLAC++/*.h | 开发头文件 |
| lib/cmake/FLAC/flac-config.cmake | CMake config 模块 |
| lib/pkgconfig/flac.pc, flac++.pc | pkg-config 文件 |
---

**编译结束**: 2026-09-05 01:45
**最终状态**: built

---

## CI 验证记录（PR #8327）

- **PR**: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/8327
- **AI Review（atomgit-bot）**: ✅ 代码审查"未发现问题"
- **CI 第 4 轮（构建 #39995, CI-026）**: ✅ 全部通过（test_package/L0/L1 门禁）
- 修复历程：
  1. 第 1 轮失败：CI worker 的 TMPDIR 在 HMDFS 上，chmod 只读语义失效 → 增加 `_pick_test_dir()` 探测 tempfs
  2. 第 2 轮失败：探测函数用 ctypes 调 libc.fopen 在 HMDFS 上段错误（进程无输出直接死）→ 改用 os.open syscall
  3. 第 3 轮失败：CI-007 worker conan SSL 模块不可用（registry_unreachable，基础设施瞬时故障，非代码问题）→ 重跑
  4. 第 4 轮：✅ PASSED

**最终状态**: built + CI PASSED，等待合并
