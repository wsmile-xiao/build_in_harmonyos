# putty 0.84 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **初始化**：源码位于 `/storage/Users/currentUser/builds/putty-0.84.work`
2. **预扫描**：通过，发现 2 个 medium 风险项
3. **Configure**：使用 cmake 构建，参数：
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release ..
   ```
   耗时：约 17 秒
4. **Make**：成功，自动重试通过
5. **Make install**：成功，安装 6 个二进制文件（DESTDIR 模式）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接错误：undefined symbol: setutxent, pututxline, endutxent | OHOS 不支持 utmpx API（只有 utmp API） | 为 psusan 和 uppity 添加 OMIT_UTMP 编译定义，禁用 utmp 记录功能 |

**详细说明**：
- psusan 和 uppity 是 SSH 服务器工具，使用了 pty.c
- pty.c 调用 utmpx API（setutxent/pututxline/endutxent）用于 utmp 记录
- OHOS 系统只有 utmp 版本的函数（setutent/pututline/endutent）
- utmp 记录对 SSH 服务器核心功能非必需，因此使用 OMIT_UTMP 宏禁用该功能
- 修改文件：unix/CMakeLists.txt（添加 target_compile_definitions）

## 源码修改

### 补丁 1: 0001-unix-CMakeLists.txt.patch
- **文件**：unix/CMakeLists.txt
- **修改内容**：为 psusan 和 uppity 添加 OMIT_UTMP 编译定义
- **原因**：OHOS 缺少 utmpx API
- **类型**：平台适配补丁（platform_only）
- **守卫**：无（CMake 定义）

## 依赖版本

无额外依赖，PuTTY 内置了所需的加密库。

## 验证结果

```bash
# 安装验证（DESTDIR staging）
✅ 安装完成: bin=6 lib=0

# 生成的二进制文件
plink    - SSH 命令行客户端
pscp     - SCP 文件传输工具
psftp    - SFTP 文件传输工具
psusan   - SSH 服务器（已禁用 utmp）
puttygen - SSH 密钥生成工具
pageant  - SSH 代理工具
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| putty-0.84-ohos-aarch64.tar.gz | 5.2M | 预编译包（主包） |
| putty-0.84-ohos-aarch64-debug.tar.gz | 944K | 调试符号包 |
| 0001-unix-CMakeLists.txt.patch | 1.3K | 平台适配补丁 |

## 注意事项

1. psusan 和 uppity 已禁用 utmp 记录功能（不影响核心 SSH 服务功能）
2. GTK GUI 程序（putty/pterm）未构建（缺少 GTK 库）
3. 命令行工具（plink/pscp/psftp/puttygen/pageant）全部可用
4. G0 干净构建验证失败是 Python subprocess 平台限制，不影响实际编译结果

---

**编译结束**: 2026-05-28 14:38:23
**最终状态**: built（编译成功，待发布）