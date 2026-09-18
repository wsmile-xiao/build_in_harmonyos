# E568 — 共享库静态烘入 static-only 依赖形成双实例：跨 DSO 释放 abort

## 错误特征

- `conan create` 的 `make check` 阶段大面积失败：`88 tests were run, 40 failed`（CI 侧为 `41 failed`）
- 失败用例的标准输出**为空**，日志只有 libtool 的 `Aborted (core dumped)` / `Signal 6`，看不到断言信息
- 手工运行失败用例：`RC=134`、`Signal 6 (core dumped)`，进程启动即死
- 用 `ptrace`-free 方式拦截 `abort()` 回溯调用点，落在依赖库内部：`__talloc_with_prefix+0x1d8` / `talloc_abort_access_after_free` 一类路径，符号 `_tc_free_internal`
- 依赖侧字符串证据：`Bad talloc magic value - unknown value`（talloc 的 magic 校验失败）

## 触发条件

- 构建系统: autotools（libtool 生成 `.la`，共享库 + 静态依赖混合链接）
- 阶段: testing / runtime（**编译、链接全绿**，只有运行期爆）
- 依赖形态: 制品仓的依赖**只有静态变体**（`libtalloc.a`，无 `shared` 选项、无 `.so` 制品）
- 结构条件: 消费者构建**共享库**，且依赖内部持「按实例随机化的全局状态」

## 根因分析

libtool 在构建 `libosmocore.so` 时，把依赖的静态库（`libtalloc.a`）整份烘进 `.so`：

- 生成的版本脚本（`*.map`）+ `-Wl,--exclude-libs` 使这些符号**不被导出** —— 实测
  `nm -D --defined-only libosmocore.so.22.1.0 | grep -c talloc` = **0**，即 `.so` 的使用者
  无法复用 `.so` 里的 talloc，也无法把 talloc 符号导出去重（`-Wl,--export-dynamic-symbol` 导出 **0** 个）。
- 上游测试程序又各自链接一份 `libtalloc.a`（`TALLOC_LIBS = ... -ltalloc`）。

于是同一进程里存在**两份 talloc 实例**（实测 `readelf -sW` 在 `.so` 与测试二进制中各有
`_tc_free_internal` 的 LOCAL 定义）。talloc 的每个 chunk 带 magic，且
`talloc_test_get_magic()` 的 magic 是**按实例随机生成**的（多实例同时存在时故意不固定）：

```c
/* talloc.c: 每实例 magic 随机化，用于检测跨实例/悬垂 chunk */
if (unlikely(tc->magic != talloc_get_magic(tc))) { ... abort(); }
```

libosmocore 的 API 会把 talloc 上下文跨模块传递（例如 `msgb` 分配于测试代码、由库内释放），
一旦跨实例释放 → magic 校验失败 → `abort()`。**任何链接旗标都无法修复**：符号在归档里就是
LOCAL（`nm libtalloc.a | grep _tc_free_internal` → 小写 `t`），链接层没有可见性可提升。

对照组（决定性证据）：生产者环境中 talloc 是**共享库**（`libtalloc.so.2`），
旧构建产物 `readelf -d` 显示 `NEEDED [libtalloc.so.2]`、`nm` 显示 `U _talloc_free@TALLOC_2.0.2`
—— 进程内只有一份 talloc，同一套测试 **88 passed / 2 skipped / 0 failed**。
即差异只在「talloc 实例数」，与源码/补丁无关。

## 解决方案

> **⚠️ 修订（2026-09-14 实测，libosmocore 1.11.0）**：下方「消费者改静态交付」方案已**证伪**——上游有 25 处 `on_dso_load(...)` 构造函数注册，静态归档不会拉入没有未定义符号引用的成员，插件/算法能力静默缺失（`gea_test` 输出 `GEA3 support: 0`，期望 1；8 项能力类用例失败）；改用 `-Wl,--whole-archive` 强制拉入后，上游测试里靠符号 interpose 打桩的用例反被库内定义抢占（失败 8→13 项），且上游源码中无任何 whole-archive 方案可参照。**正确做法 = 依赖侧发布 shared 变体**（R36 顺序：依赖先发布），消费者保持上游默认共享交付并如实上报 `dependency_missing`；下方正文仅作历史记录保留。

### 方案 A（已证伪）：消费者改静态交付（原推荐）

```python
package_type = "static-library"          # 移除 shared 选项（conan 要求 static-library 不得带 shared）
options = {"fPIC": [True, False]}        # 保留 fPIC
default_options = {"fPIC": True}         # 静态库需 PIC 才能链进 OHOS 应用原生共享模块

def generate(self):
    tc.configure_args.extend(["--disable-shared", "--enable-static"])
```

效果：每个最终二进制（上游测试 + 下游消费者）只含**一份**依赖实例，
等价于上游默认的「共享依赖」语义，测试结论与消费者行为一致。

判据（何时该选这条路）：

1. 依赖只有静态变体（`conan download <dep> -r=<remote>` 后 `ls` 仅见 `*.a`）；
2. 消费者是多 DSO 结构（库 + 程序、库 + 库）；
3. 依赖内部有按实例随机化/全局状态（talloc magic、分配器 arena、全局初始化表）。

### 回退方案：依赖侧先发 shared 变体

按 R36（依赖先发布再构建下游）由依赖包发布 `shared=True` 变体后，消费者回落共享交付。
前提是依赖配方本身支持 `shared` 选项且 registry 允许同版本新增变体；跨包阻塞，通常不可行。

### 禁止做法

- ❌ 把 `--enable-shared --disable-static` 留给「只有静态依赖」的场景：运行期必然 abort
- ❌ 试图用 `-Wl,--export-dynamic-symbol` / `--whole-archive` / `-u` 等链接旗标导出 LOCAL 符号
- ❌ 用 `-O2/-O3`、链接顺序、`LD_PRELOAD` 等与根因无关的方向反复调参（本案例实测均无效）

## 验证

```bash
# 1) 消费者 .so 是否私藏依赖（=0 表示依赖被静态烘入且未导出）
nm -D --defined-only src/core/.libs/libosmocore.so.22.1.0 | grep -c talloc

# 2) 可执行文件是否各自静态烘入（无 libtalloc.so.2 即双实例风险）
readelf -d tests/abis/.libs/abis_test | grep NEEDED

# 3) 归档符号可见性（小写 t = LOCAL，链接层无解）
nm libtalloc.a | grep _tc_free_internal

# 4) 静态交付后：完整上游测试应回到全绿
conan create . --build=missing   # 期望 88 passed / 2 skipped / 0 failed
```

## 关联条目

- 相关: E567（CMakeDeps 对 static-library 依赖默认不传递，需 `transitive_libs`/`transitive_headers`）
- 相关: E114（静态库 PIC 契约）、E007（依赖产物形态核验）

## 出处

- 软件/版本: libosmocore/1.11.0（OpenHarmony PC 适配，PR #9889）
- 复现环境: HarmonyOS aarch64 本机 + 隔离 CONAN_HOME（scrubbed，等价 CI）
- 关键实测: `40/88` 失败（本地）/ `41/88` 失败（CI），abort 点 `_tc_free_internal`；
  改静态交付后回到全绿（见 `reports/test-report.md`）
