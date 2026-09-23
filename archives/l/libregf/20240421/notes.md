# libregf 20240421 适配笔记

## 基本信息

- 上游：https://github.com/libyal/libregf（libyal，Windows NT Registry File 解析库）
- 版本：20240421（alpha 预发布，2024-04-21 发布）
- 源码包：libregf-alpha-20240421.tar.gz（1712056 字节）
- sha256：503875ffa9c8c357d1a7d503a0cebf85797cfb0f767f0a3d0bce1ca6bb926085
- 构建系统：Autotools（configure + make，捆绑 libcerror/libcdata/libbfio 等内部库）
- License：LGPL-3.0-or-later

## 上游测试审计（R51）

- tests/Makefile.am：check_PROGRAMS 共 28 个（regf_test_checksum、regf_test_data_block_key、regf_test_data_block_stream、regf_test_data_type、regf_test_dirty_vector、regf_test_error、regf_test_file、regf_test_file_header、regf_test_hive_bin、regf_test_hive_bin_cell、regf_test_hive_bin_header、regf_test_hive_bins_list、regf_test_io_handle、regf_test_key、regf_test_key_descriptor、regf_test_key_item、regf_test_multi_string、regf_test_named_key、regf_test_notify、regf_test_security_key、regf_test_sub_key_list、regf_test_support、regf_test_tools_info_handle、regf_test_tools_output、regf_test_tools_signal、regf_test_value、regf_test_value_item、regf_test_value_key）
- TESTS 共 4 个 shell 包装（test_library.sh、test_tools.sh、test_regfinfo.sh、test_regfexport.sh），另有条件单测 test_python_module.sh（本配方以 --disable-python 关闭，不计入）
- `make check` 生成 tests/test-suite.log（含 automake TAP 汇总 TOTAL/PASS/FAIL/SKIP），配方解析该文件输出 HMBS_UPSTREAM_TEST_RESULT
- pyregf Python 绑定测试不在本配方范围内（需完整 CPython 开发环境，库本体与 regftools 不依赖它）

## 配方决策

- `--disable-python`：pyregf 绑定需要完整 CPython 开发环境，真机/CI 均不保证，库本体与 regftools 不依赖它
- `--disable-nls`：NLS 仅影响工具提示信息翻译，需要外部 gettext/libintl；REGF 解析逻辑不依赖，关闭后零外部依赖
- 无外部 requirements：所有 libc* 依赖均随源码包捆绑（SUBDIRS 内编译），无需先发布依赖；构建期仅需 pkgconf 与 bash（tool_requires）
- 默认 shared=False，支持 --enable-static/--disable-shared 切换
- E007：config.guess/config.sub 内联补丁识别 HarmonyOS（uname -s=HarmonyOS），三元组走 aarch64-unknown-linux-ohos；做在 conanfile.py 内，不进 patches/ 目录，避免 PF5 平台宏闸
- E011：configure/config.status 内 `umask 077` 改 `umask 022`（HMDFS 兼容）
- make -j1：HMDFS jobserver fifo 兼容
- package_type=library：产物含 bin/regfinfo、bin/regfexport（regfmount 需 FUSE 按需提供），按 libesedb/libevtx 先例以库形态发布，不声明 commands.json
- e2e 输入：发布包无 tests/input（测试数据仅在 git 版 synctestdata.sh），配方在 build 阶段按 synctestdata.sh 语义用 Python 下载 dfwinreg 的 NTUSER.DAT、SOFTWARE、SYSTEM 到 builddir/tests/input/public/，并写入 .regfinfo_hierarchy/options（内容 -H）；数据仅用于测试，不打包

## test_package 设计（R34）

- test.c 直链 libregf，5 个真实 API 断言：get_version 非空、get_access_flags_read 非零、file_initialize 成功、check_file_signature 对非 REGF 文本返回 0、file_free 成功
- 每个用例打印 `case N: <name>: PASS/FAIL`，末尾 `RESULT: passed/total`，供 conanfile.py 解析上报 HMBS_TEST_PACKAGE_RESULT（含 discovered/passedCount）
- test() 另从包内 res/upstream_test_result.json 复发 HMBS_UPSTREAM_TEST_RESULT（真机证据门禁只采集 test_package 阶段标记）

## 本地验证

- 本机为 Windows 执行器，未运行 conan create；待 HMBS 同步工作树后在 HarmonyOS PC 真机执行完整预检（conan create + make check + test_package）
- 已做静态检查：conanfile.py/test_package py_compile 通过、YAML 解析通过、LF 行尾、无占位符、无中文乱码

## 风险与后续

- CI #50241（2026-09-18）：configure 止于 `cannot run C compiled programs`（exit 77），而同机 hello 探针可运行、编译器自检 `works: yes`。根因为 generate() 曾无条件追加 `-L<gettext>/lib -lintl`（_gettext_lib_dir 无 libintl 时仍回退返回首个存在目录），有该前缀的机器上最早的 AC_PROG_CC 运行探针链接 -lintl 却无运行时路径（LD_LIBRARY_PATH 仅带 SDK llvm），加载失败被误判为交叉编译；无此前缀的预检机则一次通过。本轮已删除该 -lintl 注入（--disable-nls + ac_cv_* 缓存足以关 NLS，预检机无 -lintl 即全流程通过为证），_dump_config_log 同步增强为先打印失败标记窗口。如后续链接报 bindtextdomain 未定义，需连运行时路径一起补回，而非仅加链接旗。
- regfmount 需 FUSE/Dokan，若 configure 在 OHOS 上禁用属预期行为，package() 的 manual pickup 已按可选处理，不因此判失败
- 若个别 regf_test_* 在 OHOS 上失败，优先打补丁修复，不删除 make check；确实平台受限则在 MANIFEST 声明并在 PR 补充说明如实写清
