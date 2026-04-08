# 📋 Build-in-HarmonyOS — 快速参考卡

> **用途**: AI 编译三方库时的操作清单。详细说明见 [SKILL.md](./SKILL.md)
> **版本**: v4.0.0 | **更新**: 2026-04-08

---

## 一、五步走流程

| 步骤 | 脚本 | 输出 |
|------|------|------|
| **Step 1** 初始化 | `init-build.sh <name> [<ver>] [--url=URL]` | `.build-context-*` |
| **Step 2** 编译 | AI 执行 configure+make+install（唯一需 AI 判断的步骤） | 二进制产物 |
| **Step 2.5** 独立测试 | 干净 tarball + 补丁 → 独立前缀 → 回归测试 | 测试结果 |
| **Step 3** 收尾 | `finish-build.sh <name> <ver> success\|partial\|failed` | 补丁+归档 |
| **Step 4** 质量门禁 | `verify-build.sh <name> <ver>` （G1-G4 四道门禁） | quality-report |
| **Step 5** 预编译包 | packaging.md 10 步流程（verify PASS 后必须执行） | tar.gz + install.sh |
| **Step 5.5** 归档收口 | `finalize-archive.sh <name> <ver>` | 校验报告 |

## 二、十条铁律 (R1-R10)

| # | 铁律 | 要点 |
|---|------|------|
| R1 | **参数最少化** | 理想只需 `--prefix=$DEFAULT_PREFIX`，额外参数 = 技术债务 |
| R2 | **Phase 3 不生成 .patch** | 只改源码 + 记录到 PROGRESS.md |
| R3 | **补丁只用 refresh-patch.sh** | `--auto` 唯一入口 |
| R4 | **危险库必须静态编译** | ncurses `--without-shared`（致命） |
| R5 | **软链接验证可执行 + 禁止 ln -sf** | `rm -f && ln -s` 或 wrapper 脚本 |
| R6 | **禁止修改生成文件** | 只改 configure.ac/CMakeLists.txt/*.c/*.h |
| R7 | **安全弹窗先触发再测试** | make install 后扫 bin 触发弹窗 |
| R8 | **源码修改"四不"准则** | `#ifdef __OHOS__` 守卫 / 保持上游风格 |
| R9 | **质量门禁 FAIL 禁止标 success** | verify 非零 → partial 或 failed |
| R10 | **临时文件用 $TMPDIR** | 鸿蒙 /tmp 只读（E002） |

## 三、目录结构

```
build_in_harmonyos/
├── SKILL.md / REFERENCE_CARD.md / KNOW_YOUR_WHY.md
├── scripts/   (init-build / finish-build / refresh-patch / verify-build / finalize-archive ...)
├── knowledge/ (error-patterns.md / build-systems.md / environment.md / packaging.md)
├── templates/ / archives/ (a-z/) / software-registry.yaml
```

## 四、常用命令速查

```bash
./scripts/init-build.sh wget 2.1.0              # 新编译
./scripts/init-build.sh libnew 1.0 --url=URL     # 新软件
./scripts/init-build.sh --resume                 # 恢复中断
./scripts/refresh-patch.sh wget 2.1.0 --auto     # 补丁管线
./scripts/finish-build.sh wget 2.1.0 success     # 收尾
./scripts/verify-build.sh wget 2.1.0             # 质量门禁
./scripts/finalize-archive.sh wget 2.1.0         # 归档收口
```

## 五、AI 执行风格（toybox ash 环境）

> 复杂 shell 脚本是地雷区。保持简单。

| ✅ 推荐 | ❌ 禁止 |
|---------|--------|
| 每条测试独立 `[ ] && echo OK \|\| echo FAIL` | 单次写 >30 行复杂脚本 |
| `$TMPDIR/$HOME/tmp` 替代 `/tmp` | heredoc / 多变量循环嵌套 |
| `grep -F` 固定字符串匹配 | grep 匹配含元字符输出 |
| autotools timeout ≥600s | 频繁中断重启 configure |

## 六、Layer 分层 & 质量门禁

| Layer | 类型 | 示例 | AI 决策？ |
|-------|------|------|-----------|
| L1 全自动 | init-build, finish-build, verify, finalize | ❌ 无 |
| L2 半自动 | finish（状态选择） | ⚠️ 极少 |
| L3 辅助工具 | search-url, gen-summary | ✅ 主导 |

**G1-G4 门禁**: 二进制完整性 → 功能可用性 → 可移植性(RPATH+$ORIGIN) → 档案完整性
→ PASS 可分发 / FAIL-Gx 修复后重验

## 七、错误快速定位

| 关键词 | 编号 | 原因 |
|--------|------|------|
| `relocation truncated` | E005 | 缺 `-mcmodel=medium` |
| `cannot find -l` / `undefined reference` | E007/E008 | 缺依赖或未 pkg-config |
| `GLIBC_.* not found` | E010 | glibc 泄漏 |
| `/tmp: Read-only` | E002 | 硬编码 /tmp |
| `fork: Function not implemented` | E055 | posix_spawn 差异 |
| `symlink: File exists` | HMDFS | 用 rm -f + ln -s |

> 完整 67 条见 `knowledge/error-patterns.md`

## 八、阶段转换检查清单

### → Step 2（编译前）
- [ ] context 已 source，`echo $DEFAULT_PREFIX` 有值
- [ ] `check-env.sh` 无 ERROR

### → Step 3（finish 前）
- [ ] make install 成功 + make check 完成 + 弹窗已确认
- [ ] 源码修改已记录到 PROGRESS.md

### → Step 4（verify 前）
- [ ] Step 2.5 独立验证通过 + PROGRESS.md 检查点已填

### → Step 5.5（完成前）
- [ ] verify PASS + 预编译包完成 + finalize-archive 通过

---

*详细规范见 SKILL.md | 知识分层原则见 KNOW_YOUR_WHY.md*
