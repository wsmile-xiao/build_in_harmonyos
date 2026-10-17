# cpu 1.4.3 — 测试报告

- 平台：HarmonyOS PC / aarch64-unknown-linux-ohos，clang 15（OHOS SDK 26.0.0.18）
- 依赖：openldap/2.6.7（制品仓 ohpcd）
- 测试入口：`test_package/conanfile.py` → `bash test.sh`（conanrun 环境），
  以及配方 `build()` 中的 `make check`（上游检查目标）

## 1. 上游测试用例

**结论：cpu 1.4.3 上游没有自动化测试用例。**

实测（在构建树中执行上游检查目标）：

```
$ make check
make: Nothing to be done for 'check-am'.
make-check-rc=0
```

上游顶层 `check` 目标存在但 `TESTS` 为空，因此这是一次空执行；配方 `build()`
仍调用它，使 CI 侧留下"上游检查目标已执行"的记录。随包发布的
`doc/test.ldif`（LDAP 目录数据，需真实服务器 `ldapadd` 导入）与
`doc/cpu.conf`（配置样例）都不是自动化用例，本环境无 LDAP 服务器，故未纳入。

## 2. 适配测试用例（新增）

`test_package/test.sh` + `test_package/consumer.c`，共 11 项断言。按真实测试边界分类：**单元测试（消费者用例）1 项（第 11 项）+ 集成测试 7 项（第 4-10 项）+ 鸿蒙特有测试 3 项（第 1-3 项，平台安装布局/加载路径断言）**；同一消费者测试步骤不重复计入多个用例。

| # | 用例 | 断言 |
|---|------|------|
| 1 | 制品内容（鸿蒙） | `bin/cpu` 存在（OHOS 布局为 `bin/` 而非上游 `sbin/`；HMDFS 忽略 chmod → E490，实际执行见第 4 项） |
| 2 | 制品内容（鸿蒙） | `lib/libcputil.so` 存在（E522 私有 prefix 影子布局，包内自洽） |
| 3 | 制品内容（鸿蒙） | `lib/libcpu_ldap.so` 存在（`-module -avoid-version` 插件模块形态，可被 `dlopen` 加载） |
| 4 | 集成（CLI 契约） | `cpu --version` 输出包含 `1.4.3` |
| 5 | 集成（CLI 契约） | `cpu --help` 输出包含 `USAGE: cpu` |
| 6 | 集成（CLI 契约） | `cpu --help` 输出包含 `--method=` |
| 7 | 集成（插件加载，反向对照） | `cpu -M bogus` 必须出现 `CPU_loadLibrary` 失败 |
| 8 | 集成（插件加载） | `cpu -M ldap -C <conf> -y cat root` 不得出现 `CPU_loadLibrary` |
| 9 | 集成（插件加载） | 同上，不得出现 `loading the ldap library` |
| 10 | 集成（消费者程序构建链接） | `consumer.c` 对制品 `libcputil.so` 编译链接成功 |
| 11 | 单元（消费者用例） | `consumer.c` 运行通过（10 个断言，见下） |

消费者测试 `consumer.c`（计数入第 11 项）断言 `libcputil.so` 的公开 API：

| 断言 | 内容 |
|------|------|
| 1 | `Strdup("cpu")` 返回内容相等的副本 |
| 2 | `Free()` 释放该副本 |
| 3 | `md5_buffer()` 处理缓冲区 |
| 4 | `MD5("abc") == 900150983cd24fb0d6963f7d28e17f72`（已知答案） |
| 5 | `sha_buffer()` 处理缓冲区 |
| 6 | `SHA1("abc") == a9993e364706816aba3e25717850c26c9cd0d89d`（已知答案） |
| 7 | `mkstemp()` 建立凭据文件（目录经 argv/TMPDIR 传入，避免 /tmp 不可写） |
| 8 | `cgetpwent()` 能查到已存在的条目 |
| 9 | `cgetpwent("root")` 解析出 uid 0 与 pw_name |
| 10 | `cgetpwent()` 对不存在的条目返回 NULL |

控制原则：`cpu` 在操作失败时也返回 0，故断言基于输出内容而非退出码；
第 7 项是第 8/9 项的反向对照（证明该断言确实能失败，R34）；
`-M ldap` 用 `LDAP_URI=ldap://127.0.0.1:1`（必然拒绝连接）保持离线确定性，
断言的是"加载器把控制权交给插件"，不是"服务器可达"。

## 3. 执行结果（实测）

```
$ bash test_package/test.sh          # CPU_TEST_ROOT=<staged package prefix>
== cpu 1.4.3 package tests ==
PASS  package ships bin/cpu
PASS  package ships lib/libcputil.so
PASS  package ships lib/libcpu_ldap.so
PASS  --version reports the upstream version 1.4.3
PASS  --help prints the usage line
PASS  --help documents the method option
PASS  unknown method fails in CPU_loadLibrary (negative control)
PASS  ldap plugin loads (no CPU_loadLibrary failure)
PASS  ldap plugin loads (no 'error loading the ldap library')
PASS  consumer.c compiles and links against libcputil.so
PASS  consumer test passes
      PASS   Strdup() returns a copy of its argument
      PASS   Free() releases the copy
      PASS   md5_buffer() digests a buffer
      PASS   md5_buffer("abc") == 900150983cd24fb0d6963f7d28e17f72
      PASS   sha_buffer() digests a buffer
      PASS   sha_buffer("abc") == a9993e364706816aba3e25717850c26c9cd0d89d
      PASS   mkstemp() created a credentials file
      PASS   cgetpwent() finds an existing entry
      PASS   cgetpwent("root") reports uid 0 and the name from the file
      PASS   cgetpwent() returns NULL for a missing entry
      CONSUMER TEST PASSED (0 failure(s))
== 11 passed, 0 failed ==
test-rc=0
```

| 项 | 结果 |
|----|------|
| 上游测试 | `make check` rc=0（空目标，上游无用例） |
| 适配测试 | 11/11 通过 |
| 消费者测试 | 通过（10/10 断言） |
| 环境无关性（E573） | 工具链 lib 目录不在搜索路径 / 同名坏 `libxml2.so.16` 前置（复刻 CI run #44867 失败条件）仍 11/11 |
| 通过率 | 100% |

## 4. 复现

```bash
# 全流程（finish 内部做 W2 结构 + R36 依赖发布校验 + W3 conan create，
# conan create 会执行 test_package，因此上面的 11 项用例会被重新跑一遍）
python3 $SKILL_ROOT/scripts/ohc-run.py finish cpu 1.4.3 built

# 仅单独复跑测试（对已 create 的制品）
export CPU_TEST_ROOT=$(conan cache path cpu/1.4.3)/..
LD_LIBRARY_PATH=$(conan cache path cpu/1.4.3)/lib bash test_package/test.sh

# 环境无关性验证（E573）：造一个同名坏 libxml2.so.16 放在搜索路径首位，
# 复刻 CI run #44867 的 lld 载入失败；测试脚本自备工具链 lib 目录后
# 同样条件应 11/11（修复前该命令逐字复现 CI 报错）
mkdir -p "$HOME/tmp/fakexml" && : > "$HOME/tmp/fakexml/libxml2.so.16"
CPU_TEST_ROOT=$(conan cache path cpu/1.4.3)/.. LD_LIBRARY_PATH="$HOME/tmp/fakexml" \
    bash test_package/test.sh
```
