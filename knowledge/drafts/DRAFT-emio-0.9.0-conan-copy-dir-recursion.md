# DRAFT-emio-0.9.0-conan-copy-dir-recursion

> Contributor: pc1-51 | Status: Draft | Updated: 2026-09-03
> Source: emio 0.9.0 HarmonyOS PC 适配（task emio-0.9.0-r01-pc1-51，conan-verify G2 失败链）
> 领域：Conan 配方（header-only 包安装）

## 背景

emio 0.9.0 是 C++20 header-only I/O 库（CMake INTERFACE target，零依赖）。
Conan 适配时 `package()` 用 `conan.tools.files.copy(self, "include/emio", src=..., dst=package_folder)`
拷贝头文件，`conan create` 的 **test_package 阶段**失败：

```text
CMake Error in CMakeLists.txt:
  Imported target "emio::emio" includes non-existent path
    ".../.conan2/p/b/emiob.../p/include"
  in its INTERFACE_INCLUDE_DIRECTORIES.
```

包内容检查发现仅 `licenses/LICENSE` 与元数据文件，`include/emio/` 整目录缺失。

## 错误签名

```text
Imported target ".*" includes non-existent path ".*/p/include"|INTERFACE_INCLUDE_DIRECTORIES.*does not exist|CMake Generate step failed
```

## 根因

`conan.tools.files.copy()` 按 **glob 文件匹配**展开 pattern，`"include/emio"` 指向目录时
不递归展开目录内文件（与 `shutil.copytree` 语义不同），因此整目录静默未拷贝，
而 `package_info()` 的 `includedirs=["include"]` 仍导出 include 路径 → CMakeDeps
导入目标引用不存在的目录 → Generate 阶段失败。

## 方案

`package()` 对目录拷贝改用 `shutil.copytree`（保留子目录结构）：

```python
def package(self):
    import shutil
    shutil.copytree(os.path.join(self.source_folder, "include", "emio"),
                    os.path.join(self.package_folder, "include", "emio"))
    copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
```

`conan.tools.files.copy()` 仍适用于单文件/通配文件（如 `LICENSE`、`*.hpp` 平铺场景）。

## 验证

- 修复前: conan-verify G2 FAIL（include 路径不存在，Generate 失败）
- 修复后: conan-verify G1-G4/L2/L4/L5 全 PASS；test_package 消费者（format/static_buffer/writer/reader/scan）编译运行通过
- 命令: `python3 scripts/ohc-run.py conan-verify emio 0.9.0`

## 适用边界

- 适用: 无上游 CMake install/export、需手动拷贝头文件目录的 header-only 库（Conan 2）
- 不适用: 上游自带 install/export 的库（走 E322 的 cmake install 路径）；单文件/glob 文件拷贝（copy() 足够）
- 相关既有知识: E322（header-only CMake INTERFACE 配方模式，含 install/export 路径）、E217（头安装子目录 includedirs）、E498（headerless includedirs 空列表）——本条目补充"目录拷贝需 copytree"这一差异点

## 查重差异

| 范围 | 结果 |
|---|---|
| 正式知识 doc/ | 部分覆盖（E322/E217/E498 未涉及 copy 目录不递归） |
| 图谱 index.tsv | 未命中 copy-dir-recursion |
| 草稿 drafts/ | 未命中 |
| 配方库 recipes/ | 未命中 |