# openapv 0.2.1.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-10
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: published

## 编译步骤

1. 初始化: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build openapv 0.2.1.2 --url=https://github.com/AcademySoftwareFoundation/openapv/archive/refs/tags/v0.2.1.2.tar.gz`
2. cmake 配置: `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DARM=TRUE`
3. 构建: `make -j1`
4. 安装(staging): `make install DESTDIR=$TEST_PREFIX`
5. 测试: `ctest` — 16/16 全部通过
6. 打包: `python3 $SKILL_ROOT/scripts/ohc-run.py package openapv 0.2.1.2`
7. 本地安装验证: `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接失败：undefined symbol: oapv_tbl_fn_sad_16b_neon 等 NEON 函数 | cmake 检测 CMAKE_SYSTEM_PROCESSOR=unknown（HarmonyOS 不被 cmake 识别），未自动启用 ARM/NEON 支持 | 重新 cmake 配置时加 `-DARM=TRUE`，手动启用 NEON 源文件编译 |

## 源码修改

无补丁，仅需 cmake 参数 `-DARM=TRUE`。

## 依赖版本

无外部依赖

## 验证结果

```bash
ctest --output-on-failure
# 16/16 tests passed, 0 tests failed
# Total Test time: 10.27 sec
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| oapv_app_enc | 203200 | 编码器可执行文件 |
| oapv_app_dec | 162240 | 解码器可执行文件 |
| liboapv.so | 137600 | 共享库 |
| liboapv.a | 185200 | 静态库 |
| oapv.h | 31749 | 公共头文件 |

## 注意事项

- cmake 在 HarmonyOS 上检测 `CMAKE_SYSTEM_PROCESSOR=unknown`，不会自动匹配 ARM 处理器模式，必须手动指定 `-DARM=TRUE`
- oapv_port.c 有 void pointer cast 警告（u32），不影响功能
- 该软件版本号在 oapv.h 中定义为 0.2.1.1，但 tarball 标签为 v0.2.1.2（可能是打包错误或小版本未更新头文件）
---

**编译结束**: 2026-06-10 22:47
**最终状态**: published
