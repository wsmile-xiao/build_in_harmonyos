# libimobiledevice-glue 1.3.0 编译记录

## 编译环境
- 平台: HarmonyOS (OpenHarmony)
- 编译器: clang
- 构建系统: autotools
- 状态: built

## 依赖
- libplist 2.3.0 (已安装)

## 编译步骤

1. 下载源码
   ```bash
   curl -k -L -o libimobiledevice-glue-1.3.0.tar.bz2 \
     "https://github.com/libimobiledevice/libimobiledevice-glue/releases/download/1.3.0/libimobiledevice-glue-1.3.0.tar.bz2"
   tar -xjf libimobiledevice-glue-1.3.0.tar.bz2
   ```

2. Configure
   ```bash
   export CC=clang
   export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig
   ./configure --prefix=~/usr/local
   ```

3. 修复 config.status 权限问题
   ```bash
   sed -i 's/umask 077 && mktemp -d/mktemp -d/g' config.status
   ./config.status
   ```

4. 编译安装
   ```bash
   make -j2
   make install
   ```

## 验证
```bash
pkg-config --modversion libimobiledevice-glue-1.0
# 输出: 1.3.0
```

## 关键发现
- HarmonyOS autotools 临时文件权限问题：需移除 config.status 中的 `umask 077`

---
**编译结束**: 2026-05-20 16:15
**最终状态**: published
