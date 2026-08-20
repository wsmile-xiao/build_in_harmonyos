# AI 适配操作手册 (ADAPTATION_GUIDE)

本文件是 AI / 人类适配人员在 HarmonyOS (OHOS) 平台上适配三方库的**操作手册**。
按步骤执行即可完成一个库的适配。

> 💡 **适用于人工手动适配场景**。AI 驱动的自动化适配流程详见 **SKILL.md §3 核心流程**
> （含 `ohc-run.py` 脚本自动化：init-build → AI 编译 → conan-init → conan-verify → finish）。
> 推荐优先使用 SKILL.md §3 的 AI 驱动流程，本手册作为手动参考和模板来源。

## 1. 框架概述

build_in_harmonyos 是一个 **AI 驱动的 OHOS 三方库编译适配框架**，包含：

```
build_in_harmonyos/
├── archives/              # conan 配方库 (按字母组织)
│   └── z/zlib/1.3.1/
│       ├── conanfile.py       # 主配方
│       ├── conandata.yml      # 源码 URL + 补丁
│       └── test_package/      # 消费者测试 + MANIFEST.yml
├── ci/                    # CI 流水线
│   ├── conan/
│   │   ├── build_and_test.sh  # 核心构建+测试脚本 (L0-L5 门禁)
│   │   ├── setup.sh           # conan 环境初始化
│   │   └── upload.sh          # 发布上传
│   └── tools/
│       └── extract_upstream_tests.sh  # 上游测试分析工具
└── docs/                  # 文档
    ├── ADAPTATION_GUIDE.md    ← 你在这里
    ├── TEST_QUALITY_SPEC.md   # 测试质量规范 (必读)
    └── MIGRATION_GUIDE.md     # 旧归档迁移指南 (按需)
```

## 2. 平台环境

| 项目 | 值 |
|------|-----|
| OS | HarmonyOS (OHOS) 6.0 |
| Arch | aarch64 (armv8) |
| Compiler | clang 15 (系统自带, `/data/service/hnp/bin/clang`) |
| C++ Stdlib | libc++ |
| Build mode | **原生构建** (build = target = OHOS/aarch64) |
| Conan | 2.x (Conan 2.29.1 验证通过) |

关键约束:
- **不是交叉编译**。worker 设备本身就是 OHOS/aarch64，编译出的二进制直接在本机运行
- `conan cache source` 命令在 Conan 2.x 中**不存在**，不要使用
- OHOS 的 `/bin/sh` 可能不存在，configure 脚本需要用 `CONFIG_SHELL=sh` 或 `self.run("sh ./configure")`

## 3. 适配工作流 (Step 1-7)

### Step 1: 确定目录位置

> ⚠️ **W0 — 依赖发布检查**（适配前第一件事）：先检查所有依赖是否已发布到制品仓（R36）。
> **R37 — 版本号策略**：首次适配用上游版本 `X.Y.Z`，后续修复用 `X.Y.Z.N`（N 从 1 递增）。

```
archives/<首字母>/<包名>/<版本号>/
```

示例: `archives/z/zlib/1.3.1/`
示例: `archives/b/bash/5.3/`

### Step 2: 分析上游构建系统

解压源码包，查看有什么:

```bash
tar xf package-1.0.tar.gz && cd package-1.0
ls configure.ac Makefile.in CMakeLists.txt meson.build Makefile
```

决策树:
```
有 configure.ac / configure.in?
  → Autotools 项目 (最常见的 C/C++ 库)
  → 用 Autotools 模板 (见 §4.1)

有 CMakeLists.txt?
  → CMake 项目
  → 用 CMake 模板 (见 §4.2)

有 meson.build?
  → Meson 项目
  → 用 Meson 模板 (见 §4.3)

只有 Makefile?
  → 纯 Makefile 项目
  → 用 Makefile 模板 (见 §4.4)
```

### Step 3: 写 conanfile.py

选择对应模板 (§4)，替换 `<TODO>` 标记。

必须完成的项:
- [ ] `package()` 方法正确声明了 `copy` 规则 (bin/lib/include)
- [ ] `build()` 方法末尾有上游测试调用 (`make check` / `cmake.test()` / 等)
- [ ] `conandata.yml` 填写了源码 URL 和 SHA256

> ⚠️ **铁律提示**:
> - **R26**: 系统同名库（如 ncurses/zlib/readline）必须在 `generate()` 中设置静态编译（`BUILD_SHARED_LIBS=OFF` / `--disable-shared`），避免 `.so` 污染 `/lib`/`/lib64`
> - **R28**: conanfile.py 必须配套 `test_package/` 目录（Conan L1 官方测试）
> - **R32**: recipe 内平台判断用 `self.settings.os in ("Linux", "OHOS")`，不能 `== "Linux"`
> - **R33**: `build()` 中禁止裸用 `${CC}`/`${CFLAGS}` 等 shell 环境变量，必须从 Conan Toolchain / `self.conf` 获取（详见 §4.3 Makefile 模板）
> - **R37**: 版本号 = 上游版本 + 适配修复后缀（首次 `X.Y.Z`，修复 `X.Y.Z.N`）

### Step 4: 提取上游测试

```bash
# 方法 1: 手动
cd 源码目录
./configure && make          # 先构建
make -n check                 # dry run 查看测试列表

# 方法 2: 辅助工具
bash ci/tools/extract_upstream_tests.sh 源码包.tar.gz
```

记录输出中所有被编译和运行的测试程序。

### Step 5: 写 test_package/

```
test_package/
├── conanfile.py     # 消费者测试 (用模板 §5)
├── test.c           # 或 test.cpp / test.sh
└── MANIFEST.yml     # 上游测试声明 (用模板 §6)
```

必须完成的项:
- [ ] `test()` 方法有 `self.run()` 调用 (不能用空壳)
- [ ] 测试源文件不是 `int main(){return 0;}` 这种空文件
- [ ] MANIFEST.yml 的 `assertion_count` 不为 0

> ⚠️ **R34**: test_package 源文件必须**实质调用被测包的 API** / 执行被测包的二进制，
> 禁止只打印字符串的空壳测试（CI L1e 破坏性反向验证会兜底拦截）。

### Step 6: 本地验证

```bash
# 在 worker 设备上
cd archives/z/zlib/1.3.1/
conan create . --user=ohpcd --channel=stable -pr:h=$HOME/.conan2/profiles/ohos -pr:b=$HOME/.conan2/profiles/ohos --build=missing
```

验证:
- [ ] conan create 成功 (含 make check + test_package)
- [ ] 日志中出现 "Testing package"
- [ ] 日志中出现 make check / ctest 的执行痕迹

> ⚠️ **R29**: `conan_verify` 通过后才可标记 `published`；未通过只能标 `built` 或 `failed`。

### Step 7: 提交 PR

> ⚠️ **禁止直接 `git push`**。必须按 **SKILL.md §0.3 适配工作流规程**（W0-W5）执行：

| 规程 | 内容 |
|------|------|
| **W0** | 依赖发布检查 — 适配前检查所有依赖是否已发布到制品仓（R36） |
| **W1** | 同步主仓库 — `git checkout main && git pull origin main` |
| **W2** | PR 原子性 — 一个配方一个 PR，框架修改单独 PR |
| **W3** | 本地 CI 模拟 — `bash ci/conan/build_and_test.sh <软件名>/<版本>` 通过后再提 PR |
| **W4** | Pre-PR 独立审计 — `python3 $SKILL_ROOT/scripts/pre_pr_audit.py` 审计通过后方可 push |
| **W5** | 知识图谱完整性 — `graph validate` 检查 + 确认 `E###.kv` 与 `doc/E###.md` 配套 |

**R16**: 协作不越权 — 创建功能分支 `git checkout -b feat/{软件名}-{版本}`，走 GitCode PR 流程。

**版本号策略 (R37)**: 首次适配用上游版本 `X.Y.Z`；修复适配问题后递增后缀 `X.Y.Z.N`（N 从 1 递增）。制品仓不支持同版本多 revision 并存。

CI 自动触发 L0-L5 门禁检查。

## 4. conanfile.py 模板

### 4.1 Autotools 项目 (bash, coreutils, sed, grep 等)

```python
from conan import ConanFile
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import get, copy, apply_conandata_patches
import os

class PackageConan(ConanFile):
    name = "<包名>"
    version = "<版本号>"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def layout(self):
        # Autotools 默认在源码目录构建
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")  # <TODO: 按需调整>
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # ── 上游官方测试 (必做) ──
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 清理不需要的文件（.la / .dylib 一律删除）
        for pattern in ["*.la", "*.dylib"]:
            copy(self, pattern, dst=os.path.join(self.package_folder, "lib"), src=os.path.join(self.package_folder, "lib"), keep_path=False, delete=True)
        # R26: 仅系统同名库删除 .so（避免污染 /lib/ /lib64/）
        # 判断方法：检查 /lib 和 /lib64 下是否已有同名 .so
        # <TODO: 如果本库是系统同名库（如 ncurses/zlib/readline），取消下面的注释>
        # copy(self, "*.so*", dst=os.path.join(self.package_folder, "lib"), src=os.path.join(self.package_folder, "lib"), keep_path=False, delete=True)
        # 非系统同名库保留 .so（默认动态链接，由 Conan 管理依赖链）

    def package_info(self):
        self.cpp_info.libs = ["<库名>"]
```

### 4.2 CMake 项目 (openssl, jsoncpp, fmt 等)

```python
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get, apply_conandata_patches

class PackageConan(ConanFile):
    name = "<包名>"
    version = "<版本号>"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False  # <TODO: 按需>
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方测试 (必做) ──
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["<库名>"]
```

### 4.3 Makefile 项目 (zlib 等)

> ⚠️ **R33**: Makefile 项目无法像 CMake/Autotools 那样通过 Toolchain 自动注入编译器路径。
> **必须**在 `generate()` 中从 Conan conf 获取编译器路径并写入环境变量脚本，
> `build()` 中的 `$CC`/`$CXX` 来自 Conan 生成的 env 脚本（`conanbuildenv`），而非 shell 环境变量。

```python
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.env import VirtualBuildEnv, Environment
import os

class PackageConan(ConanFile):
    name = "<包名>"
    version = "<版本号>"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: 从 Conan conf 获取编译器路径，禁止依赖 shell 环境变量
        env = VirtualBuildEnv(self)
        env.generate()
        # 从 Conan settings 获取编译器路径（CI/release worker 上 $CC 可能为空）
        cc = self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)
        cxx = self.conf.get("tools.build:compiler_executables:cpp", "clang++", check_type=str)
        # 写入 env 确保可追溯（$CC 由此脚本提供，不是 shell 变量）
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("AR", self.conf.get("tools.build:compiler_executables:ar", "llvm-ar", check_type=str))
        env.define("RANLIB", self.conf.get("tools.build:compiler_executables:ranlib", "llvm-ranlib", check_type=str))
        env.vars(self).save_script("conanbuild")

    def build(self):
        apply_conandata_patches(self)
        # <TODO: 按 Makefile 参数调整>
        # R33: $CC/$CXX 来自 generate() 生成的 conanbuild env 脚本，不是 shell 变量
        self.run("sh ./configure --static --prefix=/")
        self.run("make -j1 CC=$CC CXX=$CXX")
        # ── 上游官方测试 (必做) ──
        self.run("make check")

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder))

    def package_info(self):
        self.cpp_info.libs = ["<库名>"]
```

### 4.4 Meson 项目 (glib, cairo 等)

```python
from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import get, apply_conandata_patches

class PackageConan(ConanFile):
    name = "<包名>"
    version = "<版本号>"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.compile()
        # ── 上游官方测试 (必做) ──
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["<库名>"]
```

## 5. test_package/conanfile.py 模板

```python
from conan import ConanFile
from conan.tools.build import can_run

class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # <TODO: 编译测试程序并运行>
            # 示例: C 程序
            self.run("clang test.c -o test <TODO: 链接参数>")
            self.run("./test", env="conanrun")
            # 多个测试逐个运行
            # self.run("clang example.c -o example ...")
            # self.run("./example", env="conanrun")
```

## 6. MANIFEST.yml 模板

```yaml
package: <包名>/<版本号>
homepage: "<上游主页 URL>"

upstream_check_command: "make check"    # 或 "ctest" / "meson test"
upstream_test_in_build: true
upstream_test_command: "make check"

upstream_tests:                          # 从 make -n check 输出提取
  - file: <测试源文件.c>
    source: <源码包名>/<测试源文件.c>
    description: "<测试描述>"
    command: "./<测试程序>"

test_package_tests:
  - file: test.c
    description: "<消费者测试描述>"
    command: "./test"

assertion_count: <测试断言数>
```

## 7. conandata.yml 模板

> ⚠️ **R39**: 源码 URL 必须指向官方正式源（GitHub releases、官方网站）或权威镜像源，禁止使用个人 fork、网盘、不明 CDN。

```yaml
sources:
  - url: "https://example.com/package-1.0.tar.gz"
    sha256: "<SHA256 哈希值>"
patches:
  # 如果需要 OHOS 适配补丁
  - patch_file: "patches/0001-fix-ohos-compat.patch"
    patch_description: "修复 OHOS 兼容性"
    patch_type: "portability"
```

## 8. OHOS 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| configure 脚本报错 "cannot run C compiled programs" | OHOS 的 shell 可能不标准 | `CONFIG_SHELL=sh self.run("sh ./configure ...")` |
| 编译报错 `glibc` 符号找不到 | 源码硬编码了 glibc 函数 | 添加补丁用 OHOS 等价替换 |
| `-lpthread` 找不到 | OHOS 用 bionic 不是 glibc | 通常不需要显式链接 pthread |
| make check 某些用例失败 | 平台差异 | 在 MANIFEST.yml 中声明豁免原因, 补丁修复 |

## 9. PR 提交前 Checklist

```
[ ] conanfile.py 的 build() 方法末尾有 make check / cmake.test() / meson.test()
[ ] test_package/conanfile.py 有 test() 方法且含 self.run()
[ ] test_package/ 下有测试源文件（R34: 必须实质调用被测包 API）
[ ] test_package/MANIFEST.yml 已填写, assertion_count > 0
[ ] conandata.yml 有源码 URL 和 SHA256（R39: URL 必须为官方源）
[ ] 本地 conan create 成功通过 (含测试)
[ ] 日志中有 make check / test_package 执行痕迹
[ ] 系统同名库已配置静态链接（R26）
[ ] 命令行工具已创建 commands.json（R38: 软件级别目录）
[ ] 版本号正确（R37: 首次 X.Y.Z / 修复 X.Y.Z.N）
[ ] 已通过 W3 本地 CI 模拟 + W4 Pre-PR 审计
```

## 10. 参考实现

| 库 | 构建系统 | 位置 | 特点 |
|----|---------|------|------|
| zlib | Makefile | `archives/z/zlib/1.3.1/` | 最简单的 C 库适配 |
| bash | Autotools | `archives/b/bash/5.3/` | Autotools + 大量测试 |

详细测试规范见: [TEST_QUALITY_SPEC.md](TEST_QUALITY_SPEC.md)
旧版本迁移见: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
