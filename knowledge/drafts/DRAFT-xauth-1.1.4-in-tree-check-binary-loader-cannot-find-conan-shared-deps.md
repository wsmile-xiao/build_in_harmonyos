# DRAFT：automake 树内 `make check` 执行**刚链接出的**二进制，而它的共享依赖只在 conan 包目录里 → 加载器在 `main()` 之前就判死，全部场景「失败」

> 状态：草稿（待知识库主编 promote）
> 来源：xauth 1.1.4 适配，`archives/x/xauth/1.1.4`（任务 #5922）
> 类别：autotools / make-check / dynamic-linker / conan / run-environment / OHOS

## 错误特征

CI 报告「`make check` 失败」，摘要像极了断言不过：

```
FAIL: test_xauth
============================================================================
Testsuite summary for xauth 1.1.4
# TOTAL: 1
# PASS:  0
# FAIL:  1
```

但真正的原因藏在 `tests/test_xauth.log` 里 —— diff 的方向说明了问题：

```
--- out.stderr 与 090-xauth-bad-usage.stderr 的 diff ---
< Error loading shared library libX11.so.6: (needed by ../xauth)
< Error loading shared library libXext.so.6: (needed by ../xauth)
< Error loading shared library libXau.so.6: (needed by ../xauth)
< Error relocating ../xauth: XCloseDisplay: symbol not found
< Error relocating ../xauth: XGetErrorText: symbol not found
< Error relocating ../xauth: XOpenDisplay: symbol not found
...
---
> ../xauth: (argv):1:  key contains odd number of or non-hex characters
> ../xauth: (argv):1:  bad display name "bad4/unxi:0" in "add" command
> ../xauth: (argv):1:  bad display name "bad5/unix:" in "add" command
> ../xauth: (argv):1:  bad display name "bad7/unix" in "add" command
> ../xauth: (argv):1:  bad display name "127.0.0.:0" in "add" command
FAIL
```

**判据**：`>` 行是夹具（期望）里、实际产物里**一条都没有**的行。
夹具里每一行都成了 `>`，说明被测进程根本没有产生任何正常输出 ——
不是「行为不对」，是「没跑起来」。

## 根因

automake 的 parallel-tests 驱动（`check-TESTS` → `test-driver`）在**构建树内**
直接执行被测程序（xauth 的 `tests/test_xauth` 里就是一句 `../xauth "$@"`），
中间没有任何包装层。

而 conan 配方链接出来的二进制把 `libX11.so.6` / `libXau.so.6` 记成 `DT_NEEDED`：

```bash
llvm-readelf -d build/xauth | grep NEEDED
#  (NEEDED)  Shared library: [libX11.so.6]
#  (NEEDED)  Shared library: [libXext.so.6]
#  (NEEDED)  Shared library: [libXau.so.6]
```

这些 `.so` 只存在于 conan 的包缓存目录里，**不在** OHOS 加载器（musl `ld.so`）
的默认搜索路径上。而配方为 `make check` 准备的环境是 `conanbuild`
（`CPPFLAGS` / `LDFLAGS` / `PKG_CONFIG_PATH` 一类**编译期**变量），
**不含** `LD_LIBRARY_PATH`。

于是加载器在 `main()` 之前就拒绝启动进程，stderr 只留下
`Error loading shared library` / `Error relocating` 这一族报文。

### 为什么它伪装成「用例不通过」

`tests/test_xauth` 把每个场景的 stdout/stderr 重定向到文件再与随包夹具逐字节
`diff`。进程压根没跑，产物文件是空的，于是夹具的**每一行**都变成 diff 的 `>`
行 —— 报告成「N 个用例全 FAIL」。

这类失败还有两个特征，可用来与真正的断言失败区分：

| 特征 | 假失败（本条） | 真断言失败 |
|------|----------------|------------|
| diff 方向 | 夹具侧全是 `>`，实际侧只有 loading/relocating 报文 | 两侧都有内容，`<`/`>` 成对出现 |
| 换 worker | **同现象复现**（确定性缺环境变量） | 可能只在一个 worker 上出现（抖动） |
| 退出码 | 加载器判死（127 一类）而非被测程序的 1 | 被测程序自己的退出码 |

> 之所以强调「换 worker 复现」：xauth 这一轮 CI #53739（CI-016）与 #53741
> （CI-032）两个不同 worker 上日志一字不差 —— 这正是判定「不是执行环境抖动」
> 的硬证据。

## 修复

在 `build()` 里、`make check` 调用的**前后**设置/恢复 `LD_LIBRARY_PATH`：

```python
prior = {k: os.environ.get(k) for k in ("TMPDIR", "DATADIR", "LD_LIBRARY_PATH")}
os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
    self._dependency_libdirs()
    + ([prior["LD_LIBRARY_PATH"]] if prior["LD_LIBRARY_PATH"] else [])
)
try:
    autotools.configure()
    autotools.make(args=["-j1"])
    autotools.make(target="check", args=["-j1"])
finally:
    for key, value in prior.items():
        os.environ.pop(key, None) if value is None else os.environ.__setitem__(key, value)
```

`_dependency_libdirs()` 取**整张依赖图**：

```python
def _dependency_libdirs(self):
    result = []
    for _, dependency in self.dependencies.items():
        for path in dependency.cpp_info.aggregated_components().libdirs:
            if path not in result:
                result.append(path)
    return result
```

### 三个容易漏掉的点

1. **必须是整张图，不是链接行上的那几个包。**
   xauth 的链接行只有 `-lX11 -lXext -lXau`，但运行期 `ld.so` 要沿 `DT_NEEDED`
   递归找到 `libxcb.so.1` 与 `libXdmcp.so.6`：

   ```bash
   llvm-readelf -d <libX11 包>/lib/libX11.so.6 | grep NEEDED   # → libxcb.so.1
   llvm-readelf -d <libxcb 包>/lib/libxcb.so.1 | grep NEEDED   # → libXdmcp.so.6
   ```

   这两个包一个符号都不参与链接（在配方里是 run 依赖），却必须有路径。

2. **`os.pathsep` 拼接、原值放末尾。** 不要覆盖外部已有的 `LD_LIBRARY_PATH`
   —— CI worker 可能已经为 `libc++_shared.so` 设置过（同 ezstream 1.0.2 的处理）。

3. **作用域只包住测试调用。** `make install` / `package()` 不受影响；
   与 `TMPDIR`/`DATADIR` 的注入合并进同一张 try/finally 恢复表最省事。

## 备选方案

用 Conan 自己算运行环境：`generate()` 里 `VirtualRunEnv(self).generate()`，
或 `Environment` + `env.vars(self, scope="build").save_script(...)`
（同 `aaphoto/0.45`），然后 `source conanrun.sh && make check`。

语义上更「Conan 正统」（run 环境由 `cpp_info` 推导，依赖变了自动跟随），
代价是多一次文件往返、且要确认 `conanrun.sh` 与 `Autotools` 助手用的
`conanbuild` 环境不会互相覆盖。手拼 libdir 更短，且失败时能把**实际的**
`LD_LIBRARY_PATH` 打进诊断区（见下）。

## 取证建议

CI 只回传约 4000 字符的**日志尾部**，而这条线索出现在 automake
`Testsuite summary` **之前**，正好落在截断区外。配方里应保留「check 失败时
主动把 `tests/out.stdout` / `out.stderr` / `test_xauth.log` 倒到构建控制台」的
代码，并按「诊断价值倒序」打印（最有价值的放最后，保证落在保留区内）。
xauth 的实测：这样做之后，CI 日志尾部直接给出了上文的加载器报文与 diff 方向。

## 禁止事项

| # | 禁止 | 理由 |
|---|------|------|
| 1 | 把 `make check` 改成 `\|\| true` 或降级成 warning | 这是**假失败**，降级等于永久放弃上游回归套件（rule4 禁止因环境问题静默/降级跳过）；而且掩盖的恰是「二进制根本没跑起来」这种最严重的情形 |
| 2 | 只把参与链接的包拼进 `LD_LIBRARY_PATH` | 会漏掉仅被递归 `NEEDED` 的包（libxcb / libxdmcp），症状换个库名再来一轮 CI |
| 3 | 改 `tests/test_xauth` / `setup-sourced` / 夹具 | 夹具是逐字节比对契约的一部分，改动它等于把「验证上游行为」换成「验证我改过的行为」。本条的干预点全是运行期环境变量 |
| 4 | 用 `-Wl,-rpath,<conan 缓存路径>` 或 `patchelf --set-rpath` | conan 缓存路径是机器相关的绝对路径，烧进 ELF 会让产物不可重定位，也违反 conan 包「二进制可移动」的基本约定 |

## 关联条目

- `ezstream/1.0.2`：`make check` 14/14 FAIL、exit 127，根因同为本条 ——
  测试二进制动态链接 conan 依赖的 `.so`，`LD_LIBRARY_PATH` 未含包缓存目录。
- `aaphoto/0.45`：同机制但在 `configure` 的 conftest 阶段就爆发
  （conftest 链接共享 `libpng16.so.16` 后运行失败），解法同样是
  在 `generate()` 里注入依赖 libdir。
- `DRAFT-xauth-1.1.4-missing-pkgconfig-module-vendor-upstream-sublib`：
  同一次 xauth 适配的另一条**独立**教训（`xmuu` 模块无包 → vendored 最小闭包）。
  两者前后脚出现、都会表现成「`make check` 失败」，但一条在 configure/链接期、
  一条在测试运行期，诊断入口完全不同。
