# wxWidgets 3.3.3.2 适配笔记

## 当前状态

- 上游版本：3.3.3，官方 Release asset `471278068`
- 源码 SHA-256：`81b09d6dd9f1ed9301f8c55a968a488d0491f264dc2bab19a7e407ac67009482`
- 构建系统：CMake，静态库，禁用 GUI
- 适配范围：wxBase 无 GUI 变体；不宣称 wxCore 图形窗口栈已完成目标端适配
- 当前阶段：r86ar 已在 `10.62.148.108:2222` 完成唯一一次真实设备 W3 并 PASS。固定 HEAD 为 `8953ef46ca3954a08e2ad80d2e5efe68f90f6fde`，candidate tree 为 `4a4bff24d5b14ba6a71fe1bb24f31c467ce2bdc4`，pinned main 为 `493cadeeb3ef3b86c10990013b8e5df55ed8c727`。上游完整清单为 `399 PASS + 30 expected SKIP = 429/429 nonfailed`，CTest `1/1`，consumer `1/1`；WAL 12 个 receipt 全部提交，释放后 `ROOT_STATE=ABSENT` 且 `remote_process_state=ZERO`。r75/r85 的失败和 r86/r86b 的候选失败均保留为历史，不能复用或改写。

## W0-W2

wxWidgets 3.3.3.2 配方没有 Conan 前置依赖。当前 HEAD 为
`8953ef46ca3954a08e2ad80d2e5efe68f90f6fde`，本次 W3 固定的 pinned main 与
merge-base 均为 `493cadeeb3ef3b86c10990013b8e5df55ed8c727`。后续
`origin/main` 移动只记录为诊断，不重定义已固定的候选基线。r84 独立 W4 已因
当前元数据仍绑定 r77 和 0019 patch type 不合规而 FAIL，且未进入 SSH/W3；r85
修正这两项后重新生成 29 路径 candidate、freeze，独立 W4 r55 以
`P0/P1/P2/P3=0/0/0/0` 通过。r85 真机 W3 随后以 11 个 fixture-construction
异常真实失败。r86b 的最终 0020 已重新完成 20 补丁三引擎 replay，三棵树的
聚合 SHA-256 均为 `c4662aa951086e4fbaa9c6920a3f1c471b8db5cf7500fe13b52813571f62c968`；
后续必须完成 30 路径 candidate、fresh freeze、独立 W4 与一次全新 W3。配方、test_package、MANIFEST
和二十个补丁继续受结构、完整测试清单与无 OHOS 条件宏门禁约束。
r51 的 0006 文件名补丁已恢复为可严格 replay 的版本；`/tmp` 空路径 fallback
单独放入 0011，避免混合换行与上下文导致 Conan `patch_ng` 拒绝。r73 在 fresh
官方源码上使用 patch-ng 1.19.1、strip 1、fuzz=false 顺序 replay 0001-0016。
r74 在 0015 增加真实 CP950 输出缓冲区后，从 post-0015 preimage 重新绑定 0016
行号并达到 16/16。r74 证明普通非空缓冲区转换不足以覆盖 stream helper 的致命
路径；r75 因此用 `fork`/`waitpid` 隔离执行原 `TestDecoder`/`TestEncoder`，子进程
stdout/stderr 定向到 `/dev/null`，父进程只按 exit/signal 终态决定是否输出 reason-bound
skip。该实现只使用通用 POSIX 能力宏，不含 OHOS 条件编译宏，并已 fresh 16/16 replay。
r75 的独立 W4 r50 对输入
`128a23c4cbcb4d5e9d43031c68062469c6cfc112b344e58fc205f3cb14f28f52`
返回 P0/P1/P2/P3 全零；该结果只绑定历史 r75，不得用于 r76。
r76 已从官方 SHA-256 归档 fresh 解压，使用 patch-ng 1.19.1、strip 1、
`fuzz=false` 顺序重放 0001-0019；19/19 PASS，扫描 5269 个最终源码文件无
OHOS 条件宏。最终树聚合 SHA-256 为
`459f466e247259e94dc003725ab42ceb4ecc7a1cb951abba2f7b75d0d7a49766`。
但冻结 alternate index 的 `git diff --cached --check` 随后发现补丁文件中的空白
context 不符合外层仓库门禁，因此 r76 candidate、freeze 和后续证据全部失效；
r76 没有进入独立 W4、传输或设备 launch。

r77 从 r76 的顺序 postimage 重新生成 19 份边界感知补丁。patch-ng 1.19.1
19/19 与 GNU patch 2.7.6 `--fuzz=0` 19/19 均通过，重生 summary SHA-256 为
`da5893fd4ad3e3a971286376b7605fbae947074eafb932a617761ef88cf32f0b`，
补丁清单 SHA-256 为
`ec36a2cef7b31e2d8243e4d4651c6d5093307bbe994aadb40ed1add9bebbdc43`。
第三引擎在 create-new r8 中逐补丁执行 19 次
`git apply --check --whitespace=error-all` 和 19 次 `git apply`，38 个进程全部
RC0、stdout/stderr 均为空，每次启动前 CPU 为 12.64% 至 43.80% 且全机无其他
Git/rg。结果 SHA-256 为
`f493edf4fd8eb3933885db217a874194d3d5efbd628425053e431e635666399b`。
三棵结果树均为 9776 个文件，聚合 SHA-256 仍为
`459f466e247259e94dc003725ab42ceb4ecc7a1cb951abba2f7b75d0d7a49766`；
14 个受影响 postimage 与 r76 逐字节一致，5269 个源码文件及 19 份补丁中的
OHOS 条件宏命中均为 0。r6 因短函数 `h` 被 `Get-History` alias 遮蔽而缺少
逐进程记录；r7 在完成重放和 finalize 后又因 PS5 对 generic list 的 `@(...)`
转换抛出 `Argument types do not match`。两者仅保留为历史，r8 使用
`List<T>.ToArray()` 后才是正式 Git replay 证据。

## 平台修复

补丁使用 POSIX 或运行时能力语义：独立探测 `getservbyname_r` 签名、
识别 libc 内建 iconv、处理 musl 尾随百分号、拒绝无效 locale，并在
根目录不可枚举、`/tmp` 不可写、AF_UNIX、symlink、计时调度、locale 数据/排序
或 CP932、CP1252、ISO-8859-1、Fontmap、CP950、非 BMP UTF-16 编码能力缺失时保留真实测试结果并输出 warning。r76 进一步按当前 locale 的十进制符号、分组符号和分组规则门控 22 个 number-format case，并在 windows-1252 XML load 不可用时门控 `CDATA`、`PI`、`DetachRoot` 三个真实子事件。源码和补丁不含 OHOS 条件编译宏。

## 测试审计

Catch2 2.13.10 list mode 返回 255 是条目数编码。wxWidgets 3.3.3 的完整
清单为 429 个精确条目，大小写折叠后 423 个唯一名，`Format::c/hc/hs/lc/ls/s` 构成 6 组合法大小写折叠冲突；
有序清单加尾部 LF 的 SHA-256 为
`2214c00249801b8f0b2b1b7b72c6fdf6c00217d32da3a3b777c2d8afabe73ebe`。
CTest 注册项与 Catch2 内部 case 数是不同层次，runner 必须分别记录。
- 目标文件系统或运行时能力缺失只允许以
  `WX_EXPECTED_SKIP:id=...;path=...;reason=...` 标记的显式终态计数。
  r76 冻结 44 个 `(id,path,reason,case_id)` 允许事件、34 个真实顶层 case，
  四字段摘要为
  `70855349b10167b33ba26b7554072efee7624a08f24fb862d91a7c89dc03c9e9`。
  配方先验证每个 `case_id` 存在于 429 项清单，再分别统计实际 skip 事件和唯一
  skip case；能力存在时允许对应 marker 不出现。按 r75 的能力状态预计出现 42 个
  事件并映射到 33 个顶层 case，即 `396 PASS + 33 SKIP = 429 NONFAILED`；
  真机能力若变化则按实际 marker 如实计算，不能硬编码为 `395 + 34`。
  未知、重复、换行损坏或清单外映射都会失败关闭。

## 安全边界

没有伪造 W3、CI 或提交证据。r70 已消费一次 launch 并记录真实
`conan_rc=6`，原因是 `FromWCharTests` CP950 能力失败与非 BMP UTF-16 路径
SIGSEGV。r72 也已消费唯一一次 launch，记录 `conan_rc=1`、测试清单与 CTest
计数均为 0；编译器在 `mbconvtest.cpp` 的后续 `SECTION` 报
`expected unqualified-id`，并报告多余右花括号。r70/r72 的 terminal、日志和
输入哈希均保留为不可变历史证据，不得复用其 root；r73 本地冻结也因后续发现
0015 探测契约错误而失效且未进入 W4、传输或设备 launch。r74 的 terminal 记录
`conan_rc=6`、inventory_count=1、ctest_count=0、consumer_count=0、launch_count=1，
日志为 108345 bytes、SHA-256 `7785d1e6f6c32ce502269171a402b48be43b267ded945d8bbe3a04204de7a20c`；
不得重跑或复用 r74 root。r75 也已消费 `launch_count=1`，终态
`conan_rc=6`，Catch 为 `429 total / 406 passed / 23 failed`，assertions 为
`1161609 total / 1161496 passed / 113 failed`；201464-byte 日志 SHA-256 为
`d59a0ab188869b38c1c932e37f1def3680e871e7c44115d8c2bce1767da046af`。
r75 root 和 W4 r50 均只能作为历史证据。r76 也因补丁包装门禁失效且 launch_count=0，
不得复用其 alternate index、recipe tar、freeze 或 W4 输入。r84 的 candidate、freeze
和独立 W4 FAIL 也只保留为历史；它从未进入 SSH 或 W3。r85 已完成固定 main
候选、fresh freeze、独立 W4 和唯一一次 W3，但真实终态仍为 FAIL。
r6/r7 Git replay 记录器失败目录以及 r63-r85 的 predecessor 证据均不得复用或改写。
r85 terminal 为 `conan_rc=6`、`429 total / 418 passed / 11 failed`，199593-byte
日志 SHA-256 为
`628010e49b6d7161632e1488883149d05ec86699b873143622dc0e23a30a6a21`；其
远端 root、transfer、prepare、launch 与 terminal 只作不可变历史。r86b 只能使用
新的 run ID、远端 root、candidate、freeze、W4 和唯一一次 launch。
