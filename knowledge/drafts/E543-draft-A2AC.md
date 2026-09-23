# E543（草稿）— protobuf 30+ descriptor accessor 返回 absl::string_view 的下游迁移

## 现象

下游项目（典型：protoc 插件）从 protobuf 29.x 升到 30+/33.x 后，编译期爆发批量错误：

```
no matching function for call to 'std::map<std::string, std::string>::insert(std::pair<absl::string_view, absl::string_view>)'
no match for 'operator+' (operand types are 'std::string' and 'absl::string_view')
no viable conversion from 'absl::string_view' to 'std::string'
```

实测案例：protoc-gen-grpc-web 2.1.1（grpc_generator.cc）对 protobuf 33.6.1 构建时 51 处。

## 根因

protobuf 30 起把 `Descriptor::name()` / `full_name()` / `package()` / `json_name()` /
`filename()` 等 descriptor accessor 的返回值从 `const std::string&` 改为
`absl::string_view`。三类消费点全部炸：

1. `std::map<string, string>` 插入（key/value 都要 `std::string`）
2. `string + accessor()` 拼接（`std::string` 与 `string_view` 无 `operator+`）
3. 形参声明为 `string` 的 helper 接收 accessor 返回值

上游若 pin 老 protobuf（grpc-web 2.1.1 MODULE.bazel pin protobuf 29.1），源码内没有
任何 string_view 化改动可借。

## 修复方案（推荐）

对下游源码打兼容补丁（patch_type: compatibility）：

- 只读 helper 的形参从 `string` 改为 `absl::string_view`（返回值保持 `std::string`）
- map key / 字符串拼接处显式 `std::string(...)` 包裹 accessor 返回值
- 头部补 `#include "absl/strings/string_view.h"`

补丁生成建议用幂等清单式替换脚本迭代到编译零错误，再 `git diff` 固化为规范 patch
（`git diff --check` 零空白告警），经 conandata.yml `patches:` 声明、build() 内
`apply_conandata_patches` 应用，全流程 conan create 可复现。

## 禁止做法

- 批量 `.c_str()` 硬转：引入 string_view 悬垂风险（运行期 UB）
- 盲目退回老 protobuf：偏离仓库统一基线，阻塞依赖闭包升级

## 关联

- similar_to E014（同为 undefined reference 类表象，但根因不同——见 E544）
- 实测来源：protoc-gen-grpc-web 2.1.1（archives/p/protoc-gen-grpc-web/2.1.1/notes.md）
