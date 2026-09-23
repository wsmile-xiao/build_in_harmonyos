# cdpr 2.4 — 适配记录

> 分支: feat/cdpr-2.4
> 最后更新: 2026-09-06

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | cdpr |
| 版本 | 2.4 |
| 状态 | built（待真机预检复核） |
| 构建系统 | makefile（无 configure, 单 Makefile） |
| 源码 URL | https://downloads.sourceforge.net/project/cdpr/cdpr/2.4/cdpr-2.4.tgz |
| sha256 | 32d3b58d8be7e2f78834469bd5f48546450ccc2a86d513177311cce994dfbec5 |
| 大小 | 26053 字节（与 Debian cdpr_2.4.orig.tar.gz 同哈希） |
| 依赖 | libpcap/1.10.6（cdpr.h 直接 #include "pcap.h", 链接 -lpcap） |
| 包类型 | application（命令行抓包工具, R38: 软件级 commands.json 已声明） |

## 二、上游测试套件审计（hmbs 机器证据门禁）
审计对象: 官方源码包 cdpr-2.4.tgz（2026-09-06 下载校验, sha256 见上）

- 顶层文件: cdp.h / cdpr.c / cdpr.conf / Cdpr.dsp / Cdpr.dsw / cdpr.h / cdprs
  目录 / cdprs.c / conffile.c / COPYING / INSTALL / license.txt / Makefile /
  README / README.cdprs / README.Win32 / u_ints.h / XGetopt.c / XGetopt.h
- 无 tests/、test/、spec/、t/ 目录；全树无 `TEST(`/`TEST_F`（gtest）、
  无 `def test_`（pytest）
- Makefile 仅定义 `cdpr` 与 `clean` 两个目标, 无 `check` / `test` /
  `TESTS` / `check_PROGRAMS` 目标；`make -n check` 无规则可执行
- 上游是纯 CLI 抓包工具, 功能验证只能靠真实执行二进制完成

结论: 上游 cdpr 2.4 确实不存在测试套件, test_package/MANIFEST.yml 声明
`upstream_tests_exist: false` + 非空 `upstream_test_audit`；不虚构测试数字。
功能验证由 test_package 真实执行 cdpr 二进制完成（`cdpr -h` 的版本横幅、
用法说明、选项说明三断言）, 详见 test_package/MANIFEST.yml。

## 三、补丁清单
| 补丁 | 内容 | 类型 |
|------|------|------|
| 0001-makefile-use-cc-variable.patch | Makefile 链接行 `gcc` 改为 `$(CC)`, 使 Conan 工具链编译器生效（与 nixpkgs `substituteInPlace Makefile --replace gcc CC` 同源, POSIX 兼容, 无平台宏） | portability |
| 0002-cdpr-h-extern-globals-fno-common.patch | cdpr.h 全局变量改为 extern 声明, cdpr.c 增加单一定義；修复 gcc10+/clang 默认 -fno-common 下的多重定义链接失败（与 nixpkgs fno-common 补丁同源, 上游 bug 3） | portability |

## 四、配方要点（conanfile.py）
- Raw Makefile + libpcap 依赖: 从 `self.dependencies["libpcap"].cpp_info`
  取 includedirs/libdirs, 组装 `-I/-L -lpcap`（dhcpdump/1.10 先例）
- 编译器从 `self.conf.get("tools.build:compiler_executables")` 获取（R33）,
  以 `make CC=... CFLAGS=... LDFLAGS=... -j1` 传入（R9: 单作业）
- 平台守卫 `self.settings.os in ("Linux", "OHOS")`（R32）
- package_type=application, `cpp_info.bindirs=["bin"]`, `cpp_info.libs=[]`（R38）
- build() 不调用 `make check`（上游无该目标）; MANIFEST 中
  `upstream_test_in_build: false` 如实声明

## 五、验证记录
- 本机: 源码下载 + sha256 校验通过（32d3b58d…bec5, 26053 字节）；
  2 个补丁上下文行与上游原文件逐行核对一致
- 真机: 待 HMBS 预检（conan create + test_package + 上游测试审计门禁）
- 预检通过后由 HMBS 统一提交、推送并创建 PR, 正文测试表以真机 evidence 为准

## 六、遗留问题
- 无已知编译阻塞；依赖 libpcap/1.10.6 需在制品仓可用（W0 检查项, 真机预检确认）
- `cdpr` 运行时需抓包权限与 Cisco 设备, test_package 仅覆盖 `-h` 安全路径,
  不做真实抓包（需 root/网络, CI 不可复现）
