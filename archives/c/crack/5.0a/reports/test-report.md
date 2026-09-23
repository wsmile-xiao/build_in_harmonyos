# crack 5.0a verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64
- Clang 15.0.4（/data/service/hnp/bin/clang，target aarch64-unknown-linux-ohos）
- Conan 2.29.1（OHOS 适配版）
- Profile: ohos-aarch64

## Verification

- `conan create archives/c/crack/5.0a --profile:host=ci/conan/profiles/ohos-aarch64 --profile:build=default --build=missing`: **PASS**（构建 + test_package 全绿，exit 0）
- 上游测试：src/libdes/Makefile 注册唯一测试目标 `test: all` → `./destest`（libdes DES 算法自测：ecb/ede-cbc/pcbc/cfb/ofb/cbc_cksum/quad_cksum/对齐/fast crypt 十四组用例）；根/src/lib/src/util/extra 的 Makefile 无 test 目标——**上游注册测试 N=1**（1996 年源码，实证见 notes.md）
- 手工功能验证（适配期间，设备本地运行）：
  - 完整字典管线（mkdictgrps 全量 dict/1..3 + 2312 条规则）：cracker 从 `crypt("123456","ab")` 密文中恢复出明文（输出 `G:...:ab01FAX.bQRSU:123456`，命中 dgrp=1 rules.fast ':' 规则）

## 上游测试执行（N=1）

conanfile build() Stage 4 构建 src/libdes（-DTERMIOS 替代过时的 -DTERMIO，musl 无 termio.h）并执行 `./destest`：

- 14 组 DES 用例全过（Doing ecb / ede ecb / cbc / ede cbc / pcbc / cfb8..cfb64 / ede_cfb64 / ofb / ofb64 / ede_ofb64 / cbc_cksum / quad_cksum / input|output word alignment / fast crypt test）
- 零 error 输出行，exit 0
- 交付的 cracker 仍用 stdlib-cracker 后端（libc crypt(3)）；libdes 仅为运行上游测试而构建

## test_package（平台特有测试，主链路补全口径）

test_package/test_crack.py 真实运行被测包 bin/ 下全部二进制：

- 用例 1（dawg/xdawg roundtrip）：8 词表经 dawg 打包为 DAWG 词典、xdawg 解回，全部词无损恢复
- 用例 2（cracker 功能破解）：用被测包 dawg 自建最小词典（run/dict/1.dwg.gz）+ 精简 conf（rules.fast 直穿规则）+ 上游 smartcat/crack-sort 辅助脚本，喂入 `D:ab:ab01FAX.bQRSU:user1:...` SPF 行，cracker 输出 `G:<ts>:ab01FAX.bQRSU:123456` 确认恢复弱密码

- Test cases: 2
- Passed: 2
- Failed: 0
- Skipped: 0

## Result

配方已在 OpenHarmony aarch64 环境验证通过：conan create 全绿（exit 0）、上游 destest 1/1 通过（build 阶段真跑）、test_package 两个平台特有测试 100% 通过。状态为 built（本地验证通过，未 upload）。上游测试通过率 1/1（100%），新增测试通过率 2/2（100%）。
