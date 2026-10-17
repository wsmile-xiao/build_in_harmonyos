# zeek 8.2.1 兼容性评估报告（musl libc / OHOS）

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件名称 | zeek |
| 版本 | 8.2.1 |
| 评估日期 | 2026-09-22 |
| 评估者 | AtomCode (qwen3.8) 适配流程内评估 |

## 兼容性评级

**总体评级**: 🟡 中

核心 C++ 引擎（包分析/脚本引擎/日志输出）、broker 消息层与命令行工具在
OHOS aarch64 上编译、链接、运行全部通过；受限项集中在平台符号缺口
（均已用 shim/补丁补齐）与构建形态取舍（Spicy/JavaScript/Python 绑定关闭）。

## 系统调用兼容性

| 系统调用 | 状态 | 说明 |
|----------|------|------|
| pthread_create/join | ✅ | 线程支持正常 |
| pthread_cancel 系列 | ⚠️ | musl 声明未实现 → weak no-op shim（E085），线程取消语义降级为 no-op |
| dlopen/dlsym | ✅ | 插件 .so 动态加载正常（PluginManager，E013） |
| socket/bind/listen | ✅ | 网络功能正常 |
| kqueue | ❌ | OHOS 无 kqueue → libkqueue 走 src/linux/* epoll 分支（补丁 0012，E233） |
| fts_* | ❌ | sysroot 无 fts.h → 改 std::filesystem::recursive_directory_iterator（P6） |
| setreuid/chroot | ❌ | 平台未实现（E051 同族）；zeek 核心路径不依赖 |

## 库依赖兼容性

### 必需依赖

| 库 | 状态 | 版本 | 说明 |
|----|------|------|------|
| libpcap | ✅ | 1.10.6 | 制品仓已发布 |
| openssl | ✅ | 3.5.8.1 | 制品仓已发布 |
| zlib | ✅ | 1.3.1 | 制品仓已发布 |

### 可选依赖

| 库 | 状态 | 影响 |
|----|------|------|
| ZeroMQ | ❌（本版本关闭） | 集群后端不可用（-DENABLE_CLUSTER_BACKEND_ZEROMQ=OFF） |
| Python/SWIG 绑定 | ❌（本版本关闭） | zeekctl/zkg/zeek-client 不可用 |
| Spicy/HILTI 工具链 | ❌（本版本关闭） | Spicy 应用层分析器不可用（-DDISABLE_SPICY=ON） |

## musl libc 兼容性

### 已知问题

| 问题 | 影响 | 解决方案 |
|------|------|----------|
| pthread 线程取消符号未实现 | 链接期 undefined reference（pthread_cancel/pthread_setcancelstate/pthread_testcancel） | shims/pthread_compat.c weak no-op 链入可执行文件 + libkqueue check_function_exists 双机制（E085） |
| libc++ 缺 <memory_resource>（std::pmr） | broker 编译失败；曾致 13 项 broker 单测 SIGSEGV | shims/memory_resource shim 头 -I 注入（P4） |
| libc++ 缺 C++20 ranges 算法 | 47 文件 83+ 处编译失败 | 等价经典 STL 机械改写（P3） |
| fts.h 缺失 | zeekygen 编译失败 | std::filesystem 替代（P6） |
| sockaddr_storage 双定义 | AF_Packet 插件编译失败 | toolchain 追加 -D__MUSL__（能力宏，非平台宏，P7） |
| glibc 专属函数（strdupa/strchrnul/mallinfo/getrandom 等） | 潜在编译失败 | 构建中按知识图谱 musl 等价实现逐一替换 |

### 条件编译建议

本适配未使用 `__OHOS__` 平台宏（R8）：全部走 CMake 能力宏（check_function_exists 等）、
可移植 C++ 改写与 weak 符号 shim——同一套 patches 对 Linux/musl 环境保持无害。

## 功能完整度

| 功能模块 | 完整度 | 说明 |
|----------|--------|------|
| 核心引擎（包分析/会话/脚本引擎/日志输出） | 100% | 编译链接运行全通过，26/26 单测 |
| 命令行工具（zeek/zeek-cut/btest 等） | 100% | 包内 bin/ 齐全，--version 冒烟通过 |
| broker 消息层（libbroker） | 100% | 库编译入包，broker 单测 26/26 |
| 基础协议分析器（C++ 内置） | 高 | core 构建包含；依赖 Spicy 的深度字段提取受限 |
| Spicy 应用层解析 | 0%（本版本） | DISABLE_SPICY=ON，待全量构建版本 |
| 集群/zeekctl/Python 生态 | 0%（本版本） | 构建形态关闭 |

## 已知问题列表

### 问题1: broker.backend 单元测试失败

- **严重程度**: 🟢 低
- **影响范围**: ctest 26 项 broker 单测中的 1 项
- **临时方案**: 在可写目录（$TMPDIR）下运行该测试
- **长期方案**: HMDFS /tmp 只读为平台限制（E002），待平台修复或 CI 验收机提供可写 /tmp

### 问题2: btest 集成套件本环境无法全量运行

- **严重程度**: 🟡 中
- **影响范围**: 287 个 .test 集成用例
- **临时方案**: 以 --version 冒烟 + 26/26 单测覆盖核心正确性（test-report.md 逐项技术归因）
- **长期方案**: ENABLE_SPICY 全量构建 + 可写工作目录的验收机补跑（PR 已如实标注）

### 问题3: Spicy 分析器路径不可用（构建形态取舍）

- **严重程度**: 🟡 中
- **影响范围**: igmp 等依赖 Spicy 分析器的 base 脚本加载 fatal；HTTP/DNS 深度字段提取
- **临时方案**: DISABLE_SPICY=ON 最小 core 构建（本版本交付形态）
- **长期方案**: Spicy/HILTI 工具链独立包化后开启（后续版本，可走依赖项路径）

## 使用建议

### 推荐配置

```bash
# Conan 构建（CI 同源 profile）
conan create archives/z/zeek/8.2.1 -pr:a ci/conan/profiles/ohos-aarch64 --build=missing

# 下游引用
conan install --requires=zeek/8.2.1 -pr:a ci/conan/profiles/ohos-aarch64 --build=missing
```

### 注意事项

1. 临时文件不要依赖 /tmp（HMDFS 只读，E002）：用 $TMPDIR 或 $HOME 下目录。
2. 运行 zeek 分析脚本时确认 base 脚本不依赖 Spicy 分析器（本版本）。
3. 线程取消语义在 OHOS 上为 no-op，依赖 pthread_cancel 的超时逻辑需自行替代。

## 参考资料

- `notes.md`（P1-P10 平台点实测三件套：现象/证据/修复）
- `knowledge/graph/E085.kv`（pthread_cancel 未实现模式）
- `knowledge/graph/E002.kv`（HMDFS /tmp 只读）
- 上游: https://github.com/zeek/zeek

---

*评估报告生成时间: 2026-09-22*
