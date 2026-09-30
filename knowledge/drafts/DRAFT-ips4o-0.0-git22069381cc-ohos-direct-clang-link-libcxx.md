# DRAFT-ips4o-0.0-git22069381cc-ohos-direct-clang-link-libcxx

## OHOS 直接 clang 命令行链接 C++ 程序需显式 -stdlib=libc++ -lc++ -lc++abi

- **触发场景**：run_ohos_test.py / 独立消费者脚本等**非 CMake 直接 clang 通道**在 OHOS
  上链接 C++ 可执行文件
- **报错签名**：
  ```
  ld.lld: error: undefined symbol: std::logic_error::logic_error(char const*)
  ld.lld: error: undefined symbol: vtable for std::length_error
  ld.lld: error: undefined symbol: std::bad_array_new_length::bad_array_new_length()
  clang-15: error: linker command failed with exit code 1
  ```

### 根因

OHOS SDK clang 15 驱动默认链接配置不把 libc++/libc++abi 运行时库加入搜索路径。
直接 `clang++ src.cpp -o out`（缺 `-stdlib=libc++`/`-L SDK lib`/`-lc++ -lc++abi`）
时，异常/operator new 等路径的 libc++ ABI 符号全部 undefined。库实际在
`<OHOS_SDK>/ohos/native/llvm/lib` 内，只是驱动默认链接配置没有携带该搜索路径。
与 E191（`unable to find library -lc++`，CMake 通道）同一根因的两个表现面：
E191 报"找不到库"，本条目报"符号缺失"。

### 复现与验证

```bash
# 复现（缺 -L/-lc++/-lc++abi 任一项）：
clang++ -std=c++14 -O2 -fopenmp -pthread -I <pkg>/include test.cpp -o test
# → ld.lld undefined std::logic_error / vtable for std::length_error ...

# 通过：
clang++ -std=c++14 -O2 -stdlib=libc++ -fopenmp -pthread \
  -I <pkg>/include \
  -L /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib \
  -lc++ -lc++abi test.cpp -o test
```

### 适用边界 / 反例

- **适用**：直接 clang 命令行通道（鸿蒙专项测试脚本、独立消费者、Makefile 直连 clang）
- **不适用（已覆盖）**：Conan 2 CMakeToolchain/CMakeDeps 通道——toolchain 会注入完整
  link flags，tset_package 内 cmake 构建不受影响；E191/E455 已覆盖 CMake 侧根因

### 查重关系

- similar_to: E191（unable to find library -lc++）、E455（-stdlib=libstdc++ 拒绝）
- caused_by: 无（独立表现面）
- prerequisite_of: 无
- conflicts_with: 无

### 来源

- ips4o 0.0-git22069381cc 鸿蒙专项测试（test_ohos/run_ohos_test.py）实测：
  首次链接失败 → 补齐 flags 后 `OHOS_IPS4O_TESTS_PASS` exit 0（见
  archives/i/ips4o/0.0-git22069381cc/reports/test-report.md）