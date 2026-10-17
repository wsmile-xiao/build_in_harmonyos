# E429 — Meson 配置期 compile-and-run 探针在 OHOS/Conan 下需 host 共享依赖可见

- 草稿 ID：E429-draft-C4CE
- 来源包：kea-hook-stat-cmds/3.0.3（ISC Kea 3.0.3，Meson）
- 发现阶段：`meson setup`（configuration）
- 严重度：2（🟡 medium，阻塞配置但修复确定）
- 状态：draft（待主编审核）

## 1. 现象（真实日志）

```
Checking if "LOG4CPLUS_INITIALIZER_H" with dependency log4cplus runs: NO (127)
...
meson-log 原始原因：
Program stderr:
Error loading shared library liblog4cplus.so.9: (needed by
  /storage/Users/currentUser/tmp/kea-sc-probe/build-r4/meson-private/tmptwt8j6_4/output.exe)
Error relocating .../output.exe: _ZN9log4cplus11InitializerC1Ev: symbol not found

meson.build:824:24: ERROR: Unknown variable "log4cplus".
```

注意前半段是"找到了依赖但探针跑不起来"：

```
Run-time dependency log4cplus found: YES 2.2.0.1      ← 依赖解析成功
Checking if "Get Log4cplus version" ... runs: NO (127) ← 探针运行失败
```

## 2. 根因

1. meson 对 `dependency()` 之后的特性探针默认采用**编译并运行**策略，native 构建下真实执行
   `meson-private/tmpXXXX/output.exe` 并读退出码。
2. 该依赖由 Conan 以 `shared=True` 提供（log4cplus/2.2.0.1 默认动态）。运行期需要动态加载器
   在 `LD_LIBRARY_PATH` 中能找到 `liblog4cplus.so.9`。
3. `meson setup` 阶段 `conanbuild.sh` **尚未 source**，运行期环境不含 Conan 包的 `lib` 目录 →
   加载失败，退出码 127（区别于"编译失败 DID NOT COMPILE"）。
4. meson 把"探针运行失败"等同于"特性不存在"，随后引用该依赖变量的表达式报
   `Unknown variable "log4cplus"` 并中止配置。

## 3. 修复（推荐方案，优先级 1）

在 `conanfile.py` 的 `generate()` 中把 host 依赖的 libdirs 注入运行期环境：

```python
from conan.tools.env import Environment

def generate(self):
    ...
    env = Environment()
    for dep in self.dependencies.values():
        for libdir in dep.cpp_info.libdirs:
            env.append_path("LD_LIBRARY_PATH", libdir)
    env.vars(self).save_script("conanbuildenv-<name>-runtime")
```

`conanbuildenv-<name>-runtime` 会被 Conan 聚合进 `conanbuild.sh`，`meson.configure()`
前已生效，探针即可运行。

**复验**（同包实测）：

```
Checking if "LOG4CPLUS_INITIALIZER_H" with dependency log4cplus runs: YES
Checking if "Get Log4cplus version" with dependency log4cplus runs: YES
Run-time dependency log4cplus found: YES 2.2.0.1
Build targets in project: 242
meson_setup_rc=0
```

## 4. 禁止策略

| 禁止 | 原因 | 后果 |
|---|---|---|
| 把探针结果写死为 YES / 删掉探针 | 掩盖真实能力探测（同工程里 boost TLS、`stream_truncated` 探针都依赖这一机制） | 配置假绿，缺陷推迟到编译/运行期 |
| 为绕开探针把依赖改成静态 | 改变产物形态与依赖链，针对的不是根因 | 包 ABI/依赖链与上游不一致 |

## 5. 与相似条目的边界

- **E019 / E073**（运行时 `LD_LIBRARY_PATH` 找不到库）现象同源（动态加载失败），但发生在
  **运行产品/测试**阶段；本条目特指 **meson 配置期探针** 这一场景，修复位置在
  `conanfile.py generate()`，且错误表征是 `runs: NO (127)` + `Unknown variable`。
- **E090**（Meson 报 `system=harmonyos`）也发生在 configure 但错误文本完全不同
  （`Unsupported system "harmonyos"`）。

## 6. 影响范围

OHOS（或任何 native 构建）下使用 meson + Conan 共享依赖、且上游在配置阶段对共享依赖执行
compile-and-run 特性探针的项目。ISC Kea 3.0.3 全系列 hook（perfmon / stat-cmds / limits /
lease-query / legal-log / radius / ping-check / hooks / perfdhcp）共用同一顶层 `meson.build`，
均会命中本模式。
