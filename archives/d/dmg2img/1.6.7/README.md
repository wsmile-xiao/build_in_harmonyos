# dmg2img 1.6.7 — OpenHarmony 编译记录

## 基本信息
- 软件: dmg2img
- 版本: 1.6.7
- 构建系统: makefile
- 目标: ohos-aarch64
- 状态: success


### Autotools 构建命令
```bash
./configure []
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```


### 已应用补丁
- `0001-Makefile.patch` — 编译规则调整
- `0001-vfdecrypt.c.patch` — 问题修复



### 功能验证
```bash
# 安装后验证
~/usr/local/bin/bzip3 --version  # 或相应命令

# 基本压缩测试
echo 'test' > test.txt
bzip3 test.txt
bzip3 -d test.txt.bz3
cat test.txt
```
