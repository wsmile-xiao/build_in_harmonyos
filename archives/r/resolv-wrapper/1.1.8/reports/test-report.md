# resolv-wrapper 1.1.8 HarmonyOS 测试报告

## 测试环境

- 构建宿主：鸿蒙真机 PC（arm64）
- 目标：HarmonyOS 6.0.0 aarch64（OpenHarmony SDK 26.0.0，Clang 15.0.4）
- Conan：2.29.1（OHOS 适配版，profile `ohos-aarch64`）
- 测试依赖：`cmocka/2.0.2`、`socket-wrapper/1.4.1`（制品仓已可消费）

## 上游测试清点（R51 三步法）

resolv-wrapper 1.1.8 官方 `tests/` 目录在 `UNIT_TESTING=ON` 下注册 2 个 CTest 测试组：

| 测试组 | 测试源 | 用例数 |
|---|---|---|
| test_res_init | tests/test_res_init.c | 2（test_res_ninit / test_res_ninit_enoent）|
| test_dns_fake | tests/test_dns_fake.c | 16（A/AAAA/SRV/URI/SOA/CNAME/PTR/TXT fake 查询）|

## 构建与 Conan 结果

- 干净 `conan create`：退出 0。
- 包引用：`resolv-wrapper/1.1.8#343d9077453c1ea761dcfc3a03ef1afb`
- 包 ID：`01d92cf349a0dd98ff915f4bd99a04430171517f`，包修订 `9a4db8517f1c1e3fe5f8593102d01069`。
- 产物：`libresolv_wrapper.so.0.0.8`（+ `.so.0` / `.so` 符号链接）、`resolv_wrapper.pc`、CMake config。
- `conan-verify`：G1/G0/G2/G3/G4 + L2/L4/L5 全部 PASS。

## 上游测试实际执行（OHOS 交叉编译 + LD_PRELOAD）

两个 CTest 组均在本机实际编译并执行：

| 测试组 | 结果 |
|---|---|
| test_res_init | 2/2 通过 |
| test_dns_fake | 16/16 通过 |
| **合计** | **18/18 通过（100%）** |

### 测试适配说明（patch 0001/0002/0003）

1. **res_n* 缺失**：OHOS libc 只提供经典 `res_init/res_query/res_search`，无线程安全的 `res_ninit/res_nquery/res_nsearch/res_nclose` 且 `libresolv.a` 为空壳。源码层新增：libc 经典符号经 `dlsym` 绑定（避免 LD_PRELOAD 下递归拦截自身）、wrapper 自行导出 `res_n*` 符号、测试侧通过 compat 头声明并链接 wrapper 符号。
2. **tests/CMakeLists.txt**：OHOS 下对测试目标 force-include compat 头并链接 wrapper，令测试链接/运行期符号可解析。
3. **ns_initparse 长度**：OHOS 的 `ns_initparse` 需要真实应答长度而非缓冲区大小（传 256 时 SRV 应答解析失败）；测试改用 `res_nquery` 返回的真实长度。

所有修改均基于能力检测宏（`HAVE_RES_INIT/HAVE_RES_NQUERY/...`）或 `CMAKE_SYSTEM_NAME`，无平台宏硬编码，可在 glibc/musl/OHOS 间切换。

## 消费者用例（test_package）

`test_package/test.c` 调用库公开 API `res_ninit()` / `res_nquery()` / `res_nclose()` 完成一次 fake A 查询并验证应答长度，编译、链接、运行均通过（`1/1`），输出：

```
resolv-wrapper consumer test PASSED (fake A query answered, len=52)
```

## 结论

- 上游测试通过率：**18/18（100%）**
- 新增消费者用例通过率：**1/1（100%）**
- 编译状态：**通过**
