# DRAFT-libyubikey-1.13-test-vector-porting-inplace-api-semantics

> Status: Draft | Updated: 2026-09-27 | Source: libyubikey 1.13 真机 shadow CI r3（job libyubikey-1.13-20260927）

## 摘要

把上游自测向量移植成 Conan test_package 断言时的两个方法论坑（libyubikey r3
实测：21 断言在真机 20 过 1 挂，挂的是**自己改写的那条**，不是上游向量）：

### 坑 1：API 的"原地变异"语义

上游 selftest 与移植断言的等价性依赖对 API 副作用的精确理解。libyubikey 的
`yubikey_generate(token, key, out)` 会**原地加密** token 结构体（yktoken.c:50）：

```c
yubikey_generate ((void *) &tok, key, out);   /* tok 已变成密文 */
yubikey_parse ((uint8_t *) out, key, &tok);   /* 解密写回 tok */
assert (memcmp (&tok, "\x16...", 16) == 0);   /* 上游：比常量，成立 */
```

若移植成"generate 后拿 tok 与 parse 结果比对"，比较的是**密文 vs 明文**，
任何正确实现的 AES 都必然失败。上游测试通过与"API 语义正确"之间的等价性，
在改写断言结构时最容易断掉。

**规则：移植向量时保持上游的比对结构（与常量比对），或先把原始输入存成
const 副本再比对；对"输出参数同时也是输入参数"的 C API 尤其警惕。**

### 坑 2：本机交叉编译只能证明"编译通过"，不能证明"断言正确"

W4 本机验证用 OHOS SDK clang 交叉编译 test.c + 上游库源码，ELF 编译链接
通过≠逻辑正确——交叉产物在本机不可执行，断言从未真正运行过。逻辑 bug
（坑 1）就这样漏到真机 CI 才暴露，多烧一轮排队。

**可行的本机预验证（按成本递增）：**

1. 把向量用 Python 等解释语言重演（modhex/CRC16/AES 都是十几行纯逻辑，
   可直接复算上游期望值）；
2. 上游向量不动、只改断言框架时，diff 出"语义等价性"再提交；
3. 有条件时在容器/QEMU 里真跑一次交叉产物。

## 验证（本案例）

- r3 真机：`FAIL: otp generate/parse roundtrip`（21 检查仅此 1 失败）；
- 修复为"与保存的原始字节常量比对"（与上游 otp-1 语义一致）后，r4 全绿：
  21 checks 0 failures，上游 make check TOTAL=1 PASS=1，
  run codex-1.13-libyubikey-1.13-20260927-conan-20260927-150715-23005。

## 相关条目

- 工作流 W3/W4（test_package 设计与本机验证）——本条是其"断言质量"维度的
  实证补充；
- 与 L1e 假测试检测互补：L1e 抓"不依赖被测包"的假测试，本条防"依赖了包
  但断言语义写错"的真假阳性/假阴性。
