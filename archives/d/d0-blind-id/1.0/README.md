# d0-blind-id

**d0_blind_id — 盲身份 / 匿名认证密码学库**（含独立 AES 实现），
上游：<https://github.com/divVerent/d0_blind_id>，许可证 3-clause BSD（上游 `COPYING`）。

给定 RSA 公钥，双方可协商出 private ID 并做匿名认证、签名与 DH 会话密钥协商；

```c
d0_blind_id_INITIALIZE();
d0_blind_id_t *a = d0_blind_id_new(), *b = d0_blind_id_new();
d0_blind_id_generate_private_key(a, 1024);
/* … write/read_public_key → generate_private_id_modulus →
      generate_private_id_start/request → answer/finish → sign/verify →
      authenticate start/challenge/response/verify → sessionkey_public_id … */
```

交付：`libd0_blind_id.so` + `libd0_rijndael.so`、
`include/d0_blind_id/{d0_blind_id.h,d0.h,d0_rijndael.h}`、两个 `.pc`、
`bin/blind_id`（上游演示程序，commands.json 已申报）、`licenses/COPYING`。
唯一依赖：`gmp/6.3.0`。

测试：上游**无测试套件**（如实声明）——build() 内跑上游 `blind_id` 全协议流程冒烟；
消费者用例用 **NIST FIPS-197 官方 AES 向量** + 完整盲身份协议流 + 篡改负例（35 项全绿），
另有 17 项交付形态自检，见 `notes.md`。
