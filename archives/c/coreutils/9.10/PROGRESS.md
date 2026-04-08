# coreutils 9.10 — 编译进度

> 档案创建时间: 2026-04-08 00:00:00
> 最后更新: 2026-04-09 00:35 (v10: package.sh zsh 迁移 + 正确打包)
> 当前会话 ID: coreutils-9.10-final
> 状态: success#final
> status: success#final

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | coreutils |
| 版本 | 9.10 |
| 状态 | ✅ 成功（排除12个平台受限命令后） |
| 构建系统 | autotools (tar.xz) |
| 目标平台 | aarch64-unknown-linux-ohos |
| 打包产物 | coreutils-9.10-ohos-aarch64.tar.gz (8.9MB, 88个二进制) |

## 二、编译阶段

### Phase 1: 环境准备 ✅
- [x] init-build.sh 完成 / 源码下载解压

### Phase 2: 编译 ✅
- [x] configure 完成 (~13.6min, exit 0)
- [x] make -j1 编译完成 (exit 0)
- [x] make install 到 $TEST_PREFIX (101个二进制)

### Phase 2.5: Staging 验证 ✅
- [x] 3个补丁全部应用成功
- [x] 功能回归测试: 82/83 --version 通过 (test 命令无--version属正常POSIX行为)

### Phase 3: 测试验证 ✅
- [x] make check 全量执行 (~23min, 卡死后终止)
  - 结果: 76 PASS / 18 FAIL / 30 SKIP / 7 ERROR
- [x] 失败分类分析完成:
  - **类别 A (12个排除命令)**: chgrp(3)+chmod(1)+rm(7)=11FAIL → 打包后不存在
  - **类别 B (非排除命令)**:
    - help/version → 测试了 ln/readlink/whoami (环境问题)
    - mktemp → E046 stat 权限不准 (平台限制)
    - **od trad-dot** → **od.c 缺少 __OHOS__ 守卫 (已修复!)**
    - tail inotify → E051 kill 权限不足 (平台限制)
    - wc files0-from/wc-parallel → E052 fd 问题 (平台限制)
- [x] od.c 修复验证: trad-dot1/trad-dot512 均 FAIL→PASS

### Phase 4: 预编译包制作 ✅
- [x] EXCLUDE_LIST 创建 (排除12个SELinux受限命令)
- [x] 打包完成: 8.9MB, 88个二进制, 12个危险命令全部确认不在包中

### Phase 5: 归档收尾 ✅
- [x] 补丁 0003 生成 (od.c fstat 修复)
- [x] manifest.yaml / README.md / PROGRESS.md 更新

## 三、补丁清单
| # | 文件 | 用途 | 状态 |
|---|------|------|------|
| 0001 | config.guess + lib/freadahead.c | HarmonyOS 系统检测支持 | ✅ 已应用 |
| 0002 | cat/dd/head/sort/tail.c | fstat/lseek EACCES 降级处理 | ✅ 已应用 |
| 0003 | od.c | skip() 函数 fstat EACCES 降级处理 (补丁2遗漏) | ✅ 已应用+已验证 |

## 四、EXCLUDE_LIST（12个不打包的命令）
| 命令 | 根因 | 替代方案 |
|------|------|---------|
| ls, rm, cp, mv | 软链接 lstat EACCES | toybox |
| stat, chmod, chown, chgrp | 元数据修改 EACCES | toybox |
| readlink, ln, link, unlink, realpath | 链接操作 EACCES/EPERM | toybox |

根因: GNU 二进制运行在 u:object_r:hmdfs:s0 SELinux 上下文，
无法像 toybox_exec 上下文那样操作软链接。

## 五、预编译包交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| coreutils-9.10-ohos-aarch64.tar.gz | 8.9MB | 主包 (88个二进制, 已排除12个) |

## 六、测试结果总结
| 指标 | 数值 |
|------|------|
| 总二进制数 | 101 (编译) → 88 (打包分发) |
| --version 通过率 | 82/83 (99%) |
| make check PASS | 76 |
| make check FAIL | 18 (11个属排除命令 + 5个平台限制 + 2个已修复) |
| 需要源码修复 | 1个 (od.c, 已修复) |
| 平台限制无法规避 | 5个 (mktemp/tail/wc×2/help-version) |

---

## 七、选择性 make check 深度分析 (2026-04-08 20:10)

### 7.1 测试执行方式对比

| 方式 | 结果 | 问题 |
|------|------|------|
| 全量 `make check` | 76P/18F/30S/7E (~23min后卡死) | 日志聚合器崩溃，结果不完整 |
| 选择性 `make check` TESTS=... | 0 结果 (全部无法记录) | automake 日志框架在 HarmonyOS 上不可用 |
| **test-driver 直接调用** | **5P / 61F / 343S / 0E (~14秒)** | ✅ 409 个测试全部执行完毕 |

### 7.2 test-driver 直接调用结果详解

| 类别 | 数量 | 原因 |
|------|------|------|
| PASS | 5 | misc/getopt_vs_usage.sh, option-aliases.sh, read-errors.sh, usage_vs_getopt.sh, usage_vs_refs.sh |
| FAIL (Shell) | 5 | factor/create-test(空参数), help/version(built_programs空), +3 个其他 |
| FAIL (Perl .pl) | 56 | 缺少 Coreutils.pm 框架 + PERL5LIB 环境变量 |
| SKIP | 343 | built_programs 变量为空 → "not built" 跳过 |
| ERROR | 0 | — |

### 7.3 make check 适配障碍（需修复才能完整运行）

| # | 障碍 | 根因 | 优先级 | 复杂度 |
|---|------|------|--------|--------|
| 1 | **日志聚合器崩溃** | Makefile awk 片段读取 .trs 文件时被 test-driver exit trap 清理 | P0 | 中 |
| 2 | **built_programs 为空** | 外部调用未传递此变量 → 343 个假 SKIP | P0 | 低 |
| 3 | **Perl 框架缺失** | PERL5LIB 未设置, Coreutils.pm 未加载 → 56 个 .pl FAIL | P1 | 低 |
| 4 | **SED 路径错误** | configure 时 SED=/usr/bin/sed 但实际在 /usr/local/bin/sed | P2 | 极低 |
| 5 | **fd 9 不支持** | AM_TESTS_FD_REDIRECT 使用 fd 9 作日志通道, HarmonyOS zsh 报 bad fd | P2 | 低 |
| 6 | **config.guess 卡死** | 内部 uname/proc 解析路径阻塞, 仅影响 reconfigure | P3 | 低 |

### 7.4 结论

**打包的 88 个命令中:**
- 通过 --version 回归验证: **82/83 (99%)**
- 通过 make check (排除13命令后): **5 个 Shell 测试明确 PASS**
- 其余 343 个 SKIP 为**环境配置问题**（非代码 bug），修复障碍 #2 后可重新验证
- 61 个 FAIL 中 **56 个是 Perl 框架问题**（非代码 bug），修复障碍 #3 后可重新验证
- 真正需要关注的代码级 FAIL: **~5 个 Shell 测试**（需逐个分析是否为平台限制）

**建议:** 优先修复障碍 #1+#2 后重跑，可获得完整的 Shell 测试覆盖率。

---

## 编译结束

- **结束时间**: 2026-04-08 21:35:00
- **最终状态**: ✅ 成功 (排除14个平台受限命令后)
- **产物**: archives/c/coreutils/9.10/packaging/coreutils-9.10-ohos-aarch64.tar.gz

---

### 对话 #1 — 初始编译与补丁应用 (2026-04-08)
**目标**: 完成 coreutils 9.10 在 HarmonyOS 上的编译、测试与打包

#### 关键决策记录
1. **排除命令策略**: 基于 SELinux 上下文差异(u:object_r:hmdfs:s0)，确定 12 个软链接操作命令需使用 toybox 替代
2. **od.c 遗漏修复**: make check 发现 trad-dot 测试 FAIL，定位为补丁 0002 遗漏 od.c，生成补丁 0003 并验证通过
3. **完整 make check 分析**: 运行全量 1117 个测试，分类 210 个失败为 4 类，最终仅新增 chroot+tac 两个排除项
4. **tac double-free 评估**: 分析 G_buffer 指针偏移 + musl libc xrealloc 兼容性问题，决定排除而非高风险重构

#### 测试数据快照
| 轮次 | 方式 | P | F | S | E | 备注 |
|------|------|---|---|---|---|------|
| R1 | make check 全量(卡死) | 76 | 18 | 30 | 7 | ~23min 后卡死 |
| R2 | test-driver 直接调用 | 5 | 61 | 343 | 0 | 409 测试, 环境变量缺失 |
| R3 | make check 完整(SED修正) | **334** | **128** | **573** | **82** | ~50min, 1117 测试 |

### 对话 #2 — 排除列表更新与最终打包 (2026-04-08)
**目标**: 基于完整测试结果更新 EXCLUDE_LIST 并重新打包

#### 变更记录
- EXCLUDE_LIST: 12 → 14 (新增 chroot, tac)
- 打包产物: 8.9MB/88个 → 8.7MB/86个 二进制
- 补丁: 3 个全部 applied (0001-0003)
- 归档状态: success#final (0 缺失项, 0 阻塞 WARN)


### 对话 #3 — package.sh 修复与正确打包 (2026-04-09)

**目标**: 修复 package.sh 无法完成全流程的问题，产出可用的签名打包产物

**问题诊断**:
1. `make install` 因 configure --prefix 为空导致安装到系统根 `/bin` → 用 `make install prefix=$TEST_PREFIX` 解决
2. package.sh Step 4 对 10889 个文件跑 `find|file|grep` 管道超时（实际是复制了全局 /usr/local 目录的垃圾文件）
3. `set -euo pipefail` 中 `pipefail` 在 zsh 不支持
4. shebang 被误删
5. Step 2e(排除)在 Step 2b(复制)之前执行，排除无效

**修复**:
- package.sh + sign-elf.sh 迁移为 `#!/bin/zsh`
- Step 4 的 find|file|grep 管道替换为 zsh glob qualifier `**/*(.N)` + ELF magic 快速检测
- Step 2e 移至 Step 2b 之后（先复制后排除）
- `_found` bug 修复: `[ -n "_found" ]` → `[ -n "$_found" ]`
- 运行时确保 `$TEST_PREFIX` 正确传递

**最终结果**:
```
coreutils-9.10-ohos-aarch64.tar.gz   (11M)
├── bin/    86 个二进制 (14个已排除)
├── share/  100 个 man 页
└── 全部签名成功 (signed=86, failed=0)
     全部权限修复 (fixed=101)
     解压验证通过 (14/14 排除确认, 14/14 执行测试通过)
```

**遗留**: debug symbols 包为空（HarmonyOS NDK clang 不生成 DWARF 调试信息）
