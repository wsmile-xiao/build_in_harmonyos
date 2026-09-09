# pakchois 0.4 — 适配记录

> 上游: http://www.manyfish.co.uk/pakchois/pakchois-0.4.tar.gz
> sha256: d73dc5f235fe98e4d1e8c904f40df1cf8af93204769b97dbb7ef7a4b5b958b9a
> 工程类型: autotools (autoconf 2.61) + libtool; 纯 C 库 (libpakchois)

## 结论快照
- 产物: `libpakchois.so`(+.a/.la, libtool version-info 1:0:1 → soname .so.0)、
  头文件 → `include/pakchois/`、`pakchois.pc`。`package_type: library`，无 commands.json。
- 上游自动化测试: **0**。Makefile.am 无 TESTS；`test` 为 `noinst_PROGRAMS`
  手动/演示程序，运行期需真实 PKCS#11 token（离线/无 token 环境不可自动执行）。
- 反空壳验证: test_package 以 clang 编译 test.c 并运行 —— dlopen 打包目录
  `lib/libpakchois.so`，dlsym `pakchois_module_load` / `pakchois_get_info` /
  `pakchois_module_destroy` 三个真实导出符号。

## OHOS 关键适配（详见 conanfile.py build()/generate() 注释）
1. config.sub (2006-09-20) 无 aarch64 → build() 两处 replace 补入
   `aarch64 | aarch64_be`（裸 CPU 列表）与 `aarch64-* | aarch64_be-*`（带厂商名列表）。
2. `--build=aarch64-unknown-linux-gnu` 跳过 config.guess（无法猜 OHOS）。
3. `ac_cv_lib_pthread_pthread_mutex_lock=yes`、`ac_cv_lib_dl_dlopen=yes`
   跳过 configure.ac 的 AC_CHECK_LIB 实链（musl 已并入 libc）。
4. `--disable-nls` 处理 po/ gettext 子树。
5. configure/config.guess `umask 077`→`umask 022`；TMPDIR → conan build `_tmp`。

## 验证记录（true-device Harmony verify 后回填）
- [ ] HARMONY_VERIFY conan create PASS
- [ ] test_package 探针输出确认
- [ ] L0/L1/L4/L5 / CI 结果
