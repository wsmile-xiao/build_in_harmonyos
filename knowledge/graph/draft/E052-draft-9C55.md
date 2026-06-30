# E052 — HMDFS config.status 临时目录创建失败

## 错误特征
```
config.status: error creating temporary directory
can't create ./confXXXXXX/subs1.awk: Permission denied
```

## 触发条件
- 构建系统: autotools
- 阶段: configure（config.status 执行时）
- 平台: HarmonyOS HMDFS 文件系统

## 根因分析
HMDFS 文件系统对 config.status 的临时文件创建有特殊限制，即使使用 `mktemp -d` 创建的目录也可能失败。这是 E002（/tmp 只读）的补充情况，发生在 configure 生成的 config.status 脚本执行时。

config.status 在执行时会在当前目录创建临时文件（如 `confXXXXXX/subs1.awk`），但在 HMDFS 上可能会因为权限问题失败，即使使用 `mktemp -d` 创建的临时目录也可能遭遇权限限制。

## 解决方案

### 推荐方案（方案 1）
修改 config.status 使用固定临时目录（`$HOME/tmp/configure.$$`），避开 HMDFS 限制：
```bash
sed -i 's|tmpdir=.*|tmpdir=$HOME/tmp/configure.$$|g' config.status
mkdir -p $HOME/tmp
```

### 回退方案（方案 2）
在工作目录（`~/builds/`）中编译，避免使用 clean-verify 的临时目录：
```bash
cd ~/builds
tar xf <tarball>
./configure --prefix=$DEFAULT_PREFIX
```

### 禁止做法
- ❌ 使用 `/tmp` 目录（在 HMDFS 上是只读挂载点，见 E002）
- ❌ 在 clean-verify 的临时目录中运行 configure

## 验证
```bash
grep -q "tmpdir=" config.status && echo "已找到 tmpdir 配置" || echo "未找到"
```

## 关联条目
- E002: HMDFS /tmp 只读问题（根因）
- R10: 临时文件用 $TMPDIR（铁律）