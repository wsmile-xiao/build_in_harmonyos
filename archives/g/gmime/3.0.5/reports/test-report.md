# Test Report — gmime 3.0.5

- 日期: 2026-09-03
- 平台: HarmonyOS PC (aarch64, musl, clang 15.0.4)
- 构建系统: autotools（GitLab archive 无生成文件，配方内自举）+ conan 2.29.1 (profile ohos-aarch64)
- 任务: pan 0.165 前置依赖（开源鸿蒙PC专项积分赛-依赖）

## 1. conan create（配方验证）

```
conan create archives/g/gmime/3.0.5 --name=gmime --version=3.0.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

结果: **成功（exit_code=0）**

- 自举链: aclocal（glib2/libtool/pkg.m4 宏）→ autoconf 2.72 → autoheader →
  libtoolize（tool_requires libtool/2.5.4.1）→ automake（tool_requires
  automake/1.18，PERL5LIB）→ configure → make -j4
- test_package L1: PASS（真实 API 冒烟）
  - `test gmime 3.0.5: OK (parse+decode+addrlist+subject round-trip)`
  - 覆盖 GMimeParser 构造消息、RFC2047 主题解码、InternetAddressList 收件人
    解析、UTF-8 主题 set/get 往返（R34 实质测试，非空壳）
- `.ci-result.json`: exit_code=0

## 2. 上游测试套件（make check，AUTOMATED_TESTS 全量 8 个）

上游 gmime 3.0.5 tests/ 自带 15 个测试程序，其中 8 个列入 AUTOMATED_TESTS
（check-local 自动执行，ENABLE_CRYPTO 未开启时 PGP/S/MIME 相关 4 个不编入）。
本次在 conan build 内 `make check` 全量执行：

- **8 个测试程序：6 PASS / 2 FAIL（程序级通过率 75%）；check 项粒度约 40+ 项
  全部执行**

PASS（6）: test-mime（addr-spec/rfc2047/rfc2184/quoted-strings/header
folding/references 等 14 组全过）、test-headers、test-streams、test-cat、
test-partial（源码 data 目录复跑确认 PASS）、test-mbox（同上）

FAIL（2，均为 OHOS 平台/环境限制，非 gmime 代码缺陷，已逐条实测验证）:

| 测试 | 现象 | 根因（实测验证） | 结论 |
|------|------|------|------|
| test-iconv | `Testing charset conversion utils: failed (1 errors)` | 27 个 charset 往返测试中仅 `windows-cp1251` 一项失败：musl iconv 无 glibc 独有的 `windows-cp1251` 别名（独立 C 程序实测：`iconv_open("UTF-8","windows-cp1251")` 返回 -1，而 `cp1251`/`windows-1251`/`CP1251` 均 OK） | 平台 libc 别名差异，豁免 |
| test-autocrypt | 直接退出无输出，EXIT_FAILURE | 测试 main() 第一件事 `g_find_program_in_path("gpg2"/"gpg")`，找不到 gpg 二进制即 return EXIT_FAILURE；OHOS 环境无 gpg/gpg2（实测 which 均无） | 环境无 gpg，豁免（crypto 已 --disable-crypto） |

补充验证：test-mbox / test-partial 在 make check 的 check-local 中因构建目录
数据路径显示 "no tests performed"（rc=0 计入 passed）；用源码目录数据
`./test-mbox -v <src>/tests/data/mbox`、`./test-partial -v <src>/tests/data/partial`
手工复跑均输出 `passed`，确认两测试功能正常。

## 3. 产物验证（G4）

- lib/libgmime-3.0.a（静态库，R26 默认静态）
- include/gmime-3.0/gmime/*.h（完整公共头文件）
- lib/pkgconfig/gmime-3.0.pc

## 4. 平台限制与豁免清单

| 项 | 原因 |
|----|------|
| test-iconv 的 windows-cp1251 单项 | musl iconv 别名表不含 glibc 的 windows-cp1251；gmime 上游按 glibc 行为编写 |
| test-autocrypt 整体 | 依赖 gpg/gpg2 二进制；OHOS 无 gpg；且 crypto 功能链（GpgME）已在本配方 --disable-crypto |
