# DRAFT-pktanon-random-shuffle-cxx17

C++17 移除 `std::random_shuffle` 导致老 C++ 代码 `use of undeclared identifier 'random_shuffle'`。

## 错误特征
```
src/anonprimitives/AnonShuffle.cpp:36:2: error: use of undeclared identifier 'random_shuffle'
        random_shuffle (permvector.begin (), permvector.end ());
```

## 根因
2000s-era 代码直接调用 `std::random_shuffle`（C++14 弃用、C++17 移除）。OHOS profile
以 `compiler.cppstd=17` 编译 → 符号不存在。注意：在 make 子进程静默失败（无 stderr）
的环境里，这条错误可能被掩盖，需在可正常执行 clang 的通道（bash 直连）手动 make 定位。

## 修复
替换为 `std::shuffle` + `std::mt19937(std::random_device{}())`，并显式 include
`<algorithm>`、`<random>`（老文件常依赖传递包含）。

```cpp
std::shuffle (permvector.begin (), permvector.end (),
              std::mt19937 (std::random_device{} ()));
```

## 实例
pktanon 1.4.0：conanfile `_patch_anon_shuffle()`（commit b093c2e4ca），bash 通道完整
make 验证通过。
