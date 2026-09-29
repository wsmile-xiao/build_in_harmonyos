# 无 `install()` 规则的 CMake 库 OHOS 适配

> 配套条目：`knowledge/drafts/pxlib-0.6.9-no-install-cmake-package.kv`
> 来源：pxlib 0.6.9 OHOS aarch64 适配（feat/pxlib-0.6.9 分支）

## 问题

上游 `CMakeLists.txt` 只有 `add_library` + `target_include_directories`，**没有** `install(TARGETS ...)` / `install(FILES ...)` 等安装规则。conan `cmake.install()` 因此无产物，`package_folder` 下无 `lib/` 与 `include/`，consumer 侧 `find_package()` 失败。

次要问题：`*.h.in` 模板与 `configure_file` 生成的 `*.h` 并存时，consumer 侧 include 路径中 `.h.in` 优先匹配，占位符未替换导致编译失败。

## 根因

CMake 的 `install()` 规则是 conan `cmake.install()` 的**唯一**安装通道；没有规则就没有产物。conan 的 `package()` 阶段不做自动收集，只信任 `cmake.install()` 的输出。

## 解法

`package()` 中用 `conan.tools.files.copy` 手动收集：

```python
def package(self):
    cmake = CMake(self)
    cmake.install()  # 无产物但必须调用
    lib_suffix = ".so" if self.options.shared else ".a"
    copy(self, f"lib{name}{lib_suffix}",
         self.build_folder,
         os.path.join(self.package_folder, "lib"))
    # 只拷生成后的 .h，不拷 *.h.in 模板
    copy(self, "<generated>.h", os.path.join(self.build_folder, "include"),
         os.path.join(self.package_folder, "include"))
```

### 关键约束

- `cmake.install()` 仍要调用（触发 CMake install 配置步骤）。
- `*.h.in` 模板**不**随包分发。
- 头文件来源分两类：`configure_file` 生成的（`build_folder/include/*.h`）+ 源码原头（`source_folder/include/*.h`），两者都要拷。

### 配套修补（同属"上游 CMakeLists.txt 质量差"家族）

- 版本宏写死、`SHARED` 硬编码：用 `conandata.yml` 登记的**真实补丁文件**（`patches/NNNN-*.patch`，`a/ b/` 相对路径头）修复，`export_sources()` + `apply_conandata_patches()` 在 `build()` 应用（G1 配方完整性门禁要求；conan 自动剥离 `a/`/`b/` 前缀）。
- 补丁无法命中时 `apply_conandata_patches` 会 `raise ConanException`，不要静默跳过。

## 验证

```bash
conan create archives/p/pxlib/0.6.9 -pr:h ohos-aarch64 -pr:b ohos-aarch64
find <package_folder>/lib -name 'libpxlib.*'    # 非空
find <package_folder>/include -name '*.h'      # 含 paradox.h / paradox-gsf.h / pxversion.h
```

test_package `find_package(pxlib REQUIRED)` 通过且 `PX_new()` + `PX_open_file()` 冒烟 PASS。

## 同类迁移

- 任何 CMake 库遇到"无 install() 规则"都适用本模式。
- 版本宏/SHARED 硬编码修补是通用手法。
- test_package 写二进制文件格式做解析冒烟时，先读上游结构体定义算准字段偏移。
- OHOS aarch64 上 test 临时文件用 `$HOME/tmp`，**不**用 `/tmp`（HMDFS 只读）。
