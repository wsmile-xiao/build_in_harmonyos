# pakchois 0.4 — 适配记录

> 上游: https://www.manyfish.co.uk/pakchois/pakchois-0.4.tar.gz
> sha256: d73dc5f235fe98e4d1e8c904f40df1cf8af93204769b97dbb7ef7a4b5b958b9a
> 工程类型: autotools (autoconf 2.61) + libtool; 纯 C 库 (libpakchois)

## 结论快照
- 产物: `libpakchois.so`(+.a/.la, libtool version-info 1:0:1 → soname .so.0)、
  头文件 → `include/pakchois/`、`pakchois.pc`。`package_type: library`，无 commands.json。
- 上游自动化测试: **0**。Makefile.am 无 TESTS；`test` 为 `noinst_PROGRAMS`
  手动/演示程序，运行期需真实 PKCS#11 token（离线/无 token 环境不可自动执行）。
- 反空壳+行为验证: test_package 以 clang 编译 test.c 并运行 —— dlopen 打包目录
  `lib/libpakchois.so`，dlsym 真实导出符号后**经函数指针真实调用**（8 断言）：
  ① `pakchois_module_load`/`pakchois_error`/`pakchois_module_destroy` 符号存在（R34）；
  ② `pakchois_module_load` 负路径（无 provider）返回 `CKR_GENERAL_ERROR` 且
  `*module` 保持 NULL —— 完整走通 provider_mutex 加锁 → MODPATH 遍历 →
  dlopen 失败 → 错误码传播；③ `pakchois_error` 错误表 3 分支
  （CKR_OK / CKR_GENERAL_ERROR / CKR_VENDOR_DEFINED）。

## OHOS 关键适配（详见 conanfile.py build()/generate() 注释）
1. config.sub (2006-09-20) 无 aarch64 → build() 两处 replace 补入
   `aarch64 | aarch64_be`（裸 CPU 列表）与 `aarch64-* | aarch64_be-*`（带厂商名列表）。
2. `--build=aarch64-unknown-linux-gnu` 跳过 config.guess（无法猜 OHOS）。
3. `ac_cv_lib_pthread_pthread_mutex_lock=yes`、`ac_cv_lib_dl_dlopen=yes`
   跳过 configure.ac 的 AC_CHECK_LIB 实链（musl 已并入 libc）。
4. `--disable-nls` 处理 po/ gettext 子树。
5. configure/config.guess `umask 077`→`umask 022`；TMPDIR → conan build `_tmp`。

## 验证记录
- [x] HARMONY_VERIFY conan create PASS —— 2026-09-10 OHOS aarch64 profile 原生
  构建：`conan create . --name=pakchois --version=0.4 -pr:h/-pr:b=
  ci/conan/profiles/ohos-aarch64` → package `01d92cf349a0dd98ff915f4bd99a04430171517f`
  （recipe revision `637d8f1f…`），编译零警告，libtool 正常。
- [x] test_package 探针输出确认 —— 运行期真实输出（8/8 PASS，exit 0）：
  ```
  dlopen …/lib/libpakchois.so ok
  PASS: symbol pakchois_module_load present (R34)
  PASS: symbol pakchois_error present (R34)
  PASS: symbol pakchois_module_destroy present (R34)
  PASS: pakchois_module_load(missing provider) == CKR_GENERAL_ERROR (mutex -> MODPATH scan -> dlopen fail -> error propagation)
  PASS: *module unchanged on load failure (no dangling handle published)
  PASS: pakchois_error(CKR_OK) == "OK"
  PASS: pakchois_error(CKR_GENERAL_ERROR) == "General error"
  PASS: pakchois_error(CKR_VENDOR_DEFINED) == "Vendor defined error" (vendor-defined branch)
  pakchois: ok (symbols + behavior verified) (0 failure(s))
  ```
- [x] test_package 修复验证（2026-09-11，本地 CI 同款命令）—— 此前 L1 曾死于
  主配方 `os.environ["TMPDIR"]` 经 conan create 同进程泄漏到 test_package（指向主包
  打包后已被 conan 删除的 `build/_tmp`，clang `unable to make temporary file`）。
  修复：test_package build() 开头显式 `TMPDIR=<本包 build_folder>/tmp`（仓库惯例
  celt / p11-kit-server）。验证命令：`conan create … -pr:h/-pr:b=
  ci/conan/profiles/ohos-aarch64 --build=missing --build=pakchois/*`（强制同进程
  重建主包复现泄漏场景）→ exit 0，test 编译无临时文件错误，探针 8/8 PASS。
- [ ] L0/L1/L4/L5 / CI 结果 —— 待 CI 流水线回填

## 集成约束（下游必读）
- **MODPATH 为编译期烘焙**：`PAKCHOIS_MODPATH` 默认 `${libdir}:${libdir}/pkcs11`，
  本包 `prefix=/` → 实际烘焙为 `//lib://lib/pkcs11`（strings 实测）。运行时
  provider 必须落在 `/lib` 或 `/lib/pkcs11` 之一，按
  `lib<name>pk11.so` / `<name>-pkcs11.so` / `<name>.so` / `lib<name>.so`
  四种候选名 dlopen（pakchois.c suffix_prefixes）；传绝对路径会被拼成
  `//lib/<abs path>` 而失效。这是上游 2008 设计，按系统库定位（prefix=/）语义自洽。
- 产物含 libtool `.la` 文件（含构建期绝对路径，无功能影响）。
- 头文件安装于 `include/pakchois/`（pkg-config `Cflags: -I${includedir}/pakchois`），
  消费方 include 写 `#include <pakchois/pakchois.h>`。

## 测试限制与方案否决记录（R51 三步法）
- ①清点：Makefile.am 无 `TESTS`/`check_PROGRAMS`；官方 tarball 预生成
  Makefile.in 中 `check: check-recursive` 为 automake 空转（`grep '^TESTS'
  Makefile.in` 为空）→ 自动化测试 **0**；唯一 `test` 为 noinst 手动演示
  （运行期需真实 PKCS#11 provider）。
- ②运行：上游 `test` 离线不可运行（无 token）——具体技术原因而非借口。
- ③增强方案 A（test_package 内置 stub provider fixture 走正向链路）**已否决**：
  实测 `/lib -> /system/lib` 为 OHOS 只读系统分区（touch/mkdir 均
  Read-only file system），无法向编译期烘焙的 MODPATH 目录注入 fixture .so；
  改走**增强版方案 B**（当前 test.c）：不伪造 token，以负路径行为测试
  覆盖 加载/错误传播 链路 + 错误表，正向链路（槽位/会话/对象转发）留待
  真机具备真实 token 时补充验证。
