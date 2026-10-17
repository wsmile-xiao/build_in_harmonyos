# tomsfastmath

TomsFastMath — a fast, portable, easy to use multiple-precision integer (bignum)
library by the libtom project (sister project of libtommath).

- 官方仓库：https://github.com/libtom/tomsfastmath
- 许可证：Apache-2.0（上游 LICENSE 为双许可条款，本包按 Apache-2.0 申报）
- 版本：0.13.1（标签 `v0.13.1`，commit `adf0549383e9d41cf7ec6aeb6b3ad6189d731488`）
- 目录结构：`archives/t/tomsfastmath/{version}/`（conanfile.py + conandata.yml + test_package/ + manifest.yaml + notes.md）
- 说明：上游 makefile 构建静态库 libtfm.a；配方直驱上游 makefile 并内嵌运行上游 demo 测试（stest/test）
