# pwgen 2.08 — OpenHarmony 编译记录

## 基本信息
- 软件: pwgen - 密码生成器
- 版本: 2.08
- 构建系统: autotools
- 目标: ohos-aarch64
- 状态: ✅ 编译成功

## 编译指导

### 特殊处理
由于 configure 脚本的 config.status 在 OpenHarmony 平台遇到临时目录权限问题：
```
./config.status[678]: can't create ./confXXXXXX/subs1.awk: Permission denied
```

解决方案：手动创建 Makefile
1. 运行 `./configure --prefix=$DEFAULT_PREFIX` 直到失败
2. 从 `config.log` 提取 DEFS 和变量值
3. 根据 `Makefile.in` 创建完整的 `Makefile`
4. 运行 `make && make install DESTDIR=$TEST_PREFIX`

### 正常编译流程（若 configure 成功）
```bash
./configure --prefix=$DEFAULT_PREFIX
make
make install DESTDIR=$TEST_PREFIX
```

## 补丁清单
无补丁（本次编译通过手动 Makefile 绕过 configure 问题）

## 已知限制
- config.status 临时目录创建问题：zsh 环境下 mktemp 创建的目录后续写入失败
- 编译警告：8个旧式函数定义警告（不影响功能）

## 功能验证
```bash
# 基本使用
pwgen 12 5        # 生成5个12位密码

# 安全模式
pwgen -s 16 3     # 完全随机密码

# 包含特殊字符
pwgen -y 10 3     # 包含符号的密码
```

所有功能测试通过。

## 预编译包
- pwgen-2.08-ohos-aarch64.tar.gz (88KB)
- pwgen-2.08-ohos-aarch64-debug.tar.gz (59KB)

## 参考链接
- 官方网站: https://pwgen.sourceforge.net/
- 源码下载: https://downloads.sourceforge.net/project/pwgen/pwgen/2.08/pwgen-2.08.tar.gz