# DRAFT: CMAKE_POLICY_VERSION_MINIMUM 的位置陷阱（写进 conan toolchain 无效）

> Draft: DRAFT-tdlib-1.8.0-cmake-policy-minimum-toolchain-too-late
> 来源：tdlib/1.8.0 适配（OHOS 主机 CMake 4.1.2，tdlib 声明 `cmake_minimum_required(VERSION 3.0.2 FATAL_ERROR)`）
> 关系：**E187 / E103 已给出正解**（`-DCMAKE_POLICY_VERSION_MINIMUM=3.5`）。
> 本条只补齐一个未记录的**位置陷阱**：conan 配方里最自然的写法恰好无效。

## 现象

```
$ cmake -S src -B build -DCMAKE_TOOLCHAIN_FILE=<conan_toolchain.cmake>    # 其中已写 set(CMAKE_POLICY_VERSION_MINIMUM 3.5 CACHE STRING "")
CMake Error at CMakeLists.txt:1 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed from CMake.
  ...
  Or, add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 to try configuring anyway.
-- Configuring incomplete, errors occurred!        # exit=1
```

## 根因：toolchain 被读取的时机晚于 CMakeLists.txt:1

CMake 在**首个 `project()`** 时才 include `CMAKE_TOOLCHAIN_FILE`，而几乎全部老工程第 1 行就是
`cmake_minimum_required(...)`。该命令求值时 toolchain 还没被读，`tc.variables` /
`tc.cache_variables` 写进去的值一律来不及生效。

对照实验（判定顺序的唯一可靠手段）：

```bash
{ echo 'message(STATUS "TOOLCHAIN-READ-MARKER")'; cat conan_toolchain.cmake; } > tc2.cmake
cmake -S src -B b2 -DCMAKE_TOOLCHAIN_FILE=tc2.cmake
#   → 报错停在 CMakeLists.txt:1，且 MARKER 一行都没打印 ⇒ toolchain 尚未被读取
```

| 写法 | 实测结果 |
|---|---|
| `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"`（写进 toolchain） | ❌ exit=1，同样报错（日志 `19-tc-policy-test.log`） |
| `cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])` | ✅ exit=0（日志 `07/08-cmake-configure-fix*.log`） |
| `env CMAKE_POLICY_VERSION_MINIMUM=3.5 cmake ...`（conan `Environment` 生成） | ✅ exit=0（日志 `21-env-policy.log`） |

## 推荐方案

```python
def build(self):
    cmake = CMake(self)
    # 必须走命令行：CMake 4.x 拒绝 cmake_minimum_required(<3.5)，
    # 而 toolchain 文件在 CMakeLists.txt:1 之后才被读取（实测无效）
    cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
    cmake.build()
```

回退：`generate()` 里用 `Environment().define("CMAKE_POLICY_VERSION_MINIMUM", "3.5")`
（适合自定义 build()、绕过 CMake helper 的配方）。

## 反模式（禁止）

```python
# ❌ 看起来最"conan 风格"，但实测完全无效
tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
```

## 与既有条目的关系（含框架预审判定）

`draft-review` 输出：`signature=✅ root_cause=✅ rec=✅`，
相似正式条目 TOP3 → **E187 score=0.55（sig=0.88）**、**E103 0.48（sig=0.71）**、E301 0.19，
📌 预审建议 **merge-into → E187**（"疑似重复"）。

- 与 E187/E103 的**正解完全一致**（`-DCMAKE_POLICY_VERSION_MINIMUM=3.5`），
  本条唯一增量是「**放哪里才生效**」：写进 `conan_toolchain.cmake`（`tc.variables` /
  `tc.cache_variables`，也就是 conan 配方最自然的写法）实测**无效**，因为 CMake 直到首个
  `project()` 才读 toolchain，而 `cmake_minimum_required` 在其之前求值。
- **建议处理方式：merge-into E187**——把本 md 的实验对照表（toolchain ❌ / cli_args ✅ /
  环境变量 ✅）补进 E187，并给 E187 增加 `forbid`：
  `cache_variables\["CMAKE_POLICY_VERSION_MINIMUM"\]`。无需新增条目。
