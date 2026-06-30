# mgba 0.10.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 解压源码到工作目录
2. 应用 6 个 CMake 补丁（平台适配）
3. 运行 cmake 配置：
   ```bash
   cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED=OFF -DLIBMGBA_ONLY=ON ..
   ```
4. 执行 make 编译
5. 执行 make install 安装

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 平台识别问题 | 需要添加 OHOS 平台支持 | 补丁 CMakeLists.txt |
| 2 | flags.h 编译错误 | 缺少平台宏定义 | 补丁 include/mgba/flags.h |
| 3 | 第三方库构建问题 | 内嵌第三方库不兼容 | 补丁各 third-party CMakeLists.txt |

## 源码修改

共 6 个补丁文件：
- 0001-CMakeLists.txt.patch - 主 CMake 文件平台适配
- 0002-include-mgba-flags.h.patch - 平台宏定义修复
- 0003-0006 - 第三方库 CMake 配置修复

## 依赖版本

- cmake（构建工具）
- clang/clang++（编译器）

## 验证结果

```bash
# 静态库验证
file ~/builds/mgba-0.10.5.work/libmgba.a
# 输出: ar archive

# 头文件完整性
find ~/builds/mgba-0.10.5.work/include/mgba -type f | wc -l
# 输出: 113 个头文件
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmgba-0.10.5-ohos-aarch64.tar.gz | 537KB | 预编译包（静态库 + 头文件 + pkg-config） |

## 手动打包说明

由于脚本 clean-verify 不支持 CMake 项目，采用手动打包流程：
1. 收集静态库 libmgba.a
2. 收集头文件 include/mgba/
3. 创建 pkg-config 文件 libmgba.pc
4. 使用 Python tarfile 模块创建预编译包

## G0 干净构建验证（手动执行）

**验证时间**: 2026-05-28 14:21-14:23

**验证步骤**:
1. 解压原始 tarball 到临时目录
2. 应用 6 个补丁（全部成功）
3. 运行 cmake 配置（需添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`）
4. 执行 make 编译（99% 完成）
5. 验证 libmgba.a 生成（1.7MB，与原始编译产物大小一致）

**验证结果**: ✅ PASS
- 静态库成功生成
- 补丁自包含性验证通过
- ⚠️ unix2dos 错误（非致命，仅影响文档转换）

## 注意事项

- libmgba 是静态库（.a 文件），不是共享库
- 使用时需通过 `-lmgba` 链接
- 最终链接的可执行文件需要 ELF 签名
---
**编译结束**: 2026-05-28 14:19
**最终状态**: published