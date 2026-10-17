# DRAFT-scanmem-0.17: L1e 报「假测试」的真因是单个 `-pr` 让 `can_run` 恒为 False

## 症状

包在流水线里跑得好好的，`conan create` 阶段 test_package 的断言全绿，
但 L1 阶段红：

```
[step] L1e: Destructive negative test (R34)...
        [sabotage] bin/ moved away
        [sabotage] lib/ moved away
        [sabotage] include/ moved away
[fail] L1e: test passed WITHOUT package artifacts — fake test detected (R34)
        test does not depend on <pkg> — must call its API or execute its binary
```

L1e 做的事是：把包产物目录移走，然后重跑 `conan test`，**期望它失败**。
如果还通过，就判定测试是空壳。我的 test_package 明明真的执行了
`scanmem` 二进制、真的扫描了另一个进程的内存，为什么还是被判空壳？

## 根因：L1e 用单个 `-pr`，`settings_build` 回落到默认 profile

L1e 的调用是：

```bash
conan test "$TEST_PKG_DIR" "${pkg_name}/${pkg_ver}" -pr "$PROFILE_FILE" --build=missing
```

关键在**单个 `-pr`**。Conan 2 的 `-pr` 是「两个都要就写两遍」的简写形式，
只写一次等价于 `-pr:h`，**不会**同时设置 build profile。于是
`settings_build` 保持机器默认（本机是 Linux/x86_64），而 host 是 OHOS/armv8。

而 `can_run` 的实现就是：

```python
def can_run(conanfile):
    allowed = conanfile.conf.get("tools.build.cross_building:can_run", check_type=bool)
    if allowed is None:
        return not cross_building(conanfile)
    return allowed
```

`cross_building()` 比较 `settings_build` 与 `settings`：
os 或 arch 任一不同即 True → `can_run` 为 **False**。

于是 test_package 里这行惯用写法：

```python
def test(self):
    if not can_run(self):
        return          # ← 静默返回，conan test 视为成功
```

在 L1e 场景下**直接 return 且返回成功**：一个断言都没跑，产物也被移走了，
L1e 自然判定「假测试」。

**为什么难定位**：同一个 test_package 在 `conan create` 阶段是好的，
因为流水线用的是 `-pr:h` **和** `-pr:b`（build==host），`can_run` 为 True。
只有 L1e 这一条路径用单 `-pr`，行为分叉。

实测对照（探针 recipe 直接打印两组 settings）：

| 调用方式 | host | build | cross_building | can_run |
|---|---|---|---|---|
| `conan create … -pr:h <p> -pr:b <p>` | OHOS/armv8 | OHOS/armv8 | False | **True** |
| `conan test … -pr <p>` | OHOS/armv8 | **Linux/x86_64** | True | **False** |

## 修复（两处都要，缺一不可）

### 1. 去掉 `can_run` 静默短路

```python
def test(self):
    # 不再用 can_run 兜底：本执行器是 aarch64 OHOS 原生，产物本就能跑。
    # 将来若真有跑不了的执行器，应当显式失败，而不是零断言报成功。
    ...
```

R34 的口径是「0 执行一律不可交付」，静默 skip 恰好是最坏的一种。

### 2. 让 test_package 有真实的编译期 + 链接期依赖

光去掉短路还不够——那样 L1e 移走产物后测试会因为「找不到二进制」而失败，
虽然能过 L1e，但那不是**设计意图**上的依赖，而是巧合。正确做法是让依赖显式：

```c
/* test_package/check_api.c */
#include <scanmem/scanmem.h>     /* 打包安装的头文件 */
#include <stdio.h>
int main(void) { printf("%s\n", sm_get_version()); return 0; }
```

```python
def build(self):
    dep = self.dependencies[self.tested_reference_str]
    self.run('"%s" -O1 -I%s -o check_api check_api.c -L%s -lscanmem'
             % (cc, self._abs(dep.cpp_info.includedirs),
                self._abs(dep.cpp_info.libdirs)))
```

`include/` 与 `lib/` 被移走后，`check_api.c` 立刻报
`fatal error: 'scanmem/scanmem.h' file not found`，测试失败——
**这正是 L1e 想要的依赖语义**。

顺带收益：这类「链接期消费」比只做 `dlopen` 更强。
本包 t7 因此升级为双重证明：`check_api`（链接期符号解析，验证
libtool `-export-symbols-regex` 生成的版本脚本在目标链接器下有效）
+ `check_libscanmem`（dlopen 运行期解析）。

## 验证方法：必须复刻 L1e 的调用方式

用 `-pr:h -pr:b` 去验 L1e 是**验不出来的**（那不是 L1e 的路径）。正确姿势：

```bash
PF=ci/conan/profiles/ohos-aarch64
# ① 正常：应通过
conan test archives/<pkg>/<ver>/test_package <pkg>/<ver> -pr "$PF" --build=missing
# ② 破坏 bin/ lib/ include/ 后：应失败
mv "$PKG"/{bin,lib,include} "$BAK"/
conan test archives/<pkg>/<ver>/test_package <pkg>/<ver> -pr "$PF" --build=missing   # 期望非 0
```

修复后实测：

```
[ok] L1e: Negative test confirmed — test genuinely depends on <pkg>
```

## 排查这类问题的通用手法

先打一个探针 recipe 打印 `self.settings` 与 `self.settings_build`，
用 L1e 的**完全相同**的调用方式跑一遍。build 侧若回落到默认 profile，
一眼就能看出来——比逐行读 test_package 快得多。

## 适用边界

- **适用**：任何 test_package 里写了 `if not can_run(self): return`（或等价短路）
  的包，在 L1e 阶段都可能被误判为假测试。
- **注意**：这属于**框架侧**的调用方式与 `can_run` 语义交互。若维护者希望根治，
  应改 L1e 为 `-pr:h "$PROFILE_FILE" -pr:b "$PROFILE_FILE"`，或在 test_package
  允许处设置 `tools.build.cross_building:can_run` conf。配方侧按上文两处规避即可，
  不需要改框架。
- **不适用**：test_package 本来就链接被测库（`build()` 里有 `-l<lib>`）的情况——
  那类包的 `include/`/`lib/` 被移走后链接本来就会失败，L1e 不会误判。
  误判只发生在「运行期才用产物、构建期不依赖产物」的包，也就是纯
  application/CLI 类包（本例 scanmem）。
