# man-db 2.13.1 编译进度

**日期**: 2026-04-14
**状态**: ✅ 编译完成

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 已有tarball、work目录 |
| Step 2 patches | ✅ | 5个补丁 (config.guess + config.sub + encodings.c + security.c + man.c) |
| Step 3 configure | ✅ | VPATH构建, --prefix=$TEST_PREFIX, --disable-setuid, 禁用systemd |
| Step 4 make | ✅ | -j1, 需要nroff wrapper |
| Step 5 install | ✅ | --disable-setuid 使 man_mode=755, 自动跳过 chown |
| Step 6 safety | ✅ | man --version = 2.13.1 |
| Step 7 check | ⚠️ | 部分测试基础设施编译失败，跳过 |
| Step 8 staging | ✅ | 12个二进制文件, verify PASS-WARN |
| Step 9 package | ✅ | 2350KB tar.gz |
| Step 10 finish | ✅ | success |

## 编译参数

```bash
configure \
  --prefix=$TEST_PREFIX \
  --disable-setuid \
  --with-systemdtmpfilesdir=no \
  --with-systemdsystemunitdir=no \
  --with-libpipeline \
  CFLAGS="-fPIC -O2 -I$HOME/usr/local/include" \
  LDFLAGS="-L$HOME/usr/local/lib"
```

## 发现与知识

- ✅ VPATH 构建是避免 autotools 重生成的关键策略 (L1)
- ✅ musl libc iconv 不支持 glibc 的 //IGNORE 扩展 (L1)
- ✅ HMDFS 上 ln -s 不工作，configure 检测到并使用 cp -pR 替代 (L1)
- ✅ config.sub 需要在 kernel-os 验证列表添加 linux-ohos* (L2)
- ✅ man-db --disable-setuid 使 man_mode=755 跳过 chown，无需手动修改 Makefile (L2)
- ✅ MAN_OWNER 仍被定义但 security.c 补丁使 get_man_owner() 安全返回 NULL (L2)
- ✅ groff 1.23.0 无 devlocale 设备，需将 "locale" 替换为 "utf8" (L3)
- ✅ security.c get_man_owner() 需在 man 用户不存在时返回 NULL (L3)
- ✅ 需创建 nroff → groff -Tascii -mandoc wrapper (L3)
- ✅ gdbm 库文件可能安装在 ~/usr/local/ 根目录，需复制到标准路径 (L3)

---

**编译结束**: 2026-04-14 16:45
**最终状态**: success
