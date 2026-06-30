# sqlmap

sqlmap is an open source penetration testing tool that automates the process of detecting and exploiting SQL injection flaws and taking over database servers.

## 依赖
- python3 (系统自带 Python 3.12)
- 所有第三方依赖内嵌在 thirdparty/ 目录中

## OHOS 适配要点
- sqlmap是纯Python项目，无需任何源码修改即可在鸿蒙上运行
- 安装方式：复制源码到 share/sqlmap/ + 创建wrapper脚本到 bin/
- 无ELF二进制文件，无需签名/RPATH/strip等处理

## 官方网站
- https://sqlmap.org
- https://github.com/sqlmapproject/sqlmap