# file-sharedir 1.118 适配笔记

## 编译环境

- 目标：`aarch64-unknown-linux-ohos`（profile: `ci/conan/profiles/ohos-aarch64`）
- 解释器：`/data/service/hnp/bin/perl` v5.42.0（固定使用，见「注意事项」）
- conan 2.29.1
- 构建系统：**上游自带 `Makefile.PL`**（ExtUtils::MakeMaker，无需替代）

## 本包为何存在

`File::ShareDir` 提供「按发行版/按模块定位共享数据文件」的能力：库作者把数据
文件装在安装树的 `auto/share/dist/<Dist>/` 或 `auto/share/module/<Module>/`
下，运行时用 `dist_dir` / `dist_file` / `module_dir` / `module_file` 定位。

它与本仓既有的 `file-sharedir-install` 是**配套对**：

| 包 | 角色 |
|----|------|
| `file-sharedir-install` 0.14（已合入） | **安装期**：把 share/ 数据装进 `auto/share/` |
| **`file-sharedir` 1.118**（本包） | **运行期**：在安装后的树里定位这些数据 |

只有 install 侧而没有运行期查询侧，库作者无法在代码里用 `dist_file()` 取数据
——两者缺一，该功能链在本仓就不完整。

## 编译步骤

```bash
# 1) 取源码 + 校验 sha256（conandata.yml，CPAN 官方 URL）
# 2) build()：perl Makefile.PL INSTALLDIRS=site → make → make test（R51 真实运行）
#    → make install DESTDIR=<staging>
#    测试期 PERL5LIB 注入 class-inspector + file-sharedir-install 两个依赖
# 3) package()：按登台树原样拷入 package_folder；显式校验 auto/share 数据目录
# 4) package_info()：runenv_info.prepend_path 注入 PERL5LIB
```

## 遇到的问题与解决方案

### 问题 1（本包关键）：依赖的 `PERL5LIB` 不进 build 上下文

上游 `t/00_prereqs.t` 会读取自己的 `META.json` 并**逐一 `require` 声明的全部
requires**（含 `configure`/`build` 段的 `File::ShareDir::Install`）。而两个依赖
的 `package_info()` 都只声明了 `runenv_info`（无 `buildenv_info`）→ 其
`PERL5LIB` **不会自动进入本包的 build 上下文**。

**实测对照**：

| 注入范围 | 结果 |
|---|---|
| 只注入 `class-inspector`（漏 file-sharedir-install） | `t/00_prereqs.t` 报 `Can't locate File/ShareDir/Install.pm` → **1/91 失败** |
| 两者都注入 | **Files=7, Tests=92, Result: PASS** |

**修法**（不改动已合入的依赖配方，R21）：`build()` 内遍历依赖包目录，定位各自
的 perl lib 根（含目标相对模块路径的目录），显式注入 `PERL5LIB`：

```python
DEP_MODULES = {
    "class-inspector":       os.path.join("Class", "Inspector.pm"),
    "file-sharedir-install": os.path.join("File", "ShareDir", "Install.pm"),
}
dep_sites = self._dep_perl5lib()
env_prefix = 'export PERL5LIB="' + os.pathsep.join(dep_sites) + ':$PERL5LIB" && '
```

### 问题 2：不必生成替代构建脚本（与同批其它 perl 包不同）

同批适配的 `metrics-any` / `future-queue` 走 `Module::Build`（`Build.PL`），而
`Module::Build` 在 OHOS 不可得，需生成等价 `Makefile.PL`。本包**不需要**——上游
自带 `Makefile.PL`，并在 `inc/` 中捆绑 `File::ShareDir::Install` 与
`inc::latest` 自举 `install_share`。故 `build()` 直接使用上游脚本，仅在缺失时
显式报错（而非静默生成）。

### 问题 3：`auto/share` 数据目录必须显式校验

本包的核心产物不只是 `.pm` 文件，还包括 `auto/share/{dist,module}/...` 下的数据
文件。若打包时漏掉它们，`dist_dir`/`module_dir` 只会在**消费方运行期**才失败。
故 `package()` 中显式校验：

```python
if not os.path.isdir(os.path.join(site, "auto", "share")):
    raise ConanException("auto/share data files missing ...")
```

### 问题 4：`package_info` 用 `prepend_path` 而非 `define_path`

依赖用的是覆盖语义的 `define_path`。本包若也用它，消费方的 `PERL5LIB` 只会剩
本包一条，`File::ShareDir` 依赖的 `Class::Inspector` 将解析不到。故用
`prepend_path` 追加。

## 源码修改

**无**（`patches: {}`）。上游自带可用的 `Makefile.PL`，未改动任何上游文件。

## 依赖版本

| 包 | 版本 | 类型 | 说明 |
|----|------|------|------|
| class-inspector | 1.36 | requires（运行时） | `File::ShareDir` 用它解析模块安装位置（META: >= 1.12） |
| file-sharedir-install | 0.14 | requires（configure/build） | 提供 `install_share`；且 `t/00_prereqs.t` 会 require 它 |

其余为 perl 核心/hnp perl 自带：`Carp`、`File::Spec`、`File::Path`、`Test::More`。

## 验证结果

```bash
# 上游测试套件（7 文件 92 用例）
cd File-ShareDir-1.118 && perl Makefile.PL INSTALLDIRS=site && make && make test
# → Files=7, Tests=92, Result: PASS

# 完整本地验证（与 CI 相同 profile + 相同参数）
conan create archives/f/file-sharedir/1.118 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
# → EXIT CODE=0
#   [upstream] Files=7, Tests=92, Result: PASS
#   Package '76dd5e1ac968e3c22bfa4b49937c34b33720e0c8' created
#   ALL OK - file-sharedir 1.118 consumer checks passed
```

- 上游测试：**Files=7, Tests=92, Result: PASS**（92/92 = 100%，零跳过）
- 消费者测试：**19/19 passed**

## 注意事项

1. **固定使用 `/data/service/hnp/bin/perl`（5.42.0）**：与
   `file-sharedir-install` / `metrics-any` 先例一致，避免设备 perl 与 hnp perl
   的 `Errno` 实现差异。
2. **两个依赖都必须注入 PERL5LIB**：漏掉 `file-sharedir-install` 会让
   `t/00_prereqs.t` 失败（该文件 require 全部 requires），不要以为它只是
   configure 段就可以省。
3. **`auto/share` 校验不要删**：那是本包的实质产物，缺了消费方在运行期才炸。
4. **`PERL5LIB` 必须用 `prepend_path`**：依赖用 `define_path`（覆盖语义）。
5. 本包与 `file-sharedir-install` 是配套对：安装侧 + 运行期查询侧，缺一不可。
