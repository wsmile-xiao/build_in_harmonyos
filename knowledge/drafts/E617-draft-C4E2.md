# E617 — DLP autotools 包的 -tools 子包：默认开关与父 tarball 全量 N 口径

> Contributor: libfreehand-tools 0.1.2 适配 | Status: Draft | Updated: 2026-09-20
> 对应：`knowledge/drafts/E617-draft-C4E2.kv`
> 适用家族：Document Liberation Project（libfreehand / libmspub / libmwaw / libe-book /
> libcdr / libvisio …）的 `-tools` 子包（与父包**同一 tarball**）

## 错误签名
```
上游实测 N > 声明 N
上游有用例 6 个但一个也没测（0/6）
error: ... [-Werror,-Wdeprecated-copy-with-user-provided-copy]
error: use of undeclared identifier 'outbuf'      # U16_NEXT 缺分号
```

## 根因一：两个"默认是 yes"的开关

DLP 系 `configure.ac` 里：

```m4
AC_ARG_ENABLE([werror], ..., [enable_werror="$enableval"], [enable_werror=yes])
AC_ARG_ENABLE([tests],  ..., [enable_tests="$enableval"],  [enable_tests=yes])
```

| 默认开关 | 后果 | 正确处置 |
|---|---|---|
| `--enable-werror` **默认 yes** | 2017 年代码 + clang 15 的新告警（实测 `-Wdeprecated-copy-with-user-provided-copy`，`FHTransform` 有用户提供的拷贝构造却用隐式拷贝赋值）直接编译失败 | 打包传 `--disable-werror`（上游自带开关、发行版惯例）；**不要**照抄旧归档那种 `#ifdef __OHOS__` 补 `operator=` 的写法（补丁新增 `__OHOS__` 行会被 PF5 拦） |
| `--enable-tests` **默认 yes** | `CPPUNIT` 是**默认构建期依赖**，上游 CPPUnit 套件默认进构建 | 不传 `--disable-tests` = 沿用上游默认；`tool_requires("cppunit/1.15.1")` + `build()` 内真实 `make check`（`HOME` 指向构建目录内沙箱，禁止写用户真实 HOME） |

另一类硬错误（与 werror 无关，必须打补丁）：`U16_NEXT(s, j, length, c)` 在 ICU 新版展开为
`do{...}while(0)`，源码缺分号使紧随的 `unsigned char outbuf[...]` 落入 while 体 →
`error: use of undeclared identifier 'outbuf'`（18 errors）。补 1 个分号即可，**平台无关**。

## 根因二：-tools 子包的 N 口径（审方红线）

`-tools` 子包与父包**同源 tarball**，审方按**父 tarball 全量注册面**量 N；
「上游实测 N > 声明 N」直接判不通过。必须把**全部候选口径**数出来，取"用例/注册类"的**最大值**
作为主 N，断言属**另一单位**只披露、不并入：

| 候选口径 | libfreehand-0.1.2 实测 | 取数位置 |
|---|---|---|
| `check_PROGRAMS` | 1（`test`） | `src/test/Makefile.am:5` |
| `TESTS` | 1 | `src/test/Makefile.am:25` |
| CPPUnit 注册用例 `CPPUNIT_TEST(` | 2（testRead/testSeek） | `src/test/FHInternalStreamTest.cpp:32-33` |
| suite 注册 | 1 | 同文件 `:104` |
| 测试/模糊测试源文件数 | **3**（src/test 2 + src/fuzz 1）→ **主 N=3** | `_SOURCES` / `noinst_PROGRAMS` |
| `CPPUNIT_ASSERT*`（另一单位） | 20（testRead 7 + testSeek 13） | 只披露 |

五处同源：PR 正文 / `manifest.yaml` / `test_package/MANIFEST.yml` / `notes.md` /
`reports/test-report.md`；台账 `TOTAL = PASS + FAIL + SKIP + NOT_RUN` 自洽。
未运行项（如 `src/fuzz/fhfuzzer` 需 `-lFuzzingEngine`，上游 `--enable-fuzzers` 默认 no）
写 **NOT_RUN + 技术原因**，不得写 PASS，也不得为了"跑起来"放开开关引入不可得依赖。

## 识别特征
- **Severity**: 🟠 High（子包 N 少报是硬 FAIL）
- **Trigger tool**: reviewers / configure / make check
- **Phase**: review
- **Pattern**: `--enable-(tests|werror)|CPPUNIT_TEST\(|check_PROGRAMS|noinst_PROGRAMS`
- **Category**: dlp, autotools, subpackage, test-accounting, review

## 修复方案（配方要点）

```python
def generate(self):
    tc = AutotoolsToolchain(self)
    tc.configure_args += ["--build=aarch64-unknown-linux-gnu",
                          "--host=aarch64-unknown-linux-gnu",
                          "--enable-static", "--disable-shared",
                          "--disable-werror"]          # 上游默认 yes
    tc.generate()

def build_requirements(self):
    self.tool_requires("cppunit/1.15.1")                # --enable-tests 默认 yes

def build(self):
    ...
    autotools.configure(); autotools.make(args=["-j1"])
    env = Environment(); env.define("HOME", os.path.join(self.build_folder, ".test-home"))
    with env.vars(self).apply():
        autotools.make(target="check", args=["-j1"])    # 上游用例真实运行
```

## 参考实现
- `archives/l/libfreehand-tools/0.1.2/`（本条目来源；含 `--disable-werror` + `make check`）
- `archives/l/libmspub-tools/0.1.4/`（同族 -tools 子包形态：la-free shadow、sanitize PATH、commands.json）
- `knowledge/drafts/DRAFT-10251-libnfc-tools-1.8.0-autotools-test-framework-guard.md`
  （另一 -tools 子包因"用例 6 个一个也没测（0/6）"被判不通过的对照案例）

## 验证方法
1. 构建日志出现 `test::<Suite>::<case> : OK` / `OK (N)` / `PASS test (exit status: 0)`，
   以及 automake 汇总 `# TOTAL: 1 # PASS: 1 # FAIL: 0`
2. `grep -c "CPPUNIT_ASSERT"` / `grep -c "CPPUNIT_TEST("` 的读数写进 notes 与 PR（同单位）
3. NOT_RUN 项在 notes / PR / `test_package/MANIFEST.yml` 三处一致，附不可得依赖的实测命令与读数
4. 提审前自核：声明 N ≥ 父 tarball 任一候选口径读数；台账 `TOTAL = PASS + FAIL + SKIP + NOT_RUN`
