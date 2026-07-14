# charls 2.4.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-13
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **源码获取**: 从 GitHub 下载 charls 2.4.3 源码包 (tar.gz)
2. **Conan 配方**: 编写 `conanfile.py` (CMake 库模式, 参考 expat/2.8.2 + valijson/1.1.1)
3. **CMake 配置**:
   - 设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` (OHOS 适配)
   - 设置 `BUILD_SHARED_LIBS=OFF` (默认静态库)
   - 禁用 `CHARLS_BUILD_TESTS` + `CHARLS_BUILD_FUZZ_TEST` + `CHARLS_BUILD_SAMPLES`
   - 启用 `CHARLS_INSTALL=ON`
4. **CMake 构建**: `cmake.configure()` + `cmake.build()`
5. **打包**: `cmake.install()` 安装库文件 + 头文件 + CMake 配置
6. **测试**: test_package 编译 smoke test, 编码解码 8x8 灰度图像, 验证无损往返

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 OHOS 平台 | E092: CMake 未内置 OHOS 平台定义 | 设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` |
| 2 | profile 中编译器路径在本地不存在 | CI 环境 profile 引用了 HNP 特定路径 | 使用 `shutil.which()` 查找 clang/clang++ 并替换 toolchain 文件中的路径 |
| 3 | 上游测试需要测试数据文件 | 上游 charlstest 依赖 .raw/.ppm/.jls 测试数据 | 关闭 CHARLS_BUILD_TESTS, test_package 使用自带 smoke test |

## 依赖版本

- charls: 2.4.3 (C++14, 无第三方依赖)

## 验证结果

```bash
# test_package smoke test
./test_charls
# 预期输出:
# 编码成功, 压缩后大小: [N] 字节
# 解码成功, 尺寸: 8x8, 分量数: 1
# PASS: charls JPEG-LS 无损编解码验证通过
```

## 注意事项

- charls 是 C++14 库, 无第三方依赖, 构建简单
- 默认构建为静态库, 消费者需定义 `CHARLS_STATIC` 宏 (由 package_info 自动添加)
- 上游测试为单一 charlstest 可执行程序, 需测试数据文件, 未在鸿蒙平台运行
- charls 2.4.4 修复了 2.4.3 的安全漏洞 (GHSA-mqrg-gfc8-73ff), 后续可考虑升级
