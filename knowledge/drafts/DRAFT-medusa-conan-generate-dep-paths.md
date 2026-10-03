# DRAFT: Conan 2 `generate()` 中依赖包目录不可用

> **结构化数据**：[DRAFT-medusa-conan-generate-dep-paths.kv](DRAFT-medusa-conan-generate-dep-paths.kv)
> **严重度**：🔴 high | **分类**：conan / recipe / autotools / ohos
> **来源**：medusa 2.3 原生 OHOS 适配（PR #13807）

## 现象

`generate()` 里按常规写法取依赖的绝对路径，配置阶段报出与路径无关的错误：

```text
# 配方侧（错误写法）
openssl_prefix = self.dependencies["openssl"].package_folder

# 生成器实际写出
$ grep -n 'with-ssl=' <build>/conan/conanbuild.conf
configure_args = --prefix=/ ... --with-ssl=None

# 随后 configure 找不到头文件
configure: checking for OpenSSL Library and Header files...
checking None/include/openssl/ssl.h... not found
configure: error:  *** OpenSSL header files required for SSL support. ***
```

在另一条路径上，症状完全变形（与路径毫无字面关系）：

```text
checking whether we are cross compiling...
configure: error: cannot run C compiled programs.
If you meant to cross compile, use '--host'.
```

## 根因

Conan 2.29.1（OHOS 适配版，本仓库基线）在消费者配方的 `generate()` 阶段**尚未绑定依赖的包目录**：

| 表达式 | `generate()` 中的值 |
| --- | --- |
| `self.dependencies[name].package_folder` | `None` |
| `self.dependencies[name].cpp_info.location` | `None` |
| `self.dependencies[name].cpp_info.includedirs` | `['include']`（包相对路径，不可直接用） |
| `self.dependencies[name].cpp_info.libdirs` | `['lib']`（同上） |

因此 "取绝对路径" 这件事在 `generate()` 里必须换一套已物化的数据来源。

**影响面**：本仓库 `archives/` 下 **1304 个配方**在 `generate()` 中读取 `package_folder`。这说明需要沉淀的是 **API 可用性边界**，不是某一个库的补丁。

同时暴露的两个 Autotools 侧事实属于同一边界：

1. `AutotoolsToolchain`（Conan 2.29.1）只有 `extra_cflags` / `extra_cxxflags` / `extra_ldflags`，**没有 `extra_cppflags`**；而部分上游 `configure` 会自行重置 `CPPFLAGS`，所以依赖 include 路径只有放进 `CFLAGS`/`CXXFLAGS` 才活得下来。
2. `AutotoolsToolchain` 会把依赖的 `LIBS`（如 `-lgcrypt -lgpg-error -lssh2`）写进 conanbuild 环境，`configure` 又把 `LIBS` 追加到**每一个 conftest** 的链接命令上；这些共享库不在 loader 路径里，于是 `./conftest` 以 127 退出，configure 得出 "cannot run C compiled programs" 的错误结论。

`<build>/config.log` 里的直接证据：

```text
configure:4379: clang -o conftest ... -lgcrypt -lgpg-error -lssh2 -lpthread >&5
configure:4383: $? = 0                     ← 编译+链接都成功
configure:4390: ./conftest
Error loading shared library libgcrypt.so.20: (needed by ./conftest)
Error loading shared library libgpg-error.so.0: (needed by ./conftest)
Error loading shared library libssh2.so.1: (needed by ./conftest)
configure:4394: $? = 127
configure:4403: error: cannot run C compiled programs.
```

**这不是编译器问题**：编译和链接都返回 0，失败只发生在"运行 conftest"这一步。

## 修复

### 1. 从已物化数据推导依赖包目录

```python
def _dep_prefix(self, name):
    dep = self.dependencies[name]
    if dep.package_folder:            # build() 阶段可用；generate() 阶段通常为 None
        return dep.package_folder
    # 退路：从 AutotoolsDeps 生成的绝对 -I 路径反推 Conan store，再按截断目录名定位
    for flag in self._autotools_deps_flags()[0]:
        store = flag[2:].split(os.sep + "p" + os.sep)[0]
        for candidate in sorted(glob.glob(os.path.join(store, "p", name[:5] + "*", "p"))):
            if os.path.isdir(os.path.join(candidate, "include", name)):
                return candidate
    raise ConanException(f"cannot resolve the package prefix of dependency '{name}'")
```

两个关键细节：

- Conan 在 store 里只保留**包名前 5 个字符 + 哈希**（`openssl` → `opens3b77e8c5f6d9b`），用全名 glob 匹配不到；
- 命中后必须用该包自身的目录结构（`include/<name>/`）复核，避免撞到同前缀的别的包。

### 2. 标志只放进真实存在的 toolchain 属性

```python
tc = AutotoolsToolchain(self)
tc.extra_cflags.extend(includes)
tc.extra_cxxflags.extend(includes)
tc.extra_ldflags.extend(libdirs)
# configure 会把继承来的 LIBS 链接进 conftest，给它同样的 rpath
for libdir in libdirs:
    tc.extra_ldflags.append(f"-Wl,-rpath,{libdir[2:]}")
```

### 3. 被 `override=True` 引入的依赖要单独补

`override=True` 的依赖不会出现在 `AutotoolsDeps` 生成的脚本里（libssh2 钉 `openssl/3.5.6.1`、本库统一到 `3.0.21` 即属此例），必须显式追加它自己的 `-I`/`-L`。

## 验证命令

```bash
grep -n 'with-ssl=' <build>/conan/conanbuild.conf          # 不应再出现 None
grep -n 'None/include' <build>/config.log                  # 不应再出现
grep -nE 'cannot run C compiled programs|Error loading shared library' <build>/config.log
grep -nE '^export (CPPFLAGS|LDFLAGS|LIBS)' <build>/conan/conanautotoolsdeps.sh
```

真机实测（HarmonyOS PC aarch64 / clang 15.0.4 / Conan 2.29.1，隔离 `CONAN_HOME` + 隔离 `RUN_DIR`）：

- 失败基线：`medusa-2.3-conan9` → `cannot run C compiled programs`（`config.log` 的 conftest 段见上）；
- 修复后：`medusa-2.3-conan20` / `conan21` / `final` → `Success: 1 / Failed: 0`，`[info] modules loaded: 22`。

## 禁止写法

| 写法 | 后果 |
| --- | --- |
| `generate()` 中直接用 `package_folder`（无 None 检查） | 标志静默变成 `None`，很久以后才以缺头文件的形式报错 |
| 使用 `extra_cppflags` | `AttributeError`（该属性在 Conan 2.29.1 不存在）；即使存在，重置 `CPPFLAGS` 的上游 configure 也会丢弃它 |
| 用"清掉 `LIBS`"来绕过 conftest 失败 | 掩盖了真实依赖；正确做法是补 rpath，让 conftest 能加载依赖 |

## 与既有知识的关系

- **E002**（`/tmp` 只读 / TMPDIR）：同为 conftest 运行期失败，但根因不同（那条是临时目录，本条是共享库加载路径）。
- **E137**（Perl `lddlflags`/`ExtUtils::CBuilder`）：同属"构建设施把依赖塞进链接命令导致探针失败"的家族，但触发点是 Perl 工具链。
- 全库检索 `package_folder` / `cpp_info.location` / `AutotoolsDeps` / `conanbuild.conf` / `runenv_info`：**无条目覆盖本 API 边界**，属新增。
