# Data-Peek

Perl XS 模块，提供对 Perl 内部数据结构的调试和可视化功能。

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.53 | built | 2026-06-10 | 编译成功，补丁固化，打包完成（受 SELinux 策略限制用户目录加载） |

## 平台限制说明

**鸿蒙系统安全限制**：
- Perl XS 模块生成 `.so` 共享库文件
- 鸿蒙 SELinux 策略只允许加载 `hnp_file` 类型标签的共享库
- 用户目录中的 `.so` 文件标签为 `hmdfs`，无法被 Perl 加载
- 需系统管理员将模块安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/`

## 解决方案

如需安装此模块，请联系系统管理员协助：
```bash
# 需管理员权限
cp ~/usr/local/lib/site_perl/5.42.0/aarch64-linux/auto/Data/Peek/Peek.so \
   /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Data/Peek/
```

## 相关知识

- E097: Perl XS 模块共享库加载限制（SELinux 标签）