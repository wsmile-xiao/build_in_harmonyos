# E081 — HMDFS 文件系统限制导致 autotools config.status 无法创建临时子目录

## 错误现象

```
./config.status[1243]: can't create ./confmjIJUL/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**典型特征**：
- 错误发生在 config.status 执行阶段（configure 成功后）
- 临时子目录名是随机生成的（conf[a-zA-Z0-9]+）
- 即使父目录权限为 777，子目录创建仍失败
- 只在 HMDFS 挂载的目录下发生

## 根因分析

HMDFS（鸿蒙分布式文件系统）具有特殊的安全限制：
- 某些目录（如 `/storage/Users/currentUser`）虽然用户可写，但创建子目录时受到额外限制
- autotools 的 config.status 使用 `mktemp -d ./confXXXXXX` 创建随机子目录
- HMDFS 的 `hmmac=genfs` 安全策略阻止了这类操作
- 与 E002（/tmp 只读）不同，E002 是挂载点问题，E081 是文件系统特定限制

## 影响范围

**所有 autotools 项目**，在 HMDFS 挂载目录下编译时。

## 验证方法

```bash
# 检查是否在 HMDFS 上
mount | grep hmdfs

# 测试 HMDFS 子目录创建限制
cd $HOME
mkdir -p test-tmp && cd test-tmp
mktemp -d ./confXXXXXX  # 如果失败，则存在限制
ls -la || echo "HMDFS restriction detected"
```

## 解决方案

### 方案 A：使用 tmpfs 目录（推荐）

```bash
# 检查 /dev/shm 是否可用且有足够空间
mountpoint -q /dev/shm && df -h /dev/shm

# 如果可用，将源码复制到 /dev/shm
cd /dev/shm
cp -r $BUILD_SRC_DIR ./libsigrok-build
cd libsigrok-build
./configure --prefix=$DEFAULT_PREFIX
make && make install DESTDIR=$TEST_PREFIX
```

### 方案 B：标记为平台限制

如果无法使用 tmpfs，则此问题为**平台硬限制**：

```bash
# 记录到 notes.md
echo "### E081: HMDFS restriction blocks autotools config.status
- 日期: $(date)
- 影响: 无法在 HMDFS 目录下完成 configure
- 原因: HMDFS hmmac=genfs 安全策略阻止子目录创建
- 解决: 需在非 HMDFS 环境构建（如 /dev/shm 或独立构建服务器）
- 状态: failed（平台限制）
" >> $BUILD_ARCHIVE_DIR/notes.md

# 更新 manifest 状态
echo "status: failed" >> $BUILD_ARCHIVE_DIR/manifest.yaml
echo "error_pattern: E081" >> $BUILD_ARCHIVE_DIR/manifest.yaml
```

## 禁止做法

❌ **不要使用 --build/--host 绕过**

原因：
- 会导致 cross_compiling=yes，跳过运行时检测
- 生成的 config.h 与实际平台不匹配
- 违反 E007 铁律

## 关联错误

- **E002**: /tmp 只读问题（不同根因）
- **E007**: config.guess 无法识别 HarmonyOS
- **E008**: 其他文件系统限制

## 示例案例

**libsigrok 0.5.2 编译失败**：
- configure 成功识别系统为 `aarch64-unknown-linux-musl`
- config.status 创建 `confmjIJUL/` 子目录时失败
- 错误：`can't create ./confmjIJUL/subs1.awk: Permission denied`
- 原因：源码目录位于 `/storage/Users/currentUser/builds/`（HMDFS 挂载）
- 解决尝试：
  1. 设置 TMPDIR=$HOME/tmp → 无效
  2. 使用 bash 作为 CONFIG_SHELL → 无效
  3. 预创建子目录 → 无效（config.status 每次生成新的随机名）
- 最终方案：标记为平台限制，无法在当前环境完成编译

## 技术细节

**config.status 的临时文件机制**：
```bash
# config.status 内部逻辑（第 1243 行附近）
_tmp=/tmp/confXXXXXX  # 设置 TMPDIR 后变为 $TMPDIR/confXXXXXX
mkdir $_tmp || exit 1
sed 's/@S|@//g' < subs1.awk.in > $_tmp/subs1.awk
```

**HMDFS hmmac=genfs 限制**：
- 允许创建文件，但限制创建子目录
- 子目录创建需要特定的 hmmac 权限
- 用户权限（chmod 777）不足以绕过

## 建议

1. **长期方案**：鸿蒙系统更新 HMDFS hmmac 策略，允许构建场景的子目录创建
2. **短期方案**：提供构建服务器或 VM，使用非 HMDFS 文件系统
3. **临时方案**：使用 /dev/shm（tmpfs），但空间有限（通常 1GB）