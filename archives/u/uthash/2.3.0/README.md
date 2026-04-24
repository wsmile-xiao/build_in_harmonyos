# uthash 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | uthash |
| 版本 | 2.3.0 |
| 官网 | https://troydhanson.github.io/uthash/ |
| 源码下载 | https://github.com/troydhanson/uthash/archive/refs/tags/v2.3.0.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

uthash 是 C 语言哈希表宏库：
- Header-only 库，无需编译二进制
- 通过宏实现哈希表操作
- 支持多种哈希算法
- 内存高效，无额外开销

## 安装步骤

### 1. 下载源码

```bash
curl -L -o uthash-2.3.0.tar.gz "https://github.com/troydhanson/uthash/archive/refs/tags/v2.3.0.tar.gz"
tar -xzf uthash-2.3.0.tar.gz
cd uthash-2.3.0
```

### 2. 安装头文件

```bash
mkdir -p $HOME/usr/local/include
cp src/uthash.h $HOME/usr/local/include/
cp src/utlist.h $HOME/usr/local/include/  # 链表宏（可选）
cp src/utarray.h $HOME/usr/local/include/ # 动态数组（可选）
cp src/utstring.h $HOME/usr/local/include/ # 字符串（可选）
```

## 使用方法

### 基本用法

```c
#include "uthash.h"

struct my_struct {
    int id;            // 键
    char name[10];
    UT_hash_handle hh; // 哈希表句柄（必须）
};

struct my_struct *users = NULL; // 全局哈希表

// 添加元素
void add_user(int id, char *name) {
    struct my_struct *s = malloc(sizeof(struct my_struct));
    s->id = id;
    strcpy(s->name, name);
    HASH_ADD_INT(users, id, s);
}

// 查找元素
struct my_struct *find_user(int id) {
    struct my_struct *s;
    HASH_FIND_INT(users, &id, s);
    return s;
}

// 删除元素
void delete_user(struct my_struct *s) {
    HASH_DEL(users, s);
    free(s);
}
```

## 支持的键类型

| 宏 | 键类型 |
|---|--------|
| HASH_ADD_INT | int |
| HASH_ADD_STR | char* (字符串) |
| HASH_ADD_PTR | void* (指针) |
| HASH_FIND_INT | int |
| HASH_FIND_STR | char* |
| HASH_FIND_PTR | void* |

## 测试

```bash
cd tests
make
./test1
```

## 编译产物

```
$HOME/usr/local/include/
├── uthash.h    # 哈希表宏
├── utlist.h    # 链表宏
├── utarray.h   # 动态数组宏
└── utstring.h  # 字符串宏
```

## 参考链接

- [uthash 官网](https://troydhanson.github.io/uthash/)
- [uthash GitHub](https://github.com/troydhanson/uthash)
- [uthash 用户指南](https://troydhanson.github.io/uthash/userguide.html)
