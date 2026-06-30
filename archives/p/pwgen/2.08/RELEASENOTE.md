# pwgen 2.08 发布说明

**软件**: pwgen - 密码生成器  
**版本**: 2.08  
**平台**: OpenHarmony aarch64  
**发布日期**: 2026-05-15

## 概述
pwgen 是一个简单高效的密码生成工具，可以生成易于记忆或完全随机的密码。

## 编译信息
- 编译器: clang 15.0.4
- 构建系统: autotools（手动 Makefile）
- 编译警告: 8个（旧式函数定义，不影响功能）
- 测试状态: 手动功能测试全部通过

## 特殊说明
由于 configure 脚本的 config.status 在当前平台遇到临时目录权限问题，本次编译采用手动创建 Makefile 的方式绕过问题。编译产物功能完全正常。

## 包含内容
- pwgen 二进制文件
- pwgen.1 手册页
- install.sh 安装脚本

## 使用方法
```bash
# 安装
./install.sh

# 生成5个12位密码
pwgen 12 5

# 生成安全密码
pwgen -s 16 3

# 包含特殊字符
pwgen -y 10 5
```

## 功能验证
所有基本功能已验证通过：
- ✅ 默认密码生成
- ✅ 安全模式 (-s)
- ✅ 包含数字 (-n)
- ✅ 包含特殊字符 (-y)
- ✅ 组合选项

## 文件清单
```
pwgen-2.08-ohos-aarch64.tar.gz (88KB)
├── bin/pwgen
├── share/man/man1/pwgen.1
└── install.sh
```

## 状态
**partial** - 功能完整，可分发使用