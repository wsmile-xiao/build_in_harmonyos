# E568 — Release(-DNDEBUG) 构建下共享库残留未解析符号，消费者加载即失败

## 错误特征

构建期无任何报错（`conan create` 编译/链接均 exit 0），消费者进程在加载或调用时失败：

```
dlopen failed: cannot locate symbol "bjnp_hexdump" referenced by "libinklevel.so.5"
symbol lookup error: ./test_package: undefined symbol: level2str
```

用 `nm -D --undefined-only` 可在共享库里直接看到这些符号仍处于未定义状态。

## 触发条件

- 构建系统: autotools（CMake 同样适用）
- 阶段: linking（缺陷潜伏）/ runtime（实际暴露）
- 前置条件: 消费者或发行版以 Release 参数构建（`-DNDEBUG`），而上游默认构建不带该宏

## 根因分析

上游把调试 helper 的**定义**放进 `#ifndef NDEBUG` 守卫内，但**调用点**位于守卫之外
（或在另一个未同步加守卫的源文件里）：

```c
/* bjnp-debug.c */
#ifndef NDEBUG
void bjnp_hexdump(...) { ... }
#endif

/* bjnp-io.c —— 无守卫，无条件调用 */
bjnp_hexdump(...);
```

上游默认 `./configure && make` 不定义 `NDEBUG`，因此缺陷长期潜伏。Conan `AutotoolsToolchain`
在 Release 构建中注入 `-DNDEBUG` 后：定义被预处理剔除、引用仍在；libtool 默认不传
`-Wl,--no-undefined`，链接期静默通过，直到消费者 `dlopen` 才炸。

## 解决方案

### 推荐方案

对纯日志/转储类 helper（无副作用）打补丁去掉 `#ifndef NDEBUG` 守卫，让定义无条件编译：

```c
void bjnp_hexdump(...) { ... }
```

本仓库实例：libinklevel 0.9.7 的 `patches/0001-bjnp-debug.c.patch`（`patch_type: bugfix`），
修复后 4 例消费者测试全部通过。

若 helper 有真实副作用（改状态、影响返回值），则应反过来给**调用点**补同样的守卫，
而不是无条件编译。

### 禁止做法

- ❌ 用空壳 stub 顶替缺失定义（掩盖问题，符号存在但行为错误）
- ❌ 直接删掉 `-DNDEBUG` 掩盖（改变上游 release 语义，且治标不治本）
- ❌ 仅凭"链接成功"判定产物可用（消费者加载路径未被验证）

## 验证

```bash
# 1. 共享库不应残留未解析符号（libc/libgcc 等系统符号除外）
nm -D --undefined-only <package_folder>/lib/lib<name>.so* | grep -v 'GLIBC\|libc\.'

# 2. 定位守卫与调用点不一致
grep -rn '#ifndef NDEBUG' <src>/*.c | head

# 3. 端到端：消费者测试必须真实加载并调用该库
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 && echo OK
```

## 关联

- 知识条目: E568（草稿）
- 实例: libinklevel 0.9.7（archives/l/libinklevel/0.9.7）
