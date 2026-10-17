# cassbeam 1.1 适配笔记

## 编译环境
- 构建系统: autotools (预生成 configure + Makefile.in, in-tree)
- 编译日期: 2026-09-08
- 编译器: clang (Conan tools.build:compiler_executables, HMBS 真机 /data/service/hnp)
- 状态: built (待真机预检)

## 编译步骤

1. 源码: `cassbeam_1.1.orig.tar.gz` (Debian, sha256 `6731a091...`), tuna 镜像优先。
2. vendor FFTW 2.1.5 (`fftw_2.1.5.orig.tar.gz`, sha256 `f8057fae...`) 到
   `vendor/fftw-2.1.5`, 显式 triplet 绕过 config.guess,
   `--enable-static --disable-shared` 安装到 `build/vendor-install`。
3. cassbeam `sh ./configure --prefix=/` (CC/CFLAGS/LDFLAGS 预置 vendored
   fftw 头库目录 + glib/2.88.0 flags, PKG_CONFIG_PATH 指向 PkgConfigDeps 输出,
   TMPDIR/TMP/TEMP 指向 build/cfg-tmp, umask 022)。
4. `make -j1`, 手动 copy `cassbeam` 到 `package/bin` (跳过 `install -D`)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 要求 glib-2.0, 无则 AC_MSG_ERROR | 上游硬依赖 glib (g_assert/g_new 等) | conan requires glib/2.88.0 (已上传版本, 2.84.0 仅 built 不可解析) + PkgConfigDeps, PKG_CONFIG_PATH 注入 |
| 2 | vector-fftw.c 需 fftw.h/rfftw.h (FFTW2 API), registry 只有 fftw3 | fftw_create_plan 等 v2 API 与 v3 不兼容, Debian 用 fftw-dev 2.1.5 | vendor fftw 2.1.5 源码静态编译后链接, 不新增 conan 依赖 |
| 3 | config.status/configure 的 umask 077 + mktemp 0700 在 HMDFS 失败 | E011/E129 | source() sed umask 077→022, confstat 走 $TMPDIR, build 建 cfg-tmp |
| 4 | Makefile install 调 install -D | OHOS 精简环境缺 coreutils install | package() 手动 copy 二进制 |
| 5 | 无 make check/tests 目录 | 上游单二进制科学工具, 仅 README 手动示例 | MANIFEST 审计为 no_tests, test_package 跑 VLA 示例 |

## 源码修改

无补丁 (patches_applied 为空)。适配全部在 conanfile.py 环境注入完成。

## 依赖版本

- glib/2.88.0 (transitive_headers/libs, 制品仓已上传版本)
- zlib/1.3.1.1 (override only: glib 传递依赖的 zlib/1.3.1 在 conancenter 存在会抢占 remote 顺序, 拉取官方 CMake 配方在 OHOS 报 System unknown to cmake; 1.3.1.1 仅 ohpcd 有, 同源码 -fPIC 静态, gupnp/gtk4 同例)
- vendor fftw 2.1.5 (源码静态编译, 非 conan 依赖)

## 验证结果

```bash
# test_package/test.sh (3 断言, 与 HMBS_TEST_PACKAGE_RESULT discovered=3 一致)
bash test.sh
# 1. cassbeam input.in 正常退出且日志含 "has finished"
# 2. vla-1500MHz.illum{amp,phase,block}.pgm 非空
# 3. vla-1500MHz.params + vla-1500MHz.I.pgm 非空
```

上游测试: 无自动化套件, `HMBS_UPSTREAM_TEST_RESULT status:no_tests discovered:0 executed:0`
(见 test_package/MANIFEST.yml 审计)。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/cassbeam | Cassegrain 天线仿真 CLI |
| res/examples/vla/*.in | 上游示例输入 |
| licenses/LICENSE | GPL-2.0 |

## 注意事项

- FFTW2 vendor 构建增加约 1-2 分钟编译时间, 属一次性成本。
- VLA 示例 gridsize=120, 真机运行约数十秒, 输出 PGM 需判非空 (防静默通过)。
- 申请人: yinuoguo, 队伍: 干。
