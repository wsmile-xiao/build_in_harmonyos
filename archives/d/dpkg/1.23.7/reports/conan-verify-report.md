# conan-verify-report — dpkg 1.23.7（OHOS PC 适配验证报告）

## 构建验证

- 配置：ohos-aarch64（clang 15，OHOS 6.0）
- 命令：`conan create archives/d/dpkg/1.23.7 --build=missing`
- 结果：**通过** —— `dpkg/1.23.7: Package created`（包 ID 0954215d2f61edcc94e363eda1bf7141541326ae）
- 打包产物（bin/）：dpkg、dpkg-deb、dpkg-query、dpkg-split、dpkg-statoverride、dpkg-trigger、update-alternatives、start-stop-daemon

## R34 消费者验证

- test_package/test_dpkg.py：dpkg 二进制存在（1/1 = 100%）

## 上游测试核验（rule 4）

- 全量核验（tar tJf）：`tests/` 88 个 t-* 测试用例目录
- 可运行用例 **86 个**（Makefile 显式声明）：TESTS_PASS 81 + TESTS_FAIL 3
  （上游已知失败）+ TESTS_MANUAL 2
- 运行前提：as-root 特权模式写根文件系统（README 明示）或 chroot/VM——
  OHOS 沙箱无法满足，**未运行**（如实记录，不伪造通过率）
- 详见 `reports/upstream-dpkg-test.log`

## 关键攻坚点（config.status mktemp 沙箱限制）

- 问题：`./config.status: ./confXXXXXX/subs1.awk: Permission denied`
- 根因：鸿蒙沙箱 /tmp 只读 + $HOME/.ci_logs 写入 Permission denied + autoconf 相对路径 mktemp
- 解法：TMPDIR 指 /data/storage/el2/base/cache + configure 的 mktemp 模板改 ${TMPDIR}/confXXXXXX（准确替换点带引号 `mktemp -d "./confXXXXXX"`）
- 验证：config.status 完整执行（creating xxx / executing libtool commands）——详见 SKILL：
  `knowledge/drafts/DRAFT-autotools-config-status-mktemp.kv` + `docs/skills/autotools-config-status-mktemp-sandbox.md`
