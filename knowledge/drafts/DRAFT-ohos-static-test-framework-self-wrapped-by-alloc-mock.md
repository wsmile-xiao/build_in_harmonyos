# 测试框架若**静态**链入，其自身 `calloc/malloc` 也会被 `-Wl,--wrap=calloc` 拦截 → 每个用例 SIGSEGV

## 现象

用 `--wrap` 给被测代码的内存分配打桩时，**连最平凡的用例也崩溃**，且栈上全是桩函数：

```
FAIL test/unit/tctildr-getinfo (exit status: 139)      # 139 = 128 + SIGSEGV

__wrap_calloc
```

迷惑点在于：失败信息指向 `__wrap_calloc`（桩函数本身），很容易被误判为
"测试桩写错了"，实则是**链接形态**问题。

实测案例：tpm2-tss 4.2.0（`archives/t/tpm2-tss/4.2.0`）的 `test/unit/tctildr-getinfo.c`，
用 `-Wl,--wrap=calloc` 模拟分配失败分支 → **8/8 用例全部 rc=139**，
其中包括不涉及被测分配逻辑的平凡用例。

## 根因

`-Wl,--wrap=calloc` 的语义是：把本**链接单元**内对 `calloc` 的未定义引用重定向到
`__wrap_calloc`。

若测试框架与被测代码**一起静态链接进同一个可执行文件**（例如 `libcmocka.a`），
那么框架自身的簿记分配——建测试链表、分配 fixture、注册断言上下文——**也会走
`__wrap_calloc`**。而该桩函数的设计意图是「从 mock 队列取出给**被测代码**的预置
返回值」，框架于是拿到完全不相干的指针 → 立即 SIGSEGV。

## 决定性判据（秒级）

**同一个测试程序，只换框架的链接形态**：

```sh
# 静态框架
$CC -I<fw>/include t.c <fw>/lib/libcmocka.a -Wl,--wrap=calloc -o p_static
./p_static ; echo $?      # → 139（崩溃）

# 动态框架
$CC -I<fw>/include t.c <fw>/lib/libcmocka.so -Wl,--wrap=calloc \
    -Wl,-rpath,<fw>/lib -o p_shared
./p_shared ; echo $?      # → 0（正常，用例全 PASSED）
```

用真实用例验证同样如此：`tctildr-getinfo` 静态 cmocka → 8/8 rc=139；
动态 cmocka → **12/12 PASSED**。根因确认。

> 补充判据：**若是本缺陷，连平凡用例也崩**。若只有特定用例失败，则应怀疑
> 测试逻辑或 mock 队列顺序，而非本条。

## 为什么在 conan 下尤其隐蔽

多数配方的测试框架依赖用 `test_requires`，而 conan 默认取 `shared=False` 的变体。
实测 ohpcd 上 `cmocka/2.0.2` **只有 `shared: False` 一个变体**，所以默认必命中此坑，
且编译期**无任何告警**——问题只在链接形态上体现。

## 修复方案（推荐）

让测试框架以**共享库**形态链入：

```python
# 在消费者配方里为框架依赖指定 shared 变体
default_options = {
    "shared": True,
    "fPIC": True,
    "cmocka/*:shared": True,      # ← 关键
}
```

框架内部的分配调用在编译进 `.so` 时已绑定，不会被可执行文件的 `--wrap` 重定向；
而 `--wrap` 仍能正常拦截**被测代码**（它被静态链进可执行文件）的调用。

**⚠ 两个配套要点**：

1. 共享框架使测试二进制运行期需要 `libcmocka.so.0`。其 `.pc` 的 RUNPATH 方案在 OHOS 上
   不可靠（实测全部 `exit status: 127`，`Error loading shared library libcmocka.so.0`），
   须显式注入 lib 目录——且**必须作为 `make` 命令行变量**传入
   （`self.run(env=...)` 会被 conan 重新应用的 buildenv 覆盖）：

   ```sh
   make check -j1 LD_LIBRARY_PATH="<framework>/lib"
   ```

2. 若同时用 `--wrap=<libc 函数>`，还需处理 `_FORTIFY_SOURCE` 的改写问题
   —— 见同族条目
   `DRAFT-ohos-fortify-source-defeats-libc-wrap-mock`。

**回退方案**：若框架无法用共享形态，改为只对被测代码应用打桩（把被测代码单独编成
静态库与框架分离，或用函数指针注入替代 `--wrap`）。代价通常更大。

## 禁止策略

- **不要**删除该用例 / 加 XFAIL / 跳过整个测试文件——用例本身有效，缺陷在链接形态。
- **不要**把 `__wrap_calloc` 直接转发到 `__real_calloc` 来"消除崩溃"——该桩函数原本
  用于模拟分配失败分支，直接转发会让这些用例永远测不到失败路径（看似通过，实则
  失去语义，属伪造通过）。

## 与同族条目的差异

与 `DRAFT-ohos-fortify-source-defeats-libc-wrap-mock` 同属「`--wrap` 打桩」家族，
但根因与判据都不同：

| | 本条 | 同族 fortify 条 |
|---|---|---|
| 根因层 | **链接期作用域**（框架自身被拦截） | **编译期改写**（符号名变了） |
| 判据 | 框架是静态 `.a` 还是动态 `.so` | `nm` 是否见 `__*_chk` |
| 修法 | 框架换 shared 变体 | 编译时加 `-U_FORTIFY_SOURCE` |

## 检测方法（预扫描）

测试 Makefile 中出现 `--wrap=(calloc|malloc|realloc|free)`，且框架依赖为静态
（`lib*.a` / conan `shared=False`）→ 预警本条。
