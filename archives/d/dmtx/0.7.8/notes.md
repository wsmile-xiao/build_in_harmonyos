# dmtx 0.7.8（libdmtx）适配笔记

> 包名说明：本件以 `dmtx` 为包名入库（短名入口——archives/l/libdmtx/0.7.5 保持不动，多包名并存）。这是 libdmtx 的版本跟进件（0.7.5→0.7.8）。

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | dmtx（= libdmtx，Data Matrix 条码编解码库） |
| 版本 | 0.7.8 |
| 上游 | https://github.com/dmtx/libdmtx（tag v0.7.8） |
| 构建系统 | CMake（上游原生；0.7.5 时代 autotools 不可用需配方内生成 CMakeLists——0.7.8 已原生自带） |
| 语言 | 纯 C，零外部依赖（仅 libm） |
| 许可证 | BSD-2-Clause |

## 二、上游验证（W0）
- tag v0.7.8 实存 ✅
- sha256：`2394bf1d1d693a5a4ca3cfcc1bb28a4d878bdb831ea9ca8f3d5c995d274bdc39`（本地下载实测一致）
- 依赖：无

## 三、OHOS 适配要点
1. **上游原生 CMake**：v0.7.8 自带 CMakeLists.txt（DMTX_SHARED/DMTX_STATIC 选项、PUBLIC_HEADER dmtx.h、install 规则齐全）——无需 patch 文件。
2. **双库形态处理**：上游默认 SHARED+STATIC 双开；按 Conan 惯例按 options 单形态构建（shared=False 默认静态）。
3. **libm**：target_link_libraries PUBLIC m——OHOS clang 链接正常，package_info 声明 system_libs=["m"]。
4. **上游时基分支 bug（关键发现）**：上游 0.7.8 CMakeLists.txt 丢失了 0.7.5 时代（配方内生成版）的 `check_include_file(sys/time.h)`/`check_function_exists(gettimeofday)` 检测——`HAVE_SYS_TIME_H`/`HAVE_GETTIMEOFDAY` 宏未定义，dmtxtime.c 落到 `#else` "Generic 1-second resolution" 分支（`DMTX_TIME_PREC_USEC=1000000`）→ `dmtxTimeAdd(t, 1)` 的 usec=1000 被提升为整秒直接加 sec，usec 永不进位（实测 `t0.usec=999000; dmtxTimeAdd(t0,1)` 返回 sec+1/usec=999000——数学错误）。上游 unit_test 的 timeAddTest FAIL(3) 即此因。**修复**：CMakeToolchain 注入 `CMAKE_C_FLAGS="-DHAVE_SYS_TIME_H=1 -DHAVE_GETTIMEOFDAY=1"` 走 gettimeofday 分支（OHOS/Linux 均有该函数）。本地 ctest 实测：修复前 1/2（test_simple 过/test_unit FAIL）→ 修复后 **2/2 全过**。

## 四、上游测试（test/ 目录）
- **N 口径（rule4）**：上游 test/CMakeLists.txt 注册 2 个 add_test：test_simple（simple_test/simple_test.c——内存内 encode→decode roundtrip）+ test_unit（unit_test/unit_test.c——timeAddTest）。**N=2**（`ctest -N` 实测 Total Tests: 2）。
- **本地执行方式**：独立源码树 `cmake -DBUILD_TESTING=ON` + `ctest`（交叉环境真实运行）。
- **本地实测结果（2026-09-18，aarch64 OHOS）**：**2/2 全过（100%）**——test_simple Passed 0.05s / test_unit Passed 0.04s（时基宏修复后；修复前 test_unit 因上游 CMake 检测缺失 FAIL(3)，详见三.4）。
- **consumer 验证**：test_package/test_dmtx.c 复刻 simple_test 的完整 roundtrip（encode→image copy→region find→decode→逐字节比对输出串），在 OHOS 交叉环境编译链接静态库后真实运行。

## 五、构建命令（复现）
```bash
conan create . -pr:h=~/.conan2/profiles/ohos-aarch64 -pr:b=~/.conan2/profiles/ohos-aarch64 --build=missing
```
