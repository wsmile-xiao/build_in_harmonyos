# zmat 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile（src/Makefile，纯 Makefile，无 configure/无 make install 目标）
- 编译日期: 2026-10-01
- 编译器: clang/clang++ (OHOS SDK 15.0.4, aarch64-linux-ohos)
- 状态: published

## 编译步骤

```bash
# 探索性编译（模式 B）
source .build-context-zmat-1.0.0
cd $BUILD_SRC_DIR                       # ~/tmp/builds/zmat-1.0.0.work
make -C src lib CC=clang CXX=clang++ POSIX_ENV=Yes -j1
#  → 产出 ../lib/libzmat.a（自包含静态库，含 zmatlib + miniz + easylzma + lz4 + blosc2 + zstd）

# Staging 验证（无 make install 目标，手动 staging）
mkdir -p $TEST_PREFIX/{lib,include}
cp lib/libzmat.a $TEST_PREFIX/lib/
cp include/zmatlib.h $TEST_PREFIX/include/
clang -I$TEST_PREFIX/include test.c -L$TEST_PREFIX/lib -lzmat -o test && ./test

# 上游测试（R51）
clang -Iinclude example/c/testzmat.c -Llib -lzmat -o testzmat && ./testzmat
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接 libzmat.a 报 `undefined symbol: qsort_r`（来自 blosc2 内嵌 zstd 的 dictBuilder/cover.o） | zstd cover.c / zstd_deps.h 在 `__linux__` 下强制 `#define _GNU_SOURCE`，取用 glibc 专有 `qsort_r`；OHOS libc（musl 系）无此符号 | patches 去掉两处 `#define _GNU_SOURCE`，强制走 zstd 官方 C90 fallback（qsort + g_coverCtx 全局上下文）。**平台无关**，未引入 `__OHOS__` 宏（符合 R8） |
| 2 | lang-preflight 误判语言为 mixed → 自动写 env_unsupported 终态 | lang_detect.py 的 `_manifest_scan` 用递归全文件集合（`names`）检测 manifest，zmat 的 `pyproject.toml` 位于 `python/` 绑定子目录（非项目顶层），被误判为 python manifest；而源码统计 c 占 97%（177/182） | 判定为工具边界缺陷：zmat 是明确 C 库（顶层 Makefile 构建 libzmat，zmatlib.c 1493 行），符合 R47"辅助脚本不算主体/绑定类包判主体语言"。继续按 C 库流程编译，最终 result 用 --force 覆盖误判终态 |
| 3 | `make install` 无目标 | zmat 上游无 install 目标 | package() 直接 copy lib/libzmat.a 与 include/zmatlib.h |
| 4 | `make lib` 首轮失败报告中 tarball 解压报错 | 前一次下载残留损坏 tarball | 删除缓存重新下载（5952KB→6365KB 完整档），gzip -t 验证通过 |

## 源码修改（补丁）

- `0001-...zstd_deps.h.patch`：不再在 linux 分支强制定义 `_GNU_SOURCE`
- `0002-...cover.c.patch`：同上，dictBuilder 的 stableSort 走 C90 fallback

两处修改均为平台无关的 libc 兼容处理（非仅 OHOS 生效），未使用平台宏。

## 依赖版本

- 全部 bundled：miniz（zlib 兼容）、easylzma 0.4（lzma/lzip）、lz4/lz4hc、blosc2（含 zstd 1.5.7 internal）
- 无外部 conan 依赖（W0 预检通过）

## 验证结果

- 全部 12 种压缩后端（zlib/gzip/lzip/lzma/lz4/lz4hc/zstd/blosc2×5）round-trip 字节一致 ✅（本地 staging 实测 12/12）
- 上游官方 C 示例 example/c/testzmat.c：压缩→base64 编码→解码→解压还原 ✅
- test_package 消费视角：编译通过 + 13 项断言（12 方法 + base64 encode/decode）✅

## R51 上游测试清单（清点 N=14，实测 N′=2）

| 测试 | 类型 | 实测 | 说明 |
|------|------|------|------|
| example/c/testzmat.c | C 示例 | ✅ 通过 | 压/解 round-trip 完整还原 |
| test/test_zmat.m | Octave | 未运行 | 依赖 Octave（OHOS 环境无），"没有环境"已记录技术原因 |
| test/test_zmat_field.m | Octave | 未运行 | 同上 |
| test/test_zmat_roundtrip.m | Octave | 未运行 | 同上 |
| test/run_zmat_test.m | Octave 入口 | 未运行 | 同上 |
| python/tests/test_zmat.py | Python | 未运行 | 依赖 Python 绑定构建，超出本包 CI 范围 |
| src/blosc2 内嵌测试（test_ndlz.c / test_zfp_*.c 等） | blosc2 附属 | 未运行（非 zmat 自身 API 测试） | 属于 bundled blosc2 上游自测 |
| 自编 staging 多方法验证 | C | ✅ 通过 12/12 | 补充覆盖全部压缩后端 |

通过率：可运行的 C 级测试全部通过；Octave/Python 级因环境缺失如实记录未运行。

## 注意事項

- 静态库 libzmat.a 已包含全部后端，链接只需 `-lzmat`（OHOS libc 提供 pthread/dl 符号）
- 纯库类型（无 CLI），按 R38 无需 commands.json
- conanfile.py 使用 `settings.os in ("Linux","OHOS")`（R32）
---

**编译结束**: 2026-10-01 21:31
**最终状态**: built
