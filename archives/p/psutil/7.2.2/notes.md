# psutil 7.2.2 适配笔记

## 编译环境

- 目标：`aarch64-unknown-linux-ohos`（profile: `ci/conan/profiles/ohos-aarch64`）
- 编译器：clang / clang++（`tools.build:compiler_executables`）
- Python：`python/3.12.9`（ohpcd 已发布，本地 cache rev `d8eda770878152bea40b42db9f7024cd`）
- 构建工具：`setuptools/84.0.0`（tool_requires）
- conan 2.29.1

## 本包为何存在

psutil 是 **greenlet 3.5.6（PR #10408）判定 rule4「缺依赖」** 的修复依赖之一：
greenlet 的 `tests/test_gc.py` 等用例在测试期裸 `import psutil`，未安装时
整批用例 skip（实测 162 passed/**10** skipped → 装后 166 passed/**6** skipped）。

本包与仓内其它 Python 包（setuptools/objgraph 等纯 Python）**性质不同**：
psutil 带 **C 扩展** `psutil/_psutil_linux.so`，必须真实编译，产物与
CPython ABI/arch 绑定。

## 编译步骤

```bash
# 1) 取源码 + 校验 sha256（conandata.yml，PyPI 官方 URL）
# 2) build()：依赖自带 python3.12 执行 setup.py build_ext --inplace
#    → PSUTIL_OHOS=1 CC/CXX + LDFLAGS="-fuse-ld=bfd -L<py_lib> -lpython3.12"
# 3) build()：对 psutil/*.so 签名（HMDFS 必需，否则 dlopen 报 Permission denied）
# 4) build()：真实运行上游 pytest 套件（R51）
# 5) package()：拷入 lib/python3.12/site-packages → **再签一次**
# 6) package_info()：runenv_info/buildenv_info 声明 PYTHONPATH
```

## 遇到的问题与解决方案

### 问题 1：`platform ohos is not supported`

psutil 的 `setup.py` 末尾对未知平台直接 `sys.exit("platform ohos is not
supported")`，其分支表只认 linux/darwin/bsd/sunos/aix/windows。

**实测**：本平台 `sys.platform == "ohos"`（宿主 python 实测）。OHOS 是 musl
Linux ABI，故 `0001` 补丁把 `ohos` 映射到 Linux 分支。

**关键坑**：conan `python/3.12.9` 依赖自带的解释器实测 `sys.platform` 报
**`"linux"`**（宿主 python 才报 `"ohos"`）。因此**不能用 `sys.platform` 判定
是否 OHOS** —— 依赖它会让 `PSUTIL_OHOS` 永不定义、`utmpx` 守卫失效。改为由
配方显式注入环境变量 `PSUTIL_OHOS=1`。

### 问题 2：`struct sockaddr_storage` 重定义

`arch/linux/net.c` 同时引入 `<linux/if.h>` 与 `<sys/socket.h>`，而 OHOS sysroot
的两者都定义 `struct sockaddr_storage` → 编译报重定义。改用 libc 的
`<net/if.h>` 规避。

### 问题 3：sysroot 无 `<utmpx.h>`

OHOS sysroot 既无 `<utmpx.h>` 也无 `getutxent`/`setutxent`，`arch/posix/users.c`
无法编译。补丁引入 `PSUTIL_OHOS` 宏，把**启用守卫**与 `init.c` 中的**方法表
注册**一并 scoped out（只改守卫不改注册会留下悬空方法表项）。

### 问题 4（最耗时）：上游测试"看起来要跑 7 小时"，实际只要 33 秒

**这是本次适配最大的认知纠正。** 早先观测到"串行 40 分钟仅完成 65/704 项"，
线性外推得"约 7 小时"，据此改成 `-n 8` 并行；但并行下 8 个 worker 只有 1 个
在干活（实测 CPU 时间：一个 38 分钟，其余 0–12 秒），最终仍超时。

**真因（逐条实测复现）**：

| 现象 | 根因 | 证据 |
|------|------|------|
| 串行"卡住"、并行"某 worker 卡住" | `test_open_files_mode` **无限循环** | 该用例的 `giveup` 判定写在 `for file in p.open_files()` **循环体内**；OHOS 无 `/proc/self/fdinfo`（实测 `FileNotFoundError`）→ `open_files()` 恒返回空列表（实测 `num_fds()=13` 而同刻 `open_files()=0`）→ 循环体永不执行、退出条件永不判定 |
| 并行时失败清单全丢 | `test_sudo.py` 让 worker 被**硬杀** | `time.clock_settime()` 在 OHOS 触发 seccomp **SIGSYS(31)**（实测子进程 `WTERMSIG=31`）；上游期望 `except PermissionError → SkipTest` 不成立 → worker 死亡（`node down: Not properly terminated` ×18）→ xdist 抛 `INTERNALERROR` 并**吞掉 short test summary**（FAILED 行归零） |
| 并行的另一处崩溃 | `test_unicode.py` surrogate 序列化 | `funky_name` 含 surrogate → execnet `s.encode("utf-8")` 抛 `UnicodeEncodeError: surrogates not allowed` |

**修法**：改回**串行**，并 `--ignore=tests/test_sudo.py` +
`--deselect ...::test_open_files_mode`（二者会毁掉整个 run，仅列入
ALLOWED_TEST_FAILURES 不够）。修后实测 **700 项 / 33 秒**完成，完整可解析。

> 教训：受限平台上"轮询直到出现"的测试会**挂死**而非失败；遇到疑似慢/挂死，
> 应先串行跑一遍拿到逐项失败清单，而不是靠并行 + 外推，更不能用外推的耗时
> 当结论（xdist 还会在 worker 死亡时吞掉清单）。

### 问题 5：OHOS 权限模型导致大批用例失败（**非适配缺陷**）

失败按**四类平台根因**逐项归因（119 项清单，见 conanfile.py 注释）：

| 类 | 根因 | 实测证据 |
|----|------|---------|
| ① | `/proc` 以 **`hidepid=invisible`** 挂载 | `/proc/mounts` 实读 `procfs rw,gid=3009,hidepid=invisible`；`/proc/1/stat`、`/proc/1/status`、`/proc/1/cmdline` **全部 PermissionError**（自己的 `/proc/self/*` 正常）→ `ppid_map()` 抛 `AccessDenied`（46 处命中 `_pslinux.py:1575`） |
| ② | OHOS 未暴露 `/proc` 语义文件 | `/proc/self/fdinfo` 不存在；`/proc/filesystems`、`/proc/net/tcp`、`/sys/block`、`/sys/class/power_supply` 均 `PermissionError` |
| ③ | 内核版本串不可解析 | `uname -r` = `HongMeng Kernel 1.12.0`（无 major.minor 数字前缀）→ `tests/__init__.py:645` 的 `if not s: raise ValueError` |
| ④ | OHOS 自有 smaps 段 | `Name: [anon:native_heap:meta]` → `_pslinux.py:1981` 解析器不认 |

另有 **AF_UNIX bind 在本环境返回 EPERM**（实测 `PermissionError: [Errno 1]
Operation not permitted`）→ socket 类用例失败。

**注意失败计数在多轮间波动**（149 / 152 / 160），因此允许清单按**多轮实测
并集**给出（119 项）；否则 `conan create` 会随机失败。

### 问题 6：`_ctypes` 无法解析 libffi（测试解释器选择）

`python/3.12.9` 依赖自带的 `bin/python3.12`，其 `_ctypes` 加载失败：
`ImportError: ... _ctypes...so: ffi_prep_closure_loc: symbol not found`
（该包 `lib/` 下不带 libffi）。而 psutil 的 `tests/__init__.py:9` 顶层就
`import ctypes` → 19 个测试文件全部 ERROR 收集失败。

**修法**：跑 pytest 用**宿主解释器**，编译仍用依赖自带解释器。两者同为
CPython 3.12 / aarch64-linux-ohos，ABI 兼容，编出的扩展可互用。

### 问题 7：pytest 插件与 basetemp

- 上游 `pyproject.toml` 的 `addopts` 强制 `--instafail`，故测试期必须提供
  `pytest-instafail`；缺了会在 preparse 阶段抛 `ImportError: Error importing
  plugin "instafail"`（此时退出码非 0 但输出无 FAILED 行）。
- `tests/test_memleaks.py:14` 顶层 `from psleak import MemoryLeakTestCase`，
  不装 `psleak` 会**中断整个 session**（实测 `collected 597 items / 1 error`
  → Interrupted），并非只失败 1 项。
- pytest 默认 basetemp 的属主检查在 OHOS 必然 `INTERNALERROR`（新建目录属主被
  文件系统强制显示为挂载属主 20001006）→ 传 `--basetemp` 走 `_given_basetemp`
  分支绕过（meson / setuptools 先例）。
- 宿主装了 pyfakefs 会在自动加载期调 `sysconfig.get_path("stdlib")` 报
  `_sysconfigdata__linux_aarch64-linux-ohos` 缺失 → 用
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 屏蔽，所需插件显式 `-p` 指定。

## 源码修改

单一补丁 `patches/0001-ohos-linux-platform-support.patch`：

1. 平台分支表加入 `ohos`（映射到 Linux）；
2. `<linux/if.h>` → `<net/if.h>`（规避 `sockaddr_storage` 重定义）；
3. 引入 `PSUTIL_OHOS` 宏，scoped out `arch/posix/users.c` 的启用守卫**与**
   `init.c` 的方法表注册。

## 依赖版本

| 包 | 版本 | 类型 | 说明 |
|----|------|------|------|
| python | 3.12.9 | requires | 扩展链接 libpython3.12 必需 |
| setuptools | 84.0.0 | tool_requires | setup.py 顶层 import；3.12 无 stdlib distutils |

测试期依赖（未发布 ohpcd，故构建期从平台 pip 镜像取）：pytest>=6、
pytest-instafail、pytest-xdist、psleak。

> `package_type` 为 `library` 而非 `python-require`：`python/3.12.9` 传递带入
> libffi（static-library），而 `python-require` 类型禁止依赖带类型的库
> （`ERROR: Package 'psutil/7.2.2' with type 'python-require' cannot have a
> 'static-library' dependency to 'libffi/...'`）。与仓内 lxml 6.1.1 / greenlet 一致。

## 验证结果

```bash
# 完整本地验证（profile: ci/conan/profiles/ohos-aarch64）
conan create archives/p/psutil/7.2.2 --profile:host=ci/conan/profiles/ohos-aarch64
```

- 上游 pytest：**152 failed, 278 passed, 279 skipped, 1 deselected, 1 error**
  （collected 700 items；串行 33 秒；失败全部为上述四类平台根因 + EPERM）
- 消费者测试：**18/18 passed**
- 扩展模块：编译 + 签名成功，`psutil._psutil_linux` 真实 dlopen

## 注意事项

1. **`--ignore=tests/test_sudo.py` 与 `--deselect test_open_files_mode` 不可
   删除**：前者会让 worker 被 SIGSYS 杀死，后者会无限循环，二者都会使
   `conan create` 超时/失去失败清单。
2. **允许清单按多轮并集**：单轮清单会因 TLS 字节抖动式的差异而漏项，导致
   `conan create` 随机失败。
3. `PSUTIL_OHOS` 由配方注入，**不要**改回用 `sys.platform` 判定（conan
   python 报 `linux`）。
4. 签名两处都要保留：`build_ext` 后一次（pytest 前）、`package()` copy 后
   再一次（`copy()` 会使既有 ELF 签名失效）。
5. `psutil.users()` 不可用（无 `<utmpx.h>`）是本配方的**有意守卫**，
   消费者测试已按 `NotImplementedError` 接受。
