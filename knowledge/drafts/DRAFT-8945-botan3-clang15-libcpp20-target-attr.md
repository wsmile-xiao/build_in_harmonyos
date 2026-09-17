# DRAFT-8945：botan3 3.12.0 适配 OHOS clang-15 定制 libc++ 的四类 C++20/ISA 坑与修复链

> Contributor: gcw_6YxinkyD | Status: Draft | Updated: 2026-09-08
> Source: PR !8945 【知识库扩展】feat(botan3): 3.12.0 编译完成（真机 11 轮构建迭代）

## 背景

Botan 3.12.0 是 C++20 加密库（自带 Python configure.py + make，非 CMake/Autotools），
零外部依赖。在 HarmonyOS PC 真机（clang 15.0.4 + OHOS SDK 定制 libc++ +
裁剪版 arm_neon.h）上做 Conan 适配，`conan create` 依次暴露四类工具链级错误。
每类错误均用**最小复现程序在真机实证**后修复，最终 conan create exit 0、
test_package 2/2 Passed（SHA-256 已知答案 + AES-256-GCM NIST KAT）。

## 坑 1：hmdfs 拒绝 symlink 创建（configure 阶段）

### 现象

```text
ERROR: Error linking .../src/lib/asn1/asn1_obj.h into build/include/public/botan:
[Errno 13] Permission denied: '../../../../../src/lib/asn1/asn1_obj.h' -> '...'
```

### 根因

Botan configure.py 探测到"主机支持 symlink"后默认用 symlink 把源码头文件链入
build 目录；真机 /storage（hmdfs 分布式文件系统）对 symlink 创建返回 EACCES
（探测用的 /tmp 或其他路径不触发）。

### 修复

configure 加 `--link-method=copy`（上游官方选项，零 patch）。

## 坑 2：函数级 target attribute 上的 intrinsic 宏门控（编译早期）

### 现象

```text
src/lib/block/aes/aes_armv8/aes_armv8.cpp:24:19: error: use of undeclared identifier 'vaeseq_u8'
```

编译命令行只有 `-fPIC -fstack-protector -pthread -std=c++20 -O3 ...`，
**无任何 -march**。

### 根因（真机最小复现实证）

Botan 3.12 新引入 `BOTAN_FUNC_ISA("...")`（函数级 `__attribute__((target(...)))`）
标注 AES/SHA/GHASH 内核。但 OHOS clang-15 定制 arm_neon.h 的 intrinsic **声明由
`__ARM_FEATURE_CRYPTO` 等预处理宏门控**，而 target attribute 是编译期机制、
**不定义任何预处理宏** → 函数体内 intrinsic 未声明。另发现该 arm_neon.h 是裁剪版
（vrevq_* 系列整个被删）。

### 修复

configure 加 `--cc-abi-flags=-march=armv8.2-a+crypto+sha3+sm4`：命令行定义全部
特性宏。注意 clang-15 不认识 `+sha512` 扩展名，但 `+sha3` 组合下
`vsha512hq_u64` 已可见（真机验证）。

## 坑 3：多 feature target attribute 解析损坏（编译中后期，ghash_cpu.cpp）

### 现象

```text
ghash_cpu.cpp:82:38: error: always_inline function 'reverse_vector' requires target
feature '+simd', but would be inlined into function 'ghash_precompute_cpu' that is
compiled without support for '+simd'
```

### 根因（真机三个最小复现实证，关键差异）

调用者已标注 `target("+crypto+aes+simd")`，clang-15 **仍认为其不含 +simd**：

```cpp
__attribute__((always_inline, target("+simd"))) inline uint8x16_t add2(...);  // callee
__attribute__((target("+crypto+aes+simd"))) uint8x16_t callerA(...) { return add2(...); }
// → error: requires target feature '+simd' ... compiled without support for '+simd'
```

且 `target("arch=armv8.2-a+crypto+aes+simd")`（arch= 前缀）被 clang-15 直接拒绝
（unknown architecture）。即 OHOS clang-15 上**函数级 ISA attribute 路线整体不可用**。
x86 无此问题（x86 的 CLMUL 特性串 "pclmul,ssse3" 恰好包含 SIMD 需求），上游 CI
因此未暴露。

### 修复（patch 0004）

patch `src/lib/utils/compiler.h`，把 `BOTAN_FUNC_ISA` 的定义条件改为 `#if 0`
（展开为空）：
- 全局 `-march`（坑 2 修复）已启用所有特性，intrinsic 可用且指令可生成；
- 运行时 cpuid 门控（cpuid_aarch64 模块）保证只在支持的 CPU 上执行这些内核；
- 无 attribute 即无 always_inline 跨 target 检查。

## 坑 4：libc++15 的 C++20 缺口（编译中期，两批）

### 现象 A：defaulted spaceship 被隐式删除

```text
error: object of type 'const Botan::IPv6Address' cannot be compared because
its 'operator<=>' is implicitly deleted
```

### 根因 A

OHOS libc++15 的 `std::array` **没有 operator<=>**（上游 LLVM 16 才实现）→
成员为 `std::array` 且 `operator<=> = default` 的类（IPv6Address、
X509_Certificate::Tag、DER_Hash、KeyId）在有序容器 key 语境全部编译失败。
影响面判定：成员为标量（IPv4Address 的 uint32_t）或手写比较（x509_ext 的
IPAddress）的类不受影响；`Strong<T>` 的 spaceship 有
`requires(std::three_way_comparable<T>)` 约束自动排除。

### 修复 A（patch 0001）

四处替换为手写运算符（真机验证 std::array 的 `==` 与老式 `<` 均可用）：

```cpp
friend bool operator==(const IPv6Address&, const IPv6Address&) = default;
friend bool operator<(const IPv6Address& a, const IPv6Address& b) { return a.m_ip < b.m_ip; }
```

### 现象 B：ranges 算法缺失

```text
p11_interface.cpp:125:21: error: no member named 'equal' in namespace 'std::ranges'
certstor.cpp:191:56: error: no member named 'equal' in namespace 'std::ranges'
```

### 根因 B

OHOS libc++15 缺 `std::ranges::equal` 与 `std::ranges::any_of`，但
`range_value_t`/`begin`/`end`/`data` 等概念设施**存在**——同一文件里其他
ranges 用法可编译，缺失是逐算法的。

### 修复 B（patch 0002）

改为迭代器版 C++17 算法（span/vector 直接 begin/end）：

```cpp
std::ranges::equal(a, b)  →  std::equal(a.begin(), a.end(), b.begin(), b.end())
std::ranges::any_of(c, p) →  std::any_of(c.begin(), c.end(), p)
```

**教训**：影响面盘点必须 `grep -rl` 全量列出。首轮 `grep | head -5` 截断，
只修了 6/12 处 ranges::equal，第七轮在 certstor.cpp 重新失败浪费一整轮
40 分钟构建。

## 坑 5：botan 特有开关（供 botan 系列库复用）

- `--without-os-features=explicit_bzero`：musl 无该函数，上游 mem_utils.cpp
  自带 volatile memset fallback（configure 官方选项，零 patch，优于手工注释
  build.h 宏——botan 3.6.1 手工适配的老办法）。
- `--disable-modules=kyber,kyber_90s,kyber_common,kyber_round3,ml_kem,dilithium,
  dilithium_aes,dilithium_common,dilithium_round3,ml_dsa`：clang-15 C++20
  concepts 下 StrongSpan 转换失败（3.6.1 记录一致）；同用 StrongSpan 的
  frodokem/classic_mceliece/sphincsplus/xmss 反而可编译，勿扩大禁用面。
- `--build-targets=static,tests` + `make -j1 check`：**上游测试套件已启用并全量
  通过**（CI #45110）。测试侧共 5 个 patch（0003-0008）：
  - 0003：12 处 `std::ranges::sort/equal/find`（另 1 处为上游注释）改迭代器版；
  - 0005：测试运行器 mkstemp 从只读 `/tmp` 改读 TMPDIR（botan2 同款），
    配方以命令前缀 `TMPDIR=<build_folder> make -j1 check` 传递
    （ConanFile.run() 的 env= 只收 profile 环境名列表，传 dict 会断言失败）；
  - 0006：5 个测试 TU 只含 `<iosfwd>` 却用流 `operator<<`/stringstream（OHOS
    libc++15 传递包含不完整 → ostream 不完整类型），补 `<ostream>`/`<sstream>`；
  - 0007/0008：`OctetString`/`SymmetricKey`（别名！）传 span 形参无可行重载
    （LLVM16 前 libc++ span 容器构造要求 `.data()`，OctetString 只有 begin/end），
    0007 逐调用点 iterator-pair 桥接，0008 在 tests.h/tests.cpp 加
    `test_bin_eq(string_view, OctetString, OctetString)` 重载根治——
    **排查必须按类型而非字面名**（SymmetricKey 别名曾漏网多烧一轮 CI）。
- 头文件布局：configure 产物在 `build/include/public/botan`（非 botan2 时代的
  `build/include/botan-2`），打包到上游安装布局 `include/botan-3` +
  `cpp_info.includedirs=["include/botan-3"]`。
- 消费者 cppstd：共享 profile 默认 cppstd=17，botan3 头需要 C++20，
  test_package 必须自声明 `CMAKE_CXX_STANDARD 20` + `target_compile_features
  (cxx_std_20)`。
- OHOS toybox 截断超长单行 `ar crs <全部 .o>`（botan2 已知坑）保留 glob 重建
  fallback：`ar crs libbotan-3.a build/obj/lib/*.o`。

## 方法论沉淀：最小复现程序驱动定位

四类坑中有三类靠 10 行内的 C/C++ 复现程序在真机直接验证假设后修复，避免
盲目改配方浪费 40 分钟/轮的完整构建：

```sh
# 例：验证 target attribute 语义（坑 3）
printf '#include <arm_neon.h>\n__attribute__((always_inline, target("+simd"))) ...' > t.cpp
clang++ -std=c++20 -march=armv8.2-a+crypto+sha3+sm4 -c t.cpp   # 观察报错差异
```

配合 11 轮构建历史表（notes.md），每轮只改一个变量，失败点单调后移。

## 验证

真机（10.62.134.118）隔离 CONAN_HOME + 离线 download cache：

```sh
conan create archives/b/botan3/3.12.0 -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing
# exit 0；libbotan-3.a 26MB；ctest 2/2：
#   botan3_sha256（SHA-256 KAT + hex round-trip）
#   botan3_aes_gcm（AES-256-GCM NIST TC14 KAT + 认证解密 + 篡改 tag 拒绝）
```

## 关系

- 类似 E011（HMDFS 权限类）；本链新增 hmdfs 拒绝 symlink 的 configure 级表现。
- 与 botan2/2.19.5（已合入）共享 ar 截断与 --os=linux 处理；C++20 相关四坑为
  botan3 新增。
- 对所有"函数级 target attribute 标注 SIMD/加密内核"的库（mbedtls-ng、
  libsodium 现代 fork、 simdjson、任何用 BOTAN_FUNC_ISA 风格宏的代码）在
  OHOS clang-15 上直接适用：attribute 路线整体不可用，须全局 -march。
