# ragel — OpenHarmony 编译记录

## 基本信息
- **软件**: ragel (State Machine Compiler)
- **描述**: 将 Ragel DSL 编译为 C/C++/D/Java/Ruby 代码的状态机编译器
- **许可证**: GPL-2.0
- **源码URL**: https://www.colm.net/files/ragel/ragel-6.10.tar.gz
- **构建系统**: autotools
- **目标平台**: aarch64-unknown-linux-ohos

## 已编译版本

| 版本 | 状态 | 日期 | configure参数 | 补丁数 |
|------|------|------|---------------|--------|
| 6.10 | published | 2026-06-02 | --prefix=... --disable-shared | 3 |

## 编译指导

### 注意事项
1. ragel 6.10 不需要 colm 作为构建依赖（colm 是 v7+ 的需求）
2. 源码包缺少 config.guess/config.sub，需要从外部补充支持 ohos 的版本
3. configure 中 HMDFS umask 077 需改为 002
4. `--disable-shared` 对 ragel 无实际效果（只编译可执行文件），但按铁律 R4 补充仍应使用

### 编译命令
```bash
./configure --prefix=$DEFAULT_PREFIX --disable-shared
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 补丁清单

| 补丁 | 类型 | 说明 |
|------|------|------|
| 0001-config.guess.patch | 平台适配 | 新增 config.guess，支持 aarch64-unknown-linux-ohos |
| 0002-config.sub.patch | 平台适配 | 新增 config.sub，支持 aarch64-unknown-linux-ohos |
| 0003-configure.patch | 平台适配 | HMDFS umask 077→002 |

## 已知限制

1. Ruby 后端生成的代码不兼容 Ruby 3.x（`"0"[0]` 返回类型差异）
2. indep 测试需要 txl 工具（本平台未安装）
3. C++ 测试 mailbox1.rl 编译失败（缺少 vector.h 路径）
4. xml.rl 生成的 C++ 代码过大，编译超时

## 功能验证

```bash
ragel --version
# 输出: Ragel State Machine Compiler version 6.10 March 2017
```
