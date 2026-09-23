# cronolog 1.6.2-rpk — 适配记录

> 分支: feat/cronolog-1.6.2-rpk
> 最后更新: 2026-09-10

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | cronolog |
| 版本 | 1.6.2-rpk (Debian/Ubuntu 1.6.2+rpk 修订, 源码为上游 1.6.2) |
| 状态 | built（待真机预检复核） |
| 构建系统 | autotools (tarball 自带 `./configure`, 古老 autoconf, 无 config.guess) |
| 上游 | https://github.com/fordmason/cronolog |
| 源码 | cronolog-1.6.2.tar.gz, sha256 `65e91607…db88e` (MacPorts Portfile + distfiles 实测双验证) |
| 镜像 | `https://distfiles.macports.org/cronolog/cronolog-1.6.2.tar.gz` (133591 字节, 同 sha) 在前, 官方 `http://cronolog.org/download/cronolog-1.6.2.tar.gz` 作为回退 |
| 依赖 | 无 (纯 C, 仅 libc; cronosplit 为 perl 脚本随包安装, 不参与测试) |
| 包类型 | application（命令行工具，R38: 软件级 commands.json 已声明） |

## 二、上游测试套件审计（hmbs 机器证据门禁）
审计对象: 官方源码包 cronolog-1.6.2.tar.gz (2026-09-10 下载, 133591 字节, sha256 与 MacPorts Portfile 一致)
- testsuite/ 仅含空 Makefile.am (两行 automake 注释, 无 TESTS/check_PROGRAMS) + README 明示 "Unfortunately the testsuite is not yet written ;-)"
- 顶层 Makefile.am: `AUTOMAKE_OPTIONS = gnu dejagnu`, SUBDIRS 含 testsuite 但无 TESTS/check 目标
- src/Makefile.am: sbin_PROGRAMS=cronolog + sbin_SCRIPTS=cronosplit (perl) + noinst_PROGRAMS=cronotest (手动调试 helper, 非自动化套件)
- configure.in: 无测试相关宏 (AC_INIT(COPYING), 无 AC_CONFIG_TESTDIR)
- 全树无 `TEST(`/`TEST_F` (gtest)、`def test_` (pytest)、tests/ 目录
结论: 上游 cronolog 1.6.2 确实不存在自动化测试套件, test_package/MANIFEST.yml 声明
`upstream_tests_exist: false` + 非空 `upstream_test_audit`; 不虚构测试数字。
功能验证由 test_package 真实执行 cronolog 二进制完成 (-V + `-o` 单写 cmp + 日期模板自动建目录 cmp, 3 断言),
详见 test_package/MANIFEST.yml。真机预检输出 `HMBS_UPSTREAM_TEST_RESULT status:"no_tests" discovered:0 executed:0`。

## 三、配方要点（conanfile.py, 对齐 logrotate 3.22.0 / lzop 1.04 已验证模式）
- AutotoolsToolchain 不传 `--build` (本包 configure 早于三元组时代, 不识别该选项; 直接沿用工具链 CC 即可, 属 native 构建)
- generate() 透传 HMBS 注入的可写 TMPDIR/TMP/TEMP 进 Conan buildenv (缺失时回退 build 内 tmp); 不再屏蔽 mktemp (本包 1.6.2 configure 经核查无 mktemp/umask 逻辑, 常失败 shim 反而破坏编译器探测)
- generate() 经 extra_cflags 追加 -Wno-error=implicit-int / -Wno-error=implicit-function-declaration (1999 年 configure 用 K&R main 探测, 现代 clang 默认判硬错误; 降为警告不改语义)
- build() 中 configure 失败时打印 config.log 尾部 100 行, 下轮预检可直接看到真实 clang 诊断
- build() 增加编译器目标侧探测: 工具链配置的绝对路径若无法 exec (config.log 实证 `.../clang: inaccessible or not found`), 则回退到 PATH 解析的可用编译器并以 `CC=... ./configure` shell 环境前缀传入 (2026-09-10 预检实证: 本包 1.6.2 古董 configure 不识别 `VAR=VALUE` 位置参数, 会将其误判为 host/target 并报 "invalid host type / can only configure for one host and one target at a time"; 环境前缀由 shell 剥离、configure 无感, 且可覆盖 conanbuild.sh 导出的坏 CC; CFLAGS/LDFLAGS 仍来自工具链) (R33: 工具链仍为首选, 仅在其不可执行时回退); 探测与决策全量打日志
- build() 前 `os.umask(0)` + `os.chdir(build_folder)` 并注入 `PWD` (HMDFS getcwd 失败绕行, sipcalc/lzop 同源)
- make -j1 (R9/E074: 并行 make 在 HMDFS jobserver FIFO 上 EPERM)
- package() 将生成 Makefile 的 `INSTALL_DATA = ...` 重定向到多文件拷贝 wrapper (doc 的 install-man 把两个 .1m 合并为一次调用, HMBS 单文件 shim 会报 EX_USAGE 64; lzop 1.04 同源方案)
- package() 末尾 sbin→bin 归一 (本包为 sbin_PROGRAMS; 若工具链未折叠则手动合并, 保证 conanrun PATH 可见)
- package() 安装必须用 `autotools.make(target="install")` 而非 `autotools.install()`: build() 系手动 `--prefix=<package_folder>` configure, 而 install() 默认追加 `DESTDIR=<package_folder>` 会导致双重嵌套 (`<p>/<p>/sbin`, 顶层 bin/sbin 空, 2026-09-10 预检实证 `cronolog binary not found`); make(target) 不加 DESTDIR, 与手动 prefix 配平
- package() 安装后全量 walk 落盘树并打 `[cronolog] staged:` 日志 (第二轮预检仍报 binary not found, 且顶层 bin/ 为空目录、sbin/ 缺失, 需看到 make install 真实产物位置再定位); 随后在包内递归找确切文件名 `cronolog` (man/info 名称不同, 无误伤), 找不到直接抛错 (附落盘文件数), 找到则归一到 bin/ 并尽力 chmod 755 (HMBS 目标机可能无 chmod 能力, 失败只告警), 移空后剪掉空源目录
- package_type=application, cpp_info.bindirs=["bin"], libs=[] (R38)
- 零补丁 (conandata.yml 无 patches 段)

## 四、test_package 说明 (3 个真实断言, R34)
test.sh 实测 `cronolog` 二进制 (conanrun PATH):
1. `cronolog -V` 输出 "cronolog version" (stderr, exit 0)
2. `printf … | cronolog -o once.log` 单写文件与输入 cmp 一致 (管道 EOF 后 cronolog 正常退出码为 3, 显式放行; 其他非零判失败)
3. `printf … | cronolog logs/%Y/%m/%d/app.log` 自动创建日期子目录且内容 cmp 一致
- 工作区统一用 `$TMPDIR` (OHOS 上 /tmp 只读, E002), 陷阱清理
- test() 用 print() 直输 `HMBS_TEST_PACKAGE_RESULT={...discovered:3,passedCount:3}` 与 `HMBS_UPSTREAM_TEST_RESULT={status:"no_tests",...}` 双标记 (lzop 1.04 同源通道); 失败时 re-raise ConanException

## 五、验证记录
- 本机: MacPorts distfiles 下载 133591 字节 + sha256 与 Portfile 双验证通过
- 真机: 待 HMBS 预检 (conan create + test_package + 上游 no_tests 审计门禁)
- 预检通过后由 HMBS 统一提交、推送并创建 PR, 正文测试表以真机 evidence 为准

## 六、遗留问题
- cronosplit (perl 脚本) 随包安装但未在 test_package 覆盖 (目标机 perl 不保证存在); cronolog 主二进制已全覆盖
- 上游 testsuite 为空, `make check` 无可执行用例, PR 上游通过率栏填 0/0 并附审计说明, 不虚构

## 2026-09-11 package() sbin缺失修复（真机预检 failed 轮）
- 现象：真机 conan create 在 package() 报错 cronolog binary missing，staged 仅 4 个 doc 文件（info/man），sbin/ 从未生成；编译本身成功（src/cronolog 已链接）。
- 根因：HMBS install shim 仅接受单文件双参数调用（参数个数不为 2 即 EX_USAGE 64）。doc 的 INSTALL_DATA 已用 wrapper 绕过所以正常，但二进制安装以 install -c src dest（3 个参数，含 -c）形式调用，同样触发 64 门禁，导致 install-sbinPROGRAMS/SCRIPTS 落盘失败。
- 修改（conanfile.py package()）：
  1. wrapper 重定向从仅 doc/Makefile + 顶层 Makefile 的 INSTALL_DATA，扩展为构建树下全部 Makefile 的 INSTALL_DATA/INSTALL_PROGRAM/INSTALL_SCRIPT；
  2. wrapper 自身 chmod 改为 best-effort（目标机可能无 chmod 能力）并打 patched 计数日志；
  3. make install 后若包内仍找不到 cronolog，回退到构建树直接拷贝 src/cronolog（优先以 src/cronolog 结尾的候选）到 bin/，并顺带 stage 构建树生成的 cronosplit 脚本；构建树也无二进制时才抛错。
- test_package 与 MANIFEST.yml 无需改动（bin/cronolog 归一化路径不变）。

## 2026-09-15 rule4 上游 1 用例真实执行（审查 FAIL 轮）
- 背景：CI #44125 已通过；审查先判少报（实测 N=1 > 声明 N=0），修正声明为 N=1（manual_only）后，2026-09-15 复审仍 FAIL：rule4 要求上游 1 用例必须真实执行（0/1 不通过），rule6/7 因新提交缺 AI 检视/CI 需重跑。
- 根因纠正：cronotest 并非“手动交互式 helper”——通读源码用法为 `cronotest [OPTIONS] template count`，完全非交互式，`-s` 可固定起始时间做确定性验证；此前 manual_only 声明有误。
- 修改：
  1. conanfile.py package()：`make` 构建的 src/cronotest（noinst，install 不落盘）显式 stage 到 bin/cronotest（优先 build/src/cronotest，递归回退，缺失仅告警，test 侧明确报错）；
  2. test_package/conanfile.py：test.sh 3 断言不变，新增上游真实运行 `cronotest -s "01 01 2024 00:00:00" "logs/%Y/%m/%d/app.log" 3`，输出重定向到文件后校验非空 + `Rotation period` + `Period 1`/`Period 3` + `2024` 文件名展开（空文件比空文件式静默通过无法满足），标记改为 `status:passed/discovered:1/executed:1`，失败抛错；
  3. MANIFEST.yml：审计更正（唯一可执行测试为 cronotest，非交互式），upstream_tests 命令改为上述自动化命令；
  4. manifest.yaml knowledge_gained 同步。
- 待 HMBS 真机预检：conan create + test_package（3/3）+ 上游 cronotest（1/1）；通过后由 HMBS 统一 commit/push，PR 正文上游通过率以真机 evidence 为准（预期 1/1）。

## 2026-09-15 cronotest 起始时间格式修复（真机 upstream_test failed 轮）
- 现象：test_package 上游 1 用例 `cronotest -s "01 01 2024 00:00:00" "logs/%Y/%m/%d/app.log" 3` 报 `invalid start time`，executed 1 / passed 0。
- 根因：src/cronoutils.c parse_time() 的 european_date_formats 仅接受月份英文缩写（%b，如 Jan），无任何纯数字 `%d %m %Y` 格式；数字月份恒解析失败返回 -1。USAGE 中 "dd mm year" 与实现不符。
- 修改（test_package/conanfile.py + MANIFEST.yml）：起始时间改为 `01 Jan 2024 00:00:00`，命令前加 `LC_ALL=C` 固定 %b 解析 locale；校验逻辑（Rotation period/Period 1/Period 3/2024）不变。
- 头部 /proc/cmdline、/tmp Read-only、RequestsDependencyWarning 为真机容器常态噪音；readonly_tmp 诊断无实际 /tmp 写失败（cronotest 无 -D 不落盘，输出重定向到 build 文件夹，test.sh 已用 TMPDIR），无需改动。
