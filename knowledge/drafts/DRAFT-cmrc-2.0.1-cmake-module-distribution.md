# DRAFT-cmrc-2.0.1-cmake-module-distribution — 纯 CMake 模块分发包（无库无头）的 Conan 配方模式

## 问题现象

上游只发布单个 CMake 模块（cmrc 2.0.1 = CMakeRC.cmake，无库、无头、无 install 规则）的三方库，
在 OHOS aarch64 + Conan 2.x 配包装插时，conan-init 默认模板与门禁逐个暴露打包模型缺口：

```
# 1. conan-init 按 URL 后缀猜 autotools，生成 configure/make 模板（与实际 CMake 模块不符）
# 2. G1 门禁要求 build()/export_sources() 方法齐全
# 3. G2 conan create: package_type=library 必带 shared 选项
#    ERROR: Package type is 'library', but no 'shared' option declared
# 4. package() 用相对 dst 时文件落入 build 目录，包目录为空（G4 找不到产物）
# 5. test_package find_package(cmrc) 成功后 cmrc_add_resource_library 仍不可用
#    -- 模块命令必须在 consumer configure 期注入, 而非链接期
```

## 根因分析

「库+头」是 Conan 包的标准打包模型（lib/bin/include），但**纯 CMake 模块分发**
（上游只有 `.cmake` 模块文件，消费者 `include()` 后获得命令）没有对应原生表达：
1. 模块文件要装到可被下游 `find_package` 找到的位置，
2. 模块内定义的命令（如 `cmrc_add_resource_library`）要**注入 consumer 的 CMake 作用域**，
   CMakeDeps 生成的 config 默认不 include 任何上游模块。

## 解决方案（已验证，ecbuild 同款机制）

```python
# conanfile.py 关键四要素
def package(self):
    copy(self, "CMakeRC.cmake", src=self.source_folder,
         dst=os.path.join(self.package_folder, "lib", "cmake", "cmrc"))  # ① lib/cmake 落位
    copy(self, "LICENSE.txt", src=self.source_folder,
         dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

def package_info(self):
    self.cpp_info.includedirs = []
    self.cpp_info.libdirs = []
    self.cpp_info.bindirs = []
    self.cpp_info.builddirs = ["lib/cmake/cmrc"]                          # ② builddirs 暴露
    self.cpp_info.set_property("cmake_build_modules",                      # ③ 主动 include 模块
                               ["lib/cmake/cmrc/CMakeRC.cmake"])
    self.cpp_info.set_property("cmake_file_name", "cmrc")

def package_id(self):
    self.info.clear()                                                      # ④ 纯模块 → 单一 package_id
```

- 必须同时具备 `export_sources()`（export_conandata_patches）与 `build()`
  （apply_conandata_patches），满足 G1 与补丁管线。
- `package_type = "library"` + `options = {"shared": [True, False]}`，
  `default_options = {"shared": False}`（Conan 2 强制 library 型声明 shared）。
- `copy()` 的 `dst` 必须用 `os.path.join(self.package_folder, ...)` 绝对路径，
  相对路径会被解析到 build 目录。
- 上游 CMakeRC.cmake 内含 `cmake_minimum_required(VERSION 3.3)`，CMake >= 4 会拒绝，
  需补丁 bump 到 3.5（E103 精确覆盖，直接沿用 rec_approach）。

## 验证

- conan-verify G1/G2/G3/G4 + L2/L4/L5 全部 PASS（OHOS aarch64, clang 15）。
- test_package 真实消费：find_package(cmrc) → cmrc_add_resource_library 嵌入资源文件
  → 编译可执行 → 运行断言（test_cmrc 读 hello.txt；test_ohos 覆盖 exists/is_file/
  is_directory/iterate_directory/open 异常路径），CTest 2/2 通过。

## 查重结论 (Path B 必需)

- **与 E473 的区别**：E473 是**消费侧**为依赖注入缺失的 imported target
  （WebP::webpdemux，libwebp 包暴露不足）；本条是**输出侧**自身为纯 CMake 模块分发，
  四要素（lib/cmake 落位 + cmake_build_modules + builddirs + package_id clear）完整表达。
  engine 检索命中 E473（部分覆盖，场景不同），不构成精确重复。
- **与 E321/E322 的区别**：E321/E322 是 header-only INTERFACE 库（上游自带 install/export、
  CONFIG target），本条上游**无任何 install 规则**，只能手工 copy 模块。
- **正式知识/图谱/草稿**：index.tsv、doc/、drafts/ 四处均无「CMake 模块分发包打包模式」条目。
- **归档**：ecbuild 3.15.0 有同类实体案例但 notes 未沉淀为通用条目。

# 适用边界

- 适用：上游仅发布 `.cmake` 模块、无头无库无 install 的库（CMakeRC、ecbuild、
  extra-cmake-modules 型）；OHOS/aarch64 + Conan 2 + CMakeDeps 场景。
- 反例：上游自带 install/export 的 header-only INTERFACE 库走 E321/E322 模式；
  需要给依赖补 target 的走 E473；有真实编译产物的库不适用。

# 关联

related_entries: E473, E321, E322, E103