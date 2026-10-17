# DRAFT — header-only Conan 2 配方三段修复（fifo_map 1.0.1 实测）

- **触发工具**: conan-verify / conan create
- **触发阶段**: recipe 完整性 (G1) → conan create 类型校验 (G2) → test_package 消费者配置 (G2)
- **来源事件**: archives/f/fifo_map/1.0.1（第一轮适配，executor pc1-58）

## 问题

header-only C++ 库（fifo_map 为 nlohmann 系单头文件库，无构建系统）按
`conanfile-headeronly.py.tmpl` 编写配方时，conan-verify 连续暴露三处独立门禁错误：

1. **G1 FAIL：缺少 `build()` 方法**
   `conanfile.py 缺少: build() 方法` —— G1 配方完整性把 `build()` 列为必填结构字段，
   header-only 无构建系统库省略 `build()` 即 FAIL（E257 已记录同类问题）。

2. **G2 FAIL：`Package type is 'library', but no 'shared' option declared`**
   Conan 2 对 `package_type = "library"` 强制要求声明 `options = {"shared": [...]}`；
   header-only 库无二进制产物，正确类型为 `package_type = "header-library"`，
   既免除 shared 选项校验，也让 package_id 与编译器/arch 解耦。

3. **G2 FAIL（test_package）：`Imported target "fifo_map::fifo_map" includes non-existent path .../p/include`**
   三处独立成因，均在 package() 头文件拷贝环节：
   - `src=self.source_folder` 根 glob 无法命中 `src/` 子目录内的头文件 → include/ 为空；
   - 相对 `dst="include"` 会落在 build 目录而非包目录 → CMakeDeps 生成
     INTERFACE_INCLUDE_DIRECTORIES 指向不存在的 `<pkg>/include`。

## 根因

header-only 模板的默认 package() 假设头文件位于源码根或 include/ 子树，且相对
dst 隐含"当前目录=包目录"；两处假设对位于 `src/` 子目录的单头文件库均失效。
类型声明错误则源于把"无编译库"误标为普通 `library` 类型。

## 修复（三处配合，缺一不可）

```python
# (1) 显式 build()（空 patches 时即 no-op，满足 G1 结构完整性）
def build(self):
    apply_conandata_patches(self)   # patches: {} 时为 no-op

# (2) 类型声明
package_type = "header-library"

# (3) package() 拷贝：src 指实际子目录，dst 显式指包目录
copy(self, "fifo_map.hpp",
     src=os.path.join(self.source_folder, "src"),
     dst=os.path.join(self.package_folder, "include"))
```

## 验证

- conan-verify fifo_map 1.0.1：G1/G2/G3/G4 全 PASS；
- test_package 消费者（`#include <fifo_map.hpp>` + FIFO 语义断言）编译、链接、运行 rc=0；
- W3 本地 CI 模拟（build_and_test.sh）通过（JC 命中其他库基线空文件经基线隔离复验后放行）。

## 适用边界

- 适用：header-only / 单头文件 C++ 库的 Conan 2 配方（普查该类占配方 ~26%）；
- 反例：有 CMake/meson/autotools 构建系统的库照常写真实 build()，勿用 no-op 顶替；
  有二进制产物的库不得把 package_type 改为 header-library。

## 查重（七轴）

| 轴 | 结论 | 说明 |
|---|---|---|
| exact_duplicate | false | 无完全同签名的既有条目（G2 "no shared option" 签名未单独立条） |
| causal_duplicate | false | E257 覆盖 G1 build() 缺项；E322 覆盖 CMake INTERFACE 库类型声明；本条目为三处门禁的完整组合，且带 "no shared option" 独立错误签名 |
| trigger_overlap | true | 与 E257 共享 G1 build() 触发；与 E322 共享 header-library 类型讨论 |
| solution_overlap | true | 与 DRAFT-bitmapplusplus（子目录头文件拷贝）共享 package() dst 修复思路 |
| combination_novelty | true | 三处修复的完整配方组合 + G2 类型校验错误签名为本条目新增 |
| boundary_novelty | true | 明确 header-library 适用边界（无二进制 header-only）与反例 |
| test_migration_novelty | false | 无测试迁移内容 |

**关系字段**：similar_to=[E257, E322, DRAFT-bitmapplusplus-1.1.1-header-only-subdir-header-copy]；caused_by=无；prerequisite_of=无；conflicts_with=无。

## 决定

- `new_draft`（路径 B，知识库扩展）：DRAFT-fifo_map-1.0.1-header-only-conan2-recipe-gate.kv/.md
- 理由：组合新颖性成立（"no shared option" 错误签名 + 三处修复完整闭环），
  已由本轮真实日志验证，可跨库复用于 header-only 族（占配方 26%）。