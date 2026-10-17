# cbonsai 1.4.2 适配笔记

## 选型与版本核验（2026-09-05）

- GitLab jallbrit/cbonsai tags 实拉：`v1.4.2` 存在且为最新 release ✓
- 上游被 Debian/Fedora/homebrew 广泛收录，repology 状态健康 ✓
- 档案（含异名变体）无 cbonsai；任务 contrib-6223 在池 ✓
- 候选序位：cccc 3.2.0 因需要 PCCTS/ANTLR 生成解析器（古老 C 工具链，
  clang 15 高风险）被否决，落至 cbonsai（单文件 C，近零风险）

## 编译环境

- 构建系统: 纯 POSIX Makefile（单文件 C，无 configure/cmake）
- 目标平台: HarmonyOS PC arm64（OHOS/aarch64 原生）
- 编译器: /data/service/hnp/bin/clang 15.0.4（profile conf 注入，R33）
- 状态: adapting（设备验证后更新）

## W0 依赖预检（2026-09-05，Mac 侧 conan 2.32 匿名直连 ohpcd）

- `conan download ncurses/6.4 -r=ohpcd` → 二进制下载成功 ✓
- 载荷实测：libncursesw.a + libpanelw.a 静态库，头文件平铺 include/
  （curses.h/ncurses.h/panel.h）——CFLAGS/LDLIBS 直传即可，无需 pkg-config

## R51 上游测试清点（官方 archive 实测）

- **无测试套件**：单 C 文件 + Makefile + 手册页源 + 补全脚本
- 结论：实质验证由 test_package 承担（-h / 固定种子确定性输出 / 两次运行
  一致），见 test_package/MANIFEST.yml

## 配方设计决策

| 决策 | 理由 |
|---|---|
| 纯 make 变量覆盖，无 autotools/cmake 助手 | 上游就是 POSIX Makefile；命令行变量整体压制 Makefile 内建赋值（含 pkg-config $(shell) 探测），设备无需 pkg-config |
| CC 取 profile conf（R33） | /data/service/hnp/bin/clang，不裸依赖环境 |
| PREFIX=/ + DESTDIR | packetq 教训前置：默认 /usr/local 会嵌套进 usr/local/ |
| 静态链接 -lpanelw -lncursesw -lncursesw | ohpcd ncurses 为静态库；panelw 依赖 ncursesw，尾部补一次防符号环回 |
| 测试三断言 | -h 纯 printf 路径；-p -s 固定种子确定性输出（叶子字符 '@' 计数）；两次运行 diff 一致 |

## 已知前置风险

- `-p` 模式仍经 initscr（ncurses 屏幕），非 tty 下需 TERM/TERMINFO——
  test 中显式指向 ncurses 包内 terminfo 目录（share/ 或 lib/ 布局都探测），
  失败模式为 initscr 报错退出，按 R43 口径处理

## 待办（Phase 2，设备侧）

- [x] mailbox 通道可用（前序会话已验证）
- [ ] bundle 推送 → conan-verify 八门禁 → finish
---

**编译结束**: 2026-09-05 22:04
**最终状态**: built
