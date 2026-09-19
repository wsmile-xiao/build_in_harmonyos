# ConanFile.run() 继承输出流 → OHOS 上 clang 静默失败

配套草稿：`knowledge/drafts/DRAFT-libncurses-6.6-conan-run-log-bound-steps.kv`

## 现象

Autotools 配方在 `build()` 里用 `self.run("make -j1 SHELL=/bin/sh", cwd=work, env=None)`
驱动构建时，OHOS worker 上在**第一个真正编译的翻译单元**处失败：

```
/data/service/hnp/bin/clang -o make_hash -DHAVE_CONFIG_H -DUSE_BUILD_CC ... tinfo/make_hash.c
make[1]: *** [Makefile:270: make_hash] Error 1
make: *** [Makefile:131: all] Error 2
...
ERROR: libncurses/6.6_p20260516: Error in build() method, line 83
	ConanException: Error 2 while executing
```

关键特征：**日志里搜不到任何 `error:` / `fatal error` 行**，看起来像 `make_hash`
这个目标自身坏了，实际是编译器被静默终止。ncurses 的 `make_hash` 只是碰巧是构建里
最早的编译单元（Autotools 引导程序用 `$(BUILD_CC)` 先编译），所以"第一个倒下的"
就是它。

## 定位

1. 在同一构建目录手工执行日志里那条完整 clang 命令 → `rc=0`，产出 `make_hash`，
   `./make_hash "-?"` 也 `rc=0`。
2. 逐项排除：把 conan 生成的环境变量（`CC`/`CFLAGS`/`CPPFLAGS`/`LDFLAGS`/
   `LD_LIBRARY_PATH`/`TMPDIR`/`PATH`/`PWD`/`PKG_CONFIG_PATH`）原样喂给
   `env ... make make_hash` → 仍然成功。**环境不是原因。**
3. 用探针配方（复用同一已 configure 的构建目录）对照 5 种调用方式：

| 变体 | 调用方式 | 结果 |
|---|---|---|
| A | `self.run(cmd, env=None)` | `rc=2`，无二进制 ❌ |
| B | `self.run(cmd)`（默认 env） | `rc=2`，无二进制 ❌ |
| C | `self.run(cmd + " \| cat", env=None)` | `rc=0`（管道吞掉 make 的 rc，不可依赖）|
| D | `self.run(cmd + " > log 2>&1", env=None)` | `rc=0`，生成 make_hash ✅ |
| E | `subprocess.run(cmd, capture_output=True, env=os.environ.copy())` | `rc=0`，生成 make_hash ✅ |

A/B 与 C/D/E 的唯一差别是**子进程的输出流去了哪里**：`ConanFile.run()` → `conan_run()`
默认把 recipe 进程的输出流（`stdout=sys.stderr`）交给子进程。继承该流时编译器静默
失败；把输出重定向到文件（D）或由 Python 捕获（E）就正常。

## 处置

给每个构建步骤绑定独立日志文件，并把日志回显进 conan 输出：

```python
log_path = Path(root) / "logs" / f"{label}.log"
log_path.parent.mkdir(parents=True, exist_ok=True)
try:
    self.run(f"{command} > {shlex.quote(str(log_path))} 2>&1", cwd=work, env=None)
except ConanException as error:
    self.output.error("\n".join(tail_of(log_path)))
    raise ConanException(f"OHOS build step '{label}' failed, full log: {log_path}") from error
```

要点：

- **不要**用 `cmd | cat` 作为"旁路"（E009 的形态）：管道末端是 `cat`，其退出码会掩盖
  make 的失败，必须另外显式取 make 的 rc，否则失败会被静默吞掉。
- 成功时把日志回显进 conan 输出，CI 侧 `L1b/L1c` 会 grep `clang` / `make ... check`
  之类的痕迹，全部重定向进文件会让这些证据从构建日志里消失。
- 失败时回显日志尾部并抛出**带日志路径**的异常，把"静默失败"变成可诊断失败。

## 验证

```bash
# 采用日志绑定后，四步全部可复现通过
conan create archives/l/libncurses/6.6_p20260516 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
