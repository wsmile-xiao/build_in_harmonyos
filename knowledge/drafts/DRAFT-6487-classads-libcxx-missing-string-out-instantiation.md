# draft-classads-1.0.10-libcxx-missing-string-out-instantiation

## 症状

-O2 编译的 C++ 程序/测试程序链接时报：

```
ld.lld: error: undefined symbol: std::__n1::basic_ostream<char, ...>&
std::__n1::operator<< <char, std::char_traits<char>, std::allocator<char>>(
    std::__n1::basic_ostream<char, ...>&, std::__n1::basic_string<char, ...> const&)
```

引用者可以是没有直接使用 string 流的 .o（经由静态库成员间接暴露）。

## 根因

OHOS SDK 26 的 libc++ 头对 `basic_string<char>` 的 `operator<<(ostream&)` 声明了
extern template，因此 **-O2 编译的 TU 不生成隐式实例化**（发 U 引用，期望库提供
显式实例化）；但 SDK 提供的三处库经 llvm-nm 实测**均不含该符号**：

| 库 | 命中数 |
|----|--------|
| llvm/lib/aarch64-linux-ohos/libc++_shared.so | 0 |
| llvm/lib/aarch64-linux-ohos/libc++_static.a | 0 |
| 设备 /system/lib64/libc++.so | 0 |

（libc++.a 是 29 字节的 `INPUT(-lc++_static -lc++abi)` 重定向脚本。-O0 编译时
隐式实例化生成 W 弱定义，可自足，故仅 -O2/-O1 暴露。）

## 修复（classads/1.0.10 实证）

在库自身的一个 TU（common.cpp）尾部以 **asm 别名提供强定义**：

```cpp
std::basic_ostream<char, std::char_traits<char> >&
__fwd(std::basic_ostream<char, std::char_traits<char> >& os,
      const std::basic_string<char>& s)
    __asm__("_ZNSt4__n1lsIcNS_11char_traitsIcEENS_9allocatorIcEEEERNS_13basic_ostreamIT_T0_EES9_RKNS_12basic_stringIS6_S7_T1_EE");
std::basic_ostream<char, std::char_traits<char> >&
__fwd(...) { return os.write(s.data(), static_cast<std::streamsize>(s.size())); }
```

- 多 TU 需要时其余副本加 `__attribute__((weak))`，避免 duplicate symbol；
- 测试程序所在 TU 加 `-D_LIBCPP_DISABLE_EXTERN_TEMPLATE` 使调用点内联
  （注意：该宏**不能**抑制 char 特化的 extern template 声明，不能单独作为修复）；
- 2011 年 libtool 不为 clang++ 追加 C++ 运行库，另需 `LDFLAGS=-lc++`。

## 适用范围

- OHOS SDK 26（llvm 15）工具链下所有 -O2 C++ TU；
- 触发符号以链接错误里 `_ZNSt4__n1lsIc` 前缀为特征。

## 反例/边界

- -O0 编译（W 自带）不受影响；
- 简单程序中 `cout << "字面量"`（非 std::string）走不同符号，不受影响。

## 触发实例

classads/1.0.10（2026-09-09），修复后 conan-verify G2 全绿、上游 5 个测试程序
链接运行全过。
