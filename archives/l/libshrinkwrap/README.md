# libshrinkwrap (shrinkwrap)

## 简介
header-only C++11 压缩流封装库：以 std::streambuf/iostream 形式读写
xz / gzip(zlib) / zstd / BGZF 四种压缩格式，支持 seek（xz 走 lzma index、
BGZF 走虚拟偏移）与 `shrinkwrap::istream` 魔数自动探测。是 statgen/savvy、
Minimac4 等基因分析工具的依赖库。

## OHOS 适配
- header-only：包内容为 5 个头文件，无编译产物，`package_id` 与平台无关
- 上游裸 `find_library` 的三个链接依赖改为 Conan requires：
  xz/5.8.3.2、zlib/1.3.2.1、zstd/1.5.7.1
- 上游 `install(EXPORT)` 烧录构建机绝对路径，不采用；消费接口由
  `shrinkwrap::shrinkwrap`（CMakeDeps）提供
- 无源码补丁；上游测试 scratch 写在 cwd，不受只读根文件系统影响

## 依赖
- xz (liblzma)、zlib、zstd（链接期；由 Conan 依赖图传递）

## 功能验证
```c++
shrinkwrap::istream is("file.gz");        // 自动探测格式
shrinkwrap::bgzf::istream bg("f.bgzf");   // 虚拟偏移 tellg/seekg
```
`conan create` 时自动编译并运行上游 11 个 ctest 用例（33 条子链）与
23 条断言的消费者测试。

## 版本
- 1.2.0: built (2026-09-27)，真机 shadow CI 通过：上游 11/11、消费者 23/23、L0/L1/L4 pass（L2 skip 无 bin、L5 warn header-only 无 bin/lib 属预期）

## 参考
- 上游: https://github.com/jonathonl/shrinkwrap
- 许可证: MIT
