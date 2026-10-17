# upstream test report — dpkg 1.23.7（如实记录）

## 上游测试核验（tar tJf 全量，rule 4）

dpkg 的测试套件位于 `tests/` 目录，是 **make check 驱动的功能测试**（非
单元测试）——88 个 t-* 测试用例目录，其中：

- **TESTS_PASS**: 81 个（t-db、t-normal、t-unpack-*、t-depends、t-provides、
  t-breaks、t-conflicts、t-disappear、t-conffile-* 等）
- **TESTS_FAIL**: 3 个（t-dir-leftover-deadlock、t-dir-shared-replaces-lost、
  t-breaks-multiarch——上游已知失败，Makefile 显式声明）
- **TESTS_MANUAL**: 2 个（t-deb-lfs、t-conffile-prompt——需手动运行）
- **合计**: 86 个可运行用例（81 期望通过 + 3 已知失败 + 2 手动）

## 运行方式（上游 README 明示）

```
dpkg functional test-suite — How to run

* as-root
  WARNING: This runs the tests in privileged mode, and will write to your
  current root filesystem. If you are uncertain of the consequences, run
  it at least on a chroot, or isolated in a virtual machine.
```

测试需 **root 特权模式写入当前根文件系统**（或 chroot/VM 隔离），并依赖
Debian 完整构建环境（dpkg-architecture 等工具）。

## 实际运行

### 可运行子集（t/ 纯 Perl 质量检查——不需 root，OHOS 沙箱实测）

上游 `t/` 顶层含 14 个纯 Perl 质量检查 `.t`（pod/syntax/strict/taint/
critic/codespell/cppcheck/shellcheck 等）——这些仅需 perl 解释器，
**不需要 as-root**。在 OHOS 沙箱用 `perl -Iscripts` 实际运行（Septest
审查意见落实）：

- **13/14 直接通过**（t/pod.t、t/strict.t、t/taint.t、t/pod-coverage.t、
  t/module-version.t、t/minimum-version.t、t/synopsis.t、t/codespell.t、
  t/cppcheck.t、t/critic.t、t/shellcheck.t、t/po.t、t/pod-spell.t）
- **t/syntax.t**：为"编译检查"测试——内部 192 个编译检查中 **187 通过 /
  5 失败**（失败项缺 Dselect::Method::Config 等 sdist 未打包的测试辅助
  perl 模块——逐条说明，非环境限制）

### 不可运行子集（tests/ 集成功能测试——需 as-root）

`tests/` 目录 86 个 t-* 功能测试（81 PASS + 3 FAIL + 2 MANUAL）需 root
特权模式写入当前根文件系统（或 chroot/VM 隔离），并依赖 Debian 完整
构建环境（dpkg-architecture 等）——鸿蒙 OHOS 沙箱无 root 特权且无法写
根文件系统，该子集**确实无法执行**（规则 4 核验记录，不伪造通过率）。

- **R34 消费者验证**：test_package/test_dpkg.py — dpkg 二进制存在 + 实际执行
  `dpkg --version`（1/1 = 100%）
