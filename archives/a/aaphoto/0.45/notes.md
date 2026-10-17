# aaphoto 0.45 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，Autoconf 2.69 生成）
- 编译日期: 2026-08-05
- 编译器: clang 15.0.4（OHOS SDK，`/data/service/hnp/bin/clang`）
- 目标平台: HarmonyOS PC (OHOS) aarch64（conan profile: ohos-aarch64）
- 状态: built（conan-verify 全部门禁通过，尚未 CI release 上传）

## 编译步骤

1. 官方源码: `https://github.com/log69/aaphoto/archive/refs/heads/master.tar.gz`
   （GitHub master 分支即 v0.45；上游无 0.45 tag，2016-07-09 发布，sha256 见 conandata.yml）
2. `ohc-run.py init-build aaphoto 0.45 --url=<上述URL>` 下载并解压到 `~/tmp/builds/aaphoto-0.45.work`
3. 手工探索编译（VPATH 构建）:
   ```bash
   mkdir aaphoto-0.45-manual && cd aaphoto-0.45-manual
   export CONFIG_SHELL=$HOME/usr/local/bin/bash TMPDIR=$HOME/tmp CC=clang CFLAGS="-fPIC -O2"
   export CPPFLAGS="-I$DEPROOT/include -I$DEPROOT/include/libpng16" LDFLAGS="-L$DEPROOT/lib"
   ../aaphoto-0.45.work/configure --prefix=$HOME/usr/local && make -j1 && make install DESTDIR=...
   ```
   DEPROOT 为 libjpeg/libpng/zlib 预编译包的合并 include/lib 目录。
4. 功能验证: `aaphoto --version` 正常；对 2x2 BMP 执行 `aaphoto --png` 产出 `_new.png`。
5. `ohc-run.py conan-verify aaphoto 0.45` → G0/G1/G2/G3/G4 全部 PASS。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied`，configure 失败 | HMDFS 文件系统强制目录 setgid；autoconf 的 `umask 077 && mktemp -d` 生成 `drwx--S---` 目录，即使属主也无法写入（知识图谱 E114/E112/E118） | 补丁 0003-configure.patch：移除 configure 中 config.status 临时目录创建逻辑里的 `umask 077`，使 mktemp 用默认 umask 生成可写目录 |
| 2 | `clang -lgomp: unable to find library -lgomp` 链接失败 | 上游 Makefile.am 硬编码 GCC 专用 OpenMP 运行库 `-lgomp`；OHOS 无 libgomp | 补丁 0001/0002：从 AM_LDFLAGS 移除 `-lgomp`。clang 的 `-fopenmp` 自动链接 OHOS SDK 自带 `libomp.so` |
| 3 | `configure: error: cannot run C compiled programs`（conan create 中） | conftest 链接共享 `libpng16.so.16` 后运行失败：OHOS 动态加载器找不到 conan 缓存中的共享库 | conanfile.py `generate()` 中把依赖 libdir 加入 `LD_LIBRARY_PATH`（build scope），供 configure 运行 conftest 使用 |
| 4 | `make: jobserver mkfifo: ... Operation not permitted` | `make -j>1` 在 TMPDIR 创建 jobserver fifo 被拒（HMDFS）（E074） | 所有 make 调用固定 `-j1`（conanfile 中 `autotools.make(args=["-j1"])`） |

## 源码修改（补丁）

| 补丁 | 修改内容 |
|------|----------|
| 0001-Makefile.am.patch | `AM_LDFLAGS` 移除 `-lgomp` |
| 0002-Makefile.in.patch | `Makefile.in` 中 `AM_LDFLAGS` 移除 `-lgomp` |
| 0003-configure.patch | config.status 临时目录创建逻辑移除 `umask 077`（E114） |

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| libjpeg | 10 | ohpcd 制品仓 | JPEG 编解码 |
| libpng | 1.6.58 | ohpcd 制品仓 | PNG 编解码（共享库 libpng16.so.16） |
| zlib | 1.3.1.1 | ohpcd 制品仓 | 经 libpng 传递引入 |
| OpenMP (libomp) | — | OHOS SDK clang 自带 | `-fopenmp` 自动链接，无需额外依赖 |
| libgomp | — | 不适用 | OHOS 无此 GCC 运行库，已用补丁移除链接 |

> 注: 任务预检时提到可能用到 fftw，但 aaphoto 0.45 源码无任何 FFT 代码，实际不需要。

## 验证结果

```bash
# conan create（含 test_package 自动执行）
conan create archives/a/aaphoto/0.45 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 测试输出:
#   [test] aaphoto --version
#   ✅ --version OK
#   [test] aaphoto --png .../test-in.bmp
#   ✅ processed image produced (100 bytes)
```

- G2 conan create: ✅ PASS（日志: reports/conan-create.log）
- G3 系统同名库隔离: ✅ PASS
- G4 产物完整性: ✅ PASS（bin/aaphoto 单个可执行文件）

## 注意事项

- 本地禁用 conancenter remote（SSL 证书 hostname 不匹配，`conan remote disable conancenter`），仅使用 ohpcd。
- `Autotools.install()` 会追加 `-j{njobs}` 触发 jobserver fifo 告警，但不影响安装结果（非致命）。
- test_package 测试脚本需在 `$HOME/tmp` 建临时目录（OHOS `/tmp` 只读）。
- aaphoto.c 通过 `#include "aaio.c"/"aargb.c"/"aaresize.c"` 内联多文件，是单二进制应用，非库；`package_type=application`。
---

**编译结束**: 2026-08-05 11:25
**最终状态**: built
