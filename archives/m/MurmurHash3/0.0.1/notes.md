# MurmurHash3 0.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码下载: SMHasher 仓库 (commit 07bb4de10a63e8cc2e1724865454eba635742383)
2. 上游使用 hancho 构建系统，非标准 CMake/Autotools
3. conanfile.py 用自定义 CMakeLists.txt 替换上游的，仅构建 MurmurHash3.cpp
4. conan create 自动执行: cmake configure → cmake build → cmake install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游构建系统为 hancho，非标准 CMake | SMHasher 使用自定义构建工具 | 用自定义 CMakeLists.txt 替换上游 CMakeLists.txt，仅编译 MurmurHash3.cpp |
| 2 | 源码 URL 使用 refs/heads/master 不可重现 | 分支归档随上游推送变化 | 改为固定 commit SHA 07bb4de10a63e8cc2e1724865454eba635742383 |

## 源码修改

无补丁。conanfile.py build() 方法中用 save() 写入自定义 CMakeLists.txt 替换上游的。

## 依赖版本

无外部依赖，纯 C++ 单文件库。

## 验证结果

```bash
# conan create 验证通过
# 测试向量: MurmurHash3_x86_32("hello", 5, 0) = 0x248bfa47
# 测试向量: MurmurHash3_x86_32("", 0, 0) = 0
# 确定性检查: 两次计算同一输入结果一致
```

## 注意事项

- 上游 SMHasher 无 tag，使用 commit SHA 固定快照
- conanfile.py 中 BUILD_SHARED_LIBS 直接赋值为 self.options.shared，支持静态/动态库切换
---

**编译结束**: 2026-07-15 12:49
**最终状态**: built
