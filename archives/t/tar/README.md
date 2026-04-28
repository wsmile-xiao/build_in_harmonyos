# GNU tar

## 简介
GNU tar 是用于创建和提取归档文件的标准工具，支持多种格式（tar、gzip、bzip2、xz 等）。

## OHOS 适配
- 需修补 config.guess/config.sub 添加 HarmonyOS 平台识别
- 替代 toybox tar，支持 xattrs 等高级功能
- 17 个自动生成的补丁文件（config/Makefile 等）

## 依赖
- 无额外依赖

## 功能验证
```bash
tar --version
tar czf test.tar.gz /some/dir
tar xzf test.tar.gz
```

## 参考
- 官网: https://www.gnu.org/software/tar/
- 源码: https://ftp.gnu.org/gnu/tar/
