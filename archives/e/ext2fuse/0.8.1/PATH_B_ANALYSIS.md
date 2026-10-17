# ext2fuse 0.8.1 路径 B / B 类难度候选分析

更新日期：2026-09-13

## 结论

- 适配状态：OHOS armv8 编译、打包和 Conan `test_package` 已通过；上游
  `pjd-fstest` 已完整盘点并在真机上尝试前置步骤。
- 申请方向：路径 B / B 类知识库扩展候选。
- 认定边界：本文只整理可复用知识和真实验证证据，不宣称已经获得 B 类认定；
  最终分类、分值和是否纳入高难度库以维护者及赛事评审结论为准。
- 上游测试状态：发现 184 个 `.t` 文件，新真机普通 HMDFS 目录直跑 184 个，
  文件级 111 通过、73 失败、0 阻塞，并得到 1115 个 `ok` 和 833 个 `not ok`
  TAP 断言。由于该结果不是官方 `prove` runner，也不在 ext2/FUSE 挂载点内，
  官方 `prove` + ext2/FUSE 挂载闭环仍单独记录为 blocked；`prove/perl` 未安装，
  ext2 mount 返回 `bad /etc/fstab`，`/dev/fuse` 读写均为 `Permission denied`。

## 为什么不是普通“改配方”

ext2fuse 0.8.1 是一个老式 C 语言用户态文件系统程序。它的适配同时跨越
源码 API、内嵌静态库、现代 Clang 语义、Autotools 生成系统、HMDFS 文件系统
限制和特权运行时能力。最终解决的不是一个孤立编译错误，而是一条从依赖
审计到真实目标环境验证的组合问题链：

1. 上游使用 FUSE 2 低层 channel API，而目标依赖为 libfuse 3；
2. `fuse_mount`、session 生命周期、回调参数和目录项编码需要整体迁移；
3. 内嵌 ext2fs 的 `extern __inline__` 与 `inline.c` 在 OHOS Clang 下产生重复符号；
4. Autotools 在 HMDFS 上受到 `/tmp`、umask、脚本执行、生成文件重建和 jobserver
   限制；
5. 本地 Git patch 通过不足以证明 Conan `patch_ng` 能在真实解压快照中应用；
6. CLI 可执行性和 FUSE 内核挂载能力受不同权限条件控制，必须拆分测试。

这组问题具有跨项目迁移价值，适用于其他用户态文件系统、老式 Autotools
项目和带内嵌静态库的 OHOS C/C++ 软件。

## 可复用知识草稿

| 草稿 | 知识主题 | 新增价值 |
|---|---|---|
| `knowledge/drafts/E6339-draft-11A1.{md,kv}` | FUSE 2 到 FUSE 3 的低层 session、回调和目录项迁移 | 将“换库名”提升为协议/API/生命周期三层迁移清单 |
| `knowledge/drafts/E6340-draft-4C48.{md,kv}` | 旧式 `extern inline` 与 `inline.c` 的 OHOS Clang 重复符号 | 用 `nm` 追踪符号来源，使用项目开关 `NO_INLINE_FUNCS`，区分于 `-fcommon` 和内核头冲突 |
| `knowledge/drafts/E6341-draft-4C48.{md,kv}` | HMDFS 上生成式 Autotools 的组合式稳定构建 | 把 shell、TMPDIR、umask、生成器时间戳、重生成和 jobserver 作为一个配方模式 |
| `knowledge/drafts/E6342-draft-4C48.{md,kv}` | CLI consumer test 与真实 FUSE mount test 分层 | 保护上游退出码契约，避免把 `/dev/fuse` 权限限制伪装成包通过 |
| `knowledge/drafts/E6343-draft-202B.{md,kv}` | Conan `patch_ng` 与本地 Git patch 的一致性验证 | 用同一源码归档、前序补丁和干净快照解释“本地通过、Shadow 失败” |

这些条目会在草稿目录中保持 `draft: true`，不修改正式索引，也不把普通
适配记录冒充已转正知识。预审结果中，E6339/E6342 建议新建；E6340、
E6341、E6343 分别与已有条目相似，但草稿已记录根因、适用范围和差异：

- E6340 与 E163 都出现 duplicate symbol，但 E163 是 OHOS 内核头定义冲突，
  E6340 是项目 inline 语义冲突；
- E6341 与 E011/E114/E129/E223 都涉及 HMDFS 临时目录，但 E6341 关注的是
  Autotools 生成文件生命周期与构建执行链的组合策略；
- E6343 与 E515/E526 都涉及 Conan 补丁，但 E6343 关注的是实际 patch engine、
  源码快照和前序补丁顺序的等价验证。

## 失败到成功证据链

| 阶段 | 观察 | 判断 | 处理 |
|---|---|---|---|
| W0 | `libfuse/3.18.2` 已发布，构建工具包可查询 | 依赖链可闭合，不拆入 e2fsprogs | 配方只声明 libfuse 和构建工具依赖 |
| W1 | 上游使用 FUSE 2 API，源码包带 Autotools 生成文件 | 需要源码 API 迁移和 HMDFS 构建策略 | 增加 FUSE3 与 OHOS 补丁 |
| Shadow CI 第 1、2 轮 | 0006 hunk 在编译前无法应用 | 补丁上下文/偏移与 Conan 实际源码快照不一致 | 用 `patch_ng` 对干净源码按顺序验证并修正 |
| Shadow CI 第 3 轮 | `ld.lld duplicate symbol`，符号来自业务对象和 ext2fs 静态对象 | 旧式 inline 语义与 `inline.c` 外部实现冲突 | OHOS `CPPFLAGS` 加 `-DNO_INLINE_FUNCS` |
| 最终 Shadow CI | `conan create`、安装、`test_package`、L0/L1/L4/L5 通过 | 包的目标构建和消费者契约成立 | 保留真实日志在任务目录，提交摘要证据 |
| 真机上游测试前置 | 新真机 SSH 成功；184 个 `.t` 已盘点；`fstest` fallback 编译、镜像创建和 184 个脚本逐个启动均完成 | 官方 `make` 硬编码 gcc，`prove/perl` 缺失，mount 与 `/dev/fuse` 受设备能力阻塞；普通 HMDFS 直跑含 111 个文件通过、73 个文件失败、1115 个 ok、833 个 not ok 断言 | 普通 HMDFS 直跑计入上游脚本执行台账；官方 prove/ext2/FUSE 挂载闭环仍单独记 blocked，不冒充真实挂载通过 |

## 验证结果

```text
OHOS target: aarch64 / armv8
Conan create: pass
Package contents: bin/ext2fuse, README, README_for_Solaris
test_package: PASS: ext2fuse executable and argument parsing
upstream test files: 184 discovered, 184 executed, 111 passed, 73 failed, 0 blocked on ordinary HMDFS shell run
upstream prerequisites: fstest fallback compile pass; ext2 image creation pass; 184 shell scripts started on device
upstream blockers for official prove/ext2/FUSE mount: prove/perl absent; mount returned bad /etc/fstab; /dev/fuse Permission denied
manual shell probe: 184/184 scripts started; 1115 ok and 833 not ok TAP assertions on ordinary HMDFS; not counted as ext2/FUSE mount validation
L0: pass
L1: pass
L2: non-blocking warning/skip because upstream --version/--help return 9
L4: pass
L5: pass
Local Python syntax: pass
Local patch_ng sequence: pass
git diff --check: pass
```

## 评审建议

建议按“路径 A 基础适配 + 路径 B 可复用知识扩展”审查本包，不把未执行的真实
FUSE 挂载写成通过，也不把已有的 HMDFS 通用条目重复申报。路径 B 的主要
贡献点是：

- 把 FUSE 3 API 迁移拆成可执行的协议/生命周期检查表；
- 给出旧式 C inline 与现代 OHOS Clang 链接冲突的符号级诊断方法；
- 给出可复用的 HMDFS Autotools 配方组合策略；
- 建立无特权 consumer test 与特权 mount test 的证据边界；
- 证明 Conan patch engine 必须在真实源码快照上验证，并保留失败到成功的复跑链。

后续若获得授权的 `/dev/fuse` 和可丢弃 ext2 镜像，可追加只读挂载、目录枚举、
文件读写和卸载测试；这将增强运行时证据，但不改变上述知识草稿的适用范围。
