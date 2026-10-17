# DRAFT — Makefile 型 Conan 配方 build()/package() 全套陷阱（commander 1.4.0）

## 问题

裸 Makefile 型三方库（上游只有 `test`/`clean` 目标、无 configure 无 install）适配 OHOS 时，
conan-verify G2 连续 3 类失败：

1. `clang-15: error: no such file or directory: 'src/commander.c'`
2. test_package 编译 `fatal error: 'commander.h' file not found`
3. `ConanException: [conf] 'tools.build:compiler_executables:c' does not exist in configuration list`

## 根因

1. **basic_layout 下 self.run() 的 cwd 是 build 目录**（Conan 2 默认 no_copy_source=False，
   源码复制到 build 树；self.run() 的 cwd 为 build-release/ 而非源码根）。build() 里用相对
   路径 `src/commander.c` 必然失败。
2. **conan copy() 默认 keep_path=True**：`copy(self, "src/commander.h", source_folder, pkg/include)`
   把文件装进 `include/src/commander.h`，include/ 根为空，消费方 `#include "commander.h"`
   编译即失败。复制带子目录路径的头文件必须 `keep_path=False`。
3. **`tools.build:compiler_executables` 是字典型 conf**，无 `:c` 单项键。Conan 2.29.1
   实测 `self.conf.get("tools.build:compiler_executables:c")` 抛
   `does not exist in configuration list`。SKILL 模板 conanfile-makefile.py.tmpl 仍写
   单项形式，照抄即触发。

## 方案

```python
def build(self):
    compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
    cc = compilers.get("c", "clang")
    ar = compilers.get("ar") or os.environ.get("AR", "llvm-ar")
    ranlib = compilers.get("ranlib") or os.environ.get("RANLIB", "llvm-ranlib")
    # 1) 绝对路径：源读 self.source_folder，产物写 self.build_folder
    self.run(f'"{cc}" -c -fPIC -O2 src 文件绝对路径 -o build 目录绝对路径', env="conanbuild")
    ...
def package(self):
    # 2) keep_path=False：路径精确到源子目录，只取文件名
    copy(self, "commander.h", os.path.join(self.source_folder, "src"),
         os.path.join(self.package_folder, "include"), keep_path=False)
```

R26/R33：非系统同名库不必强制静态；编译器一律取自 Conan conf（字典键），禁裸 `${CC}`。

## 验证

- commander 1.4.0：conan-verify 全门禁（G1-G4、L2/L4/L5）PASS，conan create 复现成功；
  test_package 消费者用例 + 鸿蒙专项测试 11 断言全 PASS。
- 上游 test.c 运行 1/1 通过（7 种参数组合含错误路径退出码）。

## 适用边界

- 适用：无 configure 的裸 Makefile 型 C/C++ 库（需要在 build() 直调编译器/归档器）。
- 边界：系统同名库（zlib/ncurses 等）按 R26 静态；有 configure 的项目走 Autotools 模板；
  header-only 库走 headeronly 模板（E307 直编消费者）。
- 反例：cmake 型配方（CMakeToolchain 已经处理路径与编译器，不适用本方案 1/3）。

## 查重差异

- E311（source-folder isolation）聚焦 no_copy_source 语义与"修改源码"诊断，不含
  self.run() cwd 具体语义与本三连修复；
- E307/E529 用 compiler_executables 字典键，但分别聚焦 test_package 直编与工具 PATH，
  未覆盖"单项 conf 不存在"根因及 keep_path 陷阱。