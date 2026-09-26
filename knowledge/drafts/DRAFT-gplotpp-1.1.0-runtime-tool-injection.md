# DRAFT-gplotpp-1.1.0-runtime-tool-injection：header-only 库上游测试运行时工具注入（gnuplot）

> Contributor: pc4-46 | Status: Draft | Updated: 2026-09-26（R02 修订）
> Source: 【知识库扩展】gplotpp 1.1.0 适配（R01）+ R02 远端 CI 返工

## 背景

gplotpp 是 C++17 单头文件 Gnuplot 接口库：零编译产物（CMake INTERFACE 目标）、
零 Conan 依赖。但它的上游 doctest 套件（`tests/src/run_tests.cpp`，2 个
TEST_CASE）和任何消费者程序都要在**运行时通过 `popen` 驱动真实 `gnuplot`
可执行文件**。OHOS PC 没有系统 gnuplot；`conan create` 干净环境 PATH 里也
没有它。适配的关键不是编译（毫无难度），而是把外部运行时工具可靠地注入
上游测试与消费者用例，并且**在远端 CI 干净环境同样生效**。

## R02 关键教训：本地缓存注入在远端 CI 不成立

R01 仅在执行端本地把 gnuplot 从 conan2 缓存注入 PATH，`conan create`
本地通过；但远端 CI 干净环境没有该缓存 →
`GPLOTPP_GNUPLOT_BIN=NOT_FOUND`、`sh: gnuplot: inaccessible or not found`
→ 上游 `complex` 用例 popen 失败 → `complex.svg` 未生成 →
`CHECK( fin != nullptr )` 失败 → SIGABRT → `L1_RESULT=fail`。

**正确做法**：把运行时工具声明为配方级 `tool_requires`，让 CI 的
`conan create` / `build_and_test.sh` 自动从 ohpcd registry 拉取到构建
上下文，再通过 `self.dependencies.build["gnuplot"].package_folder` 定位
（本地缓存 glob 仅作兜底）。**严禁在工具缺失时静默跳过上游测试。**

## 坑 1：conan2 缓存目录名的截断前缀（glob 用 `gnu*` 而非 `gnuplot*`）

### 现象

```text
sh: gnuplot: inaccessible or not found
FATAL ERROR: test case CRASHED: SIGABRT - Abort (abnormal termination) signal
```

### 根因

从 ohpcd 制品仓下载的 `gnuplot/6.0.3` 解包在
`~/.conan2/p/<名称前缀+哈希>/p/bin/gnuplot`，实际目录名是
`gnupla03c6b9f7091e`（名称前缀被哈希截断）。用
`glob("~/.conan2/p/gnuplot*/p/bin/gnuplot")` 匹配不到任何路径。

### 修复

```python
glob.glob(os.path.join(home, ".conan2", "p", "gnu*", "p", "bin", "gnuplot"))
```

## 坑 2：HMDFS 忽略 chmod → `os.access(X_OK)` 恒 False（E046/R49 语义）

### 现象

`shutil.which("gnuplot")` 返回 None（PATH 里没有），缓存 glob 命中了路径，
但 `os.access(p, os.X_OK)` 为 False → 函数返回 None，PATH 没注入，测试仍失败。

### 根因

真机 `/storage` 是 HMDFS，忽略 POSIX chmod，权限固定 660，`X_OK` 探测
恒为 False（与 E046 "chmod 无效"、R49 "os.access(X_OK) 恒 False" 同一根因）。

### 修复

用 `os.path.isfile(p)` 过滤，不要用 `os.access(p, os.X_OK)`。

## 坑 3：Conan2 `self.run(env=...)` 只收列表 + CTest 不继承注入 PATH

### 现象

```text
AssertionError: env argument to ConanFile.run() should be a list
```

以及 `cmake.test()`（CTest）里消费者二进制找不到 gnuplot
（`0% tests passed`），即使配方层面已注入 PATH。

### 根因

Conan 2 的 `self.run(env=...)` 只接受 generator 名（如 `"conanrun"`）或
`VAR=VALUE` 字符串**列表**，传 dict 直接断言；CTest 在独立环境起子进程，
不继承配方注入的 PATH。

### 修复

测试入口一律命令内嵌 PATH：

```python
self.run('export PATH="%s${PATH:+:$PATH}"; "%s" --no-skip' % (gpdir, test_binary))
```

test_package 的 `test()` 同样直接 `self.run` 消费者二进制（不走 cmake.test()）。

## 坑 4：OHOS gnuplot 6.0.3 缺 gd 终端（gif animate 不可用）

### 现象

```text
gnuplot> set terminal gif animate delay 5 loop 0 size 800,600
         ^
line 0: warning: unknown or ambiguous terminal type
```

svg/png 终端可用，gif animate 不可用（缺 gd 支持）。

### 修复

消费者/鸿蒙专项测试断言改用 `redirect_to_svg`（SVG 文本标签可 grep）；
上游 animation 用例本身无断言（上游注释 "No checks, just try to compile"），
如实记录其 gif 输出为空，不计失败。

## R02 方案落地（tool_requires 驱动干净 CI）

```python
# conanfile.py（主配方）与 test_package/conanfile.py 均需：
def build_requirements(self):
    self.tool_requires("gnuplot/6.0.3")

# 定位优先走工具依赖 package 目录（CI 权威来源）：
def _find_gnuplot_bin(self):
    try:
        dep = self.dependencies.build["gnuplot"]
        p = os.path.join(dep.package_folder, "bin", "gnuplot")
        if os.path.isfile(p):
            return p
    except Exception:
        pass
    # ... 再 shutil.which、再缓存 glob（仅兜底）

# 找不到 gnuplot 时拒绝运行上游测试（禁止静默跳过）：
if not gnuplot_bin:
    raise RuntimeError("gnuplot not found; refusing to run upstream suite")
```

## 验证

- 上游测试：`[doctest] test cases: 2 | 2 passed | 0 failed`，
  `assertions: 5 | 5 passed`（R02 conan create 复验，GNUPLOT_BIN 检出
  `.../gnupla03c6b9f7091e/p/bin/gnuplot`）
- 消费者：test_package 直跑退出码 0，SVG 标签 `ConsumerSeries/X/Y` 核验通过
- 鸿蒙专项 test_ohos：4/4 通过（T1 ELF aarch64 / T2 musl / T3 无宿主路径 /
  T4 真实制图标签核验；T3 已修复 readelf -d 失败即 ERROR 的伪通过问题）
- W3 本地 CI：`Pass rate: 100% (1/1)`，`.ci-result.json` exit_code=0

## 适用边界 / 反例

- 适用：header-only / 无构建库中，上游测试或消费者用例需要 gnuplot 类
  外部运行时工具（matplotlib 前端、latex/dvgnip、wkhtmltopdf 等），且要求
  远端 CI 干净环境也能获得该工具。
- 反例：运行时工具本身作为 Conan `requires` 依赖注入（走 VirtualRunEnv +
  `env="conanrun"`）的库，不需要本方案的手工 PATH 注入。