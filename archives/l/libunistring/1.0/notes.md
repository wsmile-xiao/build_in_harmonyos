# libunistring 1.0 编译进度

**日期**: 2026-04-13
**状态**: ✅ 编译成功（作为 boxes 依赖编译）

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 在 boxes vendor 目录下下载解压 |
| Step 2 patches | ✅ | 更新 config.guess/config.sub 添加 HarmonyOS 识别 |
| Step 3 configure | ✅ | 使用 --enable-static --prefix |
| Step 4 make | ✅ | 编译成功 |
| Step 5 install | ✅ | 安装到 ohos-install 目录 |
| Step 6 safety | ⏭️ | 跳过（库文件） |
| Step 7 check | ⏭️ | 跳过（作为依赖库） |
| Step 8 staging | ✅ | 预编译包已创建 |
| Step 9 package | ✅ | libunistring-1.0-harmonyos-aarch64.tar.gz |
| Step 10 deploy | ⏳ | 待分发 |
| Step 11 finish | ✅ | 归档完成 |

## 发现与知识

### 问题 1: config.guess 无法识别 HarmonyOS
**症状**: configure 报错 "cannot guess build type"
**解决方案**: 
1. 下载 GNU config 最新版 config.guess/config.sub
2. 在 config.guess 中添加 HarmonyOS case 分支
3. 在 config.sub 中添加 ohos-linux 和 ohos* 识别

### 问题 2: socklen_t 类型缺失
**症状**: configure 报错 "Cannot find a type to use in place of socklen_t"
**原因**: HarmonyOS SDK 的类型定义机制与 configure 检测逻辑冲突
**解决方案**: 创建 config.cache 预置检测结果

### 问题 3: 临时目录权限问题
**症状**: configure 创建乱码目录名
**解决方案**: 修改 config.status 使用可写临时目录

## 编译产物

- **静态库**: libunistring.a (5.3MB)
- **动态库**: libunistring.so.2.2.0 (2.9MB)
- **头文件**: unitypes.h, unistring.h 等
- **安装路径**: vendor/libunistring-1.0/ohos-install

## 依赖关系

- 被依赖: boxes 2.3.1


---

**编译结束**: 2026-04-15 22:43
**最终状态**: success


---

**编译结束**: 2026-04-15 22:45
**最终状态**: successs

---

**编译结束**: 2026-04-15 22:47
**最终状态**: succes

## 2026-07-25 Conan adaptation
- Added Conan 2 recipe for `libunistring/1.0` using Autotools.
- Source URL and sha256 were recorded from GNU upstream tarball.
- Recipe builds static library by default and applies existing HarmonyOS config patches.
- Added consumer `test_package` covering `u8_strlen` and `u8_check`.
- Dependency issue: #1436.

## 2026-07-25 CI iteration
- Removed `0004-lib-libunistring.sym-t1.patch` from `conandata.yml` because the upstream 1.0 tarball does not contain `lib/libunistring.sym-t1`; CI failed before configure when trying to apply it.
- Updated recipe to run configure through `CONFIG_SHELL ./configure` because direct execution from HMDFS returned permission denied.
- Updated recipe to use `/system/bin/sh ./configure` because profile `CONFIG_SHELL=/data/service/hnp/bin/bash` is inaccessible in the CI shell.
- Recipe now overrides `SHELL` and `CONFIG_SHELL` to `/system/bin/sh` during build so configure does not use inaccessible profile bash.
