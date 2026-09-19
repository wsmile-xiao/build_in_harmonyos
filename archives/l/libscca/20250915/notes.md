# libscca 20250915 适配笔记

## 基本信息

- 上游：https://github.com/libyal/libscca（libyal，Windows Prefetch File 解析库）
- 版本：20250915（alpha 预发布，2025-09-15 发布）
- 源码包：libscca-alpha-20250915.tar.gz（1606292 字节）
- sha256：2467f821bdeb4fb0a084fc9715cab8b58fba428bef4cf700fdc223e5c8386ffd
- 构建系统：Autotools（configure + make，捆绑 libcerror/libcdata/libbfio/libfwnt 等内部库）
- License：LGPL-3.0-or-later

## 上游测试审计（R51）

- tests/Makefile.am：check_PROGRAMS 共 16 个（scca_test_compressed_block、scca_test_error、scca_test_file、scca_test_file_header、scca_test_file_information、scca_test_file_metrics、scca_test_filename_string、scca_test_filename_strings、scca_test_io_handle、scca_test_notify、scca_test_support、scca_test_tools_info_handle、scca_test_tools_output、scca_test_tools_path_string、scca_test_tools_signal、scca_test_volume_information）
- TESTS 共 3 个 shell 包装（test_library.sh、test_tools.sh、test_sccainfo.sh），另有条件单测 test_python_module.sh（本配方以 --disable-python 关闭，不计入）
- `make check` 生成 tests/test-suite.log（含 automake TAP 汇总 TOTAL/PASS/FAIL/SKIP），配方解析该文件输出 HMBS_UPSTREAM_TEST_RESULT
- pyscca Python 绑定测试不在本配方范围内（需要完整 CPython 开发环境，库本体与 sccatools 不依赖它）
- 发布包内无 tests/input（测试数据仅在 git 版 synctestdata 流程），无 input 时 file/support/sccainfo 恒 SKIP 77；配方在 build 阶段下载 plaso 的 CMD.EXE-087B4001.pf 到 builddir/tests/input/public/，与上游 synctestdata 语义一致；数据仅用于测试，不打包

## 配方决策

- `--disable-python`：pyscca 绑定需要完整 CPython 开发环境，真机/CI 均不保证，库本体与 sccatools 不依赖它
- `--disable-nls`：NLS 仅影响工具提示信息翻译，需要外部 gettext/libintl；Prefetch 解析逻辑不依赖，关闭后零外部依赖
- 无外部 requirements：所有 libc* 依赖均随源码包捆绑（SUBDIRS 内编译），无需先发布依赖
- 默认 shared=False，支持 --enable-static/--disable-shared 切换
- E007：config.guess/config.sub 内联补丁识别 HarmonyOS（uname -s=HarmonyOS），三元组走 aarch64-unknown-linux-ohos；做在 conanfile.py 内，不进 patches/ 目录，避免 PF5 平台宏闸
- E011：configure/config.status 内 `umask 077` 改 `umask 022`（HMDFS 兼容）
- make -j1：HMDFS jobserver fifo 兼容
- tool_requires：pkgconf/3.0.5（configure 硬需 pkg-config 二进制）与 bash/5.3（tests/*.sh 的 `#!/usr/bin/env bash` 经 PATH 解析，真机默认 PATH 无 bash，复用 castget/blogc/acpica-unix 先例）
- SHELL/CONFIG_SHELL 探测：CI profile 默认 /data/service/hnp/bin/bash 在 HMBS 主机不存在，配方探测可用 shell 并改写 conanbuild 脚本导出；make SHELL 不覆盖（automake LIBTOOL=$(SHELL) 语义，bash 重解释 libtool 缺 `print` 内建）
- package_type=library：产物含 bin/sccainfo，但按 libevtx/libesedb 先例以库形态发布，不声明 commands.json
- package() 兜底：若 `autotools.install()` 在 HMDFS（hardlink=0 chmod=0）下落盘失败，`_manual_pickup()` 以 os.walk + shutil.copyfile（不 chmod/hardlink）布到包内 lib/include/bin

## test_package 设计（R34）

- test.c 直链 libscca，5 个真实 API 断言：get_version 非空、get_access_flags_read 非零、file_initialize 成功、check_file_signature 对非 Prefetch 文本返回 0、file_free 成功
- 每个用例打印 `case N: <name>: PASS/FAIL`，末尾 `RESULT: passed/total`，供 conanfile.py 解析上报 HMBS_TEST_PACKAGE_RESULT（含 discovered/passedCount）
- test() 另从包内 res/upstream_test_result.json 复发 HMBS_UPSTREAM_TEST_RESULT（真机证据门禁只采集 test_package 阶段标记）

## 本地验证

- 本机为 Windows 执行器，未运行 conan create；待 HMBS 同步工作树后在 HarmonyOS PC 真机执行完整预检（conan create + make check + test_package）
- 已做静态检查计划：conanfile.py/test_package py_compile、YAML 解析、LF 行尾、无残留占位符

## 风险与后续

- 若真机 gettext 路径与 --disable-nls 行为不符（如 configure 不识 --disable-nls），按预检日志调整（备选：恢复 NLS 并补 -lintl，如 libesedb E053）
- 若个别 scca_test_* 在 OHOS 上失败，优先打补丁修复，不删除 make check；确实平台受限则在 MANIFEST 声明并在 PR 补充说明如实写清
- 若 CMD prefetch 样本下载失败（网络），按预检日志切换 plaso winprefetch 目录内其他 .pf（NOTEPAD/PING/TASKHOST 等，均为同源有效样本）
