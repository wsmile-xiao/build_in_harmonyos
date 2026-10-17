# E544（草稿）— protobuf 33 utf8 校验库拆分导致手工链接清单遗漏

## 现象

静态链接 protobuf 33（libprotoc/libprotobuf）后链接期报：

```
undefined reference to 'google::protobuf::internal::EpsCopyInputStream::VerifyUTF8Fallback'
```

实测案例：protoc-gen-grpc-web 2.1.1 手工命令
`clang++ grpc_generator.o <pkg>/lib/libprotoc.a <pkg>/lib/libprotobuf.a <absl...>`
报上述未解析符号。

## 根因

protobuf 33 把 utf8 校验拆成两个独立静态库：

- `<pkg>/lib/libutf8_range.a`
- `<pkg>/lib/libutf8_validity.a`

拆分关系只写在 CMake imported target 链上：`protobuf::libprotobuf` 的
`INTERFACE_LINK_LIBRARIES` 含 `utf8_range::utf8_validity`（后者再链
`utf8_range::utf8_range`）。手工拼库清单时没有等价信息，遗漏即报
`VerifyUTF8Fallback` 未解析。这是**链接清单问题**，不是代码问题。

⚠️ 知识图谱引擎对 "undefined reference" 类错误会粗筛命中 E014（musl 未导出
syslog/getrandom 符号）——**误匹配**：本题根因是 protobuf 库拆分而非系统库缺符号，
E014 的 `-DNO_SYSLOG` 类方案无效。判别法：未解析符号属于 `google::protobuf::*`
命名空间 → 库清单问题；属于 libc/musl 面 → E014。

## 修复方案（推荐）

用 CMake 让依赖图自动解析：

```cmake
find_package(Protobuf CONFIG REQUIRED)
target_link_libraries(<target> PRIVATE protobuf::libprotoc)
```

protobuf/33.6.1（ohpcd）是 `cmake_find_mode=none` 的原生 config 包，需在 conanfile
`generate()` 里显式设置三个变量（与 protobuf/33.6.1 配方同款）：

- `Protobuf_DIR=<pkg>/lib/cmake/protobuf`
- `utf8_range_DIR=<pkg>/lib/cmake/utf8_range`
- `absl_DIR=<absl-pkg>/lib/cmake/absl`

## 回退方案

无法用 CMake 时手工补齐：在链接命令追加
`<pkg>/lib/libutf8_validity.a <pkg>/lib/libutf8_range.a`（放 libprotobuf.a 之后）。

## 关联

- prerequisite_of E543（先解决编译期 string_view 迁移，再解决链接期库拆分）
- 实测来源：protoc-gen-grpc-web 2.1.1（archives/p/protoc-gen-grpc-web/2.1.1/notes.md）
