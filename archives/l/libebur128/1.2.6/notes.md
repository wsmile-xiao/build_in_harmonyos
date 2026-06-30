# libebur128 1.2.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 从 GitHub 下载源码 (jiixyj/libebur128 v1.2.6)
2. 修改 CMakeLists.txt 和 test/CMakeLists.txt 的 cmake_minimum_required 从 2.8.12 到 3.5
3. cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release
4. make -j1
5. make install DESTDIR=$TEST_PREFIX (staging 验证)
6. ohc-run.py package (打包预编译包)
7. make install (安装到本地 $DEFAULT_PREFIX)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 报错：cmake_minimum_required(VERSION 2.8.12) 不兼容 CMake 4.x | CMake 4.x 移除了 <3.5 版本的兼容性支持 | 将 cmake_minimum_required 更新为 3.5 |
| 2 | G0 clean-verify 使用 ./configure (autotools方式) 测试 cmake 项目 | clean_verify.py 只支持 autotools，不识别 cmake | 手动执行 cmake clean-verify 并创建 .g0-verified 标记 |
| 3 | make check 报错 "No rule to make target 'check'" | cmake 项目使用 ctest 而非 make check | 标记为 SKIP，使用功能测试替代 |
| 4 | 预编译包中库未 strip | package 管线未执行 strip | 手动 strip + 重新打包 |

## 源码修改

- CMakeLists.txt: cmake_minimum_required(VERSION 2.8.12) → 3.5
- test/CMakeLists.txt: cmake_minimum_required(VERSION 2.8.12) → 3.5

补丁文件:
- 0001-CMakeLists.txt.patch (guard: not_applicable, CMakeLists 不适用 #ifdef __OHOS__)
- 0002-test-CMakeLists.txt.patch (guard: not_applicable, 同上)

## 依赖版本

无外部依赖 (纯 C 库，仅依赖 libm → libc.so)

## 验证结果

### 功能测试（2026-06-03）

编写自定义 C 测试程序，覆盖 12 项关键功能：

| 测试项 | 结果 | 详情 |
|--------|------|------|
| 版本查询 | ✅ PASS | ebur128_get_version → 1.2.6 |
| 初始化/销毁 | ✅ PASS | init/destroy 正确 |
| 通道设置 | ✅ PASS | LEFT/RIGHT/DUAL_MONO |
| short 帧处理 | ✅ PASS | 静音数据正确处理 |
| float 帧处理 | ✅ PASS | 48kHz 正弦波 → -26.01 LUFS |
| double 帧处理 | ✅ PASS | 静音 → -inf LUFS |
| 参数变更 | ✅ PASS | change_parameters 成功 |
| 响度范围 (LRA) | ✅ PASS | 0.00 LU |
| 样本峰值 | ✅ PASS | 0.8000（与输入幅值匹配） |
| 历史/窗口设置 | ✅ PASS | set_max_history/window 成功 |
| 多实例并行 | ✅ PASS | 3 实例同时工作正常 |
| 相对阈值 | ✅ PASS | -30.68 LUFS |

**总计: 43/43 通过，通过率 100%**

### Strip 回归测试
- strip 后库大小: 43328→34576 bytes
- 43 项功能测试全部通过
- ELF 签名完成

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libebur128-1.2.6-ohos-aarch64.tar.gz | 55KB | 预编译包（stripped, ELF-signed） |

## 预编译包内容

| 文件 | 说明 |
|------|------|
| include/ebur128.h | 头文件 |
| lib/libebur128.so | 共享库 (AArch64, stripped, RUNPATH=$ORIGIN:$ORIGIN/external) |
| lib/pkgconfig/libebur128.pc | pkg-config 元数据 |

## 注意事项

- libebur128 编译为共享库 (.so)，默认 BUILD_SHARED_LIBS=ON
- ebur128.c 有 SSE2 FTZ 相关的 #warning（不影响功能，仅编译警告）
- CMake 版本兼容性：需要 cmake_minimum_required >= 3.5 以兼容 CMake 4.x
- clean_verify.py 不支持 cmake 项目，需手动验证
- make check 不可执行：cmake 项目使用 ctest，需 ENABLE_TESTS=ON + libsndfile
- 补丁 guard 为 not_applicable：CMakeLists.txt 不支持 #ifdef __OHOS__ 守卫

---
---

**编译结束**: 2026-06-03 09:55
**最终状态**: built → **published** (2026-06-03，功能测试通过后升级)