# ascon-c 1.3.0：CMake REL_FLAGS 交叉覆盖 + 组合目录双命名库 + 无 install() 手动打包

> 草稿（DRAFT）— 来自 ascon-c 1.3.0 HarmonyOS PC (aarch64) 第一轮适配的真实日志。
> 与 `.kv` 同 stem 配对，字段见 knowledge/DRAFT-ascon-c-1.3.0-cmake-rel-flags-combined-lib-naming.kv

## 问题

ascon-c 1.3.0 是纯 C99 轻量密码库（AEAD/HASH/XOF/PRF/MAC 参考实现集合），
OHOS 交叉适配中连续出现三个可跨库复用的坑：

1. **configure 失败**：`invalid value 'c99 -O2' in '-std=c99 -O2'`。
2. **G2 失败**：CMakeDeps 报 `Library 'crypto_aead_hash_asconv13_ref' not found in package`。
3. **打包缺失**：上游 CMakeLists 无 install() 规则，产物不进入包。

## 根因

### 坑 1：上游把编译旗标做成 cache 变量且默认含 `-march=native`

上游 `CMakeLists.txt`：

```cmake
set(DEFAULT_REL_FLAGS -std=c99 -O2 -fomit-frame-pointer -march=native -mtune=native)
set(REL_FLAGS ${DEFAULT_REL_FLAGS} CACHE STRING "Define custom Release flags.")
```

- `-march=native` 按**构建机** CPU 生成指令，OHOS 交叉工具链下产物不可复现；
- 命令行 `-DREL_FLAGS="-std=c99 -O2"` 含空格 → CMake 当成**单个参数**，`-std` 收到
  整个 `c99 -O2` → `invalid value 'c99 -O2' in '-std=c99 -O2'`。
- 正确写法是**分号分隔列表**：`-DREL_FLAGS="-std=c99;-O2"`，或在 Conan 配方
  `CMakeToolchain` 中 `tc.variables["REL_FLAGS"] = "-std=c99;-O2"`（Conan 会按列表注入）。

### 坑 2：组合实现目录按 CRYPTO 类别双命名生成库

上游 CMake 用 `foreach(CRYPTO aead hash auth)` 循环生成库；组合目录
`crypto_aead_hash/asconv13`（同时提供 AEAD 与 HASH）在两个 CRYPTO 类别下被
fallback 命中，生成**两个同内容库**：

- `libcrypto_aead_asconv13_ref.a`
- `libcrypto_hash_asconv13_ref.a`（md5 与前者一致，均含 `crypto_aead_encrypt`/
  `crypto_aead_decrypt`/`crypto_hash` 全符号）

按目录名臆想库名 `crypto_aead_hash_asconv13_ref` 在 CMakeDeps 阶段必然
`Library not found in package`（find_package 配置中断）。

### 坑 3：上游无 install() 规则

`cmake.install()` 为空操作；需在 package() 手动复制：

- eBACS 声明头：`tests/crypto_aead.h`、`crypto_hash.h`、`crypto_auth.h`、`crypto_aead_hash.h`
- 各 ref 实现目录头（保持相对布局，供 `#include "api.h"` 解析）
- 全部 `*.a` 静态库

## 方案（ascon-c 1.3.0 实测）

```python
# conanfile.py generate()
tc.variables["REL_FLAGS"] = "-std=c99;-O2"          # 分号列表覆盖 -march=native
tc.variables["DBG_FLAGS"] = "-std=c99;-O2;-Wall;-Wextra;-Wshadow"
tc.variables["BUILD_SHARED_LIBS"] = "OFF"

# package_info() 用真实库名
self.cpp_info.components["asconv13"].libs = ["crypto_aead_asconv13_ref"]
self.cpp_info.components["asconv13"].includedirs = ["include", "include/crypto_aead_hash/asconv13/ref"]
```

## 验证（真实证据）

- `conan-verify` G0-G5 全 PASS（含 conan create 干净构建）
- test_package 消费者：AEAD 往返 / 篡改拒绝 / HASH LWC KAT 三组断言通过
  （conan create 日志 `100% tests passed, 0 tests failed out of 1`）
- 上游 genkat：199/199 (100%)，Release + REL_FLAGS 覆盖配置下全量通过
- `nm` 静态库可见 `crypto_aead_encrypt`/`crypto_hash` 符号

## 适用边界 / 反例

- 仅适用于**编译旗标在 cache 变量**且默认含 host 特性旗标（-march/-mtune）的项目；
  若旗标硬编码在 CXXFLAGS/CFLAGS，应改用补丁移除（见 DRAFT-8958-clthreads，
  该条为 Makefile 场景，本条为 CMake cache 变量场景，两者互补）。
- 组合目录双命名仅存在于"一个实现目录同时服务多个 CRYPTO 类别"的项目
  （ascon 系 eBACS 布局）；普通单类别目录库名与目录名一致，不受影响。
- 有 install() 规则的项目不需要坑 3 的手动打包。

## 查重（七轴）

- exact_duplicate：否
- causal_duplicate：否
- trigger_overlap：与 DRAFT-8958-clthreads（`-march=native` 交叉坑）部分重叠，
  但该条是 Makefile `CXXFLAGS += -march=native` 补丁移除，本条的 cache 变量
  CMakeToolchain 覆盖为独立路径；
- solution_overlap：与 DRAFT-cmrc-2.0.1（无 install 规则手动打包）部分重叠，
  但 cmrc 是纯 CMake 模块分发，本条为完整静态库 + 多组件手动打包；
- combination_novelty：是（三个坑在同一条配方中串联出现并一次修复，含
  CMake cache 变量分号列表语法这一未收录细节）
- boundary_novelty：是（分号列表 vs 空格字符串的 cache 变量注入边界）
- test_migration_novelty：否（KAT/消费者测试均为上游既有形态）

similar_to: [E092（CMake unknown HarmonyOS platform）, DRAFT-8958-clthreads, DRAFT-cmrc-2.0.1]
caused_by: [] / conflicts_with: [] / prerequisite_of: []

## 复用要点

- 遇到 `invalid value 'c99 -O2' in '-std=...'` → cache 变量须用分号列表。
- 遇到 `Library 'crypto_..._hash_...' not found` → 先 `ls build/*.a` 或
  `nm` 确认真实库名，再填 components。
- 遇到空 install() → 手动 copy 头 + 库。
