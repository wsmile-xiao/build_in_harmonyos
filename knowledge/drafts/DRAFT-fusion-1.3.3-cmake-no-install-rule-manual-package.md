# CMake 无 install 规则的小型 C 库：package() 手动装配 include/<subdir> 头与静态库

- **草稿 ID**: DRAFT-fusion-1.3.3-cmake-no-install-rule-manual-package
- **来源**: fusion 1.3.3（xioTechnologies/Fusion）首轮 HarmonyOS PC 适配
- **分类**: cmake / conan / packaging / c-library / static-library
- **状态**: 本地草稿（随 fusion 1.3.3 归档同 PR 提交，路径 B 知识库扩展）

## 问题 / 错误签名

- **conan-verify G2 失败**：test_package 编译报 `fatal error: 'Fusion.h' file not found`
- **配方照搬模板的隐患**：上游无 install 规则时 `cmake.install()` 静默打包 0 个文件，
  G4/L5 产物门禁会失败
- **复现命令**：`ohc-run.py conan-verify fusion 1.3.3`（或直接 conan create）

## 根因

上游 CMakeLists.txt 只写：

```cmake
file(GLOB_RECURSE files "*.c")
add_library(Fusion ${files})
target_include_directories(Fusion PUBLIC .)
```

完全**没有 install 规则**（无 `install(TARGETS/FILES ...)`）。这与 E217 记载的场景不同：
E217 是上游 `install(FILES ... DESTINATION include/<subdir>)` 把头装进子目录、只需调
`includedirs`；此处上游连安装目标都没有，模板配方 `cmake.install()` 无文件可装，
且 conan-init 默认 `includedirs=["include"]` + test_package 写 `<Fusion.h>` 必然 G2 报错。

## 最小修复方案（在 archives/f/fusion/1.3.3 范围内）

1. **build()**：只构建库目标，跳过示例——
   `cmake.build(target=["Fusion"])`（上游示例目标 Simple/Advanced 不装包，R38 不适用）。
2. **package()**：手动装配——
   - 公开头：`copy(self, "*.h", src=source_folder/Fusion, dst=package_folder/include/Fusion)`
   - 静态库：`copy(self, "libFusion.a", src=build_folder/Fusion, dst=package_folder/lib)`
   - LICENSE：`copy(self, "LICENSE.md", src=source_folder, dst=package_folder/licenses)`
3. **package_info()**：
   - `cpp_info.libs = ["Fusion"]`
   - 链接数学库的库追加 `cpp_info.system_libs = ["m"]`（UNIX 平台）
4. **test_package/test.c**：include 必须用子目录形态 `#include <Fusion/Fusion.h>`，
   与手动装配布局一致；测试必须真实调用公开 API（AHRS 静止收敛 + 传感器模型数值断言），
   非空壳（R34 / L1e）。

## 验证结果

- `ohc-run.py conan-verify fusion 1.3.3`：G1/G0/G2/G3/G4 全 PASS
- conan create 日志：`Linking C static library libFusion.a` + test_package 通过
- L1e 破坏性反向验证（lib/、include/ 移走 → 测试失败）确认消费者测试真实依赖被测包
- 上游两个 C 示例程序在 OHOS 上实际运行 exit 0（Simple/Advanced 输出零欧拉角）

## 适用边界

- **适用**：上游 CMake 仅 add_library、无 install 规则的小型 C/C++ 静态库
  （传感器融合、单文件算法类库常见）；Conan 2 + OHOS aarch64。
- **不适用**：上游自带完整 install/export 的库（走标准 cmake.install()）；
  header-only INTERFACE 库（见 E322 的 header-only 模式）；需要 CMake CONFIG 包的
  大型项目（可考虑补 install 规则补丁的 fallback）。

## 反例

- 若上游有 install 规则但装到 include/<subdir>：用 E217 方案（调 includedirs），
  不要手动 copy。
- 若上游无 install 规则却调用 cmake.install()：Packaged 0 files，G4/L5 失败。

## 查重（七轴）

| 轴 | 结论 |
|---|---|
| exact_duplicate | 无（知识库无此模式条目） |
| causal_duplicate | 否（E217 根因是"install 到子目录"，本条目根因是"无 install 规则"） |
| trigger_overlap | 部分（同触发 conan G2 test_package 头文件找不到） |
| solution_overlap | 部分（E217 只调 includedirs；本条目手动 copy 头+库+system_libs） |
| combination_novelty | 有（"无 install 规则 → 手动装配头+静态库+system_libs m"组合为新增） |
| boundary_novelty | 有（E217 不覆盖"上游完全没有安装目标"这一边界） |
| test_migration_novelty | 无（test_package 沿用 R34 消费者测试范式） |

**关系**：similar_to=E217（触发器同源、方案不同层）；caused_by=无；prerequisite_of=无；conflicts_with=无。
