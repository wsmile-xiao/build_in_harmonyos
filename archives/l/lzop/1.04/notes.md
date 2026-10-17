# lzop 1.04 — 适配记录

> 分支: feat/lzop-1.04-H036-clean
> 最后更新: 2026-08-13

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | lzop |
| 版本 | 1.04 |
| 状态 | built（待真机预检复核） |
| 构建系统 | autotools |
| 源码 URL | https://www.lzop.org/download/lzop-1.04.tar.gz |
| sha256 | 7e72b62a8a60aff5200a047eea0773a8fb205caf7acbe1774d95147f305a2f41 |
| 依赖 | lzo2/2.10（configure.ac 检查 lzo/lzoconf.h + AC_CHECK_LIB(lzo2)） |
| 包类型 | application（命令行工具，R38: 软件级 commands.json 已声明） |

## 二、上游测试套件审计（hmbs 机器证据门禁）
审计对象: 官方源码包 lzop-1.04.tar.gz（2026-08-13 下载，sha256 与 lzop.org 官网一致）
- 无 tests/ 目录；全树 find -name '*test*' 无任何测试源文件（仅 autoconf 生成脚本）
- Makefile.am 仅 bin_PROGRAMS=src/lzop + dist 文档安装目标，无 TESTS/check_PROGRAMS
- configure.ac 无 AC_CONFIG_TESTDIR / 测试相关宏
- `make -n check` 展开为空（check-am: all-am，automake 默认空目标）
结论: 上游 lzop 1.04 确实不存在测试套件，test_package/MANIFEST.yml 声明
`upstream_tests_exist: false` + 非空 `upstream_test_audit`；不虚构测试数字。
功能验证由 test_package 真实执行 lzop 二进制完成（--version + lzop -c / -dc 往返
内容比对），详见 test_package/MANIFEST.yml。

## 三、补丁清单
| 补丁 | 内容 | 类型 |
|------|------|------|
| 0001-autoconf-config.guess.patch | config.guess 更新至 2022 版，识别 HarmonyOS/OHOS（E007） | portability |
| 0002-autoconf-config.sub.patch | config.sub 更新至 2021 版，接受 aarch64-linux-ohos（E007） | portability |
| 0003-configure.patch | configure 临时目录 umask 077→022（E011/E114: HMDFS setgid 下 077 目录不可写） | portability |

补丁来源: 0001/0002 沿用本仓库旧归档（前次 2026-04-24 尝试）已验证的 config.guess/
config.sub 更新内容；0003 对齐 lzo2/2.10 同源修复（同一 autoconf 生成代码）。

## 四、配方要点（conanfile.py）
- Autotools + AutotoolsDeps: lzo2 的 -I/-L/-l 由 AutotoolsDeps 喂给 configure/make
- make -j1（R9/E074: 并行 make 在 HMDFS jobserver FIFO 上 EPERM）
- package_type=application，cpp_info.bindirs=["bin"]
- 无需 CMake 路线（tarball 自带 CMakeLists.txt 但 autotools 为主流，与 lzo2 一致）

## 五、验证记录
- 本机: 源码下载 + sha256 校验通过；3 个补丁 `patch -p1 --dry-run` 全部可干净应用
- 真机: 待 HMBS 预检（conan create + test_package + 上游测试审计门禁）
- 预检通过后由 HMBS 统一提交、推送并创建 PR，正文测试表以真机 evidence 为准

### 真机预检轮次
- 第 1 轮（2026-08-12，failed@compile）: `configure: error: working directory
  cannot be determined`。根因: HMDFS 上 conan 构建目录父路径链不可访问，子进程
  getcwd()/pwd 失败，autoconf 的 `ac_pwd=\`pwd\`` 健全性检查直接退出（与
  sipcalc/libclastfm/analog 曾遇的 HMDFS getcwd 问题同源）。日志另有
  `/tmp` 只读告警（hmbs 已注入任务 TMPDIR，非本包阻塞）。
  修复: build() 在 configure 前 `os.chdir(build_folder)` 并注入
  `os.environ["PWD"]=build_folder`，bash pwd 内建按逻辑路径返回 $PWD，
  绕过 getcwd 失败（沿用 sipcalc/1.1.6 已验证写法）。
  状态: 工作树未提交，等待 HMBS 复跑预检。
- 第 2 轮（2026-08-12，failed@compile/package）: `install-dist_docDATA` 目标报
  `Error 64`（EX_USAGE）。根因: automake 的 dist_doc_DATA 规则把全部 11 个文档
  文件合并成**一次** `install -c -m 644 <f1..f11> <dir>` 调用，而 HMBS install
  shim（`install_shim:true`，能力表 chmod:0）只接受单文件双参形式
  （`[ $# -eq 2 ] || exit 64`），多文件调用直接退出 64；单文件的
  binPROGRAMS/man 安装不受影响（故此前环节通过）。
  修复: conanfile.py 新增 `_INSTALL_WRAPPER`（多文件拷贝语义: SRC... DEST，
  DEST 为目录时逐个 cp），package() 里写入 build 目录并 chmod 0755，再把生成
  Makefile 的 `INSTALL_DATA = ...` 行重定向到该 wrapper（chicken 5.4.0 /
  slang 2.3.3 同类 install wrapper 先例），最后 autotools.install()。
  状态: 工作树未提交，等待 HMBS 复跑预检。
- 第 3 轮（2026-08-13，failed@evidence）: conan create + test_package 3 个 smoke
  断言全过（--version / compress / round-trip cmp），但 hmbs 判 incomplete，
  原因「缺少 HMBS_UPSTREAM_TEST_RESULT 上游测试证据」，上游测试 发现0/执行0/通过0。
  根因（对照已通过门禁的 no_tests 范例 osmctools/0.9、sipcalc/1.1.6、
  analog/homebrew、astra/1.1.0、virtualpg/2.0.1.1）:
  1) 预检日志从未输出 `HMBS_UPSTREAM_TEST_RESULT` 标记（test.sh 只跑 smoke，
     conanfile.py 未输出任何 HMBS 标记）;
  2) MANIFEST.yml 的 `upstream_check_command: "make check"` 非空——wraplinux
     轮 32 教训: 5 个通过门禁的 no_tests 库该字段全部为空串/null，清单器凭非空
     判「上游存在测试命令」，强制要求真机发现并执行。
  修复（仅工作树，未 commit/push）:
  1) test_package/conanfile.py: test() 在 test.sh 真实执行后，用 print() 直接输出
     两个标记到 Conan 输出流（analog/astra/virtualpg 已验证渠道）:
     `HMBS_TEST_PACKAGE_RESULT={...discovered:3,passedCount:3}`（test.sh 的 3 个
     真实断言）+ `HMBS_UPSTREAM_TEST_RESULT={status:"no_tests",discovered:0,
     executed:0,...,reason:<sha256 审计 + make check 空目标事实>}`；
     test.sh 失败时标记 passed:false 并 re-raise ConanException（保持真实失败）。
  2) test_package/MANIFEST.yml: `upstream_check_command` 改为 `""`（对齐全部已
     通过门禁的 no_tests 库）; `upstream_test_audit` 从扁平字符串改为 osmctools
     同款结构化映射（source_tarball/source_sha256/top_level_files 逐文件裁定/
     scanned_for/scan_result/make_check_output/reason），供 hmbs 清单器机器解析。
  状态: 工作树未提交，等待 HMBS 复跑预检。

- 第 4 轮（2026-08-13，failed@compile）: 预检日志仅输出 preflight.sh[229]:
  `can't fork - try again`（fork EAGAIN），conan create 无任何输出，编译阶段根本
  未开始。根因: 真机设备级进程/内存资源耗尽（进程表满/OOM），与 chibicc/1.0.24.1
  第 3 轮、dhcpd-pools/3.2 记录的真机 `Out of memory` / `can't fork` 模式一致，
  属环境故障非配方问题。配方与测试接入自第 3 轮修复后未变（第 3 轮已真机通过
  conan create + test_package 3 断言），按守则停止修改、等待真机资源恢复后由
  HMBS 复跑预检。
  状态: 工作树未提交，等待环境恢复 + HMBS 复跑预检。

## 六、遗留问题
- 无已知编译阻塞；依赖 lzo2/2.10 需在制品仓可用（W0 检查项，真机预检确认）
