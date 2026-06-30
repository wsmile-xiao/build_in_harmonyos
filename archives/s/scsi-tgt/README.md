# scsi-tgt

SCSI target daemon and administration tool for Linux/OpenHarmony.

## 软件信息

- **官方网站**: https://github.com/fujita/tgt
- **源码地址**: https://github.com/fujita/tgt/archive/refs/heads/master.zip
- **编译版本**: latest (master 分支)
- **编译状态**: published

## 功能介绍

scsi-tgt 是一个 SCSI target framework，提供：
- **tgtd**: SCSI target daemon，提供 SCSI 设备服务
- **tgtadm**: SCSI target 管理工具，用于配置和管理 target
- **tgtimg**: SCSI target image 工具，用于创建和管理镜像文件

## 编译历史

| 版本 | 编译日期 | 状态 | 补丁数 |
|------|---------|------|--------|
| latest | 2026-06-08 | published | 3 |

详见各版本目录下的 `manifest.yaml` 和 `notes.md`。

## 已知平台适配问题

1. **pthread_cancel**: musl 不支持 pthread_cancel，需替换为 pthread_kill
2. **strict-prototypes**: 函数声明需补充参数类型
3. **install 命令**: 系统提供的 install 脚本有 bug，建议使用 busybox install

## 安装方式

预编译包：`scsi-tgt-latest-ohos-aarch64.tar.gz`（404KB）

安装方法：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- scsi-tgt latest
```

验证安装：
```bash
~/usr/local/sbin/tgtd --version
# 输出: 1.0.97
```

## 注意事项

- 本软件为 SCSI target framework，主要用于存储设备仿真
- 编译时无 configure 步骤，直接使用 make
- 文档（man 页面）未生成，不影响核心功能