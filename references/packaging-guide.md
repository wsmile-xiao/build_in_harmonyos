> 本文件从 SKILL.md v4.8 提取，详细内容供按需加载。

# 预编译包制作与归档收口

来源: SKILL.md Step 5, Step 5.5

---

## Step 5: 预编译分发包（⭐ verify PASS 后必须执行）

> **时机**：ohc-run.py verify-build PASS 之后（确保产物质量合格才打包）。
> **所有编译成功（status=success 或 partial）的软件都必须制作预编译包。**
> 只有 status=failed 才跳过。

### 触发条件

| 状态 | 是否必须打包 | 说明 |
|------|------------|------|
| `success` | ✅ **必须** | 编译通过 + 测试通过 + 补丁完整 |
| `partial` | ✅ **必须** | 编译通过但部分功能不可用（标注限制后仍可分发） |
| `failed` | ❌ 跳过 | 编译失败，无产物可打包 |

### 打包 10 步流程

按 `knowledge/operations/packaging.md` 10 步标准流程：

```
Step 1:  从 $TEST_PREFIX 收集已安装文件（已在隔离目录中）
Step 2:  清理缓存和非必要文件
Step 3:  符号链接替换（wrapper/cp）
Step 4:  收集外部依赖库到 lib/external/
Step 5:  设置 RPATH（$ORIGIN 相对路径）
Step 6:  Strip Debug 符号 + 分离保存
Step 7:  ELF 签名（adhoc self-sign）
Step 8:  统一修复执行权限（必做！）
Step 9:  创建 install.sh（单独托管 gitcode，不打包进 tar.gz）
Step 10: 打包干净 tar.gz + 安装验证
```

### 交付物规格（2 个 tar.gz + 1 个 install.sh）

```
archives/{首字母}/{软件名}/
├── EXCLUDE_LIST              # 🟡 可选：打包排除列表（有问题的命令/库）
├── install.sh                                # 安装脚本（软件级，参数化: sh -s -- <ver>）
├── RELEASENOTE.md                             # 发布说明（软件级）
│
└── {版本}/packaging/
    ├── {name}-{ver}-ohos-aarch64.tar.gz        # Release 制品（干净二进制，已 strip）
    └── {name}-{ver}-ohos-aarch64-debug.tar.gz   # Debug 符号包（必须）
```

用户安装：`curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/{name}/install.sh | sh -s -- {ver}`

### 打包排除列表（EXCLUDE_LIST）

> **某些命令虽然编译通过，但在鸿蒙上实际使用有问题或影响系统，且无法通过源码修复规避。**
> **这些命令必须在打包阶段移除，不进入分发的 tar.gz。**
>
> **⚠️ 排除流程（v4.4+，实测驱动）：**
> 1. **ohc-run.py build Step 8** 对每个二进制执行实际功能测试（--version + 深度调用测试）
> 2. 失败的命令自动加入 `archives/{name}/EXCLUDE_LIST`
> 3. **ohc-run.py package Step 2e** 读取 EXCLUDE_LIST 并从打包产物中物理删除
> 4. 如误排除：从 EXCLUDE_LIST 删除对应行并重新 package
>
> **禁止预定义排除列表**——必须基于实测失败数据。

**文件位置**：
- 软件级（所有版本共享）：`archives/{首字母}/{软件名}/EXCLUDE_LIST`
- 版本级（覆盖软件级）：`archives/{首字母}/{软件名}/{版本}/EXCLUDE_LIST`

**格式**（每行一个 basename，`#` 开头为注释）：
```bash
# EXCLUDE_LIST — 打包时自动移除的文件
# 需要 setuid/chroot 等 syscall (E051)
chroot
# 依赖 /proc/self/fd (E052)
stdbuf
# 可能替换系统关键命令导致问题
kill
```

**何时创建**：Staging 验证(§2.8)中发现某命令 crash/无输出 → 加入排除列表

**执行时机**：ohc-run.py package **Step 2e**（复制文件后、符号链接处理前），从 PKGDIR 中物理删除匹配文件

---

## Step 5.5: 归档收口（⭐ 最终完成前必须执行）

> **时机**：Step 5（预编译包制作）完成之后、`attemptCompletion(success)` 之前。
> **目的**：确保归档目录干净、完整、一致，可以安全关闭。

### 为什么需要独立的收口步骤？

```
整个编译过程中产生的文件:
  ✅ 正式产物: manifest.yaml / PROGRESS.md / README.md / patches/*.patch
  ✅ 正式产物: packaging/*.tar.gz / packaging/install.sh
  ⚠️ 临时文件: *.tmp (refresh-patch 中断残留) / .bak (编辑备份)
  ⚠️ 过时数据: 旧 test-report.md (重编译前) / 旧 debug 符号
  ❌ 不一致: PROGRESS 写 success 但 manifest 写 compiling

问题: ohc-run.py init-archive 策略是"保留一切"（为了复用旧信息）
结果: 重编译后目录里混合了新旧数据，需要统一清理+校验
```

### 执行方式

```bash
${SKILL_ROOT}/scripts/ohc-run.py finalize-archive <软件名> <版本>
```

### 内部执行的 4 个阶段

| 阶段 | 内容 | 失败处理 |
|------|------|---------|
| **[1] 清理** | 删除 `*.tmp`、`.bak`、debug/ 残留文件 | 无则跳过 |
| **[2] 必填校验** | 6 个必填项存在性 + 内容非空模板 + packaging 交付物完整性 | 缺失 → exit 2 |
| **[3] 一致性检查** | manifest vs PROGRESS 状态一致 / 补丁数量匹配 / 对话记录存在 | 警告但不阻塞 |
| **[4] 最终报告** | 输出汇总：补丁数/报告数/打包数/问题数 | 通过 → 可安全关闭 |

### 必填文件清单

| 文件 | 最小行数 | 说明 |
|------|---------|------|
| `manifest.yaml` | >10 行 | 元数据（init-archive 有内容则保留） |
| `README.md` | >10 行 | 编译指导 + 适配原因（版本级） |
| `PROGRESS.md` | >15 行 | 进展 + 对话记录（断点续传，版本级） |
| `RELEASENOTE.md` | >15 行 | 发布说明（软件级，finalize-archive 自动生成） |
| `install.sh` | 文件存在 | 安装脚本（软件级，参数化: sh -s -- <ver>） |
| `patches/` | 目录存在 | 补丁目录 |
| `reports/` | 目录存在 | 报告目录 |
| `packaging/*-ohos-aarch64.tar.gz` | 文件存在 | release 包（success/partial 时） |
| `packaging/*-debug.tar.gz` | 文件存在 | debug 包（必须） |
| `install.sh`（软件级） | 文件存在 | 安装脚本（参数化） |

### 一致性检查项

| 检查项 | 方法 | 允许差异 |
|--------|------|---------|
| 状态一致性 | grep status: manifest vs PROGRESS | 不允许 |
| 补丁数量 | manifest patches_applied vs 磁盘 *.patch 数 | 不允许 |
| 对话记录 | PROGRESS.md 中 `### 对话 #N` 出现次数 | 至少 1 轮 |

### 与 ohc-run.py init-archive 的分工

| 脚本 | 时机 | 策略 | 删除文件？ |
|------|------|------|----------|
| `ohc-run.py init-archive` | 编译开始前 | **保留**已有内容，只创建缺失骨架 | 否（除非 --clean） |
| `ohc-run.py finalize-archive` | 全部完成后 | 清理垃圾 + 校验 + 报告 | 是（*.tmp/.bak/不一致） |

### --clean 模式（完全重置）

当需要**丢弃所有旧补丁和打包产物重新开始**时：

```bash
# 方式 A: init 时指定 --clean
${SKILL_ROOT}/scripts/ohc-run.py init-build <软件名> <版本> --clean

# 方式 B: 手动清空后重新 init
rm -rf archives/<首字母>/<软件名>/<版本>/patches/*
rm -rf archives/<首字母>/<软件名>/<版本>/packaging/*
${SKILL_ROOT}/scripts/ohc-run.py init-build <软件名> <version>
```
