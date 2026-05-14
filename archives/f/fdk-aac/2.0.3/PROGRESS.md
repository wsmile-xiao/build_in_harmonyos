# fdk-aac 2.0.3 编译进度

**日期**: 2026-05-06
**状态**: ✅ 编译完成（partial）
**构建系统**: cmake（autotools 失败，改用 cmake）

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 下载、解压、初始化归档 |
| Step 2 patches | ⚠️ | E007: config.guess/config.sub 不识别 HarmonyOS |
| Step 3 configure | ✅ | cmake 构建成功（autotools 因 HMDFS 权限失败） |
| Step 4 make | ✅ | 编译 libfdk-aac.so |
| Step 5 install | ✅ | DESTDIR staging 安装 |
| Step 6 safety | ✅ | 无可执行文件，库安装验证 |
| Step 7 check | ⚠️ | 无测试套件 |
| Step 8 staging | ✅ | staging 目录结构正确 |
| Step 9 package | ✅ | 打包 fdk-aac-2.0.3-ohos-aarch64.tar.gz |
| Step 10 deploy | ✅ | 本地安装验证 pkg-config |
| Step 11 finish | ✅ | 归档收尾（状态: partial） |

## 发现与知识

### 问题 1: config.guess 不识别 HarmonyOS (E007)

**现象**: 
```
./config.guess: unable to guess system type
uname -s = HarmonyOS
```

**根因**: GNU config.guess 脚本不包含 HarmonyOS 检测分支

**解决**: 
1. 在 config.guess 的 case $UNAME_SYSTEM 中添加 HarmonyOS 分支
2. 在 LIBC 检测中添加 __OHOS__ 宏检测
3. 在 aarch64:HarmonyOS:*:* 分支返回正确三元组

### 问题 2: autotools config.status 临时目录权限失败

**现象**:
```
./config.status[1017]: can't create ./confXXXXXX/subs1.awk: Permission denied
```

**根因**: HMDFS 文件系统上，mktemp 使用 umask 077 创建的临时目录与当前进程权限不匹配

**解决**: 改用 cmake 构建系统（fdk-aac 同时支持 autotools 和 cmake）

### 问题 3: 无测试套件

**现象**: fdk-aac 无 make check 目标

**根因**: 项目为纯库，未集成测试套件

**解决**: 创建 test-report.md 记录"无测试套件"

## 编译参数

### cmake 配置
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local
```

### 编译输出
- `libfdk-aac.so` (2.1MB)
- 头文件: 6 个（aacenc_lib.h, aacdecoder_lib.h, FDK_audio.h 等）

## 知识沉淀建议

1. **E007 扩展**: config.guess HarmonyOS 检测方案
2. **新知识**: HMDFS 临时目录权限问题（影响所有 autotools）
3. **构建系统**: cmake 作为 autotools 失败时的备选方案

---

**编译开始**: 2026-05-06 18:06
**编译结束**: 2026-05-06 18:22
**最终状态**: partial
**编译耗时**: 约 16 分钟
---

**编译结束**: 2026-05-07 15:15
**最终状态**: partial

---

**编译结束**: 2026-05-07 15:16
**最终状态**: partial

---

**编译结束**: 2026-05-07 15:16
**最终状态**: partial

---

**编译结束**: 2026-05-07 15:17
**最终状态**: partial

---

**编译结束**: 2026-05-07 15:18
**最终状态**: partial
