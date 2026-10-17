# E429 — SCons 交叉编译：构造变量（CC/CXX/SHELL）未注入

## 错误特征

典型症状按出现顺序排列，任一条命中即可怀疑本模式：

```
Checking whether the C compiler works... no
Checking whether the C++ compiler works... no
/system/bin/sh: pkg-config: inaccessible or not found
sh: gcc: inaccessible or not found
```

编译器自检直接返回 `no`，或后续所有子进程以 127 退出，日志里只看到
`inaccessible or not found` / `not found`，很容易被误判成"缺依赖"。

## 触发条件

- 构建系统: SCons（根目录 `SConstruct` + 若干 `SConscript`）
- 阶段: configuration（编译器/工具探测），若不处理会一路拖到编译阶段（每个子进程都 127）
- 环境: 交叉编译到 OHOS（aarch64），沙箱或 CI 干净环境内无常用 shell、无宿主 gcc/g++

## 根因分析

SCons 与 autotools/make 有两点根本差异：

1. **只认 construction variables**：编译器取自 `env['CC']`/`env['CXX']`，默认 `gcc`/`g++`；
   环境变量 `CC`/`CXX` 不会被读取。交叉编译时宿主没有 gcc → 首个 `CheckCC()` 就失败。
2. **`SHELL` 也是构造变量，且走 `posix_spawn` 直执行、不搜索 PATH**：
   SCons 在 `Platform/posix.py` 里把 `env['SHELL']` 设为裸 `sh`，随后用
   `subprocess.Popen`/`os.posix_spawn` 执行它。CPython 的 `posix_spawn` 快路径不做 PATH
   解析，而 OHOS 沙箱内 `/bin/sh` 缺失、`/system/bin/sh` 受限且不在 PATH 上
   → 所有需要 shell 的步骤全部 127。

补充事实：项目自带的 `configure`/`CheckCC` 若在检查之后重新 `Environment()`，
仅在 SCons 命令行上传 `CC=`/`CXX=` 也会被覆盖掉——必须从 SConstruct 内部注入。

## 解决方案

### 推荐方案

**策略 A：源码补丁 + 构造变量覆盖（样例库 rhvoice 1.14.0 采用）**

1. 给 `SConstruct` 打补丁，允许环境变量覆盖任意构造变量：

   ```python
   # patches/0001-sconstruct-allow-construction-variable-override.patch
   for name,value in os.environ.items():
       if name.startswith("RHVOICE_SCONS_"):
           base_env[name[len("RHVOICE_SCONS_"):]]=value
   ```

2. 配方侧从 Conan toolchain 取绝对路径（R33：不依赖裸 shell 环境变量），注入到
   `RHVOICE_SCONS_<NAME>`，其中 `<NAME>` 即构造变量名：

   ```python
   env.define("RHVOICE_SCONS_CC",  compiler_c)      # -> env['CC']
   env.define("RHVOICE_SCONS_CXX", compiler_cpp)    # -> env['CXX']
   env.define("RHVOICE_SCONS_AR",  llvm_ar)
   env.define("RHVOICE_SCONS_RANLIB", llvm_ranlib)
   env.define("RHVOICE_SCONS_SHELL", command_shell) # /system/bin/sh -> /usr/bin/sh -> /bin/sh
   ```

3. 只要制品仓没有 scons 配方，就在 `generate()` 里把 SCons 私装到构建目录下的私有前缀
   （`pip install --target=<build_folder>/_scons_env scons==<ver>` + `PYTHONPATH`），
   再用 `python3 -m SCons` 驱动构建——不污染宿主、不依赖本地缓存，CI 干净环境可复现。

**策略 B：命令行传构造变量（不回改源码）**：
`python3 -m SCons -j<N> CC=<abs> CXX=<abs> SHELL=<abs>`。仅当 SConstruct 不在
`CheckCC` 之后重建 env 时有效；重建型工程仍需策略 A。

### 禁止做法

- ❌ `env["SHELL"] = "sh"`（裸名字）：`posix_spawn` 不搜 PATH，沙箱内必然
  `inaccessible or not found`（127），且会把错误伪装成"缺依赖"。
- ❌ 依赖宿主 `CC`/`CXX` 环境变量或默认 `gcc`/`g++`：交叉编译环境没有这些工具，
  首个编译器自检即 `no`，构建立刻中止。
- ❌ 在沙箱内往 `/usr/local` 之类共享前缀安装工具链（R49）——共享文件系统会互相污染。

## 验证

```bash
# 1. 判定是否 SCons 工程并列出注入锚点（只读）
sh knowledge/scons-detect.sh <source-dir>

# 2. 干净环境复现（CI 同路径）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 3. 期望在日志中看到
grep -E "Checking whether the C(\+\+)? compiler works" <build-log>   # 必须为 yes
grep -E "RHVOICE_SCONS_|Compiler found" <build-log>
```

实测（rhvoice 1.14.0，2026-10-10）：`conan create` rc=0，
`C compiler works... yes` / `C++ compiler works... yes`，
端到端合成 44520 样本、`all checks passed`。

## 关联条目

- 相关: E430（SCons 工程语言/主体判定——同一类工程的准入坑）
- 样例库: `archives/r/rhvoice/1.14.0/`（配方 + `knowledge/scons-cross-compile.md` + `knowledge/scons-detect.sh`）
- 先例: `archives/d/dxx-rebirth/0.6/`（私装 scons + DESTDIR 安装）
