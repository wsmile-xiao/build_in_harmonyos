# E429 — qmake `.pri` 转 CMake 时内嵌 `#include` 的 `.cpp` 不可再单独编译

> 草稿条目对应的 KV：`knowledge/drafts/E429-draft-B1CC.kv`
> 状态：DRAFT（待人工/主审合并为 E 条目）
> 出处：sasm 3.15.0 适配（上游 qmake 工程改写为 CMake，
> `archives/s/sasm/3.15.0/patches/0001-CMakeLists.txt.patch`）

## 错误特征

按 `.pri` 的 `SOURCES` 清单逐条搬进 CMake 后，编译在 `singleapplication`
子树处失败：

```
singleapplication/qtlockedfile.cpp:12:1: error: use of undeclared identifier
    'QtLockedFile'; did you mean 'QtLP_Private::QtLockedFile'?
```

即符号“找不到”，但 `qtlockedfile.cpp` 明明已列入 `SOURCES` —— 报错文件本身
不是问题所在，问题在它的**编译上下文**。

## 触发条件

- 构建系统：CMake（由上游 qmake `.pro`/`.pri` 迁移而来）
- 阶段：compilation（单文件编译期）
- 前提：源码树里存在“一个 `.cpp` 被另一个 `.cpp` 在命名空间内 `#include`”的写法

## 根因分析

上游 `singleapplication/qtlocalpeer.cpp` 在 `QtLP_Private` 命名空间内部：

```cpp
// singleapplication/qtlocalpeer.cpp
namespace QtLP_Private {
#include "qtlockedfile.cpp"
#if defined(Q_OS_UNIX)
#include "qtlockedfile_unix.cpp"
#endif
}
```

`qtlockedfile.cpp` 自身**不包含**命名空间声明（它设计为被内嵌），因此：

- 作为内嵌文本参与编译时 → 类定义落在 `QtLP_Private` 命名空间内，正确；
- 被 CMake 当作独立编译单元再次编译时 → 同一份类定义落在**全局命名空间**，
  于是 `qtlocalpeer.cpp` 内引用的 `QtLockedFile` 解析不到，报
  `use of undeclared identifier 'QtLockedFile'`（并伴随重复符号/重定义）。

qmake 侧之所以不出问题：`.pri` 的源列表与内嵌写法是配套的，而“把 `.pri` 的
`SOURCES` 逐条翻译成 CMake 列表”这一机械迁移忽略了 `#include` 语义。

## 影响面

| 场景 | 影响 |
|---|---|
| Qt 工程内嵌第三方子树（singleapplication / qtlockedfile / qtsinglecoreapplication） | 硬失败，编译不过 |
| 其它“条件编译靠 `#include *.cpp`”的上游写法（如 `qtsingleapplication`） | 同类硬失败 |
| 一般 qmake→CMake 迁移 | 只按文件清单搬运、不看 `#include` 关系时的常见坑 |

## 解决方案

### 推荐方案（rec_priority 1）

严格按 `.pri` 的 `SOURCES` 语义移植：**被内嵌的 `.cpp` 不列入编译单元**。

```cmake
# 只编这两个（qtlocalpeer.cpp 内嵌 qtlockedfile*.cpp）
set(SA_SOURCES
    singleapplication/qtsingleapplication.cpp
    singleapplication/qtlocalpeer.cpp)
```

实测：sasm 3.15.0 在 OHOS/arm64（clang 15、Qt 5.15.19）上按此修法一次通过
（`archives/s/sasm/3.15.0/patches/0001-CMakeLists.txt.patch`）。

### 回退方案（priority 2）

无法立刻判断内嵌关系时，先按 `.pri` 原始列表全量列入，再从报
`redefinition` / `use of undeclared identifier` 的 `.cpp` 起逐个移出编译单元，
直到编译通过——但必须逐一确认移出项确实是被 `#include` 的（否则会静默丢代码）。

### 禁止做法

- ❌ 把 `QtLockedFile` 移出 `QtLP_Private` 命名空间，或用
  `#define QtLockedFile QtLP_Private::QtLockedFile` 之类宏改写符号
  —— 改动上游语义，且使单实例锁行为与上游不一致（编译过但语义错）
- ❌ 直接删除 `qtlockedfile*` 源码 —— 单实例锁彻底丢失，运行期多实例并发写配置

## 验证

```bash
# 确认内嵌关系（应看到 namespace 内的 #include）
grep -n '#include "qtlockedfile' singleapplication/qtlocalpeer.cpp
# 迁移后编译应无该错误
cmake -S . -B build && cmake --build build 2>&1 | grep -c "QtLockedFile"   # 期望 0
```

## 关联条目

- 相关：E013（构建系统语义迁移类）、P008
