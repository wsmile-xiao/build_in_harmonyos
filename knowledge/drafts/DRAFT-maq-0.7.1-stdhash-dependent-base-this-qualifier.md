# 草稿：C++ 依赖基类成员需显式 this-> 限定（clang 两阶段名字查找）

## 错误特征

```
./stdhash.hh:415:13: error: explicit qualification required to use member 'direct_insert_aux' from dependent base class
```

## 根因

C++ 模板两阶段名字查找：派生类模板中访问**依赖基类**（dependent base class）的成员时，
非限定名在定义阶段不会到基类作用域查找，实例化阶段也不补查 → clang（及标准模式 GCC）
要求显式 `this->member` 或 `Base<T>::member`。2000 年代代码（maq 0.7.1, 2008）在旧 GCC
宽松模式下可编译通过，迁移到 clang 15 / `-std=c++17` 后成为硬错误。

## 推荐方案

对派生类模板内的基类成员调用加 `this->` 限定，逐处核对：

```cpp
// before
int ret = direct_insert_aux(key, this->n_capacity, this->keys, this->flags, &i);
// after
int ret = this->direct_insert_aux(key, this->n_capacity, this->keys, this->flags, &i);
```

## 禁止

- 使用 `-fpermissive` / `-Wno-*` 把 error 降级（会掩盖其它真实问题）

## 来源

maq/0.7.1 适配：`mapcheck.o` 编译失败，`stdhash.hh` 共 3 处（415/496/506 行）。
