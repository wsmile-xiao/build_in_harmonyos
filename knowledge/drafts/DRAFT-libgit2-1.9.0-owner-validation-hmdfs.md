# DRAFT-libgit2-1.9.0: libgit2 属主安全校验 × HMDFS

> 草稿（B 类知识库贡献候选）。关联任务：#libgit2-1.9.0-r01-pc4-30。
> 同根因族：E101（git CLI safe.directory，命令层）；本条是库 API 层。

## 错误现场

libgit2 test_package 消费者在 OHOS/HMDFS 上运行：

```
libgit2 version: 1.9.0
git_repository_init failed: repository path
  '/.../test_package/build/.../libgit2-test-repo' is not owned by current user
```

上游 util 套件同款：`path::core::validate_current_user_ownership` 失败（is_cur 0 != 1）。

## 根因

1. libgit2 1.7+ 提供 `GIT_OPT_SET_OWNER_VALIDATION`（默认开启）：仓库目录属主
   必须与当前 euid 一致，等价于 git 的 safe.directory 语义
2. OHOS 沙箱进程 euid ≠ HMDFS 目录属主（共享 uid），属性恒不匹配 → 误判拒绝
3. 这是**库 API 层**问题：E101/E497 只覆盖 git 命令层的 safe.directory 配置，
   对直接链接 libgit2 的消费者无效

## 方案

```c
git_libgit2_init();
git_libgit2_opts(GIT_OPT_SET_OWNER_VALIDATION, 0);   /* 关闭库层属主校验 */
git_repository_init(&repo, path, 0);
```

## 验证

- conan-verify G2 PASS（test_package 真实 API：version + repository_init）
- 鸿蒙专项测试 exit 0：blob → index → tree → commit 写回路，commit 50963e2d 回读一致

## 适用边界 / 反例

- 适用：HMDFS / 共享属主文件系统上消费 libgit2 的库/工具（libgit2-glib 等绑定库同适用）
- 反例：真实多用户主机、需要属主隔离的安全场景，**不应**关闭该校验

## 查重差异（相对 E101/E497）

- E101：git 命令 `fatal: detected dubious ownership` → gitconfig `safe.directory`；命令层
- E497：Git worktree 元数据 + separate-git-dir；Git 仓库层
- 本条：libgit2 库 API（GIT_OPT_SET_OWNER_VALIDATION=0）；库消费者层，修复面完全独立