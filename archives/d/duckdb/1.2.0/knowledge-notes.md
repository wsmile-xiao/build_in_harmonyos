# DuckDB 1.2.0 编译知识点

## 构建系统适配

1. **CMake + Ninja优先**：在鸿蒙平台，CMake使用Unix Makefiles生成器会遇到编译器检测问题（try-compile失败）。使用Ninja生成器可成功通过编译器检测。

2. **RPATH设置**：需要设置 `-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON` 解决安装时RPATH重定位问题。

3. **Git版本信息**：从GitHub tarball下载的源码缺少git历史，duckdb会使用dummy版本号（v0.0.1），不影响功能。

## 编译配置

```bash
cmake -GNinja \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
  ..
ninja -j1
ninja install DESTDIR=$TEST_PREFIX
```

## 编译耗时

单线程编译约36分钟（2204秒），duckdb是一个大型C++项目。

## 产物

- duckdb CLI可执行文件（40M）
- libduckdb.so共享库（49M）
- 多个静态库（extension、第三方依赖）
- 预编译包大小：193M

## 功能验证

duckdb CLI工作正常：
- SQL查询执行
- 表创建和数据操作
- 数学计算
