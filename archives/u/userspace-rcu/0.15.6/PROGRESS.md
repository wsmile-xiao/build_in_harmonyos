# userspace-rcu 0.15.6 编译进度

**日期**: 2026-05-12
**状态**: ✅ 已完成 (Partial - 使用 out-of-tree 构建)

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 初始化完成，下载源码并创建归档目录 |
| Step 2 patches | ✅ | 需要补丁修复 HMDFS 临时目录问题 |
| Step 3 configure | ✅ | 使用 out-of-tree 构建，修改 configure 临时目录逻辑 |
| Step 4 make | ✅ | 编译成功 |
| Step 5 install | ✅ | staging 安装完成 (DESTDIR=$TEST_PREFIX) |
| Step 6 safety | ✅ | 安全弹窗测试（HongMeng Kernel 1.12.0 已解决） |
| Step 7 check | ✅ | 测试通过 (PASS: 632, SKIP: 4, FAIL: 0) |
| Step 8 staging | ✅ | 验证产物完整性 |
| Step 9 package | ✅ | 手动创建预编译包 (因 out-of-tree 构建限制) |
| Step 10 deploy | ✅ | 归档文件已补全 |
| Step 11 finish | ✅ | 归档完整性检查通过 |

## 归档完整性检查 ✅

### 必需文件
- ✅ archives/u/userspace-rcu/0.15.6/manifest.yaml
- ✅ archives/u/userspace-rcu/0.15.6/PROGRESS.md (本文档)
- ✅ archives/u/userspace-rcu/0.15.6/README.md
- ✅ archives/u/userspace-rcu/0.15.6/RELEASENOTE.md
- ✅ archives/u/userspace-rcu/0.15.6/install.sh
- ✅ archives/u/userspace-rcu/0.15.6/patches/0001-fix-tmpdir-for-hmdfs.patch
- ✅ archives/u/userspace-rcu/0.15.6/reports/test-report.md
- ✅ archives/u/userspace-rcu/0.15.6/reports/quality-report.md
- ✅ archives/u/userspace-rcu/0.15.6/packaging/userspace-rcu-0.15.6-ohos-aarch64.tar.gz (预编译包)
- ✅ archives/u/userspace-rcu/0.15.6/packaging/userspace-rcu-0.15.6-ohos-aarch64-debug.tar.gz (调试符号)

### 软件级文件
- ✅ archives/u/userspace-rcu/README.md
- ✅ archives/u/userspace-rcu/RELEASENOTE.md
- ✅ archives/u/userspace-rcu/install.sh

## 发现与知识

### 问题 1: config.guess 无法识别平台
**症状**: `./config/config.guess: unable to guess system type`
**原因**: 旧的 config.guess (2022-01-09) 无法识别 HongMeng 平台
**解决方案**: 从已成功编译的软件包（acl-2.3.2）复制更新的 config.guess 和 config.sub

### 问题 2: autotools 临时目录创建失败 (HMDFS 限制) ⚠️
**症状**: 
```
./config.status[1077]: can't create ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**原因**: HMDFS 文件系统的特殊行为：
1. `mktemp -d "./confXXXXXX"` 使用 `umask 077` 创建临时目录
2. 创建的目录权限为 `drwx--S---`（只有owner可访问）
3. shell 进程可能以不同用户身份运行，导致后续文件创建失败

**解决方案**: 
1. 使用 out-of-tree 构建（在 ~/tmp/userspace-rcu-build）
2. 修改 configure 和 config.status 的临时目录创建逻辑：
   - 将 `mktemp -d "./confXXXXXX"` 改为 `mktemp -d "./.config-tmp/confXXXXXX"`
   - 将 `umask 077` 改为 `umask 002`（放宽权限）
   - 添加 `mkdir -p` 确保父目录存在

**补丁**: `patches/0001-fix-tmpdir-for-hmdfs.patch`

### 知识沉淀建议
- **L1 (平台真理)**: HMDFS 文件系统上 autotools 的临时目录创建问题 - 应写入 knowledge/graph/
- **L2 (模式经验)**: autotools 软件包建议使用 out-of-tree 构建规避 HMDFS 限制
- **L3 (本版笔记)**: 已写入 manifest.yaml 和本文件

## 编译参数

```bash
# Out-of-tree 构建
cd ~/tmp/userspace-rcu-build
$BUILD_SRC_DIR/configure --prefix=$DEFAULT_PREFIX

# 编译
make -j$(nproc)

# Staging 安装
make install DESTDIR=$TEST_PREFIX

# 测试
make check
# 结果: PASS: 632, SKIP: 4, FAIL: 0

# 手动打包
cd $TEST_PREFIX/$DEFAULT_PREFIX
tar czf userspace-rcu-0.15.6-ohos-aarch64.tar.gz lib include share
```

## 最终总结

**软件名称**: userspace-rcu  
**版本**: 0.15.6  
**编译状态**: Partial（部分成功 - out-of-tree 构建）  
**归档位置**: `/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/u/userspace-rcu/0.15.6/`

**预编译包**: `packaging/userspace-rcu-0.15.6-ohos-aarch64.tar.gz` (2.6M)  
**调试符号**: `packaging/userspace-rcu-0.15.6-ohos-aarch64-debug.tar.gz` (2.0M)