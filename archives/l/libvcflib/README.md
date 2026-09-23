# libvcflib

`libvcflib` 是 **vcflib** 的 C++ 库部分：解析、比较、转换和统计 VCF（Variant Call
Format，变异调用格式）文件的库，附带上游同一源码树构建出的一整套 `vcf*` 命令行工具。

- 上游仓库：<https://github.com/vcflib/vcflib>
- 分发形态：`libvcflib.a`（静态归档）+ `include/vcflib/` 公开头文件；命令行工具安装在 `bin/`
- 许可证：MIT

## 功能概述

- VCF v4.x 头与记录的完整解析（`vcflib::VariantCallFile` / `vcflib::Variant`），
  含 INFO/FORMAT/sample 字段类型推断与有序写回
- 等位基因分解与重整（`parsedAlternates`、`flatAlternates`、`extendedAlternates`）
- 左对齐与 repeat 感知的 indel 规范化（`LeftAlign.hpp`、`Cigar`）
- 基于 WFA2（wavefront alignment）的 `vcfwave`/`vcfallelicprimitives` 等重排工具
- 群体遗传学统计（Fst / iHS / XP-EHH / ABBA-BABA 等）与 GWAS 相关小工具
- 通过 vendored tabixpp 支持 bgzip 压缩 + tabix 索引的区域查询
- 85 个可执行工具 + 36 个 `bin/` 下的脚本（`bed2region`、`bgziptabix`、`vcf2bed.py` …）

## OHOS 适配要点

| 主题 | 结论 |
|---|---|
| 构建入口 | **CMake**。顶层 `Makefile` 只是 cmake 包装（`cd build && cmake … && make && make install`），其 `make test` 目标已失效（指向不存在的 `tests/*.t`）；上游 CI 用 `cmake -DWFA_GITMODULE=ON .. && ctest`。 |
| 源码 tarball | 必须用 release 的 **`vcflib-1.0.12-src.tar.gz`**。GitHub 自动生成的 `archive/refs/tags/v1.0.12.tar.gz` 里 `contrib/*` 子模块目录与 `src/simde` **全为空**，配置期即报 `Cannot find source file: contrib/fastahack/Fasta.cpp`。 |
| vendored 依赖边界 | tabixpp、fastahack、smithwaterman、filevercmp、fsom、c-progress-bar、intervaltree、WFA2-lib 都在 `-src` 资产内并被真正编译；`googletest` 只在 `.gitmodules` 里、`CMakeLists.txt` 不引用，构建不需要。只有 htslib / zlib / bzip2 取自 OHOS 制品仓。 |
| 大小写不敏感文件系统 | HMDFS 下 `contrib/WFA2-lib/VERSION` 会被 `#include <version>` 命中，顶替 C++17 标准头（`unknown type name 'v2'`）。补丁改用 `-idirafter` 挂载该包含目录。 |
| OHOS libc 差异 | `contrib/fastahack/LargeFileSupport.h` 用 glibc 私有类型 `__off64_t`；OHOS 无该类型，改标准 `off_t`。 |
| 静态链接 | WFA2 取 `wfa2_static`：85 个命令行工具与 `libvcflib.a` 都静态链接 `libwfa2.a`，运行期不依赖 `libwfa2.so`（`readelf -d` 实测 NEEDED 只有 `libdeflate.so.0`/`libc++_shared.so`/`libc.so`）。包内**仍会**安装上游 WFA2 自己的 `lib/libwfa2.so`（那是 WFA2 的安装规则；本包与消费者都不使用它，ConanDeps 按 `LIBRARY_TYPE=STATIC` 解析到 `libwfa2.a`）。 |
| 未启用特性 | `ZIG=OFF`（zig 仅用于 `vcfcreatemulti` 的新代码路径，OHOS 无 zig 工具链）；Python FFI 绑定 `pyvcflib` 不构建（ohpcd 无 pybind11，OHOS 无 pybind11 工具链）。 |

## 依赖关系

编译期（Conan，均取自 `ohpcd`）：

| 依赖 | 版本 | 用途 |
|---|---|---|
| `htslib` | 1.24-r0 | `src/Variant.h` → `<tabix.hpp>` → `htslib/*.h`；区域查询 |
| `zlib` | 1.3.1 | `find_package(ZLIB)` TYPE REQUIRED |
| `bzip2` | 1.0.8 | `${BZIP2_LIBRARIES}` 直接进链接行 |

运行期：静态链接，无额外 `.so` 依赖（工具链为 OHOS clang 15 / libc++）。

## 已知问题

- 上游 `VERSION` 文件在 v1.0.12 tag 上仍写着 `1.0.10`，所以编译期宏 `VCFLIB_VERSION`
  是 `"1.0.10"`；安装出的头文件不导出任何版本宏，消费者无法从库内取到版本号。
- `make test` 不可用（见上），上游测试一律通过 CTest 运行。
- Python FFI 与 zig 代码路径在本包未启用，对应 2 个上游 CTest 用例未运行（详见版本级
  `notes.md` 与 `test_package/MANIFEST.yml`）。

## 参考资料

- 上游仓库与文档：<https://github.com/vcflib/vcflib>
- 上游 CI 配置：`.github/workflows/ci_test.yml`
- VCF 规范：<http://samtools.github.io/hts-specs/VCFv4.2.pdf>
