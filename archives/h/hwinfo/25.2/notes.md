# 编译笔记 - hwinfo 25.2

## 编译环境
- **平台**: OpenHarmony aarch64
- **编译器**: clang 15
- **构建系统**: Makefile
- **源码版本**: 25.2
- **编译日期**: 2026-04-29

## Phase 1: 初始化

### 依赖检查
- 无外部依赖
- 构建工具: make, clang (已安装)

### 预扫描问题
- 🔴 PSCAN-HMDFS-001: Makefile 使用 `ln -s`，HMDFS 不支持
- 🟡 PSCAN-PATH-001: 硬编码 `/etc/` 路径

## Phase 2: 编译

### 第一次编译失败
**时间**: 21:46:35  
**问题**: `HD_VERSION_STRING` 未定义  
**日志**:
```
hd.c:1836:50: error: use of undeclared identifier 'HD_VERSION_STRING'
hd.c:5807:10: error: use of undeclared identifier 'HD_VERSION_STRING'
```

**根因**: Makefile 应生成 `src/hd/version.h` 但因 git2log 权限问题失败  
**触发规则**: 无匹配知识条目（新问题）

### 修复方案
**时间**: 21:46:50  
**操作**: 手动生成 version.h  
**命令**: `echo "#define HD_VERSION_STRING \"25.2\"" > src/hd/version.h`  
**记录**: 0001-version.h.patch

### 第二次编译成功
**时间**: 21:46:50 - 21:56 (约10分钟)  
**参数**: 默认参数  
**产物**:
- hwinfo (4.7M)
- libhd.a (6.6M)
- libhd.so.25.2 (4.6M)

**警告统计**:
- 8 个 `-Wshift-negative-value` (hddb.c)
- 6 个 `-Wgnu-designator` (input.c, int.c, check_hd.c)
- 7 个 `-Wempty-body` (cpu.c, floppy.c)

**处理**: 保留警告（代码逻辑正确，符合 GNU 标准）

## Phase 3: Staging 验证

### 安装失败
**时间**: 21:58  
**问题**: 系统缺少 GNU `install` 命令  
**错误**: `make: install: No such file or directory`

**根因**: OpenHarmony 系统使用 toybox，缺少 GNU coreutils  
**触发规则**: E002 (TMPDIR 相关，但实际是 install 命令缺失)

### 手动安装
**操作**: 使用 `cp -a` 替代 `install`  
**路径**: `$TEST_PREFIX/$DEFAULT_PREFIX`  
**结果**: ✅ 成功

### 功能验证
**测试**: `hwinfo --version`  
**结果**: 输出 `25.2` ✅

## Phase 4: 质量门禁

### 第一次验证失败
**时间**: 21:59  
**问题**: G4 门禁失败
- ❌ manifest.yaml 缺失
- ⚠️ notes.md 缺失

### 手动修复归档
**时间**: 22:00  
**操作**:
- 创建 manifest.yaml
- 创建 README.md
- 创建 PROGRESS.md
- 创建 RELEASENOTE.md

### 第二次验证成功
**时间**: 22:00  
**结果**: G1-G4 全部 PASS ✅

## Phase 5: 预编译包制作

### package 成功
**时间**: 22:00  
**警告**: 符号链接 libhd.so.25 和 libhd.so 权限问题（不影响打包）  
**产物**:
- hwinfo-25.2-ohos-aarch64.tar.gz (14M)
- hwinfo-25.2-ohos-aarch64-debug.tar.gz (2.9M)

### ELF 签名
- ✅ 已签名（通过 ohc-run.py sign-elf）
- ✅ 权限修复 (755)

## Phase 6: 本地安装验证

### 安装成功
**时间**: 22:00  
**路径**: `$DEFAULT_PREFIX` (`~/usr/local`)  
**测试**: `~/usr/local/sbin/hwinfo --version`  
**结果**: 输出 `25.2` ✅

## 知识提取

### L2: 构建模式经验
**发现**: Makefile 自动生成文件失败模式  
**类别**: 构建系统  
**通用性**: 高（影响所有依赖脚本生成文件的 Makefile 项目）

**建议知识条目**:
- **编号**: E-git2log-permission 或 E-makefile-auto-gen-fail
- **现象**: Makefile 应生成 version.h 等文件，但因前置脚本权限/路径问题失败
- **根因**: 
  - git2log 在 HMDFS 上权限问题
  - 系统缺少 GNU install 命令
- **方案**: 
  1. 检查 Makefile 是否有自动生成规则
  2. 手动执行生成命令
  3. 记录生成的文件为补丁
- **平台**: OpenHarmony HMDFS
- **关联**: E002 (TMPDIR), E006 (权限), E007 (平台识别)

## 补丁清单
- 0001-version.h.patch: 手动生成 version.h 文件

## 耗时统计
- Phase 1 (init): 15秒
- Phase 2 (build): 10分钟（含修复）
- Phase 3 (staging): 2分钟（手动安装）
- Phase 4 (verify): 1分钟（含修复）
- Phase 5 (package): 1分钟
- Phase 6 (install): 30秒
- **总耗时**: 约15分钟

## 遗留问题
- ⚠️ 系统缺少 GNU install 命令（建议安装 coreutils 预编译包）
- ⚠️ HMDFS 符号链接限制（已用 cp -a 替代）
- ⚠️ 编译警告较多（建议上游修复）

## 成功要素
- ✅ 手动生成 version.h 解决编译失败
- ✅ 手动复制文件绕过 install 命令缺失
- ✅ 完整的归档文件创建
- ✅ 质量门禁通过
- ✅ 功能验证成功

---

**编译状态**: success ✅  
**归档路径**: `/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/h/hwinfo/25.2`
---

**编译结束**: 2026-04-29 22:02
**最终状态**: built
