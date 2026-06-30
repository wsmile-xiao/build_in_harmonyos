# pari 2.17.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: built

## 编译步骤
```bash
./Configure --prefix=/storage/Users/currentUser/usr/local
make -j$(nproc)
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-pari-2.17.3
make install
gp --version
```

## 验证结果
```
GP/PARI CALCULATOR Version 2.17.3
compiled: Jun  4 2026, clang version 15.0.4
```

## 交付物
- pari-2.17.3-ohos-aarch64.tar.gz (40.4 MB)
- pari-2.17.3-ohos-aarch64-debug.tar.gz (927 KB)