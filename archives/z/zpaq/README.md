# zpaq — 增量日志式命令行归档器

zpaq 是一个增量日志式命令行归档工具，用于创建、更新和提取增量压缩归档文件。

## OpenHarmony 平台关键说明

- **必须启用 NOJIT**: zpaq 的 JIT 编译器生成 x86 机器码，在 ARM/aarch64 平台上会导致 "Illegal instruction" (SIGILL)。必须编译时添加 `-DNOJIT` 禁用 JIT，使用解释模式。解释模式性能约为 JIT 模式的 1/2~1/3，但功能完全一致。
- **简单 Makefile 构建**: zpaq 使用简单 Makefile，不支持 autotools/cmake。编译参数通过 Makefile 变量覆盖（CXX、CXXFLAGS、CPPFLAGS）。
- **许可证**: Unlicense AND MIT AND 公共领域授权

## 编译参数参考

```makefile
CXX=clang++
CPPFLAGS+=-Dunix -DNOJIT
CXXFLAGS=-O2 -fPIC
```