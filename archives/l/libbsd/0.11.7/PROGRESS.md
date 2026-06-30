# libbsd 0.11.7 编译进度

## 编译状态
- 状态：手动编译成功
- 时间：2026-04-29 20:45-20:46

## 关键修复

### 1. E011: HMDFS 权限问题
- 文件：configure
- 修改：`sed -i 's/umask 077/umask 022/g' configure`
- 原因：HMDFS 文件系统的 UID 映射导致 umask 077 创建的临时目录不可写
- 行号：17959, 17964

### 2. E007+E072: config.guess/config.sub 不支持 HarmonyOS
- 文件：build-aux/config.guess, build-aux/config.sub
- 修改：
  - config.guess: 添加 `aarch64:HarmonyOS:*:*` 分支
  - config.sub: 添加 `ohos-linux` 映射和 `ohos*` OS 白名单
- 原因：config.guess 无法识别 HarmonyOS 系统，config.sub 无法验证 linux-ohos 三元组

### 3. 依赖问题
- 问题：缺少 libmd.so 软链接
- 解决：创建 `ln -s libmd.so.0.1.0 libmd.so`

### 4. 依赖跟踪问题
- 问题：configure 在自动依赖跟踪时失败
- 解决：使用 `--disable-dependency-tracking` 选项

## 编译参数
- configure: `./configure --prefix=/storage/Users/currentUser/usr/local --disable-dependency-tracking`
- make: `make -j$(nproc)`
- install: `make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libbsd-0.11.7`

## 产物验证
- staging 目录：✅ 包含 libbsd.a, libbsd.so.0.11.7, libbsd.so, pkgconfig, 头文件
- 本地安装：✅ 已安装到 ~/usr/local

## 下一步
- 生成预编译包
- 执行 finish 流程