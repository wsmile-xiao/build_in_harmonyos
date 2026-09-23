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

## CI 适配修复 (2026-09-04)

- 移除硬编码设备路径 (/storage/Users/currentUser/usr/local/...)
- libpipeline 始终从源码构建（CI 环境无系统安装版本）
- libpipeline 下载改用 Debian 镜像 (savannah 服务器 502)
- nroff wrapper 改用 /bin/sh shebang，仅在 groff 可用时创建
- test.sh shebang 从 /data/service/hnp/bin/bash 改为 /bin/sh
- 修复 JC6 多包冲突：rebase 到最新 main，仅保留 man-db 提交

## CI 修复续 (2026-09-18, 构建失败 "no supported database library/header found")

- 根因 1: generate() 缺少 AutotoolsDeps — conan 依赖 (gdbm/zlib) 的 -I/-L/-l
  从未进入 configure 环境。之前本地 conan-verify 侥幸通过是因为设备 shell
  遗留 CPPFLAGS=-I~/usr/local/include 且探索阶段手动装过 gdbm；CI 干净环境
  直接报 "Fatal: no supported database library/header found" (L2)
- 修复 1: generate() 添加 AutotoolsDeps(self).generate() (L2)
- 根因 2: AutotoolsDeps 注入 LIBS="-lgdbm" 后，configure conftest 链接
  libgdbm.so 但 OHOS loader 无 conan cache 搜索路径 → "cannot run C
  compiled programs" (E524 同族问题)
- 修复 2: 按 aaphoto/0.45 模式给 build scope 注入 LD_LIBRARY_PATH (L2)
- 根因 3: man-db 内部库 libman/libmandb 默认构建为 .so 并安装到 lib/man-db/
  （RUNPATH=//lib/man-db 绝对路径），包内运行时无法解析 → 二进制大量符号缺失
- 修复 3: configure 加 --disable-shared --enable-static 静态化内部库 (L2)
- 根因 4: test_package 用 Conan 1.x 的 self.deps_env_info（Conan 2 已移除）
- 修复 4: 改用 self.dependencies["man-db"].package_folder + cpp_info.bindirs，
  test() 通过 sh test.sh 真实执行 man --version (L3)
- 本地复验: conan create (ohos-aarch64 profile) 完整通过，test_package
  输出 "man 2.13.1 / man-db test passed"
---

**编译结束**: 2026-09-18 18:45
**最终状态**: published
