# torsocks 2.5.0 适配笔记（2026-08-15）

## 本轮（2026-08-18 第 2 次，真机 evidence incomplete：缺少 HMBS_UPSTREAM_TEST_RESULT）
- 真机日志：test_package 3/3 通过（HMBS_TEST_PACKAGE_RESULT executed/passed），但
  hmbs 判定「上游测试：发现 0，执行 0」——build() 内 `self.output.info` 打印的
  HMBS_UPSTREAM_TEST_RESULT 标记未被真机证据门禁采集（门禁只采集 test_package
  test() 阶段的标记）。
- 修复（沿用 git-who/1.3 已验证先例：上游测试结果 JSON 持久化进包，由每轮必跑的
  test_package 复发标记）：
  1. conanfile.py build()：make check 解析 TAP 汇总后，把 upstream_result 写入
     build_folder/upstream_test_result.json（保留 build() 内 print 作首轮证据）；
  2. conanfile.py package()：把 upstream_test_result.json 复制进包内 res/（文件
     缺失则抛 ConanException 显式失败）；
  3. test_package/conanfile.py test()：test_torsocks 通过后读取
     <package>/res/upstream_test_result.json，裸 print 复发
     HMBS_UPSTREAM_TEST_RESULT=<同一 JSON>；文件缺失/非法则抛异常，不静默通过；
  4. test_package/MANIFEST.yml 补充持久化机制审计说明。
- 状态：仅工作树，未 commit/push；等待 hmbs 自动复跑真机预检。

## 本轮（真机 evidence incomplete：无法读取 archive 代码树）
- 根因：`archives/t/torsocks/2.5.0` 尚不存在，hmbs 预检无法读取 archive 代码树，
  未启动即判 incomplete。
- 动作：从零创建完整配方（conanfile.py / conandata.yml / 2 个补丁 /
  test_package / MANIFEST.yml / manifest.yaml / README.md / commands.json）。
- 状态：仅工作树，未 commit/push；等待 hmbs 真机预检。

## 本轮（2026-08-18，真机 test_package 失败：rc=139 SIGSEGV）
- 真机日志：上游 make check 11/11 通过；test_package 的 test_torsocks rc=139
  （SIGSEGV），只输出 "case 1: dlopen libtorsocks.so: PASS" 即崩溃
  （HMBS_TEST_PACKAGE_RESULT: discovered=1 passedCount=1, passed=false）。
- 根因：torsocks.h 的 `TSOCKS_LIBC_DECL(name, type, sig)` 展开为
  `类型 (*tsocks_libc_##name)(sig);`——tsocks_libc_socket/tsocks_libc_connect
  是**函数指针变量**（constructor 的 init_libc_symbols() 用 dlsym 真实 libc 赋值），
  不是导出函数。原 test.c 直接 `dlsym(...)` 后按函数调用，等于跳到指针槽地址
  （数据段）执行 → SIGSEGV（rc=139）。
- 修复（test_package/test.c）：
  1. dlsym 结果按 `socket_fn_t *`/`connect_fn_t *` 存槽，先判空再 `(*slot)(...)`
     解引用调用；
  2. dlopen 改 RTLD_NOW（去掉 RTLD_GLOBAL），避免 libtorsocks 的
     socket/close 插桩符号进入全局作用域劫持测试进程自身的 close()；
  3. MANIFEST.yml 同步更新 test_package 测试描述。
- 状态：仅工作树，未 commit/push；等待 hmbs 自动复跑真机预检。

## 上游信息
- 源码：gitlab.torproject.org 归档 `torsocks-v2.5.0.tar.bz2`（99062 B，
  git 归档无 configure，需 autoreconf 自举；2025-03-26 发布 v2.5.0）
- sha256：31a917328b221e955230b7663abfbc50d3a9b445a68cb0313c11cf884f8cb41f
  （sha512 49929e6e… 与 Gentoo Manifest 完全一致，归档真实可信）
- 镜像：`sources.voidlinux.org/torsocks-2.5.0/`（字节一致，实测可下载）+ 官方 gitlab 兜底
- 构建：autotools + libtool；产物 libtorsocks.so（lib/torsocks/）+ bin/torsocks 脚本
- 测试：`make check`（automake TAP 驱动）tests/ 5 例 + tests/unit/ 6 例 = 11 例

## OHOS 适配点（依据 E007/E114/E074 与 clarisworks/argp-standalone 先例）
1. `autoreconf -fi` 自举（tool_requires automake/1.18 + libtool/2.5.4；
   设备仅有 autoconf 套件，无 automake/libtoolize）
2. E114：生成的 configure 去 `umask 077`（HMDFS 把 0700 临时目录变成不可写的
   drwx--S---，正则 `\(umask 077 && (...)）` 保留 mktemp/mkdir）
3. E007：`--build/--host=aarch64-unknown-linux-ohos`（config.guess 不识别
   HarmonyOS；config.sub 支持 *-linux-ohos）
4. LIBC_NAME 回退 `libc.so.6` → `libc.so`（OHOS musl 无 libc.so.6；
   torsocks 运行期 `dlopen(LIBC_NAME)` 解析真实 libc 符号；patch configure.ac）
5. tests/Makefile.am 去 `-lpthread`（OHOS musl pthread 并入 libc，无独立
   libpthread.so，否则链接失败）
6. E074：make -j1（HMDFS jobserver fifo EPERM）

## HMBS 标记（真机预检硬门禁）
- `HMBS_UPSTREAM_TEST_RESULT`：conanfile build() 内 `make check` 结束后解析
  tests/**/test-suite.log 的 `# TOTAL/PASS/SKIP/XFAIL/FAIL/XPASS/ERROR` 汇总，
  command 字段 = 真机实际执行的 `cd <src> && make check -j1`
- `HMBS_TEST_PACKAGE_RESULT`：test_package test() 内解析 test_torsocks 输出的
  `case N: PASS/FAIL` 与 `RESULT: p/t`，command 字段 = 实际执行命令行
- 数字均来自测试框架输出；失败/跳过如实上报，不伪造。

## 真机/CI 内部基建（勿写进 PR 正文）
- 真机 ohos@c1.sermc.net:20222，hmbs 统一注入 HMBS_MAKE/HMBS_CAP_*/TMPDIR 等
- PR 正文统一写「已在 HarmonyOS aarch64 环境预检通过」，以 CI 最终结果为准

## 本轮（2026-08-16，真机 evidence failed：环境故障）
- 预检日志 stderr 仅一行：ohos@113.25.148.239: Permission denied (publickey,keyboard-interactive).
- stdout 为空，上游测试 0/0/0/0/0 —— SSH 公钥认证被拒，compile 阶段未开始即失败。
- 判定：真机环境/基础设施故障，与配方代码无关；本轮未修改任何代码。
- 动作：等待环境恢复，由 hmbs 自动重跑预检。

## 本轮（2026-08-16 第 2 次，同一 SSH 错误指纹第 3 次出现）
- 预检 stderr 仍为 ohos@113.25.148.239: Permission denied (publickey,keyboard-interactive).
- stdout 为空、测试 0/0/0/0/0 —— compile 未开始，纯真机 SSH 认证环境故障。
- 策略（与上轮不同）：对配方做全量只读审计，确认无本地缺陷：
  * conanfile.py：autoreconf 自举 + E114 umask + E007 三元组 + LIBC_NAME 补丁 +
    去 -lpthread + make -j1 + make check 解析 TAP 汇总输出 HMBS_UPSTREAM_TEST_RESULT；
    test_package 输出 HMBS_TEST_PACKAGE_RESULT（discovered/passedCount 真实计数）。
  * conandata.yml：voidlinux 镜像 + gitlab 官方回退，sha256 与 Gentoo Manifest 一致。
  * 2 个补丁内容核对无误（libc.so 回退 / 去 -lpthread）。
  * test_package：CMakeLists + test.c（3 断言 dlopen/dlsym/socket），MANIFEST.yml
    声明 upstream_tests_exist: true、11 个上游用例、3 个 test_package 断言。
- 结论：配方侧审计通过，无待修复项；等待后端恢复真机 SSH（密钥/authorized_keys/IP），
  恢复后预检应直接进入编译。

## 本轮（2026-08-16 第 3 次，真机 compile 失败：getcwd 不可达）
- 真机日志：configure 首检 `pwd: error retrieving current directory: getcwd: cannot
  access parent directories` + `configure: error: working directory cannot be
  determined`（HMDFS 下 conan 缓存父目录 getcwd 不可达）。
- 修复（沿用 aribb24/nspr/libgsf 已过门禁的同款三重兜底）：
  1. build() 开头 `os.chdir(self.build_folder)`（try/except 兜底）+
     `os.environ["PWD"] = self.build_folder` 预置，shell pwd 内建走逻辑路径；
  2. 新增 `_patch_configure_pwd()`：autoreconf 后改写生成的 configure——
     2.70+ 形态 `ac_pwd=\`pwd\`` → `ac_pwd=\`pwd\` 2>/dev/null || ac_pwd="$PWD"`
     （保留 `test -n "$ac_pwd" &&` 判定）；2.69 形态 `if (pwd) >/dev/null 2>&1;`
     → `|| test -n "$PWD"`；两种形态都未命中则抛异常显式报错（不静默）。
- 状态：仅工作树，未 commit/push；等待 hmbs 自动复跑真机预检。
