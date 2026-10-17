# minunit 0.0-git20230524-a0586569 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | minunit(极简单头文件 C 单元测试框架) |
| 版本 | 0.0-git20230524-a0586569(master 快照,commit a0586569bd,2023-05-24) |
| 状态 | built |
| 构建系统 | header-only(无编译产物) |
| 源码 | https://codeload.github.com/siu/minunit/tar.gz/a0586569bd8abfb7a37390d670484c201e9173bf |
| sha256 | 3e3ecbcdc4e166c782dcd1d9c1f80ce14297d948695089521a2a7769224507b9 |

## 版本溯源(快照式版本号)
- 上游为滚动 master(默认分支 master),无 release,最后推送
  2023-05;包版本取提交快照式 `0.0-git20230524-a0586569`
  (= commit a0586569bd),快照版本式先例。

## 上游形态
- 单头文件 minunit.h(11KB),MIT 许可;mu_assert + MU_TEST/
  MU_TEST_SUITE/MU_RUN_* 宏族,需消费者自带 main(或 MU_REPORT 后
  返回 minunit_fail)。
- 库不产生链接产物，但有正式 `ci/Makefile` 与
  `ci/check_example.sh`/`.bat` 上游回归入口。`minunit_example.c`
  注册 11 个用例，其中 6 个预期失败；原始脚本要求退出码恰好为 6。

## 配方设计
1. **header-only 打包规范**(DRAFT-header-only-package-spec,第三例):
   settings 全四项；build() 编译并执行原始上游 CI 回归；
   package() 装 minunit.h 与实际 MIT-LICENSE.txt；
   package_info 仅 includedirs。
2. R34 消费者验证:test_package python 探针(worker 编译器兜底链)
   编译真实 MU_TEST_SUITE 并运行,断言输出 `2 tests, 2 assertions,
   0 failures` 且 rc=0。

## 2026-10-04 真实验证

- Windows Conan create RC0：源码 SHA 不变，显式 filename 后按 tar.gz 解包；
  官方回归入口通过，消费者 `2 tests, 2 assertions, 0 failures`。
  仅为宿主配方诊断，不冒充 OHOS CI。
- HarmonyOS/aarch64 W3 `minunit-20261004-r001`：原始上游入口 1/1，
  完整覆盖 11 个示例用例与 6 个预期失败身份；消费者 2/2；
  `ohos_timer_backend` 1/1（4 个断言，真实 mu_timer_real/mu_timer_cpu
  及 nanosleep 运行路径）。
- 端点 `10.62.201.39:2222`，固定 boot_id/UID、源/脚本/工具 SHA；
  三个测试 ELF 原生编译、自签、独立传输回读；唯一 launch_count=1；
  WAL/receipt chain 重放与 RELEASED/POSTRELEASE 均通过。
- 证据根：`F:/HarmonyPC/pr-review-closure-20261004-r1/w3-minunit-r001`。
  此结果不等于当前修复提交已通过平台 CI 或 Review。

## 遇到的问题与解决方案

### AtomCode 超时替代检视修复及真机验证

- F1：声明断言总数从误写的 6 改为实际 11；6 是官方预期失败数。
- F2：两个 Python 测试脚本不再索引必有的 TMPDIR，Conan 显式传递
  当前 build_folder；脚本在其独占子目录中设置子编译/签名/运行进程
  的 TMPDIR/TMPPREFIX。未指定时仅使用显式环境目录或当前目录，
  不回退到设备只读 /tmp。
- F4：固定完整官方提交 URL，下载归档 6008 bytes。新旧归档容器 SHA
  不同，但所有成员相对路径、bytes/SHA-256 完全一致，头文件未变化。
- 新 W3 `minunit-20261004-r002` 实际调用两个修改后的 Python 脚本，
  在父进程 TMPDIR/TMPPREFIX 均未设置的场景中消费者 2/2、目标计时器
  1/1 PASS；原始官方回归入口 1/1，11 用例/11 断言/6 个预期失败。
- r002 config SHA：632a1b40e8edbfd7b3e61516d385f435db83d49d981467328633d0e8972a4c6a。
  唯一 launch=1，完整 WAL/receipt 校验、RELEASED/POSTRELEASE PASS，
  自有进程数 0。证据位于同任务根 `w3-minunit-r002/validation.json`。
- F3 的 os=OHOS 被实际 Conan profile 证实正确，不把内核 uname 的
  HarmonyOS 字符串混作 Conan 枚举。当前修复还需正式配方验证、push
  和当前 HEAD 平台 CI；此节不宣称已提审。

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 探针 undefined reference to mu_run_test | 老式教程 API(mu_run_test 需消费者自定义);现代 minunit 用 MU_TEST 宏族 | 探针改 MU_TEST/MU_TEST_SUITE/MU_RUN_TEST/MU_REPORT 现代 API,返回 minunit_fail 作退出码 |
| 2 | strcmp 隐式声明 | 探针缺 string.h | 探针补 #include <string.h> |
| 3 | CI #70019 BadZipFile | 下载 SHA 正确，但 basename master 无归档扩展名，Conan 误选 ZIP 解包器 | conandata sources 显式 filename=minunit-master.tar.gz；保留 URL/SHA |
| 4 | 消费者断言可能空过 | mu_assert 的参数应为 condition,message，旧探针写反 | 按真实头文件接口修正，并严格检查 2 tests/2 assertions/0 failures |
| 5 | 安装丢许可 | 上游许可文件为 MIT-LICENSE.txt，不是 LICENSE | 复制真实许可文件并经 Conan package 验证 |

## 已知限制(notes 如实声明)
- header-only 不豁免上游测试或目标执行。正式上游入口已执行；
  预期失败只能按未改动的官方退出码合同与精确失败身份判定。
- 快照版本:后续升级=重锚 master 快照 sha256 并升版本号。
- 其他账号 PR #14375 与本任务同源同 SHA；用户于 2026-10-04 明确要求
  保留本任务独立推进，不修改、关闭或领取他队任务。

## 上游测试用例统计
- 上游：11 个完整用例，由 1 个官方回归入口执行；5 个正向 + 6 个预期失败。
- 普通消费者：2 个用例/2 个断言。
- 鸿蒙特有：1 个原生定时器用例/4 个断言；不把通用消费者算作鸿蒙特有。
