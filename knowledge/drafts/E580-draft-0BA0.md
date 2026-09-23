# E580 — libc++abi 22 要求 clang 19+ 的 libc++ 头文件，工具链为 clang 15

## 错误特征

构建 libc++abi 22.x 时，CMake 配置或编译阶段报出与头文件版本相关的错误，典型形态：

```
fatal error: '__thread/support.h' file not found
error: no member named 'source_location' in namespace 'std'
error: no member named 'jthread' in namespace 'std'
error: unknown type name '__libcpp_aligned_free'
error: redefinition of '__libcpp_aligned_free'
```

`error_signature`：
`__thread/support\.h|__libcpp_aligned_free|source_location|_LIBCPP_HAS_LIBRARY_ALIGNED_ALLOCATION`

## 触发条件

- 构建系统: cmake
- 阶段: configuration / compilation
- 依赖: 构建 libc++abi 22.x（或任何要求与 libc++ 同版本配套的运行时库）
- 工具链: clang < 19（本环境为 SDK 自带 clang 15）

## 根因分析

libcxxabi 22 的源码必须搭配**同一版本（22）的 libc++ 头文件**，因为二者共享内部实现
细节（`__thread/support.h`、`__config_site`、`__libcpp_aligned_*` 等私有头与实现假设）。

而 libc++ 22 的头文件本身要求 **clang 19+**（使用了 clang 19 才有的内建与语言特性），
设备与 CI 工具链是 clang 15，因此：

- 用源码树自带的 libc++ 22 头文件 → 头文件自身就编译不过；
- 用 SDK 随附的 libc++ 15 头文件 → 版本不一致，暴露三类 API 差异
  （缺 `__thread/support.h`、`__libcpp_aligned_free` 重复定义、事件/线程模型宏不同）。

即"两头都不通"，必须显式收敛版本差异。

## 解决方案

### 推荐方案

改用设备 SDK 随附的 libc++ 15 头文件，并把 libcxxabi 22 源码的差异收敛为补丁：

1. **头文件来源切换为 SDK libc++ 15**。libcxxabi 22 没有独立的 libcxx includes
   变量（`LIBCXXABI_LIBCXX_INCLUDES` 不存在），因此经 `CMAKE_CXX_FLAGS` 的
   `-isystem` 注入：
   ```
   -isystem <sdk>/include/libcxx-ohos/include/c++/v1
   ```
   同时保留 `-DLIBCXXABI_LIBCXX_PATH=<src>/libcxx`
   （该变量真实存在，CMake 仍需要它定位 libcxx 源码树）。

2. **补齐 libc++ 22 的配置宏**（libc++ 15 的 `__config_site` 里没有这些值，
   不补则行为与预期不符）。本场景实际只需 4 个值型宏：
   ```
   -D_LIBCPP_HAS_THREADS=1
   -D_LIBCPP_HAS_THREAD_API_PTHREAD=1
   -D_LIBCPP_HAS_EXCEPTIONS=1
   -D_LIBCPP_HAS_LIBRARY_ALIGNED_ALLOCATION=1
   ```
   另加 `-fPIC`（静态库需被 dlopen 的 .so 链接）。

3. **补丁收敛三类 API 差异**：
   - 源码引用 `<__thread/support.h>`（libc++ 15 无此头）→ 用 `__has_include`
     守卫或改注释，全部引用点需一一覆盖（含 `test/` 下的测试文件）；
   - `fallback_malloc.cpp` → 改用 SDK libc++ 15 `<new>` 提供的
     `__libcpp_aligned_*`；
   - `stdlib_new_delete.cpp` 的 `__libcpp_aligned_free` 重复定义 →
     用 libc++ 版本宏区分两份实现。

### 禁止做法

- ❌ 硬编码 `SYS_PREFIX` / 共享 `/usr/local` 注入头文件路径——CI worker 与本地
  共享文件系统会互相污染（见 E524 教训）。
- ❌ 只打 `-isystem` 而不补配置宏——头文件能编过但线程/异常/对齐分配行为与
  libc++ 22 的预期不符，问题会推迟到运行期才暴露。
- ❌ 只修源码目录漏掉 `test/` 与 `libcxx/test/support/`——测试编译期同样引用
  内部头，补丁不全会导致测试阶段失败。

## 验证

```bash
# 配方能端到端构建（含上游测试与消费者测试）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 上游测试全量执行（不得少跑）
#   total=79 pass=65 fail=0 build_fail=0 xfail=0 skip=14
```

## 关联条目

- 相关: E524（依赖注入必须用 build_folder 私有 prefix，禁止共享 SYS_PREFIX）
- 同类: clang 22.1.8 / libcxx 17.0.6 / libunwind 适配（同 tarball、同为系统级运行时库）
