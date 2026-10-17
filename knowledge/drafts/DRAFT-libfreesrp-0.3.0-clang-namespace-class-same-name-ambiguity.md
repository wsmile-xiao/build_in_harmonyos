# E-DRAFT: clang 下 namespace 与类同名 + using-directive 的限定查找歧义（libfreesrp 0.3.0）

## 错误签名

```
error: reference to 'FreeSRP' is ambiguous
  note: candidate found by name lookup is 'FreeSRP'      ← namespace
  note: candidate found by name lookup is 'FreeSRP::FreeSRP'  ← class
error: non-constant-expression cannot be narrowed from type 'FreeSRP::command_id' to 'unsigned char'
error: reference to 'sample' is ambiguous   ← std::sample (C++17 <algorithm>) vs FreeSRP::sample
CMake Error: failed to create symbolic link 'libfreesrp.so.0': Permission denied
```

## 触发条件

上游（libfreesrp/myriadrf 全系版本）在 `namespace FreeSRP` 内声明 `class FreeSRP`，
且所有 .cpp 顶部有 `using namespace FreeSRP;`。clang>=14 对 qualified-id 首分量
的查找同时命中「真命名空间」与「using 注入的类」即报歧义；GCC 历史上放行，
所以上游从未暴露。

## 修复（详见 DRAFT-libfreesrp-0.3.0-clang-namespace-class-same-name-ambiguity.kv）

1. 类外定义整体包进 `namespace FreeSRP { ... }`，限定降一层
   （`FreeSRP::FreeSRP::impl::` → `FreeSRP::impl::`），方法体不动。
2. 必须留全局作用域的文件（有 main）：注入
   `namespace FreeSRP { typedef FreeSRP FreeSRPClass; typedef sample FreeSRPSample; }`
   后做名字替换。禁止 `using FreeSRP::FreeSRP;`（歧义依旧）。
3. 窄化补 `static_cast<unsigned char>`。
4. 沙箱内 cmake 版本化符号链接（cmake_symlink_library）稳定 EACCES（手工执行
   同一命令却成功，属进程上下文相关环境问题）：补丁去掉 VERSION/SOVERSION，
   交付扁平 .so。

## 验证

conan create 干净构建通过；test_package 7/7；W3 L0/L1/L4/L5 + L1e 全 pass；
conan-verify G0-G4 全 pass；.codesign 签名 section 实测存在。
