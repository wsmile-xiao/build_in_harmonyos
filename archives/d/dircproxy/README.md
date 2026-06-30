# dircproxy

**类别**: network

**描述**: IRC proxy server for keeping IRC connections alive

**官方网站**: https://github.com/w8tvi/dircproxy

## 编译状态

| 版本 | 状态 | 编译日期 | 测试日期 | 备注 |
|------|------|----------|----------|------|
| 1.1.0 | ✅ published | 2026-05-29 | 2026-05-29 | 功能测试通过，可正常使用 |

## 当前版本详情

### 1.1.0

**状态**: published

**功能测试**: ✅ 通过

**核心功能**:
- ✅ IRC 代理服务正常启动
- ✅ 配置文件解析成功
- ✅ 密码加密功能完整
- ✅ 所有命令行选项正常

**修复内容**:
- HMDFS mktemp 权限限制（使用固定临时目录）
- OpenHarmony crypt 函数位置（unistd.h）
- 现代编译器兼容性（socklen_t、三元运算符赋值等）

**详细说明**:
- 编译笔记：[1.1.0/notes.md](./1.1.0/notes.md)
- 测试报告：[1.1.0/reports/test-report.md](./1.1.0/reports/test-report.md)

---

## 使用指南

### 安装

通过 cmd-pkgs 预编译包安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- dircproxy 1.1.0
```

或使用本地编译版本：
```bash
~/usr/local/bin/dircproxy --version
```

### 配置

创建配置文件 `~/.dircproxyrc`：
```conf
listen_port 57001

connection {
    # 使用加密密码（通过 dircproxy-crypt 生成）
    password "加密后的密码"

    # IRC 服务器地址
    server "irc.libera.chat:6667"

    # 可选：限制连接来源
    # from "*.yourisp.com"
}
```

### 密码生成

```bash
# 管道方式
echo "yourpassword" | dircproxy-crypt

# 命令行参数方式
dircproxy-crypt "yourpassword"
```

### 启动

```bash
# 前台调试模式
dircproxy -D -f ~/.dircproxyrc

# 后台生产模式
dircproxy -f ~/.dircproxyrc
```

### 使用 IRC 客户端连接

配置 IRC 客户端连接到 `localhost:57001`，使用配置文件中的密码。

---

## 编译说明

dircproxy 使用 autotools 构建系统，在 OpenHarmony 上需要以下修复：

1. **HMDFS 平台限制**: config.status 使用固定临时目录替代 mktemp（E081）
2. **crypt 函数**: OpenHarmony 在 unistd.h 中声明，不是 crypt.h
3. **编译器兼容性**: 修复老旧 C 特性（socklen_t、三元运算符赋值等）

**适用场景**: 此修复方案适用于所有 autotools 构建的软件，建议参考 E081 知识图谱条目。

---

## 已验证的功能

| 功能项 | 验证结果 | 说明 |
|--------|---------|------|
| 安装验证 | ✅ | 二进制文件大小正常 |
| 安全弹窗 | ✅ | 无需弹窗（Kernel 1.12.0） |
| 版本查询 | ✅ | 显示 dircproxy 1.1.0 |
| 帮助信息 | ✅ | 所有选项完整 |
| 配置解析 | ✅ | 支持标准配置格式 |
| 进程启动 | ✅ | 可启动和停止 |
| 密码加密 | ✅ | crypt() 实现正确 |
| 多密码支持 | ✅ | 支持批量加密 |