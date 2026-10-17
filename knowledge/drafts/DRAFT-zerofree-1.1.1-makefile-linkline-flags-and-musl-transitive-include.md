# DRAFT: 手写 Makefile 的链接行只带 `$(CFLAGS)` —— 交叉编译时依赖包的 `-I`/`-L` 传不进去，musl 下还会连 `<sys/types.h>` 都不传递

> Contributor: username- | Status: DRAFT | Created: 2026-09-19
> 来源: zerofree 1.1.1 适配（`Makefile` 全文 6 行；`zerofree.c` 依赖 libext2fs）

## 症状

上游是个"极简 Makefile"工程（zerofree 1.1.1 的 Makefile 全文只有 6 行）：

```make
CC=gcc
all: zerofree.c
	$(CC) $(CFLAGS) -o zerofree zerofree.c -lext2fs
```

在 OHOS 交叉编译时连续踩两个坑，**报错位置在编译期/链接期，但根因都在于这份
Makefile 没有遵循 autotools 的 flags 约定**：

```
# 坑 1：编译期
zerofree.c: In function 'main':
zerofree.c:190:5: error: unknown type name 'dev_t'
zerofree.c:191:5: error: unknown type name 'mode_t'
zerofree.c:199:1: warning: implicit declaration of function 'umount'

# 坑 2：链接期
/…/ld.lld: error: unable to find library -lext2fs
```

## 根因

1. **`CC=gcc` 是硬编码**，交叉工具链进不来（`CC?=gcc` 才能被环境/`make CC=` 覆盖）。
2. **链接行只带 `$(CFLAGS)`**：`$(CPPFLAGS)`（含依赖包的 `-I`）、`$(LDFLAGS)`
   （含 `-L`）、`$(LDLIBS)`（含被 libext2fs 间接引用的 `-lcom_err`、`-luuid`）
   全部没有位置可以注入。
3. **`<sys/types.h>` 的传递包含差异**：在 x86-64 glibc 上，`<ext2fs/ext2fs.h>` 会
   间接把 `sys/types.h` 拉进来，`dev_t`/`mode_t` 于是在本机"碰巧"可用；OHOS 用的
   是 musl，**musl 的头文件不传递包含 `sys/types.h`**，同一份源码立刻报
   `unknown type name 'dev_t'`。这是"本机编得过、交叉编译编不过"的典型来源。

## 判据（两条，都不需要真机）

```sh
# 1) 链接行有没有 flags 注入点？
grep -nE '\$\(CC\)|\$\(LDFLAGS\)|\$\(LDLIBS\)' Makefile

# 2) 依赖库的头文件是否依赖传递包含？
grep -rl 'sys/types.h' /usr/include/ext2fs/ 2>/dev/null || echo "无传递包含 → musl 下会炸"
```

## 修法（可复用的补丁模式）

补丁 1 —— 让 Makefile 接受外部 flags，**次序刻意安排**：

```diff
-CC=gcc
+CC?=gcc
-	$(CC) $(CFLAGS) -o zerofree zerofree.c -lext2fs
+	$(CC) $(CPPFLAGS) $(CFLAGS) -o zerofree zerofree.c $(LDFLAGS) -lext2fs $(LDLIBS)
```

- `-lext2fs` 放在 `$(LDFLAGS)` **之后**：`-L<依赖包 lib>` 先生效；
- `-lext2fs` 放在 `$(LDLIBS)` **之前**：它自己引用的 `com_err`/`uuid` 符号随后
  才能被解析（GNU ld 单遍扫描，顺序错就是 `undefined reference`）。

补丁 2 —— 对传递包含的差异，让源码**自己显式包含**：

```diff
 #include <stdio.h>
+#include <sys/types.h>   /* dev_t / mode_t：musl 不会经由 ext2fs.h 传递包含 */
 #include <ext2fs/ext2fs.h>
```

配方侧对应写法：源码里**不要**靠 shell 变量取编译器，按 R33 从
`tools.build:compiler_executables` 取，再用 `make CC=… CPPFLAGS=… CFLAGS=… LDFLAGS=… LDLIBS=…`
把值传进去。

## 与现有条目的边界

- `E063` / `E158`：分别是 `-Werror` 把警告转错误、以及 `GNUmakefile` 里头文件缺失的
  具体案例，都不涉及"链接行没有 flags 注入点"这一结构性问题；
- `E313`（Ruby C 扩展 + musl + `stdckdint.h`）：同属"musl 与 glibc 的头文件差异"，
  但那是 C23 头文件缺失、修法是降标准/补 shim；本条修的是**链接行 flags 缺口**，
  musl 的传递包含差异只是同一份 Makefile 上的第二个症状；
- `E491`/`E289` 属于 autotools 的 `install` 侧问题，与本条（编译/链接侧）不同层。

## 上游测试情况

zerofree 1.1.1 上游没有任何自动测试（`Makefile` 只有 `all` 与 `clean` 两个目标），
N=0；本条的验证靠配方自带的 test_package（14 条断言，含真实 1 MiB ext2 镜像上的
端到端闭环：干跑报告几何信息 → 真实运行 → 复核脏块归零、空闲块数不变 → `-f 255`
非零填充）。
