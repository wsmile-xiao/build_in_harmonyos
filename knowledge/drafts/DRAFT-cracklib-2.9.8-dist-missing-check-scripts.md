# DRAFT-cracklib-2.9.8-dist-missing-check-scripts

> Contributor: pc1-62 (AtomCode) | Status: Draft | Updated: 2026-09-17 (R03)
> Source: cracklib 2.9.8 HarmonyOS PC 适配（发布包无自动化 check + 交互式驱动 →
> 环境构造后全量 14 真实运行 14/14，含 python unittest 11 入口；配方内以
> FascistCheckUser 作 CI 等效覆盖）

## 现象

cracklib 2.9.8 官方 release tarball（`releases/download/v2.9.8/cracklib-2.9.8.tar.gz`）
里 `util/Makefile.am` 声明 3 个 `check_PROGRAMS`（testlib/testnum/teststr），
全部是 **stdin 交互驱动**（提示 "enter dictionary words..." 逐行读）。与
2.10.3 不同的是，2.9.8 **根本没有声明** both-endian.sh/checkdict.sh（2.10.3
是声明了但漏分发——dist 缺陷；2.9.8 是压根没有），发布 tarball 无任何可
自动化的 check 脚本。

另有 `python/test_cracklib.py` `TestModuleFunctions` 11 个 unittest 方法，
受 `python/Makefile.am` `if BUILD_PYTHON` 条件宏控制（配方 `--without-python`
默认裁剪）；顶层 `make test`（`util/cracklib-check < test-data`）为工具链
入口，test-data（87 字节）为输入文件，dicts/（词表数据源）与 po/（翻译）
为非测试分类——R01/R02 台账曾漏掉 python 11 个入口，被审查判少报
（实测 N=11 > 声明 N=3），R03 已完整重枚举（源码声明 14）。

→ 发布包内 `make check` 的上游自动化判据**默认环境不可直接运行**。

## 根因

1. 3 个 check_PROGRAMS 交互式驱动，且都有额外环境依赖：
   - testnum/teststr 硬编码 `PWOpen(NULL, "r")`：packlib.c 用
     `snprintf("%s.pwd", NULL)` 把空前缀按 libc 行为格式化为**字面 `(null)`
     相对路径** → 默认 cwd 无 `(null).pwd/.pwi/.hwm` 时直接 `(null).pwd: No
     such file` exit 255（R01 实测）。
   - testlib 的 `FascistCheck` 内部 `getpwuid(getuid())` 取 GECOS 检查，
     OHOS 无 /etc/passwd 对应条目（且 /etc/passwd 只读，append 实测
     "Read-only file system"）→ 对任何密码恒返回 "you are not registered
     in the password file"（CI #43915 实测）。
2. python 11 个 unittest（R03 新增枚举）三个前置条件：
   - AM_PATH_PYTHON 用 `sys.version[:3]` 把 3.12 截断成 "3.1" → configure
     探测 `python3.1/Python.h` 失败，BUILD_PYTHON 不生效（R03 实测）；
   - 上游 2.9.8 测试用 `assertEquals`，Python 3.12 已移除该别名 →
     AttributeError（R03 实测 5 个 ERROR）；
   - `FascistCheck` 内部 getpwuid 依赖同 testlib（R03 实测 3 个 FAIL）。

## 解决方案（R02 三入口 3/3 + R03 python 11/11 = 全量 14/14）

1. **用上游建典工具链自建字典**：`sort -u dicts/cracklib-small |
   cracklib-packer testdict`（54763 词）。注意 cracklib-format 首段
   `gzip -cdf` 依赖 GNU gzip `-f` 对非 gzip 输入原样穿透，toybox gzip
   报 "gzip: not gzip" 产空典（CI #43836）——cracklib-small 已是小写
   净词表，format 的规范化管道对它恒等，等效收敛为 sort -u。
2. **testnum/teststr 恢复**：把同一字典以**字面 `(null)` 前缀**装入运行 cwd
   （`cracklib-packer "(null)"` → `(null).pwd/.pwi/.hwm`），PWOpen(NULL)
   按 snprintf 语义解析为相对路径 `(null).pwd` 即命中——**无需特权路径**；
   再用 stdin 管道驱动 `printf '0\n1\n5\n100\n25000\n' | ./testnum`、
   `printf 'abc\nadoration\nzznotaword\n' | ./teststr` 实测：真实词条
   （`(word 100) 'aback'`）、真实命中（`adoration: 999`）、真实未命中
   （`zznotaword: 54763 **** NOT FOUND ****`），退出码 0。
3. **testlib 恢复**：`--with-default-dict=<testdict>` 重建库使 FascistCheck
   字典装载成功（R01 已证）；其内部 `getpwuid(getuid())` 以 **LD_PRELOAD
   getpwuid shim**（nss_wrapper 同方式，等效 nss 来源；/etc/passwd 只读时的
   getpwuid 构造方法，uid/gid 取运行时 getuid()，任意执行 uid 通用）提供
   当前 uid 的 passwd 条目；随后 stdin 管道驱动实测真实语义：
   `abc: it is WAY too short`、`adoration/bawled/007bond: it is based on a
   dictionary word`、`Xk9#mQ2$vL8p: ok`，退出码 0。
4. **python 11 个 unittest 最小纳入（R03 实测 11/11 OK）**：
   - configure 以缓存变量 `am_cv_python_version=3.12` 覆盖 AM_PATH_PYTHON
     的 `sys.version[:3]` 截断（首次 `python3.1/Python.h` not found）→
     `python3.12/Python.h` 探测 yes，BUILD_PYTHON 生效；
   - 配方 `--disable-shared` 只产 `_cracklib.a`，python import 需补建共享
     模块：`clang -shared -fPIC -o python/_cracklib.so python/_cracklib.o
     lib/.libs/libcrack.a -lpython3.12`；
   - Python 3.12 移除 `assertEquals` → 运行时注入
     `unittest.TestCase.assertEquals = unittest.TestCase.assertEqual`
     兼容 shim（不改上游文件）；
   - `FascistCheck` getpwuid 同 testlib → 同一 LD_PRELOAD getpwuid shim；
   - 实测 `Ran 11 tests, OK（failures=0 errors=0 skipped=0）`，exit 0。
5. **双口径台账（R03 完整重枚举）**：source_declared_total=14
   （util 3 + python 11）、configured_executable_total=14、
   executed_passed_total=14、fail=0、unrun=0，**全量通过率 14/14 (100%)**；
   `make test` 工具入口与 test-data 非独立用例单列，不计入分母。配方对
   OHOS 目标保持 `--without-python`（python 绑定不随库交付），11 个 python
   用例为设备侧最小纳入实测（BUILD_PYTHON 互斥分支），台账如实单列。
6. 配方 build() 内 FascistCheckUser 4 条语义断言（典内词×2 拒绝/过短拒绝/
   强密码通过）作 **CI 等效覆盖**（另列，不替代上游真实通过数）。
7. 必须用 FascistCheckUser 而非 FascistCheck 作配方断言（绕 getpwuid；
   FascistCheckUser 显式传 user/gecos 参数，可传 NULL 兼容，CI #43915）。

## 验证证据（R02/R03，绝对路径 + SHA-256，任务 worktree .oh-ut/evidence/）

- `./testnum.log` sha256=5281bd1829cc77bf5375e28dac26a6b2e54590b9b3491c98ce841b3879351aef
- `./teststr.log` sha256=1d6885ffa01a4bb22d16491f2c0efaa6afb53899914c86fd6fa3e882d15a761b
- `./testlib.log` sha256=f5d2c6b385431e869041015cbca914089a3dcc744cc798894ca92ed075b94943
- `./passwd-writability.log`（/etc/passwd 只读证据）sha256=e82f978fb02957bfe930c41804e58011f835ff34776e9a5b57fdaf0ce744941e
- `gates/py-configure2.log`（BUILD_PYTHON 启用 configure，python3.12/Python.h=yes）
  sha256=6a3b4b48d37c0c3b2db4713aaf0dcc07497880815dd5a21f675b2e4e8d24c285
- `gates/py-unittest-shim.log`（python 11/11 unittest 实测）
  sha256=0a293bb0a219e10c0edad36912be7dbe43917ef3c20dfa3217a4316929daeced
- `gates/dep-final-check.log`（字典路径与 passwd 条目终态复核）
  sha256=e6924e3c4d38f39e0d7cceb2d590ac5267ab9d581d96dc517a43565269a90a12
- 复验：conan create / test_package / 消费者用例 / W3 本地 CI exit 0、
  W2 原子性通过（仅配方 13 文件）

## 适用边界/反例

- 完整发行环境安装默认字典后，testnum/teststr 以真实默认路径可运行（R02 以
  字面 `(null)` 前缀装入 cwd 等价达成，无需特权路径）；有 passwd 条目或
  nss 等效来源的环境，testlib 可作字典语义验证。
- python 11 个 unittest 需要设备具备 python3.12 + Python.h + libpython3.12.so，
  并满足三个前置构造（am_cv_python_version 覆盖 / 补建 _cracklib.so /
  assertEquals 兼容 shim + getpwuid shim）；配方 `--without-python` 下为
  BUILD_PYTHON 互斥分支，未实例化但可在设备侧按上述步骤纳入实测。
- 反例：**无任何构造时上游测试仍不可直接自动化**——发布包无 check 脚本、
  交互式驱动 + 空前缀字面 (null) + getpwuid 依赖三者并存时 `make check`
  默认不可用，须按上文环境构造后才能真实运行；python 入口在无 python3
  开发环境或 Python <3.6 / ≥3.12（assertEquals 移除）时不能直接运行。
