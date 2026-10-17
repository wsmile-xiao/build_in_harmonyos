# liblzxcomp 20050705 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-16
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. init-build 下载源码 `lzx_compress.tar.gz`（SHA256 d63f046130677db666d6cec6f4a62349060928ec85b1feaf2fce9222293a95f7），
   镜像: `https://mirrors.ustc.edu.cn/freebsd-ports/distfiles/lzx_compress.tar.gz`
   （upstream 站 russotto.net 已不可用，此为 FreeBSD distfiles 官方镜像）。
2. lang-preflight: detected=c（源码全 C，无 configure，Makefile 直接出静态库）。
3. 原生 make 自检: `make -j1` → 产出 `liblzxcomp.a`（Makefile `all` 目标即 OBS2: lzx_layer_nonslide.o + lz_nonslide.o，`ar -q` + `ranlib`）。
4. conan 配方（makefile 模板）: conan create --profile ohos-aarch64 交叉编译。
   Makefile 无 `install` 目标，package() 用 copy 直取头文件与 `liblzxcomp.a`。
5. 应用补丁 0003-lzx_config.h.patch（大小端，见下）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `lzx_config.h` 用 `#if BYTE_ORDER == BIG_ENDIAN` 判断大小端 | 源树不含任何定义 BYTE_ORDER 的头（FreeBSD 下依赖 sys/types.h 链，OHOS/glibc 下未定义 → 两个未定义宏 `#if 0==0` 恒真 → 小端机误定义 LZX_BIG_ENDIAN，LZX 位流按大端写错） | 补丁改用 clang 内建宏 `__BYTE_ORDER__`/`__ORDER_BIG_ENDIAN__`，无头文件依赖（libc 探针，符合 R8 例外） |
| 2 | Makefile 无 install 目标 | 上游就是纯自用 Makefile | conan recipe package() 用 copy 手工放 include/ 与 lib/ |
| 3 | 文件名 `lzx_compress.tar.gz` 与软件名 liblzxcomp 不一致 | FreeBSD port DISTNAME 就叫 lzx_compress | conandata.yml 使用该 URL；strip_root 解出的顶层目录本身就叫 lzx_compress |
| 4 | 编译报 `u_char` 未定义 | BSD 风格类型，本库源码全量使用；OHOS/musl libc 无此类型（FreeBSD 下由 sys/types.h 提供） | lz_nonslide.h 开头补 `typedef unsigned char u_char;`（仅非滑动路径 TU 需要） |
| 5 | 运行测试堆崩溃 `free(): invalid pointer` / `memset` 段错误 | **64 位堆溢出上游 bug**：lz_nonslide.c:191 `memset(lentab,0,sizeof(*prevtab)*chars)` 用指针大小(8B)清 int 数组（应为 sizeof(*lentab)=4B），溢出 2 倍；上游仅在 32 位（int==int* ==4B）下意外正确 | 补丁改为 `sizeof(*lentab)`；aarch64/x86_64 必须修 |
| 6 | 静态库链接缺 `log` 符号 | lzx_layer.c 用 `log()` 需 libm | package_info 补 `system_libs=["m"]` |
| 7 | 上游 `lzx_test.c` 无法回归 | 2005 年发行包只提供手工 CLI 程序：无 `check` 目标、无断言、无退出码语义（统计仅打印到 stderr），`conan create` 不会跑到它 | 按仓库规范（`ci/tools/extract_upstream_tests.sh`）把上游测试源文件字节级复制进 `test_package/lzx_test.c`，以 `lzx_test2` 目标链接 `liblzxcomp.a`，在 `test_package/conanfile.py::test()` 中随每次 `conan create` 真实执行（OHOS aarch64 + 本地 x86_64 均通过） |

## 源码修改

- `patches/0003-lzx_config.h.patch`：lzx_config.h 大小端探测改用 clang 内建宏（详见上表 #1）。
- `patches/0002-lz_nonslide.h.patch`：lz_nonslide.h 补 u_char typedef（#4）。
- `patches/0001-lz_nonslide.c.patch`：lz_nonslide.c:191 修正 lentab 清零长度（#5，aarch64 必修）。

> 注：`ohc-run.py finish` 的 refresh-patch 步骤会把补丁按 `NNNN-<文件名>.patch` 统一重命名，
> 以上为最终归档名（与 conandata.yml 一致）。

## 依赖版本

- OHOS clang 15.0.7（/data/service/hnp/bin），Conan 2.29.1（OHOS 适配版），GNU make 4.3。
- 运行库无第三方依赖（仅 libm）。

## 验证结果

```bash
# 原生 x86_64 运行时验证（打全 3 个补丁后）：
$ cc -I. test_package/test.c liblzxcomp.a -lm -o /tmp/lzx_native_test && /tmp/lzx_native_test
compressed: 1372, uncompressed 524288
test liblzxcomp 20050705: OK (in=524288 out=1372)
# 未打 0001 补丁时同用例堆崩溃（memset 溢出）。

# 上游自测程序 lzx_test.c 原生运行（真实证据）：
$ cc -I. lzx_test.c liblzxcomp.a -lm -o /tmp/lzx_test
$ /tmp/lzx_test 15 < lzx_in.bin > lzx_out.bin        # lzx_in.bin = 288000B 重复模式
compressed: 852, uncompressed 294912, ratio 99.711100  （RC=0，out=856B）

# 上游自测程序现已纳入 test_package，随 conan create 在 CI（OHOS aarch64）每次真实执行：
#   test_package/lzx_test.c  = 上游 lzx_test.c 字节级副本（sha256 217d2002…dad2，未改动一行）
#   test_package/conanfile.py::test() 执行 "lzx_test2" 15 < upstream_in.bin > upstream_out.bin
# 本地 x86_64 端到端 conan create 复现（退出码 0）：
liblzxcomp/20050705 (test package): RUN: "./lzx_test2" 15 < "./upstream_in.bin" > "./upstream_out.bin"
compressed: 896, uncompressed 163840, ratio 99.453125
liblzxcomp/20050705 (test package): upstream lzx_test.c: PASS (in=145600 out=900, ratio 99.38%)
# 完整命令与原始输出见 reports/upstream-test-evidence.md

# OHOS aarch64 交叉构建（ohc-run.py conan-verify --profile ohos-aarch64）：
G1/G0/G2/G3/G4 + L2/L4/L5 全 PASS；test_package 编译+链接通过（运行放真机/CI）。

# L1e 破坏性反向验证本地同构复现：移走包产物 lib/ 与 include/ 后
#   conan test → "CMake Error: Library 'lzxcomp' not found in package" → 退出码 1
#   （证明测试真实依赖被测包，非空壳）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| 无（静默库直接进 conan 包，无独立打包产物） | - | - |

## 注意事项

- 包名/库名 `lzxcomp`（链接 `-llzxcomp`，产物 `liblzxcomp.a`），与包名 liblzxcomp 不同，package_info 已显式设置。
- 仅静态库：Makefile 不产出 .so（FreeBSD 的 .so 由额外 Makefile.bsd 打，本适配不引入）。
- 原始版本 2005-07-05（ChangeLog 2002 年，版本号即 FreeBSD port PORTVERSION）。
---

**编译结束**: 2026-09-16 12:52
**最终状态**: built
