# 旧 C++ 的 `switch(unsigned){ case -1: }` 在 C++11 起即硬错误，bcp 先例的 gnu++14 降档对此无效

- **草稿 ID**: DRAFT-E705（待审号 E705）
- **来源**: xplc 0.3.13 HarmonyOS PC 适配（族C 最小复现钉死 bcp 降档修法的适用边界）
- **分类**: c++ / compilation / autotools / portability / standard-flags
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

- **签名**: `xplc/moduleloader.cpp:65:8: error: case value evaluates to -1, which cannot be narrowed to type 'unsigned int' [-Wc++11-narrowing]`
- **复现**: `configure` 成功后第一个 C++ 编译单元即失败，`make` rc=2；整个 `libxplc.so` 只产出 `libxplc-cxx.a`（部分产物，属"半绿"）。
- **触发条件（三重叠加，缺一不发）**:
  1. `xplc/moduleloader.cpp` 的 `switch(moduleinfo->version_major)`，`version_major` 是 `unsigned int`；
  2. `#ifdef UNSTABLE` 分支里的 `case -1:`（-1 = UNSTABLE 模块 ABI 版本哨兵）；
  3. 0.3.13 的 minor=3 为**奇数** → autoconf 判定 unstable → 向 `CFLAGS/CXXFLAGS` 注入 `-DUNSTABLE` → 该分支必然参与编译。

  换句话说：只要按上游"奇数 minor = unstable"的版本约定构建任何一个 unstable 版本，就必然撞上。

## 根因

`-Wc++11-narrowing` 自 **C++11** 起把「负的常量表达式收窄进无符号类型」从 warning 提升为 **hard error**
（列表初始化与 `case` 标签都受此约束）。这与同属"旧代码在新标准下编译失败"的 **E293 / bcp 先例**
是**两回事**，但极易被混为一谈：

| 特性 | 移除/收紧时机 | `-std=gnu++14` 下 |
|---|---|---|
| 动态异常规范 `throw(T)`、`register`（E293、bcp） | **C++17 移除** | 仍合法 → **降档有效** |
| 窄化 `case -1:` → `unsigned int`（本条） | **C++11 收紧为错误** | 仍报错 → **降档无效** |

本任务最小复现（clang 15.0.4，`-DUNSTABLE`，源文件一个 `switch(unsigned){case -1:}`）：

```
-std=c++17    rc=1   error: case value evaluates to -1, which cannot be narrowed to type 'unsigned int'
-std=gnu++14  rc=1   同一错误（bcp 档位无效）
-std=c++17 -Wno-c++11-narrowing  rc=0
-std=gnu++98  rc=0   （但偏离 profile 的 compiler.cppstd=17）
```

### 伴随的 conan API 陷阱（同族、同一次踩坑）

`AutotoolsToolchain.cxxflags` 是 **property（只读派生属性）**，`tc.cxxflags.append("-Wno-c++11-narrowing")`
**静默不生效**——`generate()` 产出的 `conanautotoolstoolchain.sh` 里 `CXXFLAGS` 不含该标志，且无任何警告。
必须写 `tc.extra_cxxflags.append(...)`（`extra_cxxflags` 才是 `__init__` 里创建的真列表，
`cxxflags` property 会把它拼进去）。本任务实测两种写法各跑一次 `conan install` 后 `grep Wno-c++11-narrowing`
区分：`extra_cxxflags` 命中、`cxxflags` 不命中。

同族的另一处注入点差异：`tc.extra_env` 在本 conan 版本**不存在**（`AutotoolsToolchain` 无该属性，
acpitool 配方里的 `tc.extra_env = {...}` 在此环境不产生任何效果），configure 期环境量要走
`tc.configure_args.append("VAR=VALUE")`。

## 最小修复方案

`archives/x/xplc/0.3.13/conanfile.py` 的 `generate()`：

```python
def generate(self):
    deps = AutotoolsDeps(self)      # 双 generator：缺 Deps 会让 AC_CHECK_LIB 假绿（E2186）
    deps.generate()

    tc = AutotoolsToolchain(self)
    tc.extra_cxxflags.append("-Wno-c++11-narrowing")   # ← 只有 extra_* 是可变真列表
    tc.generate()
```

要点：

- **保 cppstd=17**：降档会偏离 CI 的 `compiler.cppstd=17` 矩阵，且掩盖真实修复位置。
- **不改上游源码**：`case -1:` 与 UNSTABLE 模块 ABI 语义绑定，改成无符号常量属语义改动，需上游确认。
- **`extra_cxxflags` 而非 `cxxflags`**：后者是 property，append 静默丢失。

回退方案（项目强制 `-Werror` 时不接受该豁免）：补丁把 `case -1:` 改写成
`if (moduleinfo->version_major == (unsigned int)-1) { ... break; }`——`if` 比较不做窄化转换，
语义等价且不改 ABI；或与上游确认后把哨兵改成与 `version_major` 同类型的常量。

## 验证结果

| 步骤 | 结果 |
|---|---|
| 最小复现四档对照 | c++17 rc=1 / gnu++14 rc=1（降档无效）/ c++17+豁免 rc=0 / gnu++98 rc=0 |
| 全量 `make -j1`（带豁免） | rc=0，errors=0；产出 `libxplc.a`(227382 B) + `libxplc-cxx.a` + `libxplc.so` |
| 豁免是否进 CXXFLAGS | `config/config.mk` 实测 `CXXFLAGS+=-stdlib=libc++ -std=c++17 -O3 -Wno-c++11-narrowing -Woverloaded-virtual -fno-rtti ... -DUNSTABLE` |
| 上游测试面 | `make tests` rc=0 → `./testmain: 0 failed, 230 passed`（12 项 test000–011） |
| 消费者 test_package | 静态与动态（SONAME 修复后）两条路径均 `11 passed, 0 failed` |

## 禁止策略

- **禁止用 `-std=gnu++14`/`-std=c++14`/`-fpermissive` 兜窄化错误**：本条实测 gnu++14 仍 rc=1，
  且降档会偏离 CI 矩阵、并掩盖同一包里真正属于 C++17-移除特性的 E293 类问题——
  让"一个降档动作"同时误判两类问题已解决。
- **禁止去掉 `-DUNSTABLE` 或把哨兵改成 4294967295 来绕过**：UNSTABLE 是 autoconf 按"minor 奇数"
  写入的模块 ABI 标记；库本体带 `-DUNSTABLE` 而消费者不带时，头文件会展开出不同的类布局
  （`UNSTABLE_INTERFACE` 有无 `static bool` 成员），属 ABI 级错配——这正是本任务另一族
  （`xplc.pc` 不带 `-DUNSTABLE` → 消费者编译失败）的根因。

## 相关

- **边界条目（最关键）**: E293 — 动态异常规范/`register` 是 C++17 移除，**降档有效**；本条是 C++11 收紧，**降档无效**。两条并读才构成"旧 C++ 在新标准下失败"的完整处置决策树。
- **相似条目**: `DRAFT-ifcplusplus-2.5-aarch64-char-mask-narrowing`、hfsm2 草稿 — 同为 `-Wc++11-narrowing`，但发生在 `static const char[] = {-1}` 列表初始化（plain char 在 aarch64 默认 unsigned），修复位是源码显式 `signed char`；本条修复位是编译警告豁免，且**与 aarch64 char 默认符号性无关**（x86 上同样失败）。
- **同族注入点**: E2186 — `AutotoolsDeps` 缺失使 `AC_CHECK_LIB` 假绿（本任务同时踩到，见 `notes/defects/conan-verify-and-recipe.md`）。
- **引用原则**: P010。
