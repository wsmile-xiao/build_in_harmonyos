# htop 3.4.1 编译进度

**日期**: 2026-04-14
**状态**: ✅ 完成（partial - 平台限制）

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | ghfast.top 加速下载 418K |
| Step 2 patches | ✅ | 3 个补丁（build-aux/config.guess + config.sub + IOPriorityPanel.h） |
| Step 3 configure | ✅ | NCURSES_CFLAGS/LIBS 指定，70s |
| Step 4 make | ✅ | -j$(nproc)，一次通过 |
| Step 5 install | ✅ | DESTDIR staging 安装 |
| Step 6 safety | ✅ | sign-elf 签名通过 |
| Step 7 check | ⏭️ | htop 无官方测试套件，手动验证 --version |
| Step 8 staging | ✅ | NEEDED 仅 libc.so，ncursesw 静态嵌入 |
| Step 9 package | ✅ | 539K 主包 + 117K debug |
| Step 10 deploy | ✅ | 已复制到 $HOME/usr/local/bin/htop |
| Step 11 finish | ✅ | 归档完整 |

## 发现与知识

- htop config.guess/config.sub 在 `build-aux/` 子目录（不在根目录）
- patch-autotools-ohos.pl 漏加 kernel-os 白名单 `linux-ohos*`，需手动补充
- ncursesw 静态嵌入（因为只有 .a），NEEDED 仅 libc.so
- 需要 sudo 运行（/proc/stat SELinux 限制）

---

**编译结束**: 2026-04-14 00:14
**最终状态**: partial

---

**编译结束**: 2026-04-14 00:15
**最终状态**: partial

---

**编译结束**: 2026-04-14 00:16
**最终状态**: partial

---

**编译结束**: 2026-04-14 00:49
**最终状态**: partial
