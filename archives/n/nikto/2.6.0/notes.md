# nikto 2.6.0 适配笔记

## 编译环境
- 构建系统: perl_script
- 编译日期: 2026-06-10
- 编译器: N/A (Perl script)
- Perl 版本: 5.42.0
- 状态: built

## 编译步骤

Nikto 是一个 Perl web 服务器扫描器，不需要传统编译。主要步骤：

1. **下载源码**: 从 GitHub releases 获取 v2.6.0 tarball
2. **安装 Perl 依赖**:
   - 安装 JSON 模块 (JSON-4.10)
   - 安装 XML::Writer 模块 (XML-Writer-0.900)
3. **创建 Makefile**: 编写简单的安装 Makefile
4. **安装到 staging 目录**: `make install DESTDIR=$TEST_PREFIX`
5. **验证功能**: `perl nikto.pl -Version` 通过
6. **打包预编译包**: 使用 ohc-run.py package
7. **本地安装验证**: `make install PREFIX=$DEFAULT_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 JSON 模块 | Nikto 需要 JSON Perl 模块用于 JSON 报告输出 | 从 CPAN 下载并安装 JSON-4.10 |
| 2 | 缺少 XML::Writer 模块 | Nikto 需要 XML::Writer 用于 XML 报告输出 | 从 CPAN 下载并安装 XML-Writer-0.900 |
| 3 | 配置文件找不到 | nikto.conf 未安装 | 复制 nikto.conf.default 到安装目录 |
| 4 | Perl 模块路径问题 | 安装的模块不在 Perl @INC 路径中 | 创建 wrapper 脚本设置 PERL5LIB 环境变量 |

## 源码修改

无需补丁。创建了以下文件：
- **Makefile**: 自定义安装脚本，用于安装 Perl 脚本和数据文件

## 依赖版本

- Perl: 5.42.0 (已预装)
- JSON: 4.10 (CPAN)
- XML::Writer: 0.900 (CPAN)

## 验证结果

```bash
# Perl 语法检查
cd program && perl -c nikto.pl
Result: syntax OK

# 版本验证
/storage/Users/currentUser/usr/local/bin/nikto -Version
Result: Nikto 2.6.0 (LW 2.5)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| nikto-2.6.0-ohos-aarch64.tar.gz | 2.0M | 预编译包 |

## 注意事项

1. **Perl 模块依赖**: 需要预先安装 JSON 和 XML::Writer 模块
2. **配置文件**: 需要复制 nikto.conf.default 到 nikto.conf
3. **Wrapper 脚本**: bin/nikto 是 wrapper，实际脚本在 share/nikto/nikto.pl
4. **PERL5LIB**: wrapper 脚本会设置 PERL5LIB 环境变量
5. **非传统编译**: 这是 Perl 脚本软件，不需要 configure/make 编译步骤

---
**编译结束**: 2026-06-10
**最终状态**: built
---

**编译结束**: 2026-06-10 10:31
**最终状态**: built
