# lua-language-server 3.18.2 编译笔记

## 构建系统
lua-language-server 使用 luamake 构建系统（非标准的 configure/make）。

## 平台适配修改

### 1. build.sh (3rd/luamake/compile/build.sh)
- 修改平台识别：添加 `Linux|HarmonyOS` 支持
- 将 HarmonyOS 识别为 Linux 模式

### 2. linux.ninja (3rd/luamake/compile/ninja/linux.ninja)
- 编译器已使用 clang（符合 OpenHarmony 要求）
- 修改 cp 命令：`busybox cp` 替代 `cp`（OpenHarmony shell 限制）
- 修改 include 路径：`-I../bee.lua` 替代 `-Ibee.lua`
- 移除 `-lstdc++fs` 和 `-lstdc++` 链接选项
- 添加 `-lc++` 链接选项（OpenHarmony 使用 musl libc++）

### 3. lua_platform.cpp (3rd/bee.lua/binding/lua_platform.cpp)
- 添加 `__OHOS__` 平台识别
- 返回 "harmonyos" 作为平台标识

### 4. globals.lua (3rd/luamake/scripts/globals.lua)
- 修改编译器选择：Linux/HarmonyOS/NetBSD 使用 clang 而非 gcc

## 构建流程

1. 从 3.0.0 版本复制完整子模块（因网络问题无法直接克隆）
2. 在 compile 目录创建符号链接：`bee.lua -> ../bee.lua`
3. 构建 luamake bootstrap：
   ```bash
   cd 3rd/luamake/compile
   ninja -f ninja/linux.ninja bootstrap
   ```
4. 使用 luamake 构建 lua-language-server：
   ```bash
   3rd/luamake/luamake rebuild
   ```
5. 修改生成的 build.ninja 文件：
   - 移除 `-lstdc++fs`
   - 移除 `-Wl,--push-state,-Bstatic -lstdc++ -Wl,--pop-state`
   - 添加 `-lc++`
6. 链接最终二进制文件：
   ```bash
   ninja -f build/build.ninja lua-language-server
   ```

## 运行时文件

lua-language-server 需要完整的运行时目录结构：
- bin/lua-language-server（二进制）
- bin/main.lua（启动脚本）
- bin/script/（Lua 脓本库）
- bin/meta/（元数据）
- bin/locale/（本地化文件）
- bin/debugger.lua（调试器）

## 问题与解决方案

### 问题1：网络访问 GitHub 失败
- **原因**：无法直接克隆 GitHub 仓库
- **解决**：从已编译的 3.0.0 版本复制完整子模块

### 问题2：gcc 不存在
- **原因**：luamake 默认为 Linux 选择 gcc 编译器
- **解决**：修改 globals.lua，强制使用 clang

### 问题3：符号链接权限问题
- **原因**：OpenHarmony 文件系统对符号链接的 stat() 有权限限制
- **解决**：在 compile 目录复制 bee.lua 而不是符号链接

### 问题4：链接失败（缺少 C++ 标准库）
- **原因**：移除 `-lstdc++fs` 和 `-lstdc++` 后缺少 C++ 运行时
- **解决**：添加 `-lc++`（OpenHarmony 使用 musl libc++）

## 测试结果
- 二进制文件成功编译
- ELF 签名完成
- 运行测试通过（./lua-language-server --version）
---

**编译结束**: 2026-05-21 11:30
**最终状态**: built
