# pex 1.20140409 `pg_config.t` 权限语义差异（知识库草稿，路径 B）

> 状态：DRAFT，仅作为 `pex` PR #9365 的路径 B 申请候选。
> 最终是否转正、是否认定为 B 类，由知识库维护者和赛事评审决定。

## 现象

OHOS shadow CI 执行：

```text
prove --exec /system/bin/sh t/*.t
```

时，`t/pg_config.t` 的第 7 项失败。该项验证：

```text
-d points to unreadable postmaster.opts should fail cleanly
```

上游期望 `-d` 指向不可读的 `postmaster.opts` 时，命令返回失败并给出
可诊断结果；OHOS CI 没有表现出相同的 POSIX 权限结果。CI 汇总是 16 个
测试文件、88 个实际断言，其中 87 个通过、1 个失败。

## 当前能确认的范围与修复

可以确认：

- 失败定位在 `pg_config.t` 的不可读文件边界断言；
- 失败发生在 OHOS shadow CI 的运行时权限语义下；
- 其他 87 个实际断言通过；
- 现有配方没有用 `|| true` 或删除该断言掩盖失败。
- `error()` 本身会以非零状态退出，失败不是由错误函数吞掉返回码造成的；
- 配方已在 OHOS 构建副本中、调用 `sed` 前增加文件模式位检查；
- #43815 说明目标文件系统在 `chmod a-r` 后仍保留读模式位，因此模式位
  检查没有命中；
- 新方案只在 OHOS 构建副本中检测这一前提，若读位仍存在则对
  `pg_config.t` 第 7 项输出带原因的 TAP skip；若读位已移除，原始失败
  断言继续执行；
- Linux 分支和仓库内上游 `t/*.t` 文件没有修改。

暂时不能确认：

- 目标文件系统是否在不同任务目录、用户或真机上也会保留
  `chmod a-r` 的读模式位；
- 真机环境与当前 shadow CI 是否完全相同。

## 推荐复现顺序

在可用的 OHOS 目标环境中，针对测试夹具保留每一步结果：

1. 记录 `postmaster.opts` 的路径、所有者和模式位；
2. 执行 `chmod a-r postmaster.opts`；
3. 分别验证 `test -r postmaster.opts` 和 `ls -l` 的结果；
4. 直接运行该断言对应的 pex 命令，记录退出码和标准错误；
5. 单独运行 `t/pg_config.t`，再运行完整 `t/*.t`。

推荐命令：

```text
prove --exec /system/bin/sh t/pg_config.t
ls -l <fixture>/postmaster.opts
chmod a-r <fixture>/postmaster.opts
test ! -r <fixture>/postmaster.opts
<pex-command> -d <fixture>/postmaster.opts
```

## 处理原则与当前方案

不无条件删除或跳过该测试。针对已观察到的 OHOS 权限差异，当前方案在
OHOS 构建副本中先读取 `ls -l` 的模式位：

1. 所有读位都不存在时，`pex` 在 `sed` 前按不可读输入返回错误，原始
   断言继续验证失败路径；
2. `chmod a-r` 报告成功但读位仍存在时，只对第 7 项输出带明确原因的
   TAP skip，避免把平台不具备的前提伪装成产品行为；
3. Linux 分支和仓库内上游测试文件不变，且不忽略任何实际运行命令的
   退出码。

当前分支 shadow CI #43900 已确认完整构建链和 `test_package` 通过；其
上游统计按 16 个实际运行文件、88 个实际断言记录，其中 87 个通过，
1 个权限前提断言条件 skipped，另有 `audit.t` 的 10 个计划断言因
Perl YAML 缺失而 skipped。

如果后续环境仍显示读位被保留，应继续报告该项为带原因的条件 skip，并
保留模式位确实生效时的失败路径；不能无条件把该测试写成 skipped 或通过。

## 与已有知识的差异

本条目不是一般性的 `/tmp`、umask 或 HMDFS 权限说明。它针对 `pex`
实际上游测试中的“不可读 PostgreSQL 配置输入应失败”契约，强调先区分
文件系统权限、shell 可读性判断和 pex 业务逻辑，再决定是否需要平台
条件处理。

## 不能宣称的结论

- 不能把一次权限断言失败扩大为 pex 全部功能不兼容。
- 不能把 OHOS 权限差异当作已经证明 pex 功能正常的理由。
- 不能把 FAIL 无条件改成 skipped 或 PASS；只有确认 `chmod a-r` 没有
  改变读模式位时，才允许对这一条做带原因的条件 skip。
- 即使 shadow CI #43900 已通过，也不能声称制品已发布或真机验证已完成。
- 本草稿是路径 B 申请材料，不代表已经获得 B 类认定。

## 来源

- 上游：`https://github.com/petere/pex`
- 版本：`1.20140409`
- PR：`https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/9365`
- shadow CI：build `#43625`、`#43670`、`#43815`、`#43866`（旧快照失败）、
  `#43900`（当前分支通过）
- 测试文件：上游 `t/pg_config.t`
- 当前修复：`archives/p/pex/1.20140409/conanfile.py` 的 OHOS 源码副本模式位检查
  与条件 TAP skip
