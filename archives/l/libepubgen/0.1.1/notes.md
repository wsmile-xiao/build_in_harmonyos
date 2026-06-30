# libepubgen 0.1.1 鸿蒙平台适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# Step 1: 替换 config.guess/config.sub (支持 aarch64-linux-ohos)
# Step 2: configure
export CC=clang CXX=clang++
bash ./configure --prefix=$HOME/usr/local --disable-werror --disable-tests --without-docs CXX=clang++

# Step 2.5: 修复 config.status（HMDFS 权限问题）
sed -i 's/umask 077 && mktemp/mktemp/' config.status
bash ./config.status

# Step 3: make -j1 && make install DESTDIR=$TEST_PREFIX && make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 平台不识别 | config.guess/config.sub 不识别 aarch64-linux-ohos | 替换为支持 ohos 的版本 |
| 2 | config.status 权限错误 | HMDFS umask 077 创建权限 2700 目录 | 去掉 umask 077 |
| 3 | E053: cc1plus 不可用 | 鸿蒙仅提供 clang++ | CXX=clang++ |

## 源码修改

| 补丁 | 说明 |
|------|------|
| 0001-config.guess.patch | 平台识别 aarch64-linux-ohos |
| 0002-config.sub.patch | 平台识别 aarch64-linux-ohos |
| config.status sed | 去掉 umask 077（每次 configure 后手动修复，R6） |

## 功能测试（7/7 通过）
1. ✅ 动态链接验证
2. ✅ EPUBTextGenerator 构造/析构
3. ✅ EPUBPresentationGenerator 构造/析构
4. ✅ EPUBDrawingGenerator 构造/析构
5. ✅ 枚举类型验证
6. ✅ EPUBPackage 接口调用
7. ✅ Generator 选项设置

## 注意事项
1. config.status umask 修复每次 configure 后必须执行
2. 纯库产品，无可执行二进制