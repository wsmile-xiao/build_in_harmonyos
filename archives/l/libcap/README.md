# libcap

## 简介
libcap 是 Linux 能力（POSIX.1e capabilities）库，提供细粒度权限管理。

## OHOS 适配
- 使用自定义 Makefile 系统（非 autotools）
- 需要修改 Make.Rules 将 gcc 改为 clang
- 需要修改脚本 shebang 从 `/bin/bash` 到 `/data/service/hnp/bin/bash`
- 编译参数: `GOLANG=no PAM_CAP=no SHARED=yes`
- HMDFS 符号链接复制有权限问题，需用文件副本替代

## 依赖
- 无编译依赖

## 排除与替代
- GOLANG=no：禁用 Go 绑定
- PAM_CAP=no：禁用 PAM 支持

## 功能验证
```bash
getcap --help  # 或验证库安装
ls -la $HOME/usr/local/lib/libcap*
```

## 参考
- 主页: https://sites.google.com/site/fullycapable/
