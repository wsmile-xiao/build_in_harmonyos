# E080: HMDFS mktemp 临时目录权限问题

## 错误特征

```
./config.status[1356]: can't create ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

## 根本原因

HMDFS 文件系统上，`mktemp -d` 创建的临时目录权限为 `drwx--S---` (2700 + setgid)，
导致即使目录的 owner 是当前用户，也无法在其中创建文件。这是 HMDFS 的安全限制，
chmod 也无法修改权限（参见 E046）。

验证方法：
```bash
ls -ld $TMPDIR/conf* 2>/dev/null | grep "drwx--S---"
```

## 解决方案

### 方案 A：绕过 mktemp（推荐）

在 configure/config.status 运行前，预先创建临时目录（不使用 mktemp），并修改脚本中的 tmp/ac_tmp 变量：

```bash
export TMPDIR=/storage/Users/currentUser/tmp
TEMP_DIR=$TMPDIR/fixed-temp-$$
mkdir -p $TEMP_DIR

# 修改 configure 和 config.status
sed -i "s|ac_tmp=\$tmp|ac_tmp=$TEMP_DIR|g" configure config.status

# 然后运行 configure
./configure --prefix=$DEFAULT_PREFIX
```

### 方案 B：复制到 TMPFS

将整个工作目录复制到 $TMPDIR，在其中运行 configure（绕过 HMDFS 限制）：

```bash
cp -r ~/tmp/builds/sw-X.Y.work $TMPDIR/sw-build
cd $TMPDIR/sw-build
./configure --prefix=$DEFAULT_PREFIX
```

## 受影响范围

所有使用 autotools 构建系统且依赖 mktemp 创建临时目录的软件，包括：
- autoconf 系列（configure, config.status）
- 大多数 C/C++ 项目（使用 autotools）

## 相关条目

- E046: chmod 不生效（SELinux 限制）
- E002: /tmp 只读
- E007: config.guess 无法识别系统名

## 历史

- 2026-04-29: 首次发现（libtool 2.4.7 编译）