# libmstoolkit — mass spectrometry data toolkit

[MSToolkit](https://github.com/mhoopmann/mstoolkit) 是一个轻量级 C++ 质谱数据处理库，
提供统一的谱图数据结构，以及 mzML、mzXML、MGF、MS1/MS2 和二进制 MS 格式的读写能力。

## HarmonyOS 适配

- 使用 Conan 配方显式调用 profile 中的 `clang++` 和 `llvm-ar`，绕过上游 Makefile
  硬编码的 `g++`、`gcc` 与 `ar`。
- 不编译上游捆绑的旧版 Expat、SQLite 和 zlib，改为链接仓库已发布的
  `expat/2.8.2.1.1`、`sqlite3/3.49.1`、`zlib/1.3.2`。
- 保持上游 `rev82` 的完整 MSToolkit 与 mzParser 源文件集合，产出静态库
  `libmstoolkit.a` 和公开头文件。
- 上游没有测试套件；`test_package` 增加真实 MS2 文件写入/读取回环测试，以及
  一个只在 `__OHOS__` + AArch64 下编译的独立文件系统回环测试。

## Conan 使用

```text
libmstoolkit/82
```

CMake 消费目标为 `libmstoolkit::libmstoolkit`。

## 许可证

实际编入静态库的源码包含 Apache-2.0、BSD-2-Clause、Artistic-1.0-Perl 与 Zlib
授权代码。配方将 Apache-2.0、BSD-2-Clause 标准全文、README 及对应上游原始
版权/许可通知一并安装到 `licenses/`；独立 Conan 依赖继续保持各自许可证。
