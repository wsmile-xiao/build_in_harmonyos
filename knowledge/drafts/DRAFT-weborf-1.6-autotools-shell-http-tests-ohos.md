# draft-weborf-1.6-autotools-shell-http-tests-ohos

> 结论：**上游测试是 "autotools `TESTS` + shell 脚本 + `curl` 打自己起的本机 HTTP 服务" 时，
> OHOS 上有三处必撞的平台偏差，且它们的排查顺序决定成败。**
> 逐条都在 weborf/1.6（任务 11856）上实测翻口，非推測。

## 症状

### 失败一：`make check` 一上来就 14/15 挂，报 "No such file or directory"（exit 126）

```
$ make check
./build-aux/test-driver[119]: ./testsuite/version_and_help: No such file or directory
FAIL testsuite/version_and_help (exit status: 126)
# TOTAL: 15   # PASS: 1   # FAIL: 14
```

手工 `bash testsuite/site1http` 却能跑通 12/15 —— **差别只在 shebang**：
14 条脚本写 `#!/bin/bash`，而本机 `ls -l /bin/bash` → No such file or directory（只有 `/bin/sh`）。
driver 是直接 exec 测试文件的，于是得到 ENOENT ⇒ 126。

### 失败二（把 `TESTS_ENVIRONMENT` 当解释器注入点会踩的坑）

```
$ make check TESTS_ENVIRONMENT=bash
/bin/sh: /bin/sh: cannot execute binary file
make: *** [Makefile:1167: testsuite/version_and_help.log] Error 126
```

生成的 Makefile 里：

```
LOG_DRIVER  = $(SHELL) $(top_srcdir)/build-aux/test-driver
LOG_COMPILE = $(LOG_COMPILER) $(AM_LOG_FLAGS) $(LOG_FLAGS)
am__check_pre = … \
                $(AM_TESTS_ENVIRONMENT) $(TESTS_ENVIRONMENT)     # ← 在整个驱动之前展开
```

`TESTS_ENVIRONMENT` 的语义是**环境变量赋值序列**（`VAR=val VAR2=val2`），不是命令前缀；
塞一个命令进去，就变成 `bash /bin/sh test-driver …` ⇒ bash 去"执行" `/bin/sh` 这个 ELF。
**正确注入点是 `LOG_COMPILER`**：

```
$ make check -j1 LOG_COMPILER=bash        # 经 LOG_COMPILE 只包住 $$tst
Testsuite summary: # TOTAL: 15  # PASS: 15  # FAIL: 0
```

### 失败三：链上 openssl + libmagic 之后，15 条又全挂，且征象极像"沙箱禁网络"

| 症状 | 读数 |
|---|---|
| 进程 | `alive=Y`、banner 已打印、state=S |
| 端口 | 12 秒轮询 `http_code=000`，从未应答 |
| 手工 `./weborf -b site1 -p PORT` | 同上（`-k` 却显示 `mime:yes https:yes`） |

四臂对照（同一脚本、同一环境、只变链接集合）定位：

| 臂 | 未设 `MAGIC` | 设 `MAGIC=<pkg>/share/misc/magic.mgc` |
|---|---|---|
| 不链 | http=200 | http=200 |
| 仅 magic | **http=000** | http=200 |
| 仅 ssl | **http=000**（`-k` 因 `ac_cv` 覆盖也报 mime:yes） | http=200 |
| 两者 | **http=000** | http=200（HTTPS 往返亦 200） |

⇒ 根因是 **Conan 的 libmagic 制品只有静态 `libmagic.a`**，其编译期写死的 magic 数据库路径在
OHOS 不存在，`magic_open/magic_load` 走不通，程序停在 `listen()` **之前**；
与 openssl 无关。**"进程活着但端口从不应答"不能直接归因沙箱/网络限制。**

## 顺带撞到的两枚静态库副作用

- `ld.lld: error: duplicate symbol: buffer_init`
  —— `libmagic.a` 导出通用名 `buffer_init`，与 weborf 内部 `buffered_reader.c` 的同名函数相撞。
  定位方法（比猜快）：

  ```
  llvm-nm -g --defined-only *.o            | awk '$2~/[TDB]/{print $3}' | sort -u > o.txt
  llvm-nm -g --defined-only <pkg>/lib/*.a  | awk '$2~/[TDB]/{print $3}' | sort -u > l.txt
  comm -12 o.txt l.txt          # → 本例恰 1 个符号
  ```

  修法给程序侧改名（定义 1 + 声明 1 + 调用 2），不改行为。
- `musl 无 rindex`：`ld.lld: error: undefined symbol: rindex` → `strrchr`（E048 家族既有草稿已覆盖）。
- `make check` 必须 `-j1`：jobserver 的 `mkfifo` 在 HMDFS 上 `Operation not permitted`（E074）。

## 修复（配方落地形态）

```python
def _test_env(self):
    env = Environment()
    # ① curl/bash 都不在 ssh/conan 的非交互 PATH
    env.prepend_path("PATH", [d for d in (expanduser("~/.harmonybrew/bin"),
                                          expanduser("~/usr/local/bin"),
                                          "/usr/local/bin", "/usr/bin", "/bin")
                              if os.path.isdir(d)])
    # ② 被测二进制在构建树里跑，需找到依赖 .so
    env.prepend_path("LD_LIBRARY_PATH", libdirs_of_deps)
    # ③ 上游测试硬编码解释器绝对路径 ⇒ 暴露成可注入变量（默认值与上游逐字相同）
    env.define("WEBORF_CGI_PYTHON", shutil.which("python3"))
    # ④ 静态库的运行时数据文件必须显式指路
    env.define("MAGIC", self._magic_db())        # <libmagic>/share/misc/magic.mgc
    return env

if not cross_building(self):
    with self._test_env().vars(self, scope="build").apply():
        autotools.make(target="check", args=["-j1", "LOG_COMPILER=bash"])
```

数据路径要在**消费期**也可用，但不能在 `package_info()` 里直接取依赖的 `package_folder`
（`conan create` 末尾走 "Skipped binaries" 通道时它是 `None` ⇒ `TypeError`）。
可用登记文件的方式解耦：

```python
def package(self):
    …
    mgc = self._magic_db()                       # 此处依赖图完整
    if mgc:
        save(self, os.path.join(self.package_folder, "res", "magic.path"), mgc)

def package_info(self):
    marker = os.path.join(self.package_folder, "res", "magic.path")
    if os.path.isfile(marker):
        mgc = load(self, marker).strip()
        if mgc and os.path.isfile(mgc):
            self.runenv_info.define_path("MAGIC", mgc)
            self.buildenv_info.define_path("MAGIC", mgc)
```

## 排查顺序（下次照这个顺序做，别倒过来）

1. `grep -n -A 20 '^TESTS' Makefile.am` ⇒ **先按注册口径数清分母**（weborf 是 15 条，
   不是任务书写的 4 条；`functions.sh` 被上游自己列进 TESTS，也要如实计入）。
2. `grep -c 'curl' testsuite/*` ⇒ 断言依赖的外部工具有哪些、在哪。
3. `ls -l` 每条 shebang 指向的解释器 ⇒ 不可得就用 **`LOG_COMPILER`**。
4. 先**不链可选依赖**跑一遍（拿到基线通过率），再逐个链上，用"设/不设数据文件环境变量"对照归因。
5. 撞 `duplicate symbol` 就用 `llvm-nm` 求交集，不要逐个猜符号名。

## 验证

`weborf/1.6` conan create 一次跑通：`RUN: make check -j1 LOG_COMPILER=bash` →
`# TOTAL: 15 / # PASS: 15 / # SKIP: 0 / # FAIL: 0 / # ERROR: 0`，15 条**逐条具名 PASS**，
其中 `site1https` 走真实 TLS 往返、`cgi` 走 `cgi.c` 的 `alarm()+execl()` 子进程路径；
消费者测试另计 1 程序 7 断言。

## 关联

- 任务 11856 ｜ 包 `archives/w/weborf/1.6`
- M15（hishell 吞 SIGALRM）同属 CGI/alarm 面：本条的 `cgi` 用例真实执行了 `execl`，
  但 weborf 在 `execl` 前先 `waitpid` 自建进程管理，未观察到 hishell 吞信号现象 ⇒
  **不据本包声称 M15 复现**。

## 与既有条目的关系（查重结论，不回避相似项）

draft-review 的相似 TOP3 是 **E201 / E165 / E049**。E201 与 E165 确实已经覆盖
"测试脚本需要 `/bin/bash` 而 OHOS 标准路径没有"这一半事实。本条申报的是**它们没有的三点**：

1. **换解释器的注入点判别**：`TESTS_ENVIRONMENT` 在 `am__check_pre` 末项、展开于整个驱动之前，
   语义是环境变量赋值序列；拿它当前缀会得到 `/bin/sh: cannot execute binary file`。
   唯一正确注入点是 `LOG_COMPILER`（经 `LOG_COMPILE` 只包住 `$$tst`）。E201/E165 均无此判别。
2. **归因方法**：链上静态可选依赖后"进程存活 + banner 已打印 + 端口 12 秒不应答"，
   必须用"设/不设该库运行时数据文件环境变量"的四臂对照才可归因，否则极易误判成沙箱/回环限制。
3. **符号撞名定位**：静态第三方制品导出通用名（本例 `buffer_init`）与程序内部同名 ⇒
   `lld duplicate symbol`；用 `llvm-nm -g --defined-only` 求交集一次定位。

E049 是"生成脚本硬编码解释器路径"的另一签名（不同解法）；E074、E011 为本条配套既有条目。
