# libffi 3.4.6 编译进度

**日期**: 2026-04-27
**状态**: ⚠️ 编译完成，待归档

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 源码已下载和解压到 ~/tmp/builds/ |
| Step 2 patches | ✅ | 应用 config.guess 和 config.sub 补丁 |
| Step 3 configure | ✅ | --prefix=$DEFAULT_PREFIX 成功 |
| Step 4 make | ✅ | meson 构建成功，生成 libffi.a 和 libffi.so |
| Step 5 install | ✅ | DESTDIR=$TEST_PREFIX staging 隔离安装 |
| Step 6 safety | ✅ | 无可执行文件需要安全弹窗验证 |
| Step 7 check | ⏭️ | libffi 测试需要 DejaGnu，跳过 |
| Step 8 staging | ✅ | 头文件、库文件、pkgconfig 均正确 |
| Step 9 package | ✅ | libffi-3.4.6-ohos-aarch64.tar.gz 已生成 |
| Step 10 deploy | ⏳ | 待执行 |
| Step 11 finish | ⏳ | 正在执行归档操作 |

## 发现与知识

- libffi 使用 meson 构建系统（在 builddir 子目录中）
- 需要修改 config.guess 和 config.sub 识别 HarmonyOS 平台
- 静态库和动态库都成功编译
- 已生成预编译包

## 编译产物

- 预编译包：`~/tmp/test-install-libffi-3.4.6/storage/Users/currentUser/usr/local/libffi-3.4.6-ohos-aarch64.tar.gz`
- 静态库：`~/tmp/test-install-libffi-3.4.6/storage/Users/currentUser/usr/local/lib/libffi.a`
- 动态库：`~/tmp/test-install-libffi-3.4.6/storage/Users/currentUser/usr/local/lib/libffi.so`

---

**编译结束**: 2026-04-27 09:38
**最终状态**: partial
---

**编译结束**: 2026-04-28 06:33
**最终状态**: partial
