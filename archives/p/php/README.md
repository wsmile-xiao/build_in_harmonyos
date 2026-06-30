# PHP

PHP is a popular general-purpose scripting language that is especially suited to web development.

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 8.2.28 | published | 2026-05-26 |

## 编译说明

PHP编译需要特殊处理：
1. 运行buildconf生成configure脚本
2. 更新build/config.guess和config.sub支持OHOS平台
3. 修复configure中的umask问题（E011）
4. 禁用phpdbg（musl不支持pthread_cancel）

## 功能限制

- 仅编译CLI和CGI SAPI
- 禁用所有扩展（--disable-all）
- 不支持phpdbg调试器
