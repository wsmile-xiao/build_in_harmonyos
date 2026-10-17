# packaging 说明 — boost1.84-iostreams 1.84.0

打包产物（.tar.gz / .sig）由 CI release 流水线在 PR 合并后生成并上传制品仓，
源码仓不入库（.gitignore `archives/**/packaging/*.tar.gz`）。

本地验证产物：
- `libboost_iostreams.a`（file_descriptor/mapped_file/zlib/gzip/bzip2 五 TU
  手动编译，带上游 Jamfile 要求的 BOOST_IOSTREAMS_USE_DEPRECATED）
- 完整 boost/ 头文件树（组件包自包含）

依赖（Conan 传递链接）：
- zlib/1.3.1（zlib/gzip 压缩后端）
- bzip2/1.0.8（bzip2 压缩后端）

消费方式：
```bash
conan install --requires=boost1.84-iostreams/1.84.0 -pr=<ohos-aarch64 profile>
```
CMake 下游：
```cmake
find_package(boost1.84-iostreams REQUIRED CONFIG COMPONENTS iostreams)
target_link_libraries(app PRIVATE boost1.84-iostreams::iostreams)
```
