# DRAFT-8959 — Meson 工程中「只做 configure_file 的解释型脚本目标」的 Conan 打包口径

- **条目 ID**: `DRAFT-8959-kea-shell-3.0.3-meson-configure-file-only-target`
- **严重度**: 2（🟡 中等）
- **类别**: conan, meson, python, portability, ohos
- **触发工具/阶段**: meson | conan | python | test — conan_build / configuration / testing / runtime
- **来源**: kea-shell 3.0.3 适配（feat/kea-shell-3.0.3，OHOS PC aarch64）

## 错误特征

```
test name does not match any test | Invalid test name
No module named 'kea_conn' | ImportError: ... kea_connector
bad interpreter ... python3 | can't open file '<pkg>/bin/kea-shell'
Problem encountered: Unsupported system "harmonyos".
```

## 场景

`kea-shell`（ISC Kea 3.0.3 的 REST 文本客户端，源码 `src/bin/shell`）是纯 Python 3
脚本工具：其 `meson.build` 全文只有 3 个 `configure_file()` + `subdir('tests')`，
没有 `executable()` / `library()` / `dependencies:` / `link_with:`，目录内 0 个
`.cc/.h`。但它属于 Kea 的**单一 Meson 工程**，`meson setup` 会评估顶层工程门禁
（`meson.build:192` boost `required` 且无 fallback、`meson.build:231`+
`314-320` openssl 为默认 crypto 后端、`meson.build:220` log4cplus 有 wrap fallback）。

## 根因（三层）

1. **交付物在 configure 阶段就已产出**：`configure_file` 在 `meson setup` 时执行，
   脚本与 `copy: true` 的两个模块立刻出现在 build tree 的 `src/bin/shell/`。
   再调 `meson.build()` 只会去编译与本包无关的 C++ 目标。
2. **configure 是全工程的**：工程级 `dependency()` 门禁（required、无 fallback）
   使"本目标零第三方依赖"无法直接兑现，配方必须声明 boost/openssl/log4cplus；
   它们只服务配置期探针，不进入交付物，也不应经 `package_info()` 传播给消费者。
3. **生成脚本内嵌构建机绝对路径**：`#!@PYTHON@` → 构建者家目录下的解释器路径；
   `sys.path.append('@PKGPYTHONDIR@')` → 构建机 Python 的 `purelib/kea`。
   Conan 包无法占用 build-host 的 purelib，脚本运行时也拿不到构建者家目录。

## 推荐方案（实测配方形态）

```python
def build(self):
    apply_conandata_patches(self)
    Meson(self).configure()          # configure 即产出全部交付物
    if self.options.tests:
        self.run('meson test -v -C "{}" shell_unittest.py'.format(self.build_folder))

def package(self):
    shell_dir = os.path.join(self.build_folder, "src", "bin", "shell")
    bin_dir = os.path.join(self.package_folder, "bin")
    for name in ("kea-shell", "kea_conn.py", "kea_connector3.py"):
        copy(self, name, src=shell_dir, dst=bin_dir)
    os.chmod(os.path.join(bin_dir, "kea-shell"), 0o755)
```

1. `build()` 只做 `meson.configure()`，不调用 `meson.build()`；
2. `requirements()` 照实声明工程级门禁依赖（boost/1.85.0 + log4cplus/2.2.0.1 +
   openssl/3.5.8.1），`tool_requires("meson/1.11.0")`（boost 包无
   `libboost_system`，需 meson ≥1.10 的 header-only 模块回退）；
   `package_info()` 只导出 `bindirs` + runenv PATH，不透传这些依赖；
3. **shebang 在源码层补丁**：`#!@PYTHON@` → `#!/usr/bin/env python3`
   （OHOS 的 `/usr/bin/env` 由 toybox 提供，知识 E037 条件 1 成立）；
4. `sys.path.append('@PKGPYTHONDIR@')` **不改脚本**：两个模块与脚本同目录安装，
   由 CPython 的"脚本所在目录 = `sys.path[0]`"解析 `import kea_conn`；
   该 append 指向不存在的目录，无副作用；
5. **平台补丁**：`meson.build` 把 `SYSTEM == 'harmonyos'` 归一化为 `'linux'`
   （否则 `meson.build:186` 直接 `error`，见知识 E090）。

## 易踩点

| 现象 | 原因 | 处理 |
|---|---|---|
| `meson test ... <suite 名>` → `test name does not match any test` | meson CLI 位置参数是 **test name**，suite 名要走 `--suite` | 传 `shell_unittest.py` 或加 `--suite python-tests` |
| `meson setup` 报 `Unsupported system "harmonyos"` | Kea 用 `build_machine.system()` 做平台分支，白名单无 harmonyos | 补丁归一化为 `linux`（E090） |
| 特性探针 `NO (127)` | compile-and-run 探针真实执行，host 共享依赖不在配置期运行环境 | `generate()` 用 `Environment` 把依赖 `libdir` 追加 `LD_LIBRARY_PATH` |
| `Unknown linker(s): [['llvm-ar']]` | Conan buildenv 把 `AR=llvm-ar` 写进 machine file，PATH 里没有 | 从编译器路径推导同目录 `llvm-ar`/`llvm-ranlib`（E481） |
| 包目录出现 `__pycache__` | 脚本从包内 import 同目录模块，CPython 写字节码 | runenv 定义 `PYTHONDONTWRITEBYTECODE=1` |

## 影响 / 回退 / 限制

- **影响**：任何"上游是 C/C++ 构建系统、但某目标是解释型脚本或资源"的包
  （Meson/Autotools/CMake 都有 configure 等价物）。配方从"编译整工程再挑产物"
  变为"只跑配置阶段 + 按包布局放置"，CI 时间显著下降。
- **回退**：若脚本还要调用本工程的编译产物，则不能停在 configure，需恢复
  `meson.build()` 并补齐平台补丁；若目标镜像缺 `/usr/bin/env`，shebang 方案
  需退回解释器绝对路径（安装期 sed）。
- **限制**：仍受工程级配置门禁依赖约束；同工程的 `.sh` 进程测试若依赖其他
  C++ 目标（如 Kea 服务端），配方内无法运行，只能作为本地/跨组件验证。

## 证据链

- 未打补丁 `meson setup`：`meson.build:186:4: ERROR: Problem encountered:
  Unsupported system "harmonyos".` → `archives/k/kea-shell/3.0.3/reports/meson-setup-first-error.log`
- 打 0001+0002 后 `meson setup` rc=0，configure 输出 `Boost 1_85 / OpenSSL 3.5.8 /
  Log4cplus 2.2.0`，`Build targets in project: 242` → `reports/meson-setup-patched.log`
- configure 后零编译即得 `src/bin/shell/{kea-shell(0755),kea_conn.py,kea_connector3.py}`
- 首版配方把 suite 名当 test 名 → `ERROR: *:python-tests test name does not match
  any test`；改 `shell_unittest.py` 后 `Ran 11 tests ... OK`
- 包内运行：任意 cwd 执行 `<pkg>/bin/kea-shell -v` 输出 `3.0.3`；stub HTTP 往返
  12 项断言全通过（conan create test_package）
- 上游测试：13 个入口 / 79 个用例级执行全部通过（含 12 个 `.sh` 进程测试）

## 验证命令

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
meson test -v -C <builddir> shell_unittest.py
```

## 关联条目

- E090（meson host_system = harmonyos → linux 归一化）
- E091（musl + Linux UAPI 的 `sockaddr_storage` 重定义，仅构建同工程 C++ 目标时需要）
- E127（`pthread_setcancelstate` 未声明 → `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`）
- E481（MesonToolchain + llvm-ar/llvm-ranlib 推导）
- E037（shebang：`/usr/bin/env` 存在时优先用 env 形式）
