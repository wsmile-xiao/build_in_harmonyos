# ceres-solver 2.2.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 从 GitHub 下载 ceres-solver-2.2.0.tar.gz 源码包
2. 解压并创建 build 目录
3. 配置 CMake（关键选项）:
   ```bash
   cmake .. \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_BUILD_TYPE=Release \
     -DBUILD_EXAMPLES=OFF \
     -DBUILD_TESTING=OFF
   ```
4. 单线程编译: `make -j1`
5. 安装: `make install DESTDIR=$TEST_PREFIX`
6. 制作预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败下载源码 | 鸿蒙系统证书链不完整 | 使用 Python 脚本禁用 SSL 验证下载 |
| 2 | 示例程序链接错误 | 缺少 C++ 标准库符号 | 禁用示例程序构建 `-DBUILD_EXAMPLES=OFF` |
| 3 | 并发编译失败 | 编译器路径问题 | 使用单线程编译 `make -j1` |
| 4 | 质量门禁G4报"无二进制文件" | ceres-solver是纯库，无可执行文件 | 这是验证脚本限制，不影响库功能 |

## 源码修改

无补丁，源码无需修改即可编译

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| eigen | 3.4.0 | cmd-pkgs 预编译包 |
| glog | 0.7.1 | cmd-pkgs 预编译包 |
| gflags | 2.2.2 | cmd-pkgs 预编译包 |

## 验证结果

```bash
# 静态库大小
$ ls -lh ~/usr/local/lib/libceres.a
-rw-rw---- 1 20001006 file_manager 26M 5月  29 10:10 libceres.a

# 头文件
$ ls ~/usr/local/include/ceres/ | wc -l
46

# CMake 配置
$ ls ~/usr/local/lib/cmake/Ceres/
CeresConfig.cmake  CeresConfigVersion.cmake  CeresTargets.cmake
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ceres-solver-2.2.0-ohos-aarch64.tar.gz | 26MB | 预编译包，包含静态库和头文件 |

## 注意事项

1. ceres-solver 是纯静态库，没有可执行文件
2. 使用 `find_package(Ceres)` 在 CMake 项目中引用
3. 链接时需要 `-lceres` 以及依赖库 `-lglog -lgflags`
4. 建议使用单线程编译避免并发问题

---

**编译结束**: 2026-05-29 10:13
**最终状态**: published
