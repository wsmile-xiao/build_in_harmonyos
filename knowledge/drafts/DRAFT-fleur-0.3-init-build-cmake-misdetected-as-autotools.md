# DRAFT-fleur-0.3-init-build-cmake-misdetected-as-autotools：init-build 将纯 CMake 项目误判为 autotools，配方模板选错

> Contributor: pc4-45 | Status: Draft | Updated: 2026-09-26
> Source: fleur 0.3 适配（conan-init 配方生成）
> 对应：`knowledge/drafts/DRAFT-fleur-0.3-init-build-cmake-misdetected-as-autotools.kv`
> 关联：`knowledge/graph/E097.kv`（部分覆盖）、`knowledge/graph/E170.kv`（manifest 字段兼容）

## 现象

`ohc-run.py conan-init <sw> <ver>` 生成配方时输出"构建系统: autotools"，
conanfile.py 是 AutotoolsToolchain + configure/make 模板；但源码顶层只有
`CMakeLists.txt`、**没有 configure 脚本**。按模板构建必然失败：

```console
ℹ️ G0: 运行 configure...
❌ G0: configure 失败 (exit 127)     # configure: not found
```

## 根因

init-build 的构建系统检测以"是否存在 configure/configure.ac"判定 autotools。
纯 CMake 项目（顶层 CMakeLists.txt、无 configure）被**误判为 autotools**，
conan-init 据此选错模板：

- generate() 用的是 AutotoolsToolchain，不会注入 CMake 必需变量
  （本案例：上游需要 `-DTARGET_GROUP=production` 才能构建库 + CLI）；
- build() 调 autotools.configure() → 无 configure 脚本 → exit 127；
- 按模板硬跑 = 配方废品，必然返工。

> 与 E097（无 configure 的自定义 Makefile、manual install）共享"无 configure
> 脚本"触发面，但 E097 的项目本身就是 Makefile 手工构建；本候选是 **CMake 项目
> 被检测机制误判**，修复是重写配方模板，不是手工 install。

## 方案（按优先级）

### 1. 重写 conanfile.py 为 CMake 模板（推荐）

```python
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

def layout(self): cmake_layout(self)

def generate(self):
    tc = CMakeToolchain(self)
    tc.variables["TARGET_GROUP"] = "production"   # 项目必需变量
    tc.generate()

def package(self):
    # 上游 CMakeLists 无 install() 时手工拷贝
    copy(self, "fleur.h", src=..., dst=include, keep_path=False)
    copy(self, "*.a", src=self.build_folder, dst=lib, keep_path=False)
    copy(self, "fleurcli", src=..., dst=bin, keep_path=False)

def package_info(self):
    self.cpp_info.libs = ["fleur", "fnv", "myutils"]
    self.cpp_info.system_libs = ["m"]
```

要点：① CMakeToolchain + cmake_layout；② 注入项目必需 CMake 变量；③ 上游无
install() 规则时 package() 手工拷贝产物（*.a / *.h / bin）；④ package_info
补全依赖顺序与 system_libs。同时把 `.build-context` 的 `BUILD_SYSTEM` 校正为
`cmake`。验证：重写后 `conan-verify` G1/G0/G2/G3/G4 + L2/L4/L5 全通过。

### 2. 模式 B 探索 + 手工重写（复杂项目）

init-build 探索编译验证后，conan-init 只生成骨架，AI 按 CMake 模板完整重写。

## 判别步骤

1. 源码根目录含 `CMakeLists.txt` 且无 `configure` / `configure.ac` → 按 CMake 处理；
2. conan-init 输出"构建系统: autotools"时核对源码构建系统；
3. 检查上游 CMakeLists 是否有 `install()` 规则——没有则 package() 需手工拷贝。

## 适用边界 / 反例

- ✅ 适用：纯 CMake 项目（无 configure 脚本、无 autotools 痕迹）首次适配。
- ❌ 不适用：有 configure.ac/configure 的 autotools 项目（模板选择正确）；
  同时存在 configure 与 CMakeLists.txt 的混合项目（以项目 README 声明的
  主流构建路径为准）。
- 平台：非 OHOS 专有——任何用 conan-init 生成配方的平台都会踩中模板误判。
