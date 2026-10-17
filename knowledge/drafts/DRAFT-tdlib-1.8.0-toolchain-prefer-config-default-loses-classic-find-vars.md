# DRAFT: CMakeToolchain 默认 PREFER_CONFIG=ON 让上游经典 Find 变量"静默饿死"

> Draft: DRAFT-tdlib-1.8.0-toolchain-prefer-config-default-loses-classic-find-vars
> 来源：tdlib/1.8.0 适配（OHOS，conan 2.29.1）
> 关系：**E447 已记录同一机制**（上游 vendored FindSDL2*.cmake vs CMakeDeps）。
> 本条补齐一条未记录的关键事实：**`CMAKE_FIND_PACKAGE_PREFER_CONFIG` 是 conan 的默认值，不是配方选择**，
> 且给出「静默变空壳」这一更隐蔽的症状判定法。

## 现象（不报错，但构建结果为空）

```
$ cmake -S src -B build -DCMAKE_TOOLCHAIN_FILE=<generators>/conan_toolchain.cmake
-- Conan: Target declared 'openssl::openssl'          # ← config 模式确实命中了
-- Found ZLIB: <zlib pkg>/include ZLIB::ZLIB          # ← zlib 正常（见下）
...
CMake Warning at CMakeLists.txt:176 (message):
  Can't find OpenSSL: stop TDLib building             # ← 只 WARNING，然后 return()
-- Configuring done / Generating done                  # exit=0，但后半段目标全不生成
```

> 陷阱在于：`tdlib` 的 ZLIB 依赖恰好因为 conan 包产出 `ZLIBConfig.cmake`
> （定义了 `ZLIB_FOUND/ZLIB_INCLUDE_DIR/ZLIB_LIBRARIES`）而通过，OpenSSL 却因为上游用的是
> **CMake 自带 FindOpenSSL 模块的变量名**而失败 —— 同一份 CMakeLists 里两个依赖一成一败，
> 极易误判成「OpenSSL 包有问题」。

## 根因

`conan_toolchain.cmake` 默认包含：

```cmake
# 实测位置：generators/conan_toolchain.cmake 第 137/139 行
set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)
```

来源：conan `tools/cmake/toolchain/blocks.py` 的 `generic_system` 块，
conf 为 `tools.cmake.cmaketoolchain:find_package_prefer_config`，**默认 True**。

于是裸 `find_package(OpenSSL)` 优先 CONFIG 模式 → 命中 CMakeDeps 生成的 `openssl-config.cmake`，
它只设**小写** `openssl_*` 变量与 `openssl::openssl` 目标；上游要的**大写经典变量**
（`OPENSSL_FOUND / OPENSSL_INCLUDE_DIR / OPENSSL_LIBRARIES / OPENSSL_CRYPTO_LIBRARY /
OPENSSL_SSL_LIBRARY`）一个都没有 → `if (NOT OPENSSL_FOUND)` 成立 → `return()`。

CMake 变量大小写敏感，config 模式又**不会**回落到 MODULE 模式，所以「config 命中」与
「MODULE 变量为空」可以同时发生。

## 推荐方案（不改上游源码、不动 PREFER_CONFIG）

```python
def generate(self):
    tc = CMakeToolchain(self)
    openssl_pkg = self.dependencies["openssl"].package_folder.replace("\\", "/")
    tc.cache_variables["OPENSSL_FOUND"] = True
    tc.cache_variables["OPENSSL_ROOT_DIR"] = openssl_pkg
    tc.cache_variables["OPENSSL_INCLUDE_DIR"] = f"{openssl_pkg}/include"
    tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = f"{openssl_pkg}/lib/libcrypto.a"
    tc.cache_variables["OPENSSL_SSL_LIBRARY"] = f"{openssl_pkg}/lib/libssl.a"
    tc.cache_variables["OPENSSL_LIBRARIES"] = f"{openssl_pkg}/lib/libssl.a;{openssl_pkg}/lib/libcrypto.a"
    tc.cache_variables["OPENSSL_USE_STATIC_LIBS"] = True
    tc.generate()
```

复验：configure 打印 `Found OpenSSL: <pkg>/include <pkg>/lib/libssl.a;<pkg>/lib/libcrypto.a`，
且 `libtdjson.so` 的 `DT_NEEDED` 只有 `libc++_shared.so` / `libc.so`（OpenSSL 已静态链入）。

回退：`-c tools.cmake.cmaketoolchain:find_package_prefer_config=False`（让 MODULE 优先，
但会同时改变所有依赖的查找路径，须回归；E447 记录过该方向的不确定性）。

## 判定速查（避免误判成依赖包损坏）

| 观察 | 含义 |
|---|---|
| configure 有 `Can't find X: stop ... building` 之类 WARNING，但 exit=0 | 上游 `return()` 生效，构建**静默变空壳**——必须查，不能只看退出码 |
| 同一工程里某些依赖正常、某些"找不到" | 优先怀疑大写/小写变量或 vendored Find 模块，而非包本身 |
| `grep PREFER_CONFIG conan_toolchain.cmake` 命中 ON | 本条根因确认 |

## 与既有条目的关系（含框架预审判定）

`draft-review` 输出：`signature=✅ root_cause=✅ rec=✅`，
相似正式条目 TOP3 → E451 0.10、E300 0.09、E322 0.08（全部低于 0.12），
📌 预审建议 **create**（"疑似新知——无高相似条目，可考虑人工审核后纳入"）。

- 人工交叉比对：`E447` 记录过同一机制的另一实例（上游 vendored `FindSDL2*.cmake`），
  但把它描述成「配方启用了 `PREFER_CONFIG=TRUE`」；`E412` 讲 OpenSSL 可选后端的显式化。
  本条的增量正是根因本身——**它是 conan CMakeToolchain 的默认值**（conf
  `tools.cmake.cmaketoolchain:find_package_prefer_config` 默认 True），加上
  「configure 只打 WARNING、exit=0、目标静默不生成」的判定法。
- **建议处理方式**：保留为独立条目（工具判定 create），并在 E447 的 `similar_to` 中互相引用；
  或按人工判断并入 E447。
