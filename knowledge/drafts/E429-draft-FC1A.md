# E429 — Meson 配置期 compile-and-run 探针在 Conan 共享依赖下返回 NO (127)

## 错误特征

Meson 配置阶段输出（`meson-logs/meson-log.txt` 原文）：

```
Checking if "CHRONO_SAME_DURATION" runs: NO (1)
Checking if "LOG4CPLUS_INITIALIZER_H" with dependency log4cplus runs: NO (127)
Checking if "Get Log4cplus version" with dependency log4cplus runs: NO (127)
```

随后配置中止：

```
meson.build:824:24: ERROR: Unknown variable "log4cplus".
```

要点：`NO (1)` 是「探针运行后返回非 0」（真实的特性判定）；`NO (127)` 是「探针**根本没跑起来**」
（shell 的 command-not-found / 动态加载失败码）。二者混淆会把「依赖可见性问题」误判为
「特性不存在」或「依赖缺失」。

## 触发条件

- 构建系统: meson（`dependency(...)` 之外还使用 `cc.run()` / `cpp.run()` / "Checking if X runs" 探针）
- 阶段: configuration（`meson setup`）
- 依赖获取方式: Conan（`MesonToolchain` + `PkgConfigDeps`），host 依赖为**共享库**（`shared=True`）
- 实测：ISC Kea 3.0.3 全系 hook（perfmon / stat-cmds / lease-cmds / legal-log / limits / lease-query / host-cmds）

## 根因分析

1. Meson 的 feature 探针是**编译 + 运行**两步；编译期 `-I/-L` 由 MesonToolchain 提供，因此**链接成功**。
2. 运行期平台加载器只按 `LD_LIBRARY_PATH` → RPATH → 系统路径搜索，而 Conan 依赖的共享库
   仅存在于 conan 缓存包目录（`.conan2/p/<pkg>/p/lib`），不在任何默认搜索路径内。
3. 探针进程启动即失败（meson-log 原始输出 `Error loading shared library liblog4cplus.so.9`），
   Meson 记为 `runs: NO (127)`。
4. 依赖对象因此未被赋值，后续 `meson.build` 使用该变量时报 `Unknown variable "<dep>"` 并中止配置。

关键判别：`conan download <dep> -r=ohpcd --only-recipe` 返回 0（依赖存在且可消费），
即**不是依赖缺失**；`ninja` 也没参与，**不是编译失败**。

与 Autotools 侧 `AC_RUN_IFELSE`/conftest 加载失败同源
（`DRAFT-conan-dep-shared-libs-break-configure-conftest`），本条是 Meson 对应面。

## 解决方案

### 推荐方案

在 `conanfile.py` 的 `generate()` 中把 host 依赖的 `libdirs` 注入 `LD_LIBRARY_PATH`，
并 `save_script()` 落到 `conanbuild` 环境（`build()` 阶段自动 source）：

```python
from conan.tools.env import Environment
# ... MesonToolchain 配置与 tc.generate() 之后
env = Environment()
for dep in self.dependencies.values():
    for libdir in dep.cpp_info.libdirs:
        env.append_path("LD_LIBRARY_PATH", libdir)
env.vars(self).save_script("conanbuildenv-kea-runtime")
```

修复后同一项目 `meson setup` 成功（OS Family 正确输出），`grep "runs: NO"` 在 meson-log 中 0 命中。

### 回退方案

用项目自有选项关闭**可选**特性的探针（Kea：`-Dmysql=disabled -Dpostgresql=disabled
-Dnetconf=disabled -Dkrb5=disabled`）。仅适用于可选特性；核心依赖（log4cplus/openssl/boost）
无法关闭，必须走推荐方案。

### 禁止做法

- ❌ 把 Conan 缓存中的 `.so` 拷进 `/usr/lib`、`/lib` 等系统路径——缓存/系统污染（R26 精神），
  引入版本漂移与跨任务相互污染。
- ❌ 用 `--build=missing` 重编依赖——探针加载失败不是「依赖缺失」，全量重建耗时且不解决加载路径问题，
  会掩盖真实根因。

## 验证

```bash
# 对照组（关闭注入）：预期出现 127
grep -n "runs: NO (127)" <builddir>/meson-logs/meson-log.txt

# 修复后：预期 0 命中且配置成功
meson setup <builddir> <srcdir> --native-file=<out>/conan_meson_native.ini -Dtests=enabled
echo "meson_setup_rc=$?"     # 预期 0
```

实测证据（kea-hook-lease-cmds 3.0.3）：`reports/control-0004-log4cplus-ldpath.log`（未注入 → rc=1，127 命中）、
`reports/meson-setup.log`（注入后 → rc=0）。

## 关联条目

- 相关: `DRAFT-conan-dep-shared-libs-break-configure-conftest`（Autotools/configure conftest 同源面）
- 相关: E085 / E090（Kea 同批适配中的 musl pthread、meson harmonyos 平台名）
