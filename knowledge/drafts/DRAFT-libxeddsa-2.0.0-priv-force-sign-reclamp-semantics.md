# priv_to_ed25519_pub 的内部 clamp 会破坏 priv_force_sign 的取反标量——断言要走功能等价路径

- **草稿 ID**: DRAFT-libxeddsa-2.0.0-priv-force-sign-reclamp-semantics
- **来源**: libxeddsa 2.0.0-20231128.d725c81 真机 test_package 第三轮（18/19，唯符号位断言失败；同轮上游套件全绿 → 读源码定位为测试误用）
- **分类**: testing / crypto / api-semantics
- **状态**: 本地草稿（路径 B 知识库扩展申请中）
- **严重级**: 3（不损库功能，但极易诱发"库有平台 bug"的误报排查）

## 问题 / 错误签名

消费者测试直觉写法失败：

```c
priv_force_sign(priv1, key, 1);
priv_to_ed25519_pub(pub1, priv1);
CHECK(pub1[31] & 0x80);   /* FAIL——符号位并非 1 */
```

真机表现为单条断言失败（本例 18/19），且失败键固定可复现。

## 根因（读 src/pub_derivation.c 与 src/seed_priv_utils.c）

- `priv_force_sign` = `sc_clamp` 后按需 `sc_neg`：输出可能是**取反标量**，
  不是 clamped 形态。
- `priv_to_ed25519_pub` 入口**自己再 clamp 一次**。clamp（置位 254、清 253
  与低 3 位）只对 clamped 形态幂等；对一般标量（如取反结果，位于 [0,q) 任意
  形态）clamp 出来的是**另一个不等价标量**（无模约简）。
- 于是取反标量回灌 `priv_to_ed25519_pub` 得到的公钥与 `-A` 无关，符号位随机。
- **库本身正确**：`ed25519_priv_sign` 直接用传入标量做 `ge_scalarmult_base`
  （不 clamp），`priv_force_sign` 输出正是它的预期输入；上游 `test_signing.c`
  的验证路径是 `curve25519_pub_to_ed25519_pub(curve_pub, sign)` + `ed25519_verify`，
  真机全绿。

## 正解写法（真机 4/4 通过）

符号位断言写成 2×2 交叉签名/验签：

```c
ed25519_priv_sign(sig, priv0, msg, len, nonce);   /* force(key, 0) */
CHECK(ed25519_verify(sig, ed_pub0, msg, len) == 0);   /* sign=0 公钥验过 */
CHECK(ed25519_verify(sig, ed_pub1, msg, len) != 0);   /* sign=1 公钥拒绝 */
ed25519_priv_sign(sig, priv1b, msg, len, nonce);  /* force(key, 1) */
CHECK(ed25519_verify(sig, ed_pub1, msg, len) == 0);
CHECK(ed25519_verify(sig, ed_pub0, msg, len) != 0);
```

其中 `ed_pubN = curve25519_pub_to_ed25519_pub(curve_pub(key), N)`。

## 影响面与推广

- 给 XEdDSA 系库（libxeddsa、libsignal 系）写消费者测试的场景。
- 更一般的原则：**入口自规范化（clamp/hash-to-scalar/编码转换）的 API 与
  输出非规范形态的 API 串联时，先确认规范化的幂等域**；断言打在公开契约上，
  不做内部表示的旁路观测。
- 排查方法论：自写断言失败、而上游同主题套件通过 → 先怀疑测试误用再怀疑
  库；读两个函数的源码语义比盲改断言快。

## 第二现场：force 后的标量不能复用为 X25519 密钥（会话用例实测）

同一语义在消费者会话用例中再踩一次：先 `priv_to_curve25519_pub(pub, priv)`
再用 `priv_force_sign(priv, priv, 0)` **原地覆写** priv，随后拿该标量做
`x25519(secret, priv, peer_pub)`——两侧若只有一方被取反，ECDH 共享密钥
不一致（真机 26/27，唯 ECDH 一致性失败）。

正确写法：**签名用 force 后的副本，ECDH 用 force 前的原始标量**（各自独立
变量）。这不是库 bug 而是使用契约：sign-bit 强制本质上会换一个（可能取反
的）标量，会话代码必须为签名与 ECDH 维护两份标量。
