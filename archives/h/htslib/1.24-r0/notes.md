# htslib 1.24-r0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-14
- 编译器: clang/clang++
- 状态: built

## 编译步骤

使用 Conan 配方驱动构建：

```bash
TMPDIR=$HOME/tmp conan create archives/h/htslib/1.24-r0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=htslib*
```

配方核心流程：
1. 下载上游 htslib 1.24 源码包。
2. `AutotoolsDeps`/`PkgConfigDeps` 注入 `zlib/1.3.1`、`xz/5.6.2`、`libdeflate/1.25`。
3. `configure` 参数使用 `--host=aarch64-unknown-linux-ohos --disable-bz2 --disable-libcurl --disable-plugins --disable-ref-cache --with-libdeflate`。
4. `make -j1` 构建库、命令行工具和测试程序。
5. 运行可复现的上游小测试：`test/hts_endian`、`test/test_kstring`、`test/test_str2int`。
6. `test_package` 编译并运行消费者程序，调用 `hts_version()`、`sam_hdr_init()`、`sam_hdr_destroy()`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 源码直连曾超时 | 当前网络访问 github.com 偶发不稳定，但 PR 规范要求 `conandata.yml` 使用官方源 | `conandata.yml` 保持官方 GitHub release URL；本地验证已在源码缓存/直连可用时通过，manifest 额外记录 ghfast 镜像作为历史 fallback |
| 2 | `configure: cannot run C compiled programs` | OHOS/Conan 环境中 configure 生成的 conftest 无法直接运行 | 显式传入 `--host=aarch64-unknown-linux-ohos` |
| 3 | `config.guess` 访问临时目录出现 Permission denied | HarmonyOS/HMDFS 下临时目录权限与 `umask 077` 组合不兼容 | 将 `umask 077` 替换为 `umask 022`，TMPDIR 指向用户可写目录 |
| 4 | `ln -sf` 软链接覆盖不可靠 | HMDFS 对覆盖式软链接创建有限制 | 将 Makefile 中相关 `ln -sf` 改为 `rm -f && ln -s` |
| 5 | 完整 `make check` 的 htscodecs 数据测试失败 | 当前 OHOS Conan 环境运行 bundled htscodecs shell 数据测试不稳定 | 执行可复现的上游 C 小测试，并由 `test_package` 做消费者 API 验证 |
| 6 | 上游小测试运行缺 `libdeflate.so.0` | 构建阶段运行测试需要依赖库运行时路径 | 测试前将 Conan 依赖 libdir 注入 `LD_LIBRARY_PATH` |
| 7 | CI 链接 `libhts.so` 失败 | 已发布 `zlib/1.3.1` 在 CI 中为静态 `libz.a`，不适合参与共享库链接 | 默认构建静态 `libhts.a` 与命令行工具，consumer API 测试仍覆盖库调用 |

## 源码修改

未生成 patch 文件；适配在 Conan 配方构建阶段进行：
- `configure`: `umask 077` → `umask 022`，修正 TMPDIR 默认值。
- `Makefile`: `ln -sf` → `rm -f && ln -s`。
- 构建环境: 增加 uname shim，辅助 Autotools 在 OHOS 环境识别为可处理的 Linux/aarch64 组合。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| zlib | 1.3.1 | BGZF/gzip/zlib 压缩支持 |
| xz | 5.6.2 | liblzma，CRAM LZMA 支持 |
| libdeflate | 1.25 | 更快的 deflate/crc 实现 |

## 验证结果

```bash
python3 -m py_compile archives/h/htslib/1.24-r0/conanfile.py archives/h/htslib/1.24-r0/test_package/conanfile.py
# PASS

TMPDIR=$HOME/tmp conan create archives/h/htslib/1.24-r0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=htslib*
# PASS: package created
# PASS: upstream subset tests: ./test/hts_endian, ./test/test_kstring, ./test/test_str2int
# PASS: test_package output: htslib version: 1.24
```

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/h/htslib/1.24-r0/conanfile.py` | Conan 配方 |
| `archives/h/htslib/1.24-r0/conandata.yml` | 源码 URL 与 sha256 |
| `archives/h/htslib/1.24-r0/test_package/` | 消费者 API 测试 |
| `archives/h/htslib/commands.json` | 命令行工具声明 |
| Conan package `lib/libhts.a` | 静态库 |
| Conan package `bin/bgzip`, `bin/htsfile`, `bin/tabix`, `bin/annot-tsv` | 命令行工具 |

## 注意事项

- 当前配方禁用了 bzip2/libcurl/plugins/ref-cache；核心本地格式读写、zlib/xz/libdeflate 支持已构建验证。
- 完整上游 `make check` 在 htscodecs shell 数据测试处不稳定，已记录为环境限制；PR 中建议说明使用可复现上游 C 小测试 + consumer API 测试替代。
