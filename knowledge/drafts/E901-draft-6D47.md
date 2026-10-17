# E901 — musl 系目标（含 OHOS）上 `-D_FORTIFY_SOURCE` 使二进制在装载阶段失败

## 错误特征

编译、链接、打包**全部成功**，`conan create` 的 build/package 阶段无任何告警，
但一旦真实执行二进制，动态装载器报：

```
Error relocating /.../bin/worklog: __vsprintf_chk: symbol not found
Error relocating /.../bin/worklog: __strcat_chk: symbol not found
```

或链接期直接：

```
undefined symbol: __vsprintf_chk
```

`nm -D --undefined-only <bin>` 里出现 `U __vsprintf_chk` / `U __strcat_chk` /
`U __strlen_chk` 这类**下划线开头的 glibc fortify 变体**。

## 触发条件

- 上游构建脚本硬写 `-D_FORTIFY_SOURCE=1/2/3`（常见于老 Makefile 项目）。
- 目标平台 libc 为 **musl 系**（OHOS / OpenHarmony、部分嵌入式 Linux）。
- 产物需要 `sprintf` / `strcat` / `strlen` / `memcpy` 等会被 fortify 重定向的调用。
- ⚠️ 关键隐蔽性：**只跑 `conan create` 的 rc 抓不到**——必须真实执行二进制
  （`test_package` 里 `self.run(...)`）才暴露。本条即由 test_package 实测发现。

## 根因分析

`_FORTIFY_SOURCE` 是 **glibc 专有**加固机制：启用后 glibc 头文件把
`sprintf` / `strcat` / `strlen` 改写为调用带边界参数的 `__vsprintf_chk` /
`__strcat_chk` / `__strlen_chk`。

OHOS 的 libc 是 musl 系。`nm -D --defined-only` 实测其 `__*_chk` 导出**只有
`__stack_chk`**（栈保护，与 fortify 无关），**不提供**上述 glibc fortify 变体。
clang 预处理阶段只认 `-D_FORTIFY_SOURCE` 这个宏名，并不校验目标 libc 是否实现，
于是照常生成对 `__*_chk` 的调用引用 → 链接期（静态库场景漏过）或装载期（动态场景）失败。

**判据**：
```bash
nm -D --defined-only <目标平台 libc.so> | grep -oE '__[a-z]+_chk' | sort -u
# musl / OHOS → 仅 __stack_chk
```

## 解决方案

### 推荐方案

在**追加型** CFLAGS 变量里用 `-U_FORTIFY_SOURCE` 抵消上游宏，并用
`-fstack-protector-strong` 保留栈保护加固：

```bash
make CC=<clang> EXTRA_CFLAGS='-U_FORTIFY_SOURCE -fstack-protector-strong'
```

**顺序要求**：`-U_FORTIFY_SOURCE` 必须排在 `-D_FORTIFY_SOURCE=2` **之后**
（即上游 CFLAGS 之后追加）。若排在之前会被随后的 `-D` 重新定义回去。

conan 配方侧对应写法（`EXTRA_CFLAGS` 由补丁提供为 `CFLAGS+=` 追加，不覆盖上游）：
```python
extra_cflags = " ".join(
    ["-U_FORTIFY_SOURCE", "-fstack-protector-strong"] + [f"-I{d}" for d in nc.includedirs]
)
```

### 备选方案

保留 fortify 但**自实现**缺失的 `__*_chk`（不推荐：偏离上游语义、维护成本高）。

### 禁止做法

- ❌ 直接整体覆盖上游 `CFLAGS` 来"顺手"去掉 `-D_FORTIFY_SOURCE`：
  上游 CFLAGS 常含需要 shell 二次引号的 `-DVERSIONS=\"x.y\"`，
  整体覆盖会破坏字符串字面量语义导致编译错或运行期显示错版本号。
  应改为**追加** `-U_`。
- ❌ 认为"编译链接过了就没事"——本条的核心教训就是装载期才炸。
- ❌ 用改上游源码（删 `-D_FORTIFY_SOURCE`）替代构建变量注入：
  扩大改动面、破坏可复现性。

## 验证

```bash
# 1) 确认不再引用 glibc 专有 fortify 符号
nm -D --undefined-only <bin> | grep -i '_chk'     # 期望：只剩 __stack_chk*

# 2) 确认栈保护仍在（加固未被削弱）
nm -D --undefined-only <bin> | grep stack_chk     # 期望：__stack_chk_fail / __stack_chk_guard

# 3) 确认动态依赖没有意外引入
readelf -dW <bin> | grep NEEDED
```

worklog 2.1 实测结果：`__stack_chk_fail` + `__stack_chk_guard` 存在、
无 `__*_chk` fortify 引用、`NEEDED` 仅 `libc.so`、全 RELRO、PIE、GNU_STACK 不可执行。

## 关联条目

- 实证：worklog 2.1（`archives/w/worklog/2.1`）——`patches/0001-Makefile-honour-CC-and-EXTRA_CFLAGS.patch`
  提供 `CFLAGS+=`/`LDFLAGS+=` 追加点，配方注入 `-U_FORTIFY_SOURCE -fstack-protector-strong`。
- 相关：ncurses 静态链接的运行期 terminfo 路径问题（见 worklog notes.md「已知限制」）。
- 原则：P001（鸿蒙是原生编译环境，不是交叉编译）——但 libc 仍为 musl 系，本条同样适用。
