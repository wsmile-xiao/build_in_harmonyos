# envchain

## 软件简介

envchain 是一个命令行工具，用于从 D-Bus Secret Service（如 GNOME Keyring、KeePassXC）安全地存储和检索环境变量。

通过 envchain，用户可以将敏感的环境变量（如 API 密钥、密码等）存储在加密的秘密服务中，然后在需要时通过命名空间机制安全地注入到命令执行环境中。

## 版本历史

| 版本 | 状态 | 发布日期 | 说明 |
|------|------|----------|------|
| 1.1.0 | built | 2026-06-05 | 首次编译，修复 Makefile DESTDIR 问题 |

## 项目信息

- **上游仓库**: https://github.com/sorah/envchain
- **许可证**: MIT License
- **编程语言**: C
- **构建系统**: Makefile（纯 Makefile，无 configure）

## 功能特性

- 从 D-Bus Secret Service 存储和检索环境变量
- 支持命名空间机制隔离不同项目的环境变量
- 支持 passphrase 保护（可选）
- 支持静默模式（noecho）输入敏感信息

## 依赖

### 运行依赖

- libreadline (命令行交互)
- libsecret (D-Bus Secret Service 客户端)
- glib (基础库)
- pcre2 (正则表达式)
- D-Bus Secret Service 后端（GNOME Keyring 或 KeePassXC）

### 构建依赖

- clang/clang++
- pkg-config
- libreadline-dev
- libsecret-dev

## 使用方法

### 基本命令

```bash
# 显示版本和用法
envchain

# 添加环境变量到命名空间
envchain --set NAMESPACE ENV_VAR1 ENV_VAR2

# 带密码保护添加
envchain --set --require-passphrase NAMESPACE API_KEY

# 列出所有命名空间
envchain --list

# 使用命名空间中的环境变量执行命令
envchain NAMESPACE command [args...]

# 删除环境变量
envchain --unset NAMESPACE ENV_VAR1
```

### 使用示例

```bash
# 存储 AWS 凭证
envchain --set aws AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY

# 使用 AWS 凭证执行命令
envchain aws aws s3 ls

# 存储 GitHub token
envchain --set github GITHUB_TOKEN

# 使用 GitHub token
envchain github gh repo list
```

## 编译说明

### 已知问题

1. **Makefile DESTDIR 非标准**: 原始 Makefile 使用 `$(DESTDIR)/./bin` 而非标准的 `$(DESTDIR)$(PREFIX)/bin`
2. **无 PREFIX 支持**: 原始 Makefile 缺少 PREFIX 变量
3. **pkg-config 子 shell 问题**: Makefile 中 export PKG_CONFIG_PATH 不生效

### 补丁说明

**0001-Makefile.patch**:
- 添加 PREFIX 变量支持标准 DESTDIR 模式
- 修复 install 目标路径
- 添加 PKG_CONFIG_PATH export

### 编译参数

```bash
# 编译时需设置 LDFLAGS 指定 RPATH
make LDFLAGS="-Wl,-rpath,$PREFIX/lib -Wl,--enable-new-dtags"

# 安装时使用标准 DESTDIR 模式
make install PREFIX=$PREFIX DESTDIR=$TEST_PREFIX
```

## 注意事项

1. **需要 Secret Service 后端**: envchain 需要 D-Bus Secret Service（如 GNOME Keyring 或 KeePassXC）才能正常工作
2. **不支持 --version/--help**: 无参数运行时显示版本和用法说明
3. **RPATH 配置**: 预编译包使用 `$ORIGIN/../lib` 相对路径，确保可移植性
4. **依赖库**: 用户安装后需要安装 readline、libsecret、glib、pcre2 等依赖库

## 归档目录

```
archives/e/envchain/
├── README.md          # 软件级说明（本文件）
├── manifest.yaml      # 软件级元数据（版本索引）
└── 1.1.0/
    ├── manifest.yaml  # 版本级元数据
    ├── notes.md       # 编译笔记
    ├── patches/       # 补丁目录
    │   └── 0001-Makefile.patch
    ├── packaging/     # 预编译包
    │   └── envchain-1.1.0-ohos-aarch64.tar.gz
    └── reports/       # 测试报告
        ├── test-report.md
        └── verify-report.md
```

## 相关链接

- [GitHub 仓库](https://github.com/sorah/envchain)
- [cmd-pkgs 预编译包](https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs)

---

*最后更新: 2026-06-05*
