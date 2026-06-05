# E082: TMPDIR umask 077导致临时目录无法写入

## 问题概述

HarmonyOS环境下，configure脚本使用umask 077创建临时目录会导致权限问题：
- `mktemp -d "./confXXXXXX"` 创建的临时目录权限为 `drwx--S---`
- 当前用户无法写入该目录
- 导致 `config.status: error: could not setup config files machinery`

## 根本原因

1. **umask 077**: configure脚本默认使用umask 077创建临时文件/目录
2. **SGID目录**: HarmonyOS某些目录（如/tmp）设置了SGID位
3. **相对路径**: 使用相对路径 `./confXXXXXX` 而非绝对路径 `$TMPDIR/confXXXXXX`
4. **组合效果**: umask 077 + SGID → drwx--S--- → 当前用户无法写入

## 错误特征

典型错误日志：
```
config.status: error: could not setup config files machinery
./configure: line 15713: cannot create a temporary directory in .: Permission denied
mktemp: failed to create file via template './confXXXXXX': Permission denied
```

## 解决方案

### 方案1：修改configure脚本（推荐）

```bash
# 在configure脚本中添加TMPDIR强制设置并修改umask
sed -i configure -e '15710a\: "${TMPDIR:=/storage/Users/currentUser/tmp}"' \
    -e 's/umask 077 && mktemp -d "./confXXXXXX"/umask 022 \&amp;\&amp; mktemp -d "$TMPDIR\/confXXXXXX"/g' \
    -e 's/tmp=./conf$$-$RANDOM/tmp=$TMPDIR\/conf$$-$RANDOM/g'
```

### 方案2：设置环境变量

```bash
export TMPDIR=~/tmp
mkdir -p $TMPDIR
chmod 1777 $TMPDIR
make -e  # 使用-e确保环境变量传递给子进程
```

### 方案3：预创建临时目录

```bash
# 在运行configure之前预创建临时目录并设置权限
tmpdir=$(mktemp -d ~/tmp/confXXXXXX)
chmod 755 $tmpdir
export TMPDIR=$tmpdir
```

## 验证方法

```bash
# 验证configure修复
grep -n 'TMPDIR.*umask 022' configure && echo "修复成功"

# 验证临时目录权限
ls -la ~/tmp/ | grep conf
# 应显示: drwxr-xr-x (而非 drwx--S---)

# 验证configure能成功
./configure && echo "configure成功"
```

## 适用范围

- **所有autotools软件**: configure脚本使用mktemp的场景
- **HarmonyOS环境**: SGID目录特别容易触发此问题
- **musl libc环境**: 权限处理与glibc不同

## 相关案例

- **krb5 1.22.1**: 修复补丁 `0003-configure.patch`
- 其他可能的案例需要扫描configure脚本中的 `umask 077 && mktemp` 模式

## 预防措施

1. **统一TMPDIR**: 在编译脚本中统一设置 `export TMPDIR=~/tmp`
2. **使用make -e**: 确保环境变量传递给子进程
3. **补丁固化**: 对configure脚本进行补丁修复，确保后续版本也能正确处理

## 分类标签

`platform` `configuration` `permission` `HarmonyOS` `autotools`

## 优先级

HIGH - configure失败会导致整个编译流程无法进行