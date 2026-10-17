# msfconsole 4.11.7 适配笔记

## 编译环境
- 构建系统: custom（Ruby 脚本 + C 工具程序混合体，非 autotools/cmake）
- 编译日期: 2026-09-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

msfconsole 是 Metasploit Framework 的 Ruby 控制台脚本，主体为 Ruby 代码不需要编译。
仅编译框架中可在 aarch64/OHOS 上运行的 C 工具程序：

```bash
# stat-key: POSIX stat() 工具
clang -fPIC -O2 -o tools/context/stat-key tools/context/stat-key.c

# time-key: POSIX time/strptime 工具（需 _GNU_SOURCE 启用 strptime）
clang -fPIC -O2 -D_GNU_SOURCE -o tools/context/time-key tools/context/time-key.c
```

Ruby 脚本（msfconsole、msfvenom、msfrpc 等）和库目录（lib/、modules/、data/）直接打包到 Conan 包中。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 嵌套源码检测错误提升 byakugan | byakugan 目录有 .cpp/.h 被误判为主源码 | 手动重新解压完整 tarball |
| 2 | cpuid-key.c 编译失败 | x86 inline asm (cpuid)，aarch64 不支持 | 跳过 — x86 专用工具 |
| 3 | cpuinfo.c 编译失败 | x86 __asm__("cpuid")，aarch64 不支持 | 跳过 — x86 专用工具 |
| 4 | memdump.c 编译失败 | #include <windows.h> — Windows 专用 API | 跳过 — Windows 专用工具 |
| 5 | serialport.c 编译失败 | #include <ruby.h> — Ruby C 扩展，非独立二进制 | 跳过 — 需要 Ruby 开发头文件 |
| 6 | time-key.c strptime 隐式声明 | 需要定义 _GNU_SOURCE | 编译时加 -D_GNU_SOURCE |

## 源码修改

无补丁，源码未修改。

## 依赖版本

无 Conan 依赖。Ruby gems 由用户在运行时通过 Gemfile 安装。

## 验证结果

```bash
# conan create 验证
conan create archives/m/msfconsole/4.11.7/conanfile.py -pr ci/conan/profiles/ohos-aarch64 --build=missing
# 结果: PASS (G1-G4 + L2/L4/L5 全部通过)

# test_package 验证
# - time-key: 输出 hex 时间 key，exit 0
# - stat-key: 无参数时 exit 1 (usage error)
# - msfconsole Ruby 脚本存在于 bin/
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（application 类型，custom 构建） |
| conandata.yml | 源码 URL + sha256 |
| test_package/ | L1 测试（test.c 调用 time-key 和 stat-key） |
| commands.json | CLI 工具声明（软件级） |
| manifest.yaml | 编译元数据 |

## 注意事项

- msfconsole 运行需要 Ruby 解释器和 Gemfile 中的 gems
- x86 专用工具（cpuid-key、cpuinfo）和 Windows 专用工具（memdump）已跳过
- serialport.c 是 Ruby C 扩展，需要 Ruby 开发头文件才能编译
- init-build 的嵌套源码检测会对包含 Windows 专用子目录的 Ruby 项目误判，需手动修复

---

**编译结束**: 2026-09-08 10:52
**最终状态**: built

<!-- audit: W4 passed, P2 fixes applied -->
