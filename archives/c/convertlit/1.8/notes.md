# convertlit 1.8 适配笔记

## 编译环境

- 构建系统：plain Makefile（`lib/` 后 `clit18/`）
- 编译日期：2026-09-08
- 目标：HarmonyOS / OHOS armv8，Clang 15
- 本地先行验证：macOS arm64，Apple Clang 17

## 上游与依赖预检

- 上游 1.8 源码只由官方站点以 HTTP 发布；配方使用 MacPorts 的 HTTPS
  权威分发镜像。下载文件的 SHA256 与 Homebrew、MacPorts 公布值一致。
- `libtommath/1.3.0` 已通过
  `conan download libtommath/1.3.0 -r=ohpcd --only-recipe` 确认发布。
- 主仓归档、origin/upstream 任务分支均未发现 convertlit/1.8 重复项。

## 上游测试清点（修改前）

- 测试目录：0
- Makefile `test`/`check` 目标：0
- 上游自动化测试总数：0
- 证据：原始 zip 共 51 项，仅 README、`clit18/`、`lib/`；两个
  Makefile 只提供 `all`、产物目标和 `clean`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `gcc` 和 `../libtommath-0.30` | 2004 年源码假设同级内置依赖，不能接受 Conan 工具链/依赖 | 改用 `$(CC)`、`$(AR)`、`$(LDFLAGS)`、`$(LDLIBS)`；配方把 libtommath 复制到 build-folder 私有 prefix |
| 2 | Clang 报 LZX、`memset`、`isalnum`、`mkdir` 等隐式声明 | 源码缺少标准头和旧 LZX API 声明 | 添加标准头，并从 newlzx 头包含旧 LZX 声明 |
| 3 | `dir_program[MAX_PATH]` 越界、格式字符串不安全、`size_t` 使用 `%d` | 上游旧代码缺陷 | 修正终止下标，改用 `fputs`、`S_ISDIR`、`%zu` |
| 4 | 官方源码只有 HTTP | 当前 PF7 要求 HTTPS | 使用 MacPorts 权威 HTTPS distfiles 镜像，SHA256 与官方下游配方一致 |

## 源码修改

`0001-modern-c-and-portable-build.patch` 是通用 POSIX/现代 C 修复，不包含
`__OHOS__` 条件分支、不删除功能、不引入 stub。核心修复与 MacPorts
`implicit.patch`、Debian `1030-missing-prototypes.patch` 一致，额外纳入
Debian 的安全/可移植性修正。

## 依赖版本

- libtommath/1.3.0（静态库，已发布）

## 验证结果

- 原始源码 + Apple Clang 17：因 LZX/标准函数隐式声明失败（已复现）。
- 应用补丁 + libtommath 1.3.0：`lib/openclit.a` 与 `clit18/clit` 构建成功。
- `clit` 无参数运行：非零退出并输出 `ConvertLIT (Version 1.8)`。
- 22 字节伪 LIT：非零退出并输出 `LIT FORMAT ERROR: File is too small`。
- HarmonyOS CI build #9041：编译与原有 4/4 消费者断言通过。
- 新增 OHOS 目标产物检查：验证打包后的 `clit` 是小端 ELF64 AArch64，
  防止误打包宿主机或错误架构二进制；须由下一轮 CI 执行该新增检查。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/clit` | ConvertLIT 1.8 命令行工具 |
| `licenses/COPYING` | GPL-2.0-or-later 许可证文本 |

## 已知限制

- 上游没有可合法随配方分发的完整 LIT 测试样本，因此消费者测试覆盖
  程序启动、版本信息与真实解析器的损坏输入拒绝路径；不伪造端到端电子书。

---

**编译结束**: 2026-09-09
**最终状态**: built（HarmonyOS CI build #9041 已通过；新增的 OHOS ELF
目标产物检查等待下一轮 CI 复验）
