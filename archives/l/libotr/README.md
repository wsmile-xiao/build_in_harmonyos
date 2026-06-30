# libotr

## 简介

libotr 是 Off-the-Record (OTR) 加密消息协议的 C 语言实现库，用于提供即时消息的端到端加密、认证和完美前向保密。

**主要功能**:
- 提供 OTR 协议的加密和认证功能
- 支持完美前向保密 (Perfect Forward Secrecy)
- 提供 toolkit 工具集用于密钥管理

**项目信息**:
- 官网: https://otr.cypherpunks.ca/
- 源码: https://otr.cypherpunks.ca/libotr-4.1.1.tar.gz
- 许可证: LGPL-2.1+

## 编译状态

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|---------|--------|
| 4.1.1 | built | 2026-06-11 | 23 |

## 依赖关系

- **必需依赖**: libgcrypt (加密库)
- **可选依赖**: 无

## 已编译版本

### 4.1.1 (2026-06-11)

**编译产物**:
- 主库: `libotr.a` (静态库), `libotr.so.5.1.1` (动态库)
- 工具集: otr_parse, otr_sesskeys, otr_mackey, otr_readforge, otr_modify, otr_remac
- 头文件: libotr/*.h (17 个头文件)

**编译状态**: built（主库编译成功，未生成预编译包）

**平台适配**:
- config.guess/config.sub 添加 OpenHarmony 支持
- autotools 平台识别正常

**测试状态**:
- ✅ 单元测试: 全部通过
- ❌ Regression 测试: 编译失败（缺少 socket 头文件，不阻塞主库发布）

**注意事项**:
- Regression 测试失败不影响主库功能（根据 skill R9 规则）
- toolkit 工具集全部可用

## 使用方式

### 从预编译包安装（推荐）

暂无预编译包（需要通过 staging verify 才能生成）

### 从源码编译

```bash
# 下载源码
wget https://otr.cypherpunks.ca/libotr-4.1.1.tar.gz
tar xzf libotr-4.1.1.tar.gz
cd libotr-4.1.1

# 应用补丁（从归档目录）
patch -p1 < archives/l/libotr/4.1.1/patches/0002-config.guess.patch
patch -p1 < archives/l/libotr/4.1.1/patches/0003-config.sub.patch
# ... 应用其他必需补丁

# 配置和编译
./configure --prefix=$HOME/usr/local
make -j1
make install

# 验证
otr_parse --version
```

## 相关链接

- [归档目录](./4.1.1/): 编译笔记、补丁、测试报告
- [知识图谱](../../knowledge/graph/): 平台适配知识