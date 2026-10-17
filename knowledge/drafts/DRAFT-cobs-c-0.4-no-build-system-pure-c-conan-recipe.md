# DRAFT-cobs-c-0.4-no-build-system-pure-c-conan-recipe：无构建系统纯 C 库的 Conan 自定义配方

> Contributor: pc4-9 | Status: Draft | Updated: 2026-09-20
> Source: cobs-c 0.4 适配（feat/cobs-c-0.4）；触发场景：init-build 按 autotools 生成配方，conan create 直接失败
> 对应：`knowledge/drafts/DRAFT-cobs-c-0.4-no-build-system-pure-c-conan-recipe.kv`

## 现象

官方源码仅含 `cobs.c`/`cobsr.c`/`cobs.h`/`cobsr.h` + 测试目录，无 configure、无 Makefile、无 CMakeLists.txt。
init-build 按 autotools 模板生成 conanfile.py 后，`conan create` 失败：

```text
clang-15: error: no such file or directory: 'cobs.c'
clang-15: error: no input files
ERROR: cobs-c/0.4@ohpcd/stable: Error in build() method
```

随后 conan-verify G1 又报：

```text
❌ conanfile.py 缺少: export_sources() 方法
❌ conanfile.py 缺少: 补丁应用调用
```

再修配方时若尝试 `self.conf.get("tools.build:archiver")` 会报：

```text
ConanException: [conf] 'tools.build:archiver' does not exist in configuration list
```

## 根因

1. **basic_layout 路径语义**：`basic_layout(self)` 下 `source()` 把源码解包进
   `source_folder`，而 `build()` 的工作目录是 `build_folder`（如 `.../b/build-release`），
   裸写 `clang -c cobs.c` 在当前目录找不到源文件。
2. **G1 门禁硬性要求**：conan-verify 的 G1（配方完整性）强制 conanfile.py 声明
   `export_sources()`（含 `export_conandata_patches`）与 `build()` 内的补丁应用调用
   （`apply_conandata_patches`），即使该库 0 补丁也必须有方法声明。
3. **Conan 2.29 无 archiver conf**：`tools.build:archiver` 不存在于配置列表，不能读，
   归档器直接写 `llvm-ar`。

## 方案

conanfile.py 改为自定义编译（不用 Autotools/CMake 工具链）：

```python
def build(self):
    apply_conandata_patches(self)
    c_compiler = self.conf.get("tools.build:compiler_executables", default={}).get("c") or "clang"
    cflags = "-fPIC -O2" if not self.settings.build_type == "Debug" else "-fPIC -g"
    src, bld = self.source_folder, self.build_folder
    self.run(f"cd {src} && {c_compiler} {cflags} -c cobs.c -o {bld}/cobs.o")
    self.run(f"cd {src} && {c_compiler} {cflags} -c cobsr.c -o {bld}/cobsr.o")
    self.run(f"llvm-ar rcs {bld}/libcobs.a {bld}/cobs.o {bld}/cobsr.o")

def package(self):
    copy(self, "cobs.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
    copy(self, "cobsr.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
    copy(self, "libcobs.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
```

要点：源文件用 `source_folder` 前缀、产物落到 `build_folder`；`export_sources()` 用
`export_conandata_patches`；`build()` 开头 `apply_conandata_patches`；归档器直接 `llvm-ar`。

## 验证

- `conan create ... -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`：PASS（含 test_package）
- conan-verify：G1/G2/G3/G4 全过
- W3 本地 CI（build_and_test.sh）：L0/L1/L2/L4/L5 全过，Pass rate 100%

## 适用边界 / 反例

- 适用：无任何构建系统、直接可用编译器编译的轻量纯 C 库（cobs-c 形态）
- 反例：有自定义 Makefile 的库走 E097（custom-config-mk）；header-only 库走 header-only 配方；
  依赖多、需要链接系统库的库需评估手动链接

## 关系

- similar_to: E097（自定义 Makefile 库，BuildSSL）、E012（llvm-ar 缺失）
- caused_by: — | prerequisite_of: — | conflicts_with: —
