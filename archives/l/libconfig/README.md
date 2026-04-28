# libconfig

## 简介
libconfig 是 C/C++ 配置文件处理库，支持结构化配置文件读写。

## OHOS 适配
- autotools 构建，需要更新 config.guess/config.sub
- HMDFS umask 权限问题需 workaround
- 共享库动态加载失败，建议使用静态链接（libconfig.a / libconfig++.a）

## 排除与替代
- 动态链接不可用 → 使用静态链接替代

## 依赖
- 无编译依赖

## 功能验证
```bash
ls -la $HOME/usr/local/lib/libconfig*
```

## 参考
- 主页: https://github.com/hyperrealm/libconfig
