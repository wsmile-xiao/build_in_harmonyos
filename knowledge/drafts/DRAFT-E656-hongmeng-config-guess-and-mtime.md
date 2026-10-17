# DRAFT-E656-hongmeng-config-guess-and-mtime：GitHub tag 归档 autotools 包在 OHOS 上的两个 bootstrap 陷阱（config.guess 不识别 HongMeng / 物化丢 mtime 触发 aclocal 重生成）

> Contributor: re-flex-6.3.0 执行体 | Status: Draft | Updated: 2026-09-22
> Source: re-flex 6.3.0 适配（feat/re-flex-6.3.0，Genivia RE-flex tag 归档 autotools 工程）
> 对应：`knowledge/drafts/DRAFT-E656-hongmeng-config-guess-and-mtime.kv`

## 现象

两个报错先后出现，形态都像「上游脚本损坏 / 缺工具」：

### 陷阱①：config.guess 无法识别鸿蒙内核（configure 阶段）

```console
$ ./configure --host=aarch64-linux-ohos
UNAME_SYSTEM  = "HarmonyOS"
UNAME_VERSION = "#1 SMP Wed Apr 29 10:16:03 UTC 2026"
configure: error: cannot guess build type; you must specify one
```

**即使已经显式传了 `--host` 也会死**——报错发生在 build 侧推导，不是 host 侧。

### 陷阱②：物化丢 mtime → make 触发 automake 重生成（make 阶段）

```console
$ make -j2
…/missing: line 85: aclocal-1.18: command not found
WARNING: 'aclocal-1.18' is missing on your system.
         You should only need it if you modified 'acinclude.m4' or
         'configure.ac' or m4 files included by 'configure.ac'.
make: *** [Makefile:400: aclocal.m4] Error 127
```

设备与 CI worker 的 PATH 都没有 automake（AGENTS §一.4），而这个包的归档里
**本来就带着预生成的 `configure`/`Makefile.in`/`aclocal.m4`**，本不该有任何
autotools 工具参与构建。

## 根因

### ① config.guess 的探测列表没有鸿蒙

上游 `config.guess` 逐项比对 `UNAME_MACHINE/RELEASE/SYSTEM/VERSION`；鸿蒙内核返回
`UNAME_SYSTEM="HarmonyOS"`、`UNAME_RELEASE="HongMeng Kernel …"`，不在已知列表 →
直接 `cannot guess build type`。configure 默认对 **build** 侧跑 config.guess，
所以：

- 只传 `--host` 不传 `--build` → 照死；
- `config.sub` 其实已认识 `linux-ohos*`（`grep -c ohos config.sub` 可确认），
  说明上游 autotools 口径本身支持 OHOS，缺的只是 build 侧显式三元组。

### ② GitHub 归档的「同刻 mtime」被复制破坏

GitHub codeload 归档内全部文件 mtime 相同（=commit 时刻）。automake 的
maintainer-mode 重生成规则按 **mtime 早于 prerequisites** 触发：

- `tar xzf` / `conan get()` 解包：全部同刻 → `aclocal.m4` 不早于 `configure.ac`
  → 规则休眠（上游预期形态，构建不需要任何 autotools 工具）；
- `cp -r` 物化（无 `-p`）：副本按复制先后各得新 mtime，`configure.ac` 这类
  prerequisites 晚于 `aclocal.m4` → 规则唤醒 → 调用**版本化**的
  `aclocal-1.18` → 设备/CI 无 automake → 在真正编译开始前就死。

同因异形态：`configure: error: newly created file is older than configure` 一类
时间戳比较失败也是它。

> 易误判点：这个报错诱导人去「补 autoreconf / 加 automake 依赖」。真因是
> mtime，不是工具缺失；重生成还会产出与上游归档不同版本的 bootstrap 产物，
> 破坏「按该 SHA 核对构建输入」的一致性。

## 方案

### 主方案（零侵入、不改上游）

1. **configure 显式传同值三元组**（OHOS 设备原生构建 build == host）：

```bash
./configure --build=aarch64-linux-ohos --host=aarch64-linux-ohos \
    CC=clang CXX=clang++ CXXFLAGS='-O2 -Wall -Wextra -Wunused -std=gnu++17'
```

2. **构建树物化必须保 mtime**：`tar xzf` 解包，或 Python 侧
   `shutil.copytree(src, dst)`（内部 `copy2` 保留 mtime）。conan 的
   `source()`（`conan.tools.files.get`）解包同样保序，因此在 conan 配方里
   「`source_folder` → `/data/storage/el2/base` 工作目录」这一步用
   `copytree` 即可。

### 救急方案（已丢序的既成树）

按依赖序 touch，使生成物不早于源头（顺序错会换个方式再触发）：

```bash
touch configure.ac aclocal.m4 configure Makefile.am Makefile.in config.h.in
```

### 何时才真的需要 automake

仅当任务确需修改 `configure.ac` / `Makefile.am`（重生成不可避免）时，配方加
`def build_requirements(self): self.tool_requires("automake/1.18")`（仓库已有
同写法）。为「修 mtime」而引入是错配。

## 复现/验证（设备可直接执行，落任务目录）

```bash
cd "$TASK_DIR" && rm -rf e656-probe && mkdir -p e656-probe/src
cp -r <autotools-src>/configure e656-probe/src/
python3 - <<'EOF'
import os
p1 = os.environ.get('SRC_CONFIGURE', 'configure')
p2 = 'e656-probe/src/configure'
print('mtime src  =', os.stat(p1).st_mtime)
print('mtime copy =', os.stat(p2).st_mtime)
print('verdict:', 'cp -r 丢序（危险）' if os.stat(p2).st_mtime > os.stat(p1).st_mtime else 'mtime 保序')
EOF
```

re-flex 6.3.0 实测：`cp -r` 物化 → make 报 `aclocal-1.18: command not found`；
改 `copytree`（保 mtime）→ maintainer-mode 规则休眠，预生成 bootstrap 全程
无需 automake，`configure`+`make -j2`+6 个上游自包含测试全绿。

## 关联

- **E011**（HMDFS 无法承载 autotools 生成器临时目录/执行位语义，`config.status`
  的 `confXXXX/subs1.awk: Permission denied`）：同批适配的第三个 bootstrap 面。
  E011 决定「在哪构建」（非 HMDFS 工作目录），本条决定「怎么传参、怎么物化」；
  GitHub 归档 autotools 包的 OHOS 适配三者高频同现，缺一不可。
- prescan：配方/脚本层面 `\bcp\s+-r\b`（`**/conanfile.py`、`**/*.sh`）提示
  「物化丢 mtime」风险；`-rp`/`-pr`/`-a`（保 mtime 形态）不命中。
