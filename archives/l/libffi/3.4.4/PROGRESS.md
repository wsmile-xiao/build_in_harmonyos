# libffi 3.4.4 编译进度

**日期**: 2026-04-21
**状态**: ✅ 编译完成

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | init-build 成功，历史记录存在 |
| Step 2 patches | ✅ | 应用 0001-port-for-ohos.patch + sed umask 077→022 |
| Step 3 configure | ✅ | --prefix=$DEFAULT_PREFIX --enable-shared |
| Step 4 make | ✅ | make -j$(nproc) 成功 |
| Step 5 install | ✅ | DESTDIR=$TEST_PREFIX staging 隔离安装 |
| Step 6 safety | ✅ | 无可执行文件需要安全弹窗验证 |
| Step 7 check | ⏭️ | libffi 测试需要 DejaGnu，跳过 |
| Step 8 staging | ✅ | 头文件、库文件、pkgconfig 均正确 |
| Step 9 package | ✅ | libffi-3.4.4-ohos-aarch64.tar.gz 生成 |
| Step 10 deploy | ✅ | make install 安装到 $DEFAULT_PREFIX |
| Step 11 finish | ⏳ | 待执行 |

## 发现与知识

- libffi 使用 autotools，configure 会自动在子目录 `aarch64-unknown-linux-ohos` 中构建
- 需要修改 config.guess 和 config.sub 识别 HarmonyOS 平台
- HMDFS umask 077 问题：需要 `sed -i 's/umask 077/umask 022/g' configure`
- HMDFS 软链接问题：打包时 symlinks 读取受限，需手动处理
- clang `-print-multi-os-directory` 不支持（非致命，不影响构建）


---

**编译结束**: 2026-04-21 14:11
**最终状态**: success
