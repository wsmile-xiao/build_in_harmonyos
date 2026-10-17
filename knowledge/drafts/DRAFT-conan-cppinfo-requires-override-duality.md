# conan 2.29 package_info 双向校验二象性：override=True 依赖不能进 cpp_info.requires，其余直接依赖缺一不可

> 状态：本地路径 B 草稿，需人工审核后才可提升为正式知识条目。

## 现象

多依赖包在 conan create 的最后一步（package_info() 评估，此时全部对象与工具已编译链接完成）失败，两种表象交替出现：

1. `ERROR: <pkg>/x.y.z: package_info(): The direct dependency 'flatbuffers' is not used by any '(cpp_info.components).requires'`
2. `ERROR: ... package 'zlib::' not a direct requirement`（把 override 依赖写进 cpp_info.requires 时）
3. 图解析期：`ERROR: Version conflict: Conflict between zlib/1.3.1 and zlib/1.3.1.1 in the graph. Conflict originates from boost/1.84.0`

osrm-backend/26.5.0（15 个直接依赖）三轮 G2 实测复现以上全部三种。

## 根因（conan 2.29.1 实测）

conan 对 `cpp_info.requires` 做的是**双向**校验，且 `override=True` 在图模型里不建边：

- **正向**：图中每个"直接依赖"（`requires()` 建立的本包→依赖边）必须被 `cpp_info.requires`（或 components.requires）引用，缺一条即失败；
- **反向**：`cpp_info.requires` 的条目必须是真实直接依赖；`override=True` 声明只参与全图版本解析、**不建图边**，因此永远不算直接依赖；
- **版本冲突**：对同一包的多路径精确钉版不一致，conan 2 直接报 Version conflict，没有"就近覆盖"的隐式仲裁——唯一合法出路是 `override=True`。

三者合流成一个两难：为了压平冲突而 `override=True` 的包（osrm 直需 zlib/1.3.1.1，boost 钉 zlib/1.3.1）**不能**进 `cpp_info.requires`；而其余直接依赖**一个都不能少**。

## 诊断（无副作用，两分钟）

对照法：`requires()` 中非 override 包名集合 ≡ `cpp_info.requires` 中 `<name>::<name>` 前缀集合。差集非空即必失败，提前在本地可查，不必等 G2 跑完 135 个对象再炸。

## 推荐方案

```python
def requirements(self):
    self.requires("zlib/1.3.1.1", override=True)   # 只做全图版本解析
    ...  # 其余 14 个正常 requires

def package_info(self):
    self.cpp_info.requires = [
        "boost::boost", "tbb::tbb", "expat::expat", "bzip2::bzip2",
        "lz4::lz4", "lua::lua", "fmt::fmt", "libarchive::libarchive",
        "flatbuffers::flatbuffers", "libosmium::libosmium",
        "protozero::protozero", "vtzero::vtzero", "sol2::sol2",
        "rapidjson::rapidjson",
    ]  # 无 zlib —— override 依赖不建图边
```

## 替代方案（受限）

若反向校验误报仍出现：删除该包的 cpp_info.requires 条目、保留 requirements() 的 override=True。此时该包的头文件/链接必须经传递闭包中其他直接依赖携带（本例经 libarchive→CMakeDeps 生成的 ZLIB config 供 find_package），否则构建期缺头。适用边界：仅当该依赖只被构建期 CMake 探测消费、不需对外传播时可用。

## 反例与禁止

- 不得为凑正向校验编造 dummy 包/捎带第三方源码；
- 不得用 `--build=missing` 强建压掉 Version conflict（冲突是图问题不是构建问题）；
- 不得直接删 cpp_info.requires 条目"过校验"——链接传播会断。

## 与现有知识的关系（查重）

- E234：改精确依赖版本改变 package_id、需新二进制——是"版本选择"边界，不涉及 cpp_info 校验语义，互补不重复；
- E298：消费者运行环境显式化（virtual-run-env）——属 test_package 运行侧，本条属 package_info 图校验侧；
- DRAFT-conan-cmaketools-transitive-includedirs：includedirs 传播，同族不同环节。

## 触发实例与验证

- 触发：osrm-backend 26.5.0 适配，G2 三轮失败定位（conan-verify 62/63/64 轮 conan-create.log）；
- 验证：按对照法修正 14 条清单 + zlib 保留 override 后，G2 图解析通过并完成全量编译（conan-verify66 轮）。
