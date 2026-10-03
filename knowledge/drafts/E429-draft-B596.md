# E429 — 依赖包自带 .pc 漏声明 system_libs：静态 C++ 依赖链入共享对象时 C++ 运行时未解析

> Draft: E429-draft-B596（kamailio-memcached 6.0.6 适配产出）

## 错误特征

编译/链接**成功**（`rc=0`），但产物的动态符号表残留 C++ 运行时未定义符号：

```text
$ llvm-nm -u memcached.so | grep -E '_Z|__gxx|__cxa'
                 U _ZSt9terminatev
                 U __cxa_begin_catch
                 w __cxa_finalize
                 U __gxx_personality_v0
```

随后运行时装载失败：

```text
dlerror: Error relocating .../memcached.so: __gxx_personality_v0: symbol not found
```

关键迷惑点：**共享对象链接允许未定义符号**，所以 `ld` 不会报错，`rc=0`，
隐患完全静默，直到 `dlopen` 才暴露。

## 触发条件

- 构建系统: pkg-config 驱动的 Makefile / autotools（本例 kamailio 模块 Makefile）
- 阶段: linking（症状出现在 runtime）
- 依赖形态: 依赖是**静态归档且由 C++ 实现**（本例 `libmemcached/1.0.18`），
  其 Conan 配方 `package_info()` 声明了 `system_libs=["m", "c++"]`，
  但**包内自带的 `.pc` 文件没有把这些 system_libs 写进 `Libs:`**。

```text
# 包内 lib/pkgconfig/libmemcached.pc（问题源）
Libs: -L${libdir} -lmemcached -lmemcachedutil          # ← 缺 -lm -lc++

# conan PkgConfigDeps 生成的 libmemcached.pc（正确）
Libs: -L"${libdir}" -lmemcached -lm -lc++              # ← 带上 system_libs
```

## 根因分析

消费方按上游 Makefile 的方式取链接参数：

```make
BUILDER = $(shell which pkg-config)
LIBS   += $(shell $(BUILDER) --libs libmemcached)
```

`pkg-config --libs libmemcached` 解析的是**包内自带**的 `.pc`，因此只得到
`-lmemcached -lmemcachedutil`。静态归档被链入共享对象后，其中的 C++ 目标文件
（异常处理、`std::terminate`）需要 libc++ 运行时，而 `-lc++` 从未出现在链接行上。
`ld -shared` 不要求未定义符号闭合，于是链接成功、产物带病。

## 解决方案

### 推荐方案

用 **Conan `PkgConfigDeps` 生成器**产出的 `.pc` 取代包内自带的 `.pc`：
它由 Conan 依据 `package_info()`（含 `system_libs`）生成，天然带上 `-lm -lc++`。

```python
def generate(self):
    PkgConfigDeps(self).generate()          # 产出 ${generators_folder}/libmemcached.pc

def build(self):
    env = Environment()
    env.define("PKG_CONFIG_PATH", self.generators_folder)
    with env.vars(self, scope="build").apply():
        self.run("make -C src modules modules=modules/memcached -j1 SHELL=<bash>")
```

### 禁止做法

- ❌ 看到 `rc=0` 就认为构建健康、直接打包（隐患静默，运行期才炸）
- ❌ 以 `LD_PRELOAD=libc++_shared.so` 之类运行期手段掩盖链接期缺陷
- ❌ 手工在链接行硬编码 `-lc++` 而不修正 `.pc` 来源（换依赖版本/换构建系统即复发）

## 验证

```bash
# 1) 产物不得残留 C++ 运行时未定义符号
llvm-nm -u <产物>.so | grep -E '_Z|__gxx|__cxa'      # 期望：无输出
# 2) DT_NEEDED 应包含 C++ 运行时（OHOS 系统运行时）
llvm-readelf -d <产物>.so | grep NEEDED              # 期望：libc++_shared.so, libc.so
# 3) 端到端：dlopen 该 .so 不得报 symbol not found
```

## 关联条目

- 相关: E430（OHOS/musl 无延迟绑定 —— 宿主插件装载模型）
- 相关: E431（make 默认 /bin/sh 下 pkg-config 探测不稳定）
