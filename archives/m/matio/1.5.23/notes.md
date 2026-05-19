# matio 1.5.23 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：从SourceForge下载源码包
2. 修改config/config.guess和config/config.sub添加HarmonyOS识别
3. 使用CMake构建（autotools在HarmonyOS上有临时目录权限问题）：
   ```bash
   cmake -DCMAKE_BUILD_TYPE=Release \
         -DMATIO_MAT73=OFF \
         -DMATIO_WITH_HDF5=OFF \
         -DMATIO_SHARED=OFF \
         -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
   make -j2
   make install DESTDIR=$HOME/tmp/test-install-matio-1.5.23
   ```
4. 预编译包制作：ohc-run.py package matio 1.5.23
5. 本地安装验证：matdump --help 运行正常

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess无法识别HarmonyOS | HarmonyOS是新系统，不在GNU config已知列表 | 修改config/config.guess添加HarmonyOS检测分支 |
| 2 | autotools临时目录权限问题 | HarmonyOS对某些临时目录有权限限制 | 使用CMake构建系统替代autotools |
| 3 | 共享库链接器符号文件问题 | LLVM链接器不支持GNU风格的符号文件 | 编译静态库(-DMATIO_SHARED=OFF) |
| 4 | HDF5依赖缺失 | MAT73格式需要HDF5库 | 禁用MAT73和HDF5支持 |

## 源码修改

- `0001-config-config.guess.patch`: 添加HarmonyOS系统识别
- `0002-config-config.sub.patch`: 同步更新config.sub

## 依赖版本

无外部依赖（禁用了HDF5）

## 验证结果

```bash
$ ~/usr/local/bin/matdump --help
Usage: matdump [OPTIONS] FILE
  -v,--verbose    verbose output
  -H,--header     print header information
  ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| matio-1.5.23-ohos-aarch64.tar.gz | 462KB | 预编译包（静态库+头文件+工具） |
| matio-1.5.23-ohos-aarch64-debug.tar.gz | 35KB | 调试符号包 |

## 注意事项

1. 本软件编译为静态库，避免LLVM链接器兼容性问题
2. MAT73格式支持已禁用，如需支持需先编译HDF5
3. CMake构建系统比autotools更适合HarmonyOS

---

**编译结束**: 2026-05-19 16:02
**最终状态**: built