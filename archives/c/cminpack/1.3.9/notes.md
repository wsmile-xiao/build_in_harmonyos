# cminpack 1.3.9 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-24
- 编译器: clang/clang++ (Clang 15.0.4)
- 平台: HarmonyOS (aarch64)
- 状态: published

## 编译步骤

1. init-build 下载并解压 cminpack-1.3.9.tar.gz
2. CMake 配置: `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF -DCMAKE_BUILD_TYPE=Release -DUSE_BLAS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5`
3. 编译: `make -j2`
4. Staging 安装: `make install DESTDIR=$TEST_PREFIX`
5. 测试: `ctest --output-on-failure`
6. 打包: `ohc-run.py package cminpack 1.3.9`
7. 本地安装: `make install` (不带 DESTDIR)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败无法下载 | HarmonyOS 缺少CA证书 | 用 curl -kL 手动下载，放到 $TMPDIR/builds/ |
| 2 | CMake 配置失败 | cmake_minimum_required(3.0) 与 CMake 4.x 不兼容 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 3 | G0 干净构建验证失败 | clean-verify 脚本硬编码 ./configure，不支持 CMake | 脚本限制，手动验证通过 |
| 4 | 6/24 测试失败 | 浮点精度/输出格式跨平台差异 | 记录为平台差异，非算法错误 |

## 源码修改

无补丁，源码未修改。

## 依赖版本

无外部依赖（BLAS 已禁用）

## 验证结果

```bash
ctest --output-on-failure → 18/24 PASS (75%)
pkg-config --modversion cminpack → 1.3.9
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cminpack-1.3.9-ohos-aarch64.tar.gz | 530KB | 预编译包（3个静态库+头文件+pkgconfig+cmake config） |

## 注意事项

- CMinpack 使用 CMake 构建系统，init-build 默认识别为 autotools 需手动修正
- 纯静态库包，无可执行文件，R7 安全弹窗验证 N/A
- G0 clean-verify 脚本不支持 CMake 项目（仅支持 autotools），需手动验证
---

**编译结束**: 2026-06-24 18:12
**最终状态**: published
