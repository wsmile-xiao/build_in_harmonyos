# PR 信息

- **三方库名称**：ekhtml
- **上游版本**：0.3.2
- **上游仓库地址**：https://downloads.sourceforge.net/project/ekhtml/ekhtml/0.3.2/ekhtml-0.3.2.tar.gz
- **适配路径**：路径 A（基础适配）
- **开源许可证**：BSD-2-Clause
- **使用知识库**：E213 方案（config.guess/sub HarmonyOS 检测，knowledge/graph/draft/E213-draft-4739.kv）

# 测试用例对比

## 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
| --- | --- | --- |
| 单元测试 | 0 | 上游无独立单元测试 |
| 集成测试 | 3 | testsuite/ 目录 3 个 shell 测试（test_basic.sh、test_bogus_feedsize.sh、test_crazypage.sh，用 tester + Python 脚本对比 HTML 解析输出） |
| 其他测试 | 0 | — |
| **合计** | **3** | |

## 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
| --- | --- | --- | --- |
| 消费者测试 | 1 | +1 | 链接 libekhtml，ekhtml_parser_new/datacb_set/feed/flush 解析 HTML 验证 data 事件 |
| **合计** | **1** | **+1** | |

# 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

# 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试套件（testsuite/ 3 个 shell 测试）

# 验证结果

- 编译状态：**通过**（本地 CI 模拟 L0/L1/L4/L5 全部通过）
- 上游测试用例通过率：3/3（100%，testsuite/ 3 个 shell 测试真机实测通过）
- 新增测试用例通过率：1/1（100%，test_package ekhtml 解析验证通过）

### 适配过程关键点

| 项 | 说明 |
| --- | --- |
| 源码下载 | ✅ 官方 tarball（sha256 1ed1f016... 与 FreeBSD distinfo 一致） |
| config.guess/sub 补丁 | ✅ 输出 aarch64-unknown-linux-ohos（E213 方案） |
| config.status 沙箱绕过 | ✅ umask 077→022 + 循环重跑（OHOS hmdfs 沙箱 0700 新目录禁写） |
| Makefile 变量污染修复 | ✅ make top_srcdir 命令行覆盖 + .deps 预建 + include 容错 |
| install | ✅ DESTDIR 重定向（--prefix=/ 装 /lib 只读问题） |

# 补充说明

- **构建方式**：Autotools（自带 configure），CC=clang
- **补丁**：
  - 0001-config-guess-ohos.patch — config.guess/sub HarmonyOS 检测（E213 方案）+ configure umask 022（OHOS 沙箱适配）
- **产物**：1 个静态库（libekhtml.a）
- **依赖**：无外部 Conan 依赖（纯 C，libc-only）
- **上游测试说明**：testsuite/ 3 个 shell 测试（tester + Python 脚本对比解析输出）真机实测 3/3 通过
