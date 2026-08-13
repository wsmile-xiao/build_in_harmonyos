# adms 2.3.7 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，libtool）
- 编译日期: 2026-08-11
- 目标平台: HarmonyOS PC (aarch64)，clang 15，libc++
- 状态: adapting（真机预检通过前）

## 上游信息
- 上游仓库: https://github.com/Qucs/ADMS（Qucs 组织维护，2.3.7 为最新 release）
- 发布归档: https://github.com/Qucs/ADMS/releases/download/release-2.3.7/adms-2.3.7.tar.gz
- sha256: `3a78e1283ecdc3f356410474b3ff44c4dcc82cb89772087fd3bbde8a1038ce08`（本地实测下载计算）
- 许可证: GPL-3.0
- 产物: admsXml/admsCheck 两个命令行工具 + libadmsElement/libadmsPreprocessor/libadmsVeriloga/libadmsAdmstpath 四个库 + 头文件（constants.vams/disciplines.vams）

## 编译步骤
```
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
配方内流程：apply_conandata_patches → ./configure --enable-static --disable-shared --build=aarch64-unknown-linux-gnu → make -j1 → 上游测试（admsCheck + admsXml dummy.va）→ make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 硬性要求 perl + XML::LibXML、flex、bison>=2.5（as_fn_error 直接失败） | configure.ac 中 AX_PROG_FLEX/AX_PROG_BISON_VERSION/AX_PERL_MODULE_VERSION 为硬检查 | 发布包已内置生成好的 parser/lexer 源码（verilogaYacc.c/verilogaLex.c/preprocessorYacc.c 等，时间戳晚于生成脚本），构建根本不需要这些工具；补丁 0001 将 7 处 as_fn_error 降级为注释跳过 |
| 2 | config.guess 不识别 HarmonyOS 平台 | OHOS 内核未被上游 config.guess 收录 | configure 加 `--build=aarch64-unknown-linux-gnu`（与 bash 5.3 配方同法） |
| 3 | 上游无 make check 自动化测试（Makefile.am 无 TESTS 变量，check 目标只构建 BUILT_SOURCES） | 上游测试机制是 admsCheck 程序 + dummy.va/dummy.xml 示例转换，未接入 automake TESTS | 按上游设计接入：build() 中运行 admsCheck（自检）+ admsXml dummy.va -e dummy.xml（生成 dummy.net），并断言输出文件非空 |
| 4 | 真机预检 configure 报 `working directory cannot be determined`（伴随大量 getcwd 失败告警） | HMDFS 下 conan 建树后父目录对 getcwd() 不可达，autoconf 严格 pwd 判定失败（analog/homebrew 同款） | conanfile build() 预置 os.environ["PWD"]=build_folder（shell pwd 内建走逻辑路径）+ 补丁 0002 让 configure 在 pwd 失败时回退 $PWD |
| 5 | config.status 临时目录 `umask 077 && mktemp -d ./confXXXXXX`（潜在下一失败点） | HMDFS 新目录固定 setgid，umask 077 生成 drwx--S--- 目录连属主都无法写入（E011/E129 同款） | 补丁 0002 将 configure 中两处 umask 077 改 umask 022 |
| 6 | 真机预检 make install 阶段 `install-man1` 退出码 64（Error 64） | E182/E188：真机 HMFS 上带 `-c` 选项的 install（toybox/HMBS shim）直接失败，多源拷贝到目录（`install -c a.1 b.1 dir/`）退出 64；INSTALL_DATA='${INSTALL} -m 644' 与 INSTALL_PROGRAM='${INSTALL}' 展开后均带 `-c`（INSTALL 变量自带 `-c` 后缀），二进制单源安装侥幸通过、man 页多源安装失败 | 仿 libfstconst（已过门禁）在 conanfile 写 cp/mkdir install shim（容错 chmod），sed 改生成 Makefile 的 `INSTALL = ...` 行指向 shim（INSTALL_DATA/PROGRAM 引用 ${INSTALL} 自动重算） |
| 7 | 首轮曾误判根因为 `-m 644`（补丁 0003 去 -m 后仍失败） | 去掉 `-m` 后命令变为 `install -c a.1 b.1 dir/`，仍退出 64——`-m` 不是触发点 | 回退 0003，改用 install shim 方案（行 6） |

## 源码修改
- `patches/0001-configure-skip-build-tools-check.patch` — 跳过 configure 对 flex/bison/perl+XML::LibXML 的 7 处硬性检查（生成源码已内置，无需这些工具）
- `patches/0002-configure-hmdfs-pwd-tmpdir.patch` — HMDFS 适配：configure 的 ac_pwd 判定在 `pwd`（getcwd）失败时回退 `$PWD`；config.status 临时目录 umask 077→022

## 依赖版本
- 无外部 conan 依赖（工具链由 profile 提供：clang 15 / libc++ / autotools）

## 验证结果
- 待真机预检（本轮为未提交工作树，HMBS 将自动执行预检）
- test_package 用例（test_adms.py，3 用例 6 断言）：
  1. admsXml --version 输出版本号
  2. admsCheck 生成 dummy.va/dummy.xml（非空）
  3. admsXml dummy.va -e dummy.xml → dummy.net（非空）

## 注意事项
- 上游测试通过率以真机预检日志为准（HMBS 机器证据硬门禁），本文件不填数字
- 静态构建（--enable-static --disable-shared）：工具运行时无 .so 依赖，避免 OHOS 缺失系统库问题（R26 精神）
