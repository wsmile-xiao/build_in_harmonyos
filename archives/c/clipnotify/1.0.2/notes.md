# clipnotify 1.0.2 适配笔记

## 选型与版本核验（2026-09-07）

- GitHub cdown/clipnotify tags 实拉：`1.0.2`（最新 release，无 v 前缀）✓
- 档案无 clipnotify；制品仓零发布（conan list 交叉确认）✓
- 平台任务 contrib-6502 已认领（claimer Ember5843，10 火种）✓
- 源码极小：clipnotify.c 单文件 + Makefile（tarball 1.3KB）

## 配方决策

- **绕开上游 Makefile**：其硬编码 `-I/usr/X11R6/include -L/usr/X11R6/lib`，
  设备/CI 无此路径 → 配方直接执行同一编译式，include/lib 全部来自
  conan 依赖包（libx11/6.4.0 + libxfixes/6.1.0 + xorgproto/2025.1，
  xclip 0.13.1 先例同款组合；R36）
- **E549**：产物为 ELF 工具 → binary-sign-tool 自签名（cc-connect 同款
  _sign_elf 实现）
- **R34 测试**：设备无 X server，消费者测试断言确定性错误路径——
  已签名 ELF 可执行 + 动态链接 X11 正确 + exit 1 + "Can't open X display"
  （上游 clipnotify.c 第 13-16 行）；上游无测试套件（MANIFEST 申报）

## 待办（Phase 2，设备侧）

- [ ] bundle 推送 → conan create → conan-verify 八门禁 → finish

## 对话记录（关键转折）

- 2026-09-07 用户授权后第二单：六连筛全绿 → 两段式认领（contrib-6502，10 火种）
- conan create 一次通过（签名 ELF + 无 X 错误路径消费者测试 PASSED）
- conan-verify 八门禁 rc=0；finish 首轮 L0c no_test_sources → 测试逻辑落成
  test_nox.sh（test_package 必须含 .sh/.c 测试源文件）后全绿
- staging 直跑 rc=127 属预期（无 conanrun 的 LD_LIBRARY_PATH；test_package 环境
  已证明产物可执行）

## 终态（2026-09-07）

- **status: built（submit 就绪）**：create + test_package + 八门禁 + W3/W2 全绿
- 下一步（人工）：push 分支 → submit 建 PR → CI 绿后 submit 自动升级 success（R50）
