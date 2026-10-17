# SCons 交叉编译知识库扩展（样例库：rhvoice 1.14.0）

> 本文件是【知识库扩展】交付物的可读部分：把 rhvoice 1.14.0 的适配经验固化为一类
> 可复用知识（SCons 构建系统的 OHOS 交叉编译）。配套产物：
> - 检测脚本：`knowledge/scons-detect.sh`（判定 SCons 工程 + 列出注入锚点信号）
> - 知识图谱草稿：`knowledge/drafts/E429-draft-*.{kv,md}`（SCons 交叉编译）、
>   `knowledge/drafts/E430-draft-*.{kv,md}`（SCons 工程语言/主体判定）
> - 样例库（本目录，实测通过 `conan create`）：`archives/r/rhvoice/1.14.0/`

## 1. 适用场景（检测信号）

满足任一即命中本知识：

| 信号 | 位置 | 含义 |
|---|---|---|
| `SConstruct` / `SConscript` | 源码树 | 构建由 SCons 驱动（不是 CMake/Make/autotools） |
| `env['SHELL'] = 'sh'` 或裸 `sh` 调用 | SConstruct | SCons 经 `posix_spawn` 执行，**不搜索 PATH**，沙箱内必然 127 |
| `CheckCC()` / `CheckCXX()` / `Configure()` | SConstruct | 首个编译器自检，构造变量未注入 → `C compiler works... no` |
| `['CC']` / `['CXX']` 赋值点 | SConstruct | 打补丁的注入锚点 |
| `pkg-config` / `ParseConfig` | SConstruct | 沙箱内外部工具不可用 → `inaccessible or not found` |

一键检测：`sh knowledge/scons-detect.sh <source-dir>`（只读，退出码 0=SCons 工程）。

## 2. 处理策略（构造变量覆盖 + 工具链注入）

**根因**：SCons 只认 construction variables（默认 `gcc`/`g++`），完全不读环境变量
`CC`/`CXX`；`SHELL` 亦为构造变量，经 `posix_spawn` 直执行、不搜 PATH（R33 的反面）。

**策略 A（推荐，本样例采用）——源码补丁 + 构造变量覆盖**：

```python
# SConstruct：补丁 0001-sconstruct-allow-construction-variable-override.patch
for name,value in os.environ.items():
    if name.startswith("RHVOICE_SCONS_"):
        base_env[name[len("RHVOICE_SCONS_"):]]=value
```

配方侧只注入绝对路径（来自 Conan toolchain，不依赖 shell 变量）：

```python
# conanfile.py: _scons_env() / build()
env.define("RHVOICE_SCONS_CC",  compiler_c)     # -> env['CC']
env.define("RHVOICE_SCONS_CXX", compiler_cpp)   # -> env['CXX']
env.define("RHVOICE_SCONS_AR",  llvm_ar)
env.define("RHVOICE_SCONS_RANLIB", llvm_ranlib)
env.define("RHVOICE_SCONS_SHELL", command_shell)  # /system/bin/sh -> /usr/bin/sh -> /bin/sh
```

**策略 B（不回改源码）**：SCons 命令行直接给构造变量
`python3 -m SCons -j<N> CC=<abs> CXX=<abs> SHELL=<abs>`。仅当 SConstruct 不在
`CheckCC` 之后重建 env 时有效——重建型工程仍需策略 A。

**SCons 本体获取（本机/CI 均无 scons 制品配方）**：配方 `generate()` 私装到构建目录，
不污染宿主、不依赖本地缓存：

```python
pip install --target=<build_folder 私有目录> --index-url <社区 PyPI> "scons==4.10.0"
env.define_path("PYTHONPATH", "<build_folder 私有目录>")   # 运行 python3 -m SCons
```

（版本号与样例配方一致：rhvoice 1.14.0 固定 `scons==4.10.0`；换工程时按需调整，dxx-rebirth 先例用的是 4.4.0。）

**其他实测坑（本样例踩过，已固化）**：

| 坑 | 现象 | 处理 |
|---|---|---|
| 空子模块占位 | 发布 tarball 内 `external/libs/boost` 为空 → `FileNotFoundError` | 改制品仓 `boost` 依赖 + 注入 `CPPPATH`；空 `language.info` 占位先清理 |
| 数据子模块与源码分离 | `data/languages/*`、`data/voices` 上游独立仓 | `conandata.yml` 声明 `data_sources`（URL + sha256），`source()` 内落地，保证可复现 |
| 不可复现的数据源 | codeload 动态打包，多次哈希不同 | 逐仓验证 **两次同 sha256** 才可用；许可非自由（CC BY-NC-ND 等）直接弃用 |
| 补丁解析失败 | `patch stream is incomplete!` | 补丁必须是标准 git 格式（`From <sha>` + `Subject: [PATCH]` + 行数自洽） |
| 语音/模型类数据仓 | 只有模型文件、无元数据 | 由配方 `package()` 生成 `voice.info` 等元数据字段 |

## 3. 复现（干净环境，CI 同路径）

```sh
# 环境：OHOS aarch64 clang profile，CI 干净环境无本地缓存
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

实测结论（rhvoice 1.14.0，2026-10-10）：`conan create` rc=0，日志含
`Checking whether the C compiler works... yes`、`Checking whether the C++ compiler works... yes`、
`voices: 1`、端到端合成 44520 样本、`all checks passed`。
G0/clean-verify：`G2 PASS`、`G3 PASS`、`配方验证通过`。

上游测试口径（与 `test_package/MANIFEST.yml`、`notes.md` 一致）：上游 1.14.0 **没有自动化
测试套件**——`.github/workflows/ci.yml` 只跑 `scons -j2`，`src/test` 输出的是命令行工具
`RHVoice-test`（非测试套件），各语言仓的 `checktrans` 是数据维护脚本、不在构建内运行。
因此本样例的构建期验证以 `test_package` 为准（12 项断言 + `RHVoice-test --help`），未申报
上游用例数。

## 4. 参照先例

- `archives/d/dxx-rebirth/0.6/`：同类 SCons 库，私装 scons + 原位构建 + DESTDIR 安装（本知识的方法来源之一）。
- 本样例（rhvoice 1.14.0）：新增「构造变量覆盖」补丁（策略 A 的模板）+ 数据源 sha256 可复现约束。
- 关联条目：`E429`（SCons 交叉编译注入）、`E430`（SCons 工程语言/主体判定）。
