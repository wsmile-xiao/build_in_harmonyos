# libconfuse 3.3 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，tarball 自带生成文件）
- 编译日期: 2026-09-10
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18, target aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 探索编译（显式 GNU triplet 跳过 config.guess OHOS 探测）
./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
    --prefix=/storage/Users/currentUser/usr/local --enable-static --disable-shared
make -j1
make check   # 24 项：22 PASS / 2 FAIL（OHOS 平台限制，见下）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type` | 2018 版 config.guess 不识别 HarmonyOS（uname -s=HarmonyOS），bundled config.sub 无 *-linux-ohos | 显式传 `--build/--host=aarch64-unknown-linux-gnu` 跳过探测（abiword/libfstrm 先例） |
| 2 | config.status 报 `./confXXXXXX/subs1.awk: Permission denied` | HMDFS 把 mktemp 创建的 0700 目录投影为不可写 drwx--S---（E114/E046） | 补丁 0001：configure 临时目录改用 mkdir 创建 |
| 3 | 上游测试 2 项 FAIL | quote_before_print 用 tmpfile()（/tmp 只读返回 NULL）；print_filter 用 fmemopen()（OHOS musl 写缓冲不回读，探针实测 buf 为空） | 均为 OHOS 平台限制，非库缺陷；22/24 PASS 如实回填 |

## 源码修改

- `patches/0001-configure-tmpdir-mkdir.patch`：config.status 临时目录 mktemp → mkdir（HMDFS 权限投影）

## 依赖版本

- 无第三方运行时依赖（configure.ac 仅检查标准头；AM_PROG_LEX 用系统 flex 2.6.4 生成 lexer，tarball 已含 lexer.c）

## 验证结果

```bash
make check   # 24 项：22 PASS / 2 FAIL（平台限制）
# test_package 消费者测试：cfg_init/cfg_parse_fp/cfg_getstr/cfg_getint/cfg_print 全链路
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（Autotools，显式 triplet，静态默认，cmake target libconfuse::libconfuse） |
| conandata.yml | 官方源 URL + sha256 + 补丁声明 |
| patches/0001-configure-tmpdir-mkdir.patch | HMDFS 临时目录修复 |
| test_package/ | 消费者测试（真实 API 调用）+ MANIFEST.yml（上游 24 项测试申报） |
| manifest.yaml / notes.md | 版本级元数据与适配笔记 |

## 注意事项

- libtool 构建 libconfuse.so（SONAME libconfuse.so.2）；库名 `confuse`，头文件 `confuse.h`
- 系统 flex 2.6.4 可生成 lexer；tarball 自带 lexer.c，无需 tool_requires
---

**编译结束**: 2026-09-10 10:59
**最终状态**: built
