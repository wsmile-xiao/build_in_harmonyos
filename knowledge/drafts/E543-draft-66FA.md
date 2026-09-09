# E543 — Conan toolchain 强制 CMAKE_CXX_EXTENSIONS=OFF 导致 GNU 扩展项目编译被拒

## 错误特征

```text
Cap'n Proto requires compiler-specific extensions (e.g., -std=gnu++14) (…)
conan_toolchain.cmake: set(CMAKE_CXX_EXTENSIONS OFF)
```

capnproto 1.3.0（及同系列）在 Conan + OHOS aarch64 toolchain 下编译时，报"requires compiler-specific extensions"，即使 `generate()` 中设置了 `tc.cache_variables["CMAKE_CXX_EXTENSIONS"]=True` 也无效。

## 触发条件

- 构建系统: cmake
- 阶段: configure（G2/conan create）
- 前提: Conan CMakeToolchain 且 profile 指定 `compiler.cppstd=17`（非 gnu17）

## 根因分析

Conan 的 `CMakeToolchain` 对 `compiler.cppstd` 生成 `set(CMAKE_CXX_EXTENSIONS OFF)`（标准 `-std=c++NN` 语义）。该 set() 在 toolchain 文件中位于项目 CMakeLists 解析之前执行，**覆盖** `generate()` 里写入的 `tc.cache_variables`（cache_variables 走 `-D` 参数，也会被 toolchain 文件的 set() 覆盖）。capnproto 上游显式要求 GNU 扩展（`-std=gnu++14`），拒绝纯标准模式，因此 configure 直接失败。

## 解决方案

### 推荐方案

`generate()` 中设 `tc.cache_variables["CMAKE_CXX_EXTENSIONS"]=True` 之后，再对生成的 `conan_toolchain.cmake` 做字符串补丁，把 OFF 改回 ON：

```python
def _patch_toolchain_extensions(self):
    tc_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
    with open(tc_file, "r", encoding="utf-8") as fh:
        content = fh.read()
    content = content.replace("set(CMAKE_CXX_EXTENSIONS OFF)", "set(CMAKE_CXX_EXTENSIONS ON)")
    with open(tc_file, "w", encoding="utf-8") as fh:
        fh.write(content)
```

（同仓 capnproto 1.1.0/1.3.0 配方验证：conan create 全流程通过。）

### 禁止做法

- ❌ 只设 `tc.cache_variables["CMAKE_CXX_EXTENSIONS"]` 而不补丁 toolchain 文件（会被 toolchain 的 set() 覆盖，无效）
- ❌ 在 patches/ 补丁中注入平台宏 `__OHOS__`（R8/PF5 拦截）

## 验证

```bash
conan create archives/c/capnproto/1.3.0 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 结果：G2 PASS，test_package 4/4 PASSED
```

## 关联条目

- 相关: DRAFT-E321（同族：Conan toolchain 变量干预，POLICY_VERSION_MINIMUM 用 cache_variables 传递）
