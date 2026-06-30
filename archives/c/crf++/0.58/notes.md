# crf++ 0.58 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-24
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

```bash
cd $BUILD_SRC_DIR
# 1. 更新 config.guess/config.sub (E007: 平台不识别)
cp /usr/local/share/automake-1.17/config.guess .
cp /usr/local/share/automake-1.17/config.sub .
# 2. 运行 configure
./configure --prefix=$DEFAULT_PREFIX
# 3. 修补 config.status (umask 问题)
sed -i 's/umask 077 && mktemp -d/umask 000 \&\& mktemp -d/g; s/umask 077 && mkdir/umask 000 \&\& mkdir/g' config.status
# 4. 运行 config.status
/bin/sh config.status
# 5. 编译安装
make -j1 && make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2011 版 config.guess 过旧 | 替换为 automake-1.17 的 config.guess/config.sub |
| 2 | config.status 创建临时目录失败 (Permission denied) | HMDFS 上 mktemp -d + umask 077 创建的目录无法写入文件 | 修补 config.status 将 umask 077 改为 umask 000 |
| 3 | libtool 使用 `print -r --` 命令但 bash 无此内置命令 | /bin/sh (musl sh) 有 print 内置命令，configure 检测到后写入 libtool/config.status；make 使用 bash 执行时 print 不存在 | 创建 `print` 包装脚本到 $DEFAULT_PREFIX/bin/print，模拟 ksh `print -r --` 行为 |
| 4 | /tmp 只读导致 config.status 失败 | HarmonyOS /tmp 为只读文件系统 (E002) | 使用 $TMPDIR 环境变量，config.status 在当前目录创建临时目录 |

## 源码修改

### 替换文件 (非补丁)
- **config.guess**: 替换为 automake-1.17 版本（支持 aarch64-unknown-linux-ohos）
- **config.sub**: 替换为 automake-1.17 版本

### 生成的配置文件修改 (非源码补丁)
- **config.status**: umask 077 → umask 000 (HMDFS mktemp 兼容)
- **$DEFAULT_PREFIX/bin/print**: 新建包装脚本，模拟 ksh print 内置命令

### 环境工具
- **print wrapper**: `/storage/Users/currentUser/usr/local/bin/print` - 模拟 ksh `print -r --` 和 `print -rn --` 命令

## 依赖版本

无外部依赖。仅需标准 C/C++ 库和 pthread。

## 验证结果

```bash
# make check: 通过 (无测试套件, exit code 0)
# 二进制文件:
#   crf_learn: 18752 bytes (aarch64 ELF)
#   crf_test:  18752 bytes (aarch64 ELF)
# 库文件:
#   libcrfpp.so.0.0.0: 293312 bytes (shared library)
#   libcrfpp.a: 671870 bytes (static library)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libcrfpp.so.0.0.0 | 293312B | 共享库 |
| libcrfpp.a | 671870B | 静态库 |
| crf_learn | 18752B | CRF 训练工具 |
| crf_test | 18752B | CRF 测试工具 |
| crfpp.h | 头文件 | CRF++ API 头文件 |

## 注意事项

1. **config.guess/config.sub 必须更新**: 原始版本（2011）不支持 HarmonyOS 平台识别
2. **print 包装脚本**: 系统的 `/bin/sh` (musl sh) 有 `print` 内置命令，但 `make` 使用的 bash 没有。需要安装 print wrapper 到 $DEFAULT_PREFIX/bin/
3. **HMDFS umask 限制**: `mktemp -d` 配合 `umask 077` 在 HMDFS 上创建的目录无法写入文件，需修改为 `umask 000`
4. **无 make check 测试套件**: CRF++ 0.58 没有自动化测试，make check 返回 0 但不执行测试
---

**编译结束**: 2026-06-24 15:47
**最终状态**: built
