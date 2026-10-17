# mashmap 3.1.3 适配笔记

## 编译环境

- 构建系统: cmake（上游 CMakeLists.txt，C++17）
- 编译日期: 2026-10-02
- 编译器: clang/clang++（OHOS NDK 15，target aarch64-linux-ohos）
- 目标平台: HarmonyOS PC aarch64（`os=OHOS os.version=6.0 arch=armv8 compiler=clang 15 compiler.libcxx=libc++ compiler.cppstd=17 build_type=Release`）
- 本地验证 profile: `ohos-aarch64-wsl`（`-pr:h` 与 `-pr:b` 同 profile，与 CI 一致）
- 状态: built

## 编译步骤

```bash
# W3 本地硬门槛验证（与 CI 同 profile）
conan create archives/m/mashmap/3.1.3 --name=mashmap --version=3.1.3 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
```

配方在 `generate()` 里做的四件事：

1. `OPTIMIZE_FOR_NATIVE=OFF` —— 上游默认 ON，Release 下会追加 `-march=native`；
2. `USE_HTSLIB=OFF` —— 可选 htslib 依赖，保持依赖图只有上游无条件链接的 gsl 与 zlib；
3. `SKIP_VERSION_FILE=ON` —— 跳过配置阶段那条依赖 `git describe` 的脚本；
4. `CMAKE_SYSTEM_NAME=Linux` +（OHOS 时）`CMAKE_SYSTEM_PROCESSOR=aarch64` —— 绕开 Conan 把
   `os=OHOS` 映射成 CMake 不认识的系统名 `HarmonyOS` 的问题（E092）。

此外 `generate()` 里额外实例化了 `CMakeDeps`（补丁引入的 `find_package` 需要它生成的配置包）
与 `VirtualBuildEnv`（build() 要执行刚链接出来的 aarch64 二进制，需要 gsl/zlib 的运行时搜索路径）。

`build()` 在编译完成后执行上游测试程序集（见「验证结果」）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Could not find a package configuration file provided by "gsl"` | 配方只生成了 `CMakeToolchain`，没有 `CMakeDeps`；补丁引入的 `find_package(gsl CONFIG REQUIRED)` 在 toolchain 文件里找不到 `conan_cmakedeps_paths.cmake`，因此没有任何配置包路径 | `generate()` 中补 `CMakeDeps(self).generate()` |
| 2 | 上游 `target_link_libraries(mashmap gsl gslcblas m pthread z)` 在交叉构建下既缺 include 目录也缺库路径 | 裸库名只在依赖恰好落在系统默认库搜索路径时可用；交叉构建的依赖被 stage 在 sysroot 之外 | 补丁改为 `find_package(gsl CONFIG REQUIRED)` / `find_package(zlib CONFIG REQUIRED)`，链接 `gsl::gsl` / `zlib::zlib` |
| 3 | `SKIP_VERSION_FILE` 未关时配置阶段执行 `scripts/generate_git_version.sh` | 该脚本跑 `git describe`，release tarball 没有 git 元数据必然失败 | 配方显式 `SKIP_VERSION_FILE=ON`；额外核实 `src/` 下无任何文件 include 它生成的 `mashmap_git_version.hpp`（全树 grep 只命中生成脚本与 CMake option 文案这 2 处），跳过无功能损失 |
| 4 | `mashmap -v` 的输出为空，误判为「没打印版本」 | MashMap 通过 logger 打印版本，走的是 **stderr** 而不是 stdout | 版本断言改为读 stdout+stderr 合并流 |
| 5 | 上游第三个测试 `scripts/test.sh` 无法执行 | 该脚本 shell out 到 `bedtools`（sort/merge/intersect），是 x86_64 Linux 专用二进制，既不在 OHOS SDK/NDK 内也无法在 aarch64 目标上跑 | 按脚本的算术 1:1 复算：PAF 的 query 区间并集长度 ÷ .fai 序列长度，阈值沿用上游的 0.92 |
| 6 | 消费者用例拿不到上游 `data/scerevisiae8.fa.gz`（25711390 字节） | `conan create` 的 test_package 里 `self.tested_source_folder` 属性不存在（Conan 2.29.1），test_package 无法访问被测配方的 source 目录 | test_package 自行用 xorshift64 生成确定性合成数据集（6 contig / 2.2Mb / 3% 替换），不往仓库里塞 25MB 固件 |
| 7 | 合成数据集用 bgzip 风格的 `.gz.fai` 后 `mashmap` abort：`std::invalid_argument: stoul: no conversion` | `mapQuery()` 用 `std::ifstream` + `std::stoul` 读 `<query>.fai` 第二列，.fai 必须是**明文**；上游 `data/scerevisiae8.fa.gz.fai` 也是明文，被压缩的是 `.gzi` | .fai 以明文写在 `.fa.gz` 旁边 |
| 8 | 按 SAM 规范解析 `mashmap-align` 输出会全量误判 | 它写的不是标准 SAM：没有 `@HD/@SQ/@PG` 头行，CIGAR 被拼在最后一列的 `kc:f:<x> <score> <CIGAR>` 里 | test_package 按上游实际格式校验（记录数、`id:f:`、CIGAR 合法性与参考跨度一致性） |
| 9 | CI #68290（CI-019）test_package 阶段 python `posix_spawn` 执行 `p/bin/mashmap` 报 `PermissionError: [Errno 1] Operation not permitted`（EPERM）；同一 worker 上 build 阶段直接执行 build 树同名产物 3/3 通过 | OHOS/HMDFS 上由 `cmake install` 直接落地的可执行文件带内核级「不可执行」标记（非 POSIX 权限位，chmod 无效，与文件内容无关）；mmsd-tng 2.6.4 已实测同款（知识草稿 `mmsd-tng-2.6.4-meson-install-executable-eperm`，`error_signature` 完全命中） | `package()` 在 `cmake.install()` 之后用 `copy()` 把 `build_folder/bin` 的两个产物重新复制到 `package_folder/bin`（新建 inode → 新属性），先例即 mmsd-tng 2.6.4 的已合并修法 |

## 源码修改

- `patches/0001-cmake-resolve-gsl-and-zlib-via-config-packages.patch`
  —— 只改 `CMakeLists.txt`：在 `add_compile_options(-Wfatal-errors)` 之后插入两个
  `find_package(... CONFIG REQUIRED)`，并把两个 `target_link_libraries` 块里的
  `gsl` / `gslcblas` / `z` 换成 `gsl::gsl` / `zlib::zlib`。
  零 `.cpp`/`.hpp` 改动，零平台宏（不含 `__OHOS__`）。

## 依赖版本

| 依赖 | 版本 | 制品仓状态 | 用途 |
|------|------|-----------|------|
| gsl | 2.8 | 已发布（`conan download gsl/2.8 -r=ohpcd --only-recipe` 成功） | `gsl_cdf_binomial_Q` / `gsl_ran_hypergeometric_pdf` 等显著性过滤统计量 |
| zlib | 1.3.1.2 | 已发布（同上验证） | gzstream 层的 `gzopen` / `gzread` |

上游还有一个可选依赖 htslib（`USE_HTSLIB`），本配方保持关闭，未纳入依赖图。

## 验证结果

```bash
conan create archives/m/mashmap/3.1.3 --name=mashmap --version=3.1.3 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
# → 退出码 0，package_id d70f6d801b925ac1047c67ded4c4620deb4d6168
```

上游测试程序集（`.github/workflows/build-and-test.yml` 的 3 个 step，build() 内执行）：

| 上游用例 | 执行方式 | 实测结果 |
|----------|----------|----------|
| 1. `build/bin/mashmap -v` | 直接执行 | 打印 `3.1.3` |
| 2. 酵母自比对（`--pi 95 -n 1 -Y '#'`） | 直接执行（`--threads 2` 替代 `$(nproc --all)`） | PAF 1037538 字节 / 9236 条记录 / 136 条 contig 全部被比对；参考索引 61.6s + 比对 23.6s（x86_64 构建机 qemu-user 模拟下） |
| 3. `scripts/test.sh <fai> <paf> 0.92` | 等价复算（bedtools 不可用，见问题 5） | 最低覆盖度 0.9419 ≥ 0.92 |

消费者用例（`test_package/test_mashmap.py`）：断言数由脚本在运行时实测并按分组打印
（`_require()` 把每次断言登记进 `RECORDED`，循环内的按记录逐次计数），最后一次实测：

```text
  functional/version-banner: 2 assertions
  functional/align-usage: 5 assertions
  functional/end-to-end-mapping: 115 assertions
  harmonyos/elf-profile: 8 assertions
mashmap consumer checks passed, 130 assertions
```

| 类别 | 实测断言数 | 内容 |
|------|-----------|------|
| 功能 | 2 | `mashmap -v` 退出码 + 版本横幅行（合并 stdout+stderr） |
| 功能 | 5 | `mashmap-align -h` 退出码 + `--mappingFile` / `--perc_identity` / `--threads` / `--output` 四个选项面 |
| 功能 | 115 | 合成数据集端到端：PAF 逐记录校验（12 列、名称在 `.fai` 内、坐标不越界、链方向、`id:f` 恒等度 ≥ 0.95、6/6 contig 双向命中）+ SAM 逐记录校验（记录数与 contig 数相等、`id:f` ≥ 0.95、CIGAR 正则、CIGAR 参考跨度与记录跨度一致）+ 数据集/退出码/聚合断言 |
| **鸿蒙特有** | **8** | 两个产物的 ELF 头，各 4 项：`e_machine == 0xB7 (AArch64)`、`PT_INTERP` 指向 OHOS musl 加载器、`DT_NEEDED` 非空且不含任何 glibc/libstdc++ SONAME、`DT_NEEDED` 含 musl 的 `libc.so` |
| **合计** | **130** | |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/mashmap | 6225016 字节 | ELF 64-bit PIE, ARM aarch64, interpreter `/lib/ld-linux-aarch64.so.1` |
| bin/mashmap-align | 5081312 字节 | 同上 |

`readelf -d bin/mashmap` 的 `DT_NEEDED`：`libgsl.so.28` / `libgslcblas.so.0` / `libc.so`
（zlib 符号被静态链接进来，因此没有 `libz.so` 运行期依赖）。

## 注意事项

- 本配方是纯命令行工具包（`package_type = "application"`），因此软件级目录
  `archives/m/mashmap/commands.json` 必需（R38）。
- `cross_building()` 在本仓 OHOS 同 profile 双传（`-pr:h` / `-pr:b` 同一个 profile 文件）时
  **恒为 False**；判定「要不要 qemu-user」必须看 `platform.machine()`，否则在 x86_64 构建机上会
  直接 exec aarch64 产物。与知识库草稿 `DRAFT-mapcode-2.5.7-cross-building-false` 同源。
- 本方案**不需要** `-static` 全静态链接：gsl 是共享库，且构建机已注册 `binfmt_misc` 的
  `qemu-aarch64`，配合 `VirtualBuildEnv` 提供的 `LD_LIBRARY_PATH` 即可直接运行。
  这也是与 mapcode 2.5.7 配方的一处差异，notes 里显式记录。
- 上游没有 unit test 框架（无 `tests/`、无 CTest 注册），测试程序集只有 CI workflow 里的 3 个 step；
  `scripts/test.sh` 依赖的 bedtools 在 OHOS 侧不可用，已按其算术等价复算，未修改上游任何文件。
- `mashmap-align` 输出的 SAM 不符合 SAM 规范（无头行、CIGAR 混在最后一列），
  下游消费者若要消费其输出需按上游实际格式解析。
- `package()` 在 `cmake.install()` 后把两个可执行文件从构建目录 re-copy 到
  `package_folder/bin`（见问题 9）：OHOS/HMDFS 上 install 动作落地的文件会被内核
  拒绝执行（EPERM），重新 copy 一份（新 inode）即可运行；re-copy 会保留构建树的
  RPATH，消费侧由 conanrun/hnp 的 `LD_LIBRARY_PATH` 解析 gsl，死 RPATH 条目由
  加载器跳过，不影响运行（mmsd-tng 2.6.4 同款交付形态）。
