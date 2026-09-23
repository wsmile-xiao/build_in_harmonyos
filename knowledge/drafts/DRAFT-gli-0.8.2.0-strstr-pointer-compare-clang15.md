# DRAFT-gli-0.8.2.0-strstr-pointer-compare-clang15

**状态**: Draft only（路径 B 知识草稿，未 promote 至 knowledge/graph）
**产生库**: gli 0.8.2.0（测试代码 test/core/core_convert.cpp）

## 问题

gli 0.8.2.0（2016）测试代码：

```cpp
if(std::strstr(FilenameDst, ".dds") > 0 || std::strstr(FilenameDst, ".ktx") > 0)
    return false;
```

clang 15 下编译报错：

```
core_convert.cpp:35:38: error: ordered comparison between pointer and zero ('const char *' and 'int')
```

## 根因

`strstr()` 返回 `const char*`，旧代码用 `> 0` 做"非空"判断——把指针与整数 0 有序比较。
clang 15 对指针与零/整数的**有序比较**（`>`/`<`/`>=`/`<=`）按编译错误处理；
`== 0`/`!= 0` 相等比较不受影响。

## 方案

```cpp
if(std::strstr(FilenameDst, ".dds") != NULL || std::strstr(FilenameDst, ".ktx") != NULL)
    return false;
```

## 验证

- 修复后 `make -j2` 全量 0 错误，100% 构建完成
- `ctest --output-on-failure` → 70/70 全部通过（含 core_convert 用例）

## 适用边界

- 适用：任何将 strstr/strchr/memchr 等指针返回值与 0 做有序比较的旧 C/C++ 代码在 clang 15+。
- 反例：`ptr == 0` / `ptr != 0` 合法无需修改；仅 `>`/`<`/`>=`/`<=` 有序比较报错。

## 查重

- E419（plain char 符号性）、E420（隐式 int 调用）、E432（native API 契约）、E462（ptrace）均不相关。
- DRAFT-crack-5.0a-knr-clang15：同为"老代码 × clang 15 严格化"，但错误面是 K&R 隐式
  int→pointer 转换（-Wint-conversion），与本候选的 ordered comparison 不同。
- E429 为未填写模板。
- 结论：未命中完整条目 → new_draft（路径 B）。

## 关键词

strstr, pointer, ordered comparison, clang 15, NULL, legacy, portability