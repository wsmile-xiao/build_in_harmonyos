# DRAFT-cyrus-sasl-digestmd5-2.1.28-testsuite-unsigned-char-userdb-gates

> cyrus-sasl `utils/testsuite` 在 OHOS 上的**两道串联门槛**：① `getopt()` 返回值必须用 `int` 承接（`char` 无符号平台上 `!= EOF` 恒真 → harness 在任何用例前 `exit 3`）；② 修好后仍需已初始化的 sasldb 口令库，机制型最小包（`--with-dblib=none`）在设计上不具备，故首个用例即阻塞——必须如实申报而非冒充通过。

## 问题特征（真实日志片段）

**门槛 ①（编译期告警 + 运行期首个输出）**

```
testsuite.c:2957:51: warning: result of comparison of constant -1 with expression of type 'char' is always true
    while ((c = getopt(argc, argv, "Ms:g:r:han")) != EOF)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ^  ~~~

$ SASL_PATH=<empty-dir> ./utils/testsuite
Usage:
 testsuite [-g name] [-s seed] [-r tests] -a -M
    …
Failed with: Invalid parameter
（rc=3，任何用例都未执行）
```

**门槛 ②（修 ① 之后）**

```
$ SASL_PATH=<empty-dir> ./utils/testsuite
NOTE:
-Must be able to read sasldb, which needs to be setup with a
 username and a password (see top of testsuite.c)

Checking plaintext passwords... Failed with: sasl_checkpass() failed on simple case
（rc=3）
```

变体一致性：`默认 / -n / -r 3 / -a` 四种调用、动态（`utils/testsuite`）与静态（`utils/testsuitestatic`）两个 harness，**六次实测结果完全一致**。

## 根因

1. **可移植性（门槛 ①）**：`utils/testsuite.c` 的 `main()` 用 `char c` 承接 `getopt()` 返回值；OHOS clang 下 `char` 为无符号，`-1` 转 255，`!= EOF` 恒真 → `switch(c)` 落 `default:` → `usage()` + `fatal("Invalid parameter")` 并 `exit(3)`。同族先例：`archives/c/cyrus-sasl-sql/2.1.28/patches/0003-testsuite-use-int-for-getopt.patch`。
2. **夹具依赖（门槛 ②）**：`main()` 在 `init(seed)` 之后**第二个动作**即 `test_checkpass()`，要求已初始化的 sasldb 口令库（上游源码顶部 NOTE 原文）。DIGEST-MD5 机制包按最小闭包构建（`--with-dblib=none`；configure 输出 `checking DB library to use... none` + `WARNING: Disabling SASL authentication database support`），口令库后端在 cyrus-sasl 中属独立子包，故 harness 在首例即 `fatal()`，其余 18 个标号阶段不可达。
3. **类别性**：cyrus-sasl 全家族同源机制/子包（login/crammd5/ntlm/scram/sql/gssapiv2/gs2）共用该 harness；广义适用于"上游自带手工测试台（EXTRA_PROGRAMS）且断言依赖运行期夹具"的所有项目。

## 使用说明

1. **何时用**：适配 cyrus-sasl 家族（login/crammd5/ntlm/scram/sql/gssapiv2/gs2 及本 digestmd5）并需要执行上游 `utils/testsuite` 时；或任何"上游自带手工测试台但断言依赖运行期夹具"的项目申报上游测试证据时。
2. **怎么用**：① 先打最小可移植性补丁（`char c` → `int c`）让 harness 能进入用例；② 运行 `SASL_PATH=<empty-dir> ./utils/testsuite`（及 `./utils/testsuitestatic`）；③ 若在 `Checking plaintext passwords...` 处失败，即确认命中 sasldb 夹具门槛，按 `blocked_by_userdb` 如实申报，不要改判通过。
3. **判定口径**：`discovered/executed/passed/failed/skipped` 必须与源码 `main()` 阶段枚举自洽（本例 1+18=19），并给出具体技术原因。
4. **禁止**：以"零发现/未执行"申报通过；对 `HMBS_UPSTREAM_TEST_RESULT` 写 `passed` 而 `discovered: 0`。

## 适用范围

- cyrus-sasl 家族各机制/子包的 `utils/testsuite` 执行与上游测试证据申报；
- 任何"有上游测试入口但断言需要运行期夹具（用户库/守护进程/网络服务）"的 C/C++ 项目适配。

## 输入 / 输出定义

- 输入：构建好的 `utils/testsuite`（及 `testsuitestatic`）+ 隔离的 `SASL_PATH` 空目录。
- 输出：`rc`、逐阶段输出、以及机器证据行 `HMBS_UPSTREAM_TEST_RESULT`（discovered/executed/passed/failed/skipped + status + reason）。

## 修复方案（rec，优先级 1）

1. **最小可移植性补丁**（不动任何断言逻辑）：

   ```diff
   --- a/utils/testsuite.c
   +++ b/utils/testsuite.c
   @@ -2939,7 +2939,7 @@
    int main(int argc, char **argv)
    {
   -    char c;
   +    int c;
   ```

2. **如实申报夹具阻塞**：配方 `build()` 仍执行 harness，证据行记录真实计数：

   ```json
   {"status":"blocked_by_userdb","framework":"cyrus-utils-testsuite",
    "discovered":19,"executed":1,"passed":0,"failed":1,"skipped":18,"rc":3,
    "reason":"… main() 的 test_checkpass() 需要已初始化 sasldb；本包 --with-dblib=none …"}
   ```

3. **机制级验证由 test_package 承担**（消费者视角，8 项检查含 2 项鸿蒙特有）。

4. **MANIFEST.yml** 的 `upstream_test_audit` 逐条列出入口声明位置、真实读数与阻塞原因。

## 回退方案（优先级 2）

不改上游测试源码时：以"无自动化测试目标（无 `TESTS`/`check_PROGRAMS`）+ 手工测试台需外部夹具"如实申报（`ci/config/no_official_test.txt` 口径），并附清点命令与原始输出为证据——**禁止无证据地声明"无测试"**。

## 禁止策略

- ❌ 上游存在测试入口却以"零发现/未执行"申报通过（零证据放行）；
- ❌ `HMBS_UPSTREAM_TEST_RESULT` 出现 `"status":"passed"` 与 `"discovered":0` 自相矛盾的组合。

## 本任务实测

`cyrus-sasl-digestmd5 2.1.28`（OHOS aarch64 / clang 15.0.4，`--enable-digest --with-openssl=openssl/3.5.6 --disable-shared --enable-static --without-staticsasl --with-dblib=none`）：

- 补丁前：四变体 × 两 harness 全部 `Failed with: Invalid parameter`（rc=3）；
- 补丁后：全部进入真实用例，在 `Checking plaintext passwords...` 处 `Failed with: sasl_checkpass() failed on simple case`（rc=3）；
- 配方留痕：`HMBS_UPSTREAM_TEST_RESULT={"status": "blocked_by_userdb", "discovered": 19, "executed": 1, "passed": 0, "failed": 1, "skipped": 18, "rc": 3, ...}`；
- 旁证：`utils/pluginviewer -c/-s`（SASL_PATH 置空）列出 `DIGEST-MD5`（`best SSF: 128`），`sample/sample-server` 机制列表输出 base64 `RElHRVNULU1ENQ==`（= `DIGEST-MD5`）。
