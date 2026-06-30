# openfa 20231011.0.3 适配笔记

## 编译环境
- 构建系统: cmake（out-of-tree build）
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4
- 状态: published
- 平台: OpenHarmony / HarmonyOS aarch64（musl libc）

## 编译步骤

### 步骤1: cmake 配置
```bash
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DLIBM_LIBRARIES=m
```
- 配置耗时：~1s
- 结果：成功，生成 Makefile

### 步骤2: 编译
```bash
make -j2
```
- 编译 280 个 C 源文件（src/ 目录 + extra/ 目录）
- 生成 `libopenfa.a`（695KB 静态库）
- 编译测试程序 `t_openfa_c` 和 `t_version`
- 结果：成功，0 错误，0 警告

### 步骤3: DESTDIR 安装（staging）
```bash
make install DESTDIR=$TEST_PREFIX
```
- 安装 9 个文件到 `$TEST_PREFIX/$DEFAULT_PREFIX/`
- 包含头文件、静态库、cmake 配置、文档

### 步骤4: 测试
```bash
make test  # 即 ctest
```
- 2 个测试全部通过
- t_openfa_c: 验证库算法正确性 — Passed (0.03s)
- t_version: 验证版本号一致性 — Passed (0.02s)

### 步骤5: 预编译包制作
```bash
ohc-run.py package openfa 20231011.0.3
```
- 9 步打包流程完成
- 产物：`openfa-20231011.0.3-ohos-aarch64.tar.gz`（739KB）

### 步骤6: 本地安装验证
```bash
make install  # 无 DESTDIR，安装到 $DEFAULT_PREFIX
```
- 安装到 `~/usr/local/`，验证用户可用

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置失败: `LIBM_LIBRARIES` set to NOTFOUND | HarmonyOS/musl 平台上 libm 是 libc 的一部分，不存在独立的 libm.so 或 libm.a 文件，CMake `find_library(m)` 在标准搜索路径中找不到 libm，返回 NOTFOUND | 传递 `-DLIBM_LIBRARIES=m` 给 cmake 命令行。因为 find_library 在缓存变量已设置时不会覆盖，且 `-lm` 链接在 musl 上实际生效（数学符号在 libc 中） |

## 源码修改

无源码修改。无需补丁。仅需在 cmake 配置时传递 `-DLIBM_LIBRARIES=m` 参数。

## 依赖版本

- 无外部依赖（仅需 libc 中的数学库 libm）

## 验证结果

### 单元测试（真实输出）
```
100% tests passed, 0 tests failed out of 2
Total Test time (real) =   0.05 sec
```

### 功能验证程序（真实输出）
```
[PASS] openfaCal2jd(2024,6,17) = 2460478.5 JD
[PASS] openfaJd2cal(2460478.5) = 2024-06-17
[PASS] openfaEpb(2460478.5) = 2024.460390 Besselian year
[PASS] openfaDat(2024) = 37.0 seconds (TAI-UTC)
[PASS] openfaGmst82(2460478.5) = 4.638062 rad (265.74 deg)
[PASS] openfaPm([3,4,0]) = 5.0
=== 总计: 6 通过, 0 失败 ===
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| openfa-20231011.0.3-ohos-aarch64.tar.gz | 739KB | 预编译包（静态库 + 头文件 + cmake 配置） |

## 注意事项

- openfa 是 SOFA 库的开源衍生版本（BSD-3 许可），函数前缀使用 `openfa` 而非 `iau`（如 `openfaCal2jd` 而非 `iauCal2jd`）
- 这是纯库包（library-only），不生成可执行文件，只有 `libopenfa.a` 静态库 + 3 个头文件
- musl 平台上 cmake 的 `find_library(m)` 会返回 NOTFOUND，需用 `-DLIBM_LIBRARIES=m` 覆盖（见知识图谱 E105 草稿）
- cmake 在 HarmonyOS 上报告 `System is unknown`，但不影响编译结果

---

**编译结束**: 2026-06-17 21:49
**最终状态**: published
