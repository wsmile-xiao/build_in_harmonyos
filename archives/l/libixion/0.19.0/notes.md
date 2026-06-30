# libixion 0.19.0 编译笔记

## 源码信息
- 来源: deepin-community/libixion tag 0.19.0-4
- 许可证: MPL-2.0

## 依赖
- mdds-2.1.1 (header-only)
- Boost 1.84 program_options

## HMDFS 适配
### 问题1: umask 权限
configure 文件中 `umask 077` 导致 HMDFS 文件系统权限问题，修改为 `umask 022`

### 问题2: config.guess/config.sub 过旧
替换为最新版本以支持 aarch64-linux-gnu

## 编译选项
```bash
./configure --prefix=$HOME/usr/local \
    --build=aarch64-linux-gnu \
    --disable-python \
    --enable-static-boost
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 产物
- libixion-0.18.so (共享库)
- ixion-parser (解析器工具)
- ixion-sorter (排序工具)
- ixion-formula-tokenizer (公式分词器)
