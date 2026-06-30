# boost 1.76.0 适配笔记

## 编译环境
- 构建系统: 手动编译（绕过 b2）
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built（成功）

## 核心问题

boost 使用的 b2 (Boost.Build) 构建系统在鸿蒙上存在严重兼容性问题：
- b2 SHELL 命令执行失败
- 平台架构检测失败
- mkdir 命令在 b2 中失败

## 解决方案

**手动编译源文件绕过 b2**

```bash
# 编译单个库的所有源文件
for src in libs/<libname>/src/*.cpp; do
    clang++ -c "$src" \
        -I. \
        -DBOOST_<LIBNAME>_SOURCE \
        -DBOOST_<LIBNAME>_NO_LIB \
        -fPIC \
        -std=c++14 \
        -o ~/tmp/boost_manual_build/$(basename "$src" .cpp).o
done

# 创建静态库
ar rcs libboost_<libname>.a *.o
```

## 编译成功的库

| 库名 | 大小 | 编译参数 |
|------|------|---------|
| atomic | 36KB | -DBOOST_ATOMIC_SOURCE -Ilibs/atomic/src |
| chrono | 587KB | -DBOOST_CHRONO_SOURCE |
| thread | 1.1MB | -DBOOST_THREAD_BUILD_LIB=1 -pthread |
| serialization | 7.2MB | -DBOOST_SERIALIZATION_SOURCE |
| filesystem | 1.7MB | -DBOOST_FILESYSTEM_SOURCE |

## 测试验证

所有库通过功能测试：
- filesystem: ✅ 文件路径操作成功
- thread: ✅ 线程创建、运行、join 成功
- chrono: ✅ 时间记录成功
- serialization: ✅ 序列化/反序列化成功

## 参考知识

- E099: b2 构建系统无法识别 OHOS 平台

## 注意事项

1. 手动编译方法需要指定正确的包含路径和编译定义
2. boost.thread 需要 -pthread 参数
3. 编译时会有 deprecated 警告（旧 C++ 特性），但不影响功能
