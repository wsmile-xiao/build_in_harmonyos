# embedmq 1.0.1 — Conan 2 手动打包：上游 CMake 无 install() 规则时的规范化配方

> Draft: DRAFT-EMBEDMQ-0101-CONAN2-NO-INSTALL-RULES-MANUAL-PACKAGING
> Stem: `embedmq-1.0.1-conan2-no-install-rules-manual-packaging` — pairs with the same-stem `.kv`
> Observed: pc1-27 (AtomCode oh-executor embedmq 1.0.1 R01, 2026-09-22)

## 基本信息

- **ID**: DRAFT-EMBEDMQ-0101-CONAN2-NO-INSTALL-RULES-MANUAL-PACKAGING
- **严重度**: 2
- **类别**: conan|packaging|cmake|conan2
- **触发工具**: conan|conan create|conan-verify|cmake
- **阶段**: packaging|testing

## 错误特征（真实日志）

上游 embedmq 1.0.1 是小型 CMake 工程（静态库 embedmq + 公开头 include/），CMakeLists.txt
**完全没有 install() 规则**。conan-verify G2 阶段：

```
embedmq/1.0.1@ohpcd/stable: Calling package()
embedmq/1.0.1@ohpcd/stable: Running CMake.install()
embedmq/1.0.1@ohpcd/stable: RUN: cmake --install ".../b/build/Release" --prefix ".../p"
embedmq/1.0.1@ohpcd/stable: package(): WARN: No files in this package!
...
CMake Error at .../cmakedeps_macros.cmake:81 (message):
  Library 'embedmq' not found in package.
  If 'embedmq' is a system library, declare it with 'cpp_info.system_libs' property
ERROR: embedmq/1.0.1@ohpcd/stable (test package): Error in build() method, line 27
```

初版修复用了旧 API / 相对路径，又踩了两个 Conan 2 差异：

```
ERROR: embedmq/1.0.1@ohpcd/stable: Error in package() method, line 71
    self.copy("libembedmq.a", dst="lib", src=self.build_folder, keep_path=False)
    AttributeError: 'EmbedmqConan' object has no attribute 'copy'
```

```
ERROR: embedmq/1.0.1@ohpcd/stable: Error in package() method, line 73
    copy(self, "*.h", dst="include", src="include")
    ConanException: copy() 'src' and 'dst' arguments must have different values
```

## 根因

1. 上游无 install() → `cmake.install()` 不产出文件 → 包空 → CMakeDeps 找不到库。
2. Conan 2 移除 `self.copy`（旧 Conan 1 API），必须 `from conan.tools.files import copy`。
3. `copy()` 的 dst/src 成对解析：字面量相同（src="include" 且 dst="include"）直接拒绝。
4. Conan 2 不再把相对 dst 自动落到 package_folder 下，dst 必须显式
   `os.path.join(self.package_folder, ...)`。

## 修复（规范化配方模式，可跨库复用）

```python
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

def package(self):
    cmake = CMake(self)
    cmake.install()  # 上游无 install 规则时实际不装任何东西，保留无妨
    copy(self, "libembedmq.a", dst=os.path.join(self.package_folder, "lib"),
         src=self.build_folder, keep_path=False)
    copy(self, "libembedmq.so*", dst=os.path.join(self.package_folder, "lib"),
         src=self.build_folder, keep_path=False)
    copy(self, "*.h", dst=os.path.join(self.package_folder, "include"),
         src=os.path.join(self.source_folder, "include"), keep_path=False)
    copy(self, "*.hpp", dst=os.path.join(self.package_folder, "include"),
         src=os.path.join(self.source_folder, "include"), keep_path=False)
```

另外：改配方前若缓存已存在**陈旧空包**（同一 package_id 的旧 revision），conan create 会直接
`Already installed!` 复用空包，必须 `conan remove "name/ver*" -c` 清缓存后重验。

## 验证

- `conan-verify embedmq 1.0.1`：G0-G4 + L2/L4/L5 全过，`配方验证通过`。
- test_package：2/2 Passed（test_embedmq + test_ohos 鸿蒙专项），conan create 日志留档
  `archives/e/embedmq/1.0.1/reports/conan-create.log`。
- 包内容：`p/lib/libembedmq.a` + `p/include/embedmq.h` / `embedmq.hpp` 存在。

## 适用范围 / 边界

- 适用：上游 CMake 工程无任何 install() 规则、配方需手动打包的库（小型静态库最常见）。
- 边界：上游自带 install() 规则的库**不要**用本模式（正常 cmake.install() 即可）；
  头文件若装到 include/<subdir>，dst/src 需按实际子目录调整（参见 E217）。
- 反例：试图把 `src="include"`/`dst="include"` 写成同名相对路径 → API 拒绝；
  试图用 `self.copy` → AttributeError。

## 查重差异（与既有条目）

- E217（headers 安装到 include/<subdir>）：触发阶段同为 test_package 找不到头/库，但根因是
  **includedirs 指向子目录**，方案是改 package_info().includedirs，与本候选（上游无 install →
  package() 手工拷产物）根因与方案均不同 → 部分触发重叠、方案新增。
- E392（raw-makefile 配方模式）：方向不同（手工 make 配方 vs CMake 打包），无遮挡。
- 知识图谱引擎对 `self.copy`/`copy src dst` 无既有命中（本候选为该组合首次记录）。

## 关系

- similar_to: E217
- caused_by: （无既有条目）
- prerequisite_of: 消费者用例/测试可用性验证（包内必须有真实产物）
- conflicts_with: （无）