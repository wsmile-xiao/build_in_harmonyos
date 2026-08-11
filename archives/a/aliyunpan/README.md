# aliyunpan

阿里云盘命令行客户端，支持 JavaScript 插件与同步备份功能。

- 上游仓库：https://github.com/tickstep/aliyunpan
- 许可证：Apache-2.0
- 语言：Go（CGO_ENABLED=0，纯静态）
- 适配路径：路径 A（基础适配）

## 版本

| 版本 | 状态 | 构建日期 |
|------|------|----------|
| 0.4.0 | built | 2026-08-11 |

## 用法

```bash
aliyunpan            # 进入交互式 shell
aliyunpan login      # 登录
aliyunpan ls         # 查看文件列表
aliyunpan upload     # 上传文件
aliyunpan download   # 下载文件
aliyunpan --version  # 输出版本
```

## OHOS 适配要点

- Go 工具链与产物均需 binary-sign-tool 签名（Seccomp 拦截未签名 ELF）
- Go linker 链接输出必须放到非 hmdfs 工作区
- 上游 TestBoltUltraFiles 硬编码作者 macOS 路径，任何标准环境不可运行，以 -skip 排除并记录
