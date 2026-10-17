# libevt 20240421 适配笔记

## 编译环境
- 构建系统: autotools（libyal 自包含发布包，自带 configure）
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15（aarch64-unknown-linux-ohos）
- 状态: built

## W0 依赖检查

libevt 是 libyal 自包含发布包：Debian orig tarball 内嵌 20 个本地 libyal 支撑库
（libbfio、libcdata、libcdirectory、libcerror、libcfile、libclocale、libcnotify、
libcpath、libcsplit、libcthreads、libexe、libfcache、libfdata、libfdatetime、
libfguid、libfvalue、libfwnt、libfwevt、libregf、libuna、libwrc），configure 输出
全部为 `local`，**无外部 Conan requires**。与先例 libfsntfs 20251028、libesedb
20240420 同形态。

上游 GitHub release 资产已被 libyal 清理（repo 仅保留 tags 20260523/20260705，
releases/download/20240421 返回 404），故使用 Debian archive orig tarball：
`https://deb.debian.org/debian/pool/main/libe/libevt/libevt_20240421.orig.tar.gz`
SHA-256 `984837219de4155b2fbe5817dea6ce737e39f36457e89511371b3cad0ab18606`。
包内 configure/config.guess/config.sub/Makefile.in 为上游发布包生成物。

## 编译步骤

```bash
# 本地探索（~/huawei/builds/libevt-20240421/src）
sed -i 's/umask 077/umask 022/g' configure   # E011: HMDFS 0700 临时目录拒绝
export CC=/data/service/hnp/bin/clang CONFIG_SHELL=/data/service/hnp/bin/bash
/data/service/hnp/bin/bash ./configure \
    --prefix=... \
    --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
    --disable-python --enable-static-executables=no
make -j4          # 全绿 0 error
make check        # 上游测试
```

## 上游测试结果（make check 实测）

上游 TESTS 注册 4 个顶层 shell runner（test_library.sh / test_tools.sh /
test_evtinfo.sh / test_evtexport.sh），内部驱动 check_PROGRAMS 注册的 19 个 C
测试程序：

| runner | 结果 | 内部 C 程序 |
|---|---|---|
| test_library.sh | **PASS** | 11 个：end_of_file_record/error/event_record/file_header/io_handle/notify/record/record_values/strings_array/file/support 全 PASS |
| test_tools.sh | **PASS** | 8 个：info_handle/message_handle/message_string/output/path_handle/registry_file/resource_file/signal 全 PASS |
| test_evtinfo.sh | SKIP (exit 77) | 发布包不含 tests/input/ 测试数据目录（上游标准形态），"Test input directory not found" |
| test_evtexport.sh | SKIP (exit 77) | 同上 |

Testsuite summary: TOTAL 4, PASS 2, SKIP 2, FAIL 0。
evtinfo --version 烟测输出 `evtinfo 20240421` 正常。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 创建 0700 临时目录被 HMDFS 拒绝 | E011 平台限制 | 构建期 sed 将 configure 内 `umask 077` 替换为 `umask 022` |
| 2 | 上游 GitHub release 404 | libyal 清理旧 release 资产 | 改用 Debian archive orig tarball（SHA256 固定） |
| 3 | /tmp 只读 | E002 | 日志/临时文件走 $TMPDIR |
| 4 | libtool wrapper 脚本在 OHOS 无法直接执行 | HMDFS 禁直接 exec | test_runner.sh 构建期补丁：解析 .libs/ 下真实 ELF 再执行（沿用 libfsntfs 先例） |

## 源码修改

无独立 patch 文件（patches/ 为空）。全部兼容处理限定在 Conan 配方构建期
（configure umask 替换、test_runner.sh 调度适配），源码包本身零修改。

## 依赖版本

- 零外部依赖（20 个 libyal 支撑库内嵌于上游发布包，闭包校验在 build() 首行）

## 验证结果

```bash
# 本地 make check 实测（OHOS aarch64 clang 交叉编译产物）
# TOTAL: 4 / PASS: 2 / SKIP: 2 / FAIL: 0
# test_library.sh: 11 C programs PASS
# test_tools.sh: 8 C programs PASS

# conan create + test_package 见 test-report.md
```

## 注意事项

- libyal 发布包是"多库合一"形态，未来若单独适配 libfvalue/libregf 等支撑库，本包不作为其依赖方
- evttools（evtinfo/evtexport）随库一起产出，commands.json 已声明
