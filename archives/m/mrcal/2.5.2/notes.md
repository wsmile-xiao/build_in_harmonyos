# mrcal 2.5.2 OHOS 适配记录

平台任务 `contrib-8989`，`mrcal 2.5.2`，`taskBranch=feat/mrcal-2.5.2`，路径 A。

## 源码

- Debian orig：`https://deb.debian.org/debian/pool/main/m/mrcal/mrcal_2.5.2.orig.tar.xz`
- `sha256 = e7ea976a5b70137fe98bea9ce11b1e334d4bf69bde9105410f73228faf6d1491`
- 构建框架 `mrbuild v1.16`（`codeload.github.com/dkogan/mrbuild/tar.gz/refs/tags/v1.16`，
  sha256 `f2ae97ce0b6a2d5bfab132a27757c269cb378c22bc4b5e1e0e36380abc954433`）。

## 构建（mrbuild）

- 生成 `cameramodel-parser_GENERATED.c`：`re2c cameramodel-parser.re > …`。
- 生成 `minimath/minimath_generated.h`：`perl minimath/minimath_generate.pl > …`。
- `make libmrcal.so` 与 4 个纯 C 测试目标。
- 依赖头/Lib 路径由配方从 `self.dependencies` 汇总后经 CFLAGS/LDFLAGS 传入。
  mrbuild 规定 `%FLAGS` **只能作环境变量**（不能作 make 参数）。
- 链接：`-ldogleg -lcholmod -lamd -lcolamd -lccolamd -lsuitesparseconfig -lopenblas -lpng -ljpeg -lm`。
  其中 `lapack/3.12.1` 由 `openblas/0.3.34` 提供实现（`libopenblas.so`，含 LAPACK）。

## 补丁（4 个）

| # | 文件 | 原因 |
|---|---|---|
| 0001 | `Makefile` | 去掉 `python-cameramodel-converter.c`（`#include <Python.h>`、`<numpy/arrayobject.h>`，仅 Python 绑定用；C 核心不引用其符号） |
| 0002 | `minimath/minimath_generate.pl` | 去掉 `List::MoreUtils::pairwise`（build-only CPAN），改等价的显式循环（输出一致） |
| 0003 | `mrbuild/Makefile.common.footer` | 注释 `-Wl,--default-symver`（GNU ld 专有选项，lld 报 `unknown argument`） |
| 0004 | `test/test-parser-cameramodel.c` | 硬编码 `/tmp/...` 改为相对路径（OHOS `/tmp` 不可写；这是**对上游测试的唯一修改**，仅路径，不改断言语义） |

另：Conan `stb_image` 包只装 `include/stb_image.h`，而 mrcal `#include <stb/stb_image.h>`；
`build()` 里建 `_stb_shim/stb/stb_image.h` 并把该目录加入头路径。

## 上游测试

`test.sh` 共 62 个测试条目（取数 `grep -c 'test/' test.sh`）：40 个 `test/test-*.py`、
5 个 C 程序等。本环境实跑 4 个**不需要 Python** 的 C 程序：

- `test/test-cahvor`（通过）
- `test/test-heap`（通过）
- `test/test-lensmodel-string-manipulation`（**30/30**）
- `test/test-parser-cameramodel`（**122/122**）

其余 Python 套件需要 CPython+numpy+scipy 与编译好的 `_mrcal` 扩展，本环境不具备，
已在 `test_package/MANIFEST.yml` 逐条声明。运行测试时 `LD_LIBRARY_PATH` 指向依赖库目录。

## 消费者测试

`test_package/test_mrcal.c`：用安装后的 `mrcal.h` + `libmrcal.so` 调
`mrcal_lensmodel_num_params/name/type_from_name`，9 项断言。

## 结果

- 真机 `conan create` 退出码 0；上游 4 个 C 程序全过（30 + 122 等），消费者 9/9。
