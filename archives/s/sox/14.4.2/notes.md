# sox 14.4.2 编译笔记

## 编译过程

### 平台识别问题（E007）

**问题**：config.guess 无法识别 HarmonyOS 系统，报错 `unable to guess system type`。

**解决**：
1. 使用 perl 补丁脚本修复 config.guess：
   ```bash
   perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl ./config.guess ./config.sub
   ```
2. 手动修复 config.sub 添加 ohos-linux 识别
3. 修复 config.guess 的输出格式（GUESS → echo）

### Autotools 权限问题

**问题**：config.status 在当前目录创建临时目录失败，报错 `Permission denied`。

**原因**：HarmonyOS sandbox 限制在当前目录创建子目录。

**解决**：改用 CMake 构建。

### musl libc FILE 结构问题

**问题**：编译 src/formats.c 时报错 `#error FIX NEEDED HERE`。

**原因**：musl libc 不暴露 FILE 结构内部成员（_p、_r、_IO_read_ptr 等），无法实现 rewind_pipe。

**解决**：添加 `#elif defined __OHOS__ || defined __musl__` 分支，跳过 rewind_pipe 功能。

### CMake 构建成功

**构建命令**：
```bash
cd builds/sox-14.4.2.work
mkdir -p build && cd build
export CC=clang CXX=clang++
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DCMAKE_POLICY_VERSION_MINIMUM=3.5
make -j2
```

**安装验证**：
```bash
$STAGING_PREFIX/bin/sox --version
# 输出: SoX v14.4.2
```

## 依赖情况

- 无必需依赖
- 可选依赖（音频格式库）全部缺失，不影响基本编译
- 部分功能受限：无管道文件类型检测（rewind_pipe 跳过）

## 知识提取

- **E007**：config.guess/config.sub 平台识别问题（已有知识，应用成功）
- **新发现**：musl libc 不支持 FILE 内部结构，需在编译时跳过相关功能
- **新发现**：CMake 比 Autotools 更适合 HarmonyOS（避免 config.status 权限问题）

---
**编译结束**: 2026-05-25 20:00
**最终状态**: built
---

**编译结束**: 2026-05-25 20:03
**最终状态**: built
