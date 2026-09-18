# kqwait 1.0.3 适配笔记

## 编译环境
- 构建系统: makefile（上游单行 clang -Wall kqwait.c dirinfo.c -o kqwait，conanfile 等价直呼 cc）
- 编译日期: 2026-09-15
- 编译器: clang 15.0.4（aarch64-ohos）
- 状态: built

## 平台能力判断（W0 结论）
| 检查项 | 结果 |
|--------|------|
| 核心功能是否 kqueue/kevent | **是** —— kqwait 唯一功能就是 EVFILT_VNODE 等待 |
| sys/event.h 存在性 | sysroot（`/usr/local/sysroot/usr/include/`）**无** sys/event.h |
| libc 符号 | libc.so 1595 个动态符号中**无** kqueue/kevent/EV_SET |
| 内核 syscall | HongMeng 内核**不提供** kqueue（BSD 私有事件机制） |
| 语义等价物 | **inotify 完整可用**：探针 S1–S9 九类边沿事件全部实测通过（含 IN_MOVE_SELF、IN_DELETE_SELF） |
| 结论 | 非构建检测问题，是平台 API 缺失；但存在真实等价实现 → **inotify 重写**（同 entr 5.8 先例） |

## 语义映射（补丁核心）
| kqueue | inotify | 分支去向 |
|--------|---------|----------|
| NOTE_WRITE | IN_MODIFY\|IN_CREATE\|IN_DELETE\|IN_MOVED_FROM\|IN_MOVED_TO | 文件→打印路径；目录→dirinfo diff |
| NOTE_DELETE | **IN_DELETE_SELF**（非 IN_DELETE！） | 短路输出 `- path` |
| NOTE_RENAME | IN_MOVE_SELF\|IN_MOVED_FROM\|IN_MOVED_TO | 同 NOTE_WRITE 去向 |

**关键陷阱**（调试中发现）：初版把 `IN_DELETE`（目录内子项被删）误映射为 `NOTE_DELETE` 短路，导致"目录内删文件"输出 `- dir/` 而非上游期望的 `- dir/file`。kqueue 的 NOTE_DELETE 指 **被 watch 的路径自身被删**，inotify 对应 IN_DELETE_SELF；子项删除在 kqueue 下表现为目录的 NOTE_WRITE，走 dirinfo 对称差分支。

## 编译步骤

1. `conan create archives/k/kqwait/1.0.3 --profile ohos-aarch64-local`
2. conanfile source(): 官方 tag tarball + sha256 校验
3. build(): 应用移植补丁 → 覆写 version.h（上游 tag 打包失误）→ `clang -std=c99 -Wall -O2 kqwait.c dirinfo.c`
4. build(): `sh t/run_upstream_tests.sh` — 15 项上游断言（**15/15 PASS**，OHOS aarch64 真机）
5. test_package: 消费者冒烟 + 功能测试 + OHOS 专项（目录 create/delete diff 断言）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 移植版运行即打印 usage 退出 | 上游 `char ch; while((ch=getopt(...)) != -1)`：aarch64 上 char 默认 unsigned，`(char)-1 == 255 != -1` 无限循环 | 补丁内改 `int ch`（上游真实 bug，BSD 平台 char 默认 signed 未暴露） |
| 2 | 目录内删文件输出 `- dir/` 而非 `- dir/file` | 初版将 inotify IN_DELETE 误映射为 kqueue NOTE_DELETE 短路 | 短路条件改为 IN_DELETE_SELF；IN_DELETE 属子项事件，走 dirinfo diff |
| 3 | 上游测试无法运行 | t/kqwait.pl 依赖 perl IPC::Run（本机不可安装） | SPEC 3.3 豁免 + 断言 1:1 移植为 POSIX sh（t/run_upstream_tests.sh），5 场景 × 3 断言 = 15 项全过 |
| 4 | tag 内 version.h 为 v1.0.2-1-g0425-dirty | 上游 tag 打包失误（git describe 产物入库） | build() 覆写 version.h 为 v1.0.3 |
| 5 | /tmp 不可写 | OHOS HMDFS 限制 | 全部在 conan build 目录内操作 |

## 源码修改

1. **patches/0001-kqwait-ohos-inotify-port.patch**（235 行）：
   - `sys/event.h` → `sys/inotify.h`，kqueue/kevent/EV_SET → inotify_init/add_watch/read
   - 每 watch 一个 wd，wd→target 索引表（替代 ev[i].udata）
   - 事件解析循环取第一个触发的 watch（对应上游只看 ev[0]）
   - `char ch` → `int ch`（getopt unsigned-char 修复）
   - CLI/输出/退出码逻辑保持逐字节一致

## 验证结果（OHOS aarch64 真机，HongMeng 1.12.0）

```
$ sh t/run_upstream_tests.sh
ok - should return (returns filename on write)
ok - produces no output to stderr (returns filename on write)
ok - returns filename on write
...（15 项全部 ok）
# tests=15 failed=0
ALL PASS
```

test_package（消费者 + OHOS 专项）：
- `-h`/`-v` 冒烟 ✓
- 单文件写等待：打印 watched 路径，rc=0，stderr 空 ✓
- 目录 delete：输出 `- <dir>/victim.txt`（dirinfo diff）✓
- 目录 create：输出 `+ <dir>/created.txt` ✓

## 交付物

| 文件 | 说明 |
|------|------|
| kqwait/1.0.3/bin/kqwait | CLI 工具（静态链接 libc 无第三方依赖） |

## 注意事项
- 上游 2013 年后无维护；BSD 系统上原版仍可用，本移植不改变上游仓库
- `IN_MOVE_SELF`（watch 目录被重命名）后 inotify watch 失效（wd 收 IN_IGNORED），与 kqueue NOTE_RENAME 一次触发即退出行为一致（工具打印后即退出，无长驻场景）
- 本工具为单事件等待（打印首个事件即退出），非长驻守护，语义边界清晰

## 最终状态

编译结束。status: closed。

- conan create（ohos-aarch64-local，两次干净重建）：**全绿**
- 上游断言（移植执行）：**15/15 PASS**
- test_package（消费者 + OHOS 专项）：**PASS**
- 质量门禁：preflight/junk 均过（JC 失败项均为仓库预存状态，非本次引入）；knowledge_check KC1–KC5 **pass**（540 条目）
- 知识库扩展：DRAFT-8959-kqwait-1.0.3-kqueue-to-inotify-faithful-rewrite（kv + md，预审三态: review-similar → E399，待人工晋升）
