# Notes — clock-setup 0.168

## 软件识别
- clock-setup 是 Debian installer（debian-installer）时钟配置 udeb，上游即 Debian
  installer-team 的 clock-setup（https://salsa.debian.org/installer-team/clock-setup），
  0.168 为 2026-05-17 发布的原生包（Format 3.0 native）。
- 源码树极小：`Makefile` + `set-date-epoch.c` + `finish-install.d/10clock-setup` +
  `debian/`（打包文件与 debconf 模板/翻译）。唯一编译产物为单文件 C 工具
  `set-date-epoch`（gettimeofday 读时钟；早于 1970 则 settimeofday 回拨到 epoch）。
- 构建系统为裸 Makefile（`CC := gcc`，目标仅 set-date-epoch/build/clean）。
- 许可证 GPL-2.0（debian/copyright：GPL version 2；set-date-epoch.c：GPL v2 or later）。

## 源码获取
- 官方 URL: https://deb.debian.org/debian/pool/main/c/clock-setup/clock-setup_0.168.tar.xz
- conandata.yml 另前置 raspbian 镜像（同文件、同 sha256，Windows 侧实测可达；
  deb.debian.org 在本机 TLS 握手失败，按下载超时例外做镜像优先+官方回退）。
- sha256: 04893115e360cad0126f1714a82ee9b9423993551bc3e638550833fecbd28692
  （本地下载实测 81688 字节，与 .dsc 的 Checksums-Sha256 条目逐字一致）。
- 上游结构通过 `git clone https://git.launchpad.net/ubuntu/+source/clock-setup`
  的 origin/debian/sid（0.168）交叉核对：与 tarball 内容一致。

## 上游测试审计（no_tests 判定依据）
结论：**上游不存在任何测试套件**，故 test_package/MANIFEST.yml 写
`upstream_tests_exist: false` + 非空 upstream_test_audit，test_package 每轮
输出 HMBS_UPSTREAM_TEST_RESULT status=no_tests、discovered=0、executed=0。
- tarball 无 tests/、test/、regress/ 目录，无 *test* 源码；
- Makefile 无 check/test 目标（仅 set-date-epoch/build/clean）；
- debian/rules 的 override_dh_auto_test 仅 `sh -n` 两个 shell 脚本（打包 lint，
  0 用例），不构成测试套件；
- debian/control Build-Depends 无测试框架依赖。

## 配方要点（对照 checkbashisms 工具包与 backuppc-rsync HMBS 标记范式）
1. **类型**：package_type=application；package_info 只设 bindirs=["bin"]、libs=[]（R38
   工具包，软件级 commands.json 已声明）。
2. **构建**：沿用上游 Makefile（`make CC=<conan-conf> -j1 build`），CC 取自
   `tools.build:compiler_executables:c`（R33），-j1（R9）；in-source 布局同 zlib
   先例（basic_layout + build="."）。
3. **链接**：动态链接。仅依赖系统 libc，产物名唯一，无 R26 系统同名污染风险；
   无外部 Conan 依赖，不触发 R36。
4. **补丁**：无（零源码修改；debconf 脚本不参与构建，不做 shebang 改写）。
5. **test_package 设计（R34/L0d/L0e）**：
   - test_set_date_epoch.sh：POSIX sh（`set -eu` 同 checkbashisms 先例，toybox 兼容），
     6 个内容级用例真实执行包内 bin/set-date-epoch：存在且可执行、两处程序字符串
     检查（反 `exit 0` 空壳）、正常时钟退出码 0、stdout 为空、stderr 为空
    （反打印字符串空壳）。末行固定输出 `RESULT: N passed, M failed`。
   - conanfile.py test()：解释器按 CONFIG_SHELL→SHELL→/bin/sh 解析（backuppc
     [shell_getcwd] 教训，不硬编码 HNP 路径）；Environment+apply() 注入
     SET_DATE_EPOCH_BIN/TMPDIR；日志重定向后解析 RESULT 行输出
     HMBS_TEST_PACKAGE_RESULT；随后复发 no_tests 上游标记（防包缓存命中轮次缺证据）。

## 本地静态验证（Windows 侧，非真机结论）
- tarball sha256 与 .dsc 条目一致；文件清单与 launchpad debian/sid 一致。
- 双 conanfile 通过 py_compile；conandata.yml YAML 解析正常（url 为 2 条列表，
  sha256 为 64 位 hex）。
- 测试脚本 neglect 检查：含 6 个用例计数逻辑与 RESULT 行；`trap - 0` 后显式 exit
 （backuppc dash/trap 退出码教训已吸收）。
- 行尾均为 LF（core.autocrlf=false 环境），无 BOM、无模板占位符。

## 待真机预检确认
- OHOS clang 下单文件编译一次性通过情况；
- 6 项功能用例在真机/HMDFS 上的实际表现；
- 动态链接产物在真机 exec 情况（若遇 SIGKILL 需补 OHOS 自签名，参考 backuppc 先例）。
