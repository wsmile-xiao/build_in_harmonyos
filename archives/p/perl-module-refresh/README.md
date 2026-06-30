# perl-module-refresh (Module::Refresh)

Refresh `%INC` files when updated on disk. Designed for simple iterative development in persistent environments (e.g., mod_perl, FastCGI).

## 版本历史

| 版本 | 日期 | 状态 | 说明 |
|------|------|------|------|
| 0.18 | 2026-06-18 | ✅ published | 纯 Perl 模块，OpenHarmony 平台编译通过，全功能测试通过 |

## 软件说明

Module::Refresh 提供在持久化环境中刷新已加载 Perl 模块的功能。当模块文件在磁盘上被修改后，调用 `Module::Refresh->refresh()` 可重新加载变更的模块，无需重启进程。

### 核心功能

- `new()` — 初始化刷新器，缓存 %INC
- `refresh()` — 批量刷新所有已变更模块
- `refresh_module($mod)` — 刷新指定模块
- `refresh_module_if_modified($mod)` — 仅当文件已变更时刷新
- `unload_module($mod)` — 卸载模块
- `unload_subs($file)` — 清理模块中定义的子程序

### 模块类型

**纯 Perl 模块**（无 C/XS 代码），在 OpenHarmony 平台上：
- 无需源码修改
- 不受 SELinux HMDFS 限制
- 可直接从用户目录加载
- 无需管理员协助安装

## 使用说明

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-module-refresh 0.18

# 验证安装
perl -MModule::Refresh -e 'print $Module::Refresh::VERSION'
# 输出: 0.18
```

## 构建依赖

- Perl 5.8.1+
- ExtUtils::MakeMaker 6.36+
- Path::Class (仅测试时需要)

## 许可证

Perl Artistic License (同 Perl 本身)
