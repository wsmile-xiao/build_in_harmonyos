# zrc 2.7 OHOS 适配笔记

- 状态: built
- 上游: https://github.com/Edd12321/zrc （tag v2.7，BSD-2-Clause）
- 包类型: application（CLI shell/脚本语言，纯可执行文件，无库产物）
- 构建系统: 纯 Makefile（C++11，零外部依赖，仅 libc/libc++）
- 版本号: 2.7（首次适配，上游版本原样）

## 关键适配决策

1. **CXXFLAGS 覆盖**：上游默认 `-flto`（OHOS 系统链接器 LTO 风险）被去掉，
   追加 `-fsigned-char`（AArch64 char 默认无符号，zrc 做逐字符处理，
   恢复上游 x86 有符号语义）。
2. **不使用 `make install`**：上游 install 目标会向 /etc/shells 追加行，
   打包直接从 `bin/zrc` 拷贝（同 jpnevulator 先例）。
3. **日志绑定**：make 输出 `> make-release.log 2>&1`，失败回显日志尾部
   （本平台 conan 管道吞编译器输出的已知问题）。
4. **上游无测试套件**：Makefile 仅 release/debug/clean，无 check 目标，
   验证由 test_package 消费者测试承担（8 项断言，脚本改编自上游
   examples/99bottles.zrc）。

## 构建台账

- conan create: RC=0（本地，ohos-aarch64 profile，Release，--user=ohpcd --channel=stable）
- test_package: 8/8 断言通过（test_zrc.sh；首版 2 个退出码断言按上游
  语义修正：zrc 退出码=stonum($status)，echo 不更新 status，--version
  恒退 1，脚本用 `exit 0` 收尾保证确定性）
- 实验记录：`zrc -c 'echo hi'`→rc 255；`zrc s.zrc(echo done)`→255；
  `exit 0`→0；`--version`→1（横幅正常输出到 stderr）

### 对话 #1

- 确定 zrc 为 CLI application，参照 jpnevulator 2.3.6 模板；
- 确认 tag 为 v2.7（上游 release 页面），sha256 fe304ffb...12d0；
- 三查确认 archives 无 zrc 适配记录。
---

**编译结束**: 2026-09-23 23:58
**最终状态**: built
