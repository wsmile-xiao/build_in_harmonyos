# E585 — 严格 ANSI（-ansi / -std=c89）让 musl 隐藏 POSIX 声明，隐式 int 截断 64 位指针：编译只有告警，运行即 SIGSEGV

## 错误特征

编译阶段（上游 `make linux` 口径 `-ansi -O`，不带 `-Wall`）只有这一类告警，构建成功：

```
tal.c:322:33: warning: cast to 'char *' from smaller integer type 'int' [-Wint-to-pointer-cast]
            opt->trailer.text = (char *) strdup (optarg);
```

加 `-Wall` 才能看到根源：

```
tal.c:322:42: warning: implicit declaration of function 'strdup' [-Wimplicit-function-declaration]
tal.c:838:19: warning: implicit declaration of function 'strcasecmp' [-Wimplicit-function-declaration]
```

运行阶段，处理第一行输入即崩溃：

```
qemu: uncaught target signal 11 (Segmentation fault) - core dumped    # 退出码 139
```

## 触发条件

- 构建系统: 手写 Makefile，按 OS 分发的平台目标（`make linux`/`sunos5`/…）或 CFLAGS 里固定 `-ansi`、`-std=c89`/`c90`
- 源码: 调用 `strdup`/`strndup`/`fdopen`/`popen` 等返回指针的 POSIX 扩展，且没有自行定义 `_POSIX_C_SOURCE`/`_XOPEN_SOURCE`/`_DEFAULT_SOURCE`/`_GNU_SOURCE`
- 平台: LP64 目标（HarmonyOS PC aarch64，musl）
- 阶段: 编译期静默，运行期崩溃

## 根因分析

1. `-ansi`（等价 `-std=c89`）使编译器预定义 `__STRICT_ANSI__`。
2. musl `features.h` 只在未定义 `__STRICT_ANSI__` 时才默认开启 `_BSD_SOURCE`/`_XOPEN_SOURCE`；于是 `string.h` 不再声明 `strdup`，也不再引入 `strings.h`（`strcasecmp`）。
3. C89 允许隐式函数声明，调用被当作返回 `int`。源码里的显式 `(char *)` 强转，把 clang 本应报错的 int→指针隐式转换（`-Wint-conversion`）降级成仅 `-Wint-to-pointer-cast` 告警。
4. aarch64 上 musl 分配器返回的堆地址高于 32 位可表示范围，返回值被截断为 32 位再符号扩展，第一次解引用即 SIGSEGV。tal 1.9 实测：`-static` 与 `-static-pie` 两种链接方式都会崩溃。
5. 在 int 与指针同宽的 ILP32 平台上截断无害，所以上游当年的多平台测试从未暴露这个问题。

## 解决方案

### 推荐方案

不走带 `-ansi` 的上游平台目标，改用通用目标，保持编译器默认 C 方言，并把隐式声明升级为错误（无需补丁）：

```python
# conanfile.py build()（tal 1.9 实例；编译器取自 Conan conf，R33）
cflags = "-O2 -Werror=implicit-function-declaration -static-pie"
self.run(shlex.join(["make", "-j1", "tal", f"CC={cc}", f"CFLAGS={cflags}"]),
         cwd=self.source_folder, env="conanbuild")
```

`-Werror=implicit-function-declaration` 在 `-ansi` 下同样生效，任何人把 `-ansi` 加回来，都会在编译期得到 7 个错误，而不是一个会崩溃的二进制。

### 回退方案

上游确实需要严格 C89 语义时，保留 `-ansi`，追加 `-D_DEFAULT_SOURCE`（musl 由此打开 `_BSD_SOURCE`，`string.h` 重新声明 `strdup` 并引入 `strings.h`），仍配合 `-Werror=implicit-function-declaration`：

```bash
CFLAGS='-ansi -D_DEFAULT_SOURCE -O2 -Werror=implicit-function-declaration'   # tal 1.9 实测 15/15
```

注意：只加 `-D_XOPEN_SOURCE=700` 不够，`strcasecmp` 依旧是隐式声明（`string.h` 只在 `_BSD_SOURCE`/`_GNU_SOURCE` 下引入 `strings.h`）。

### 禁止做法

- ❌ 用 `-Wno-int-to-pointer-cast`、`-Wno-implicit-function-declaration`、`-Wno-error=int-conversion` 屏蔽诊断：指针截断仍在，只是被藏起来。
- ❌ 沿用 `make linux` 这类平台目标、只在外层覆盖 `CC`：平台目标内部递归 `$(MAKE) ... CC=gcc CFLAGS="-ansi -O"`，`-ansi` 不一定能被可靠去掉，`gcc` 也与交叉工具链冲突。
- ❌ 只看构建是否通过：必须真正执行产物（本例构建阶段零错误）。

## 验证

```bash
# 诊断：严格 ANSI 下 strdup 未声明（默认方言下同一命令编译通过）
printf '#include <string.h>\nint main(void){return strdup("x") != 0;}\n' \
  | clang -ansi -Werror=implicit-function-declaration -x c -c -o /dev/null - 2>&1 \
  | grep -q "implicit declaration of function 'strdup'" && echo "strict ANSI hides strdup"

# 修复后：产物实跑（tal 1.9：test_package 15/15；-ansi 口径产物同一脚本 4/15，11 项 SIGSEGV）
```

## 关联条目

- 相似: E213（musl 缺 `l64a`，同样提到隐式声明截断指针）、E420（依赖头拆分后的隐式 int，编译期报错形态）
- 冲突: E063（按类别关闭 `-Werror`：把 `-Wno-error=int-conversion` 用到本模式会掩盖崩溃）
- 相关草稿: DRAFT-E628-rtklib（`-ansi` 隐藏 `gethostbyname`，无显式强转时表现为编译错误）、E701-draft-6837（显式窄整数保存指针导致截断）
- 本条新增点: 显式 `(char *)` 强转把"编译错误"变成"仅告警"，问题推迟到运行期才暴露；给出编译期兜底（`-Werror=implicit-function-declaration`）与经实测的特性宏回退（`_DEFAULT_SOURCE`，而非 `_XOPEN_SOURCE`）
- 触发实例: tal/1.9（2026-09-24）
