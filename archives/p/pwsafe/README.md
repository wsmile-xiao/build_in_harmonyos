# Password Safe

> Password management utility based on Bruce Schneier's Blowfish algorithm

## 简介

pwsafe (Password Safe) 是一个密码管理工具，使用 Bruce Schneier 的 Blowfish 加密算法来安全存储密码。支持密码生成、组织、搜索、自动填充等功能。提供 CLI 和 GUI 版本。

## OHOS 适配要点

- CMakeLists.txt 需添加 __OHOS__ 平台条件宏
- src/os/unix/ 需适配 keystub.cpp 和 run.cpp 的 syscall 差异（seteuid 等）
- src/core/StringX.cpp 需要 mbstate_t 类型适配
- secure_getenv 需替换为 getenv（__OHOS__ 守卫）
- src/ui/cli 版本模板适配

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libxerces-c | 3.2 | XML 解析库 |

## 功能验证

```bash
pwsafe --version
```

## 参考

- [Password Safe 官网](https://pwsafe.org/)
- [GitHub: pwsafe/pwsafe](https://github.com/pwsafe/pwsafe)
