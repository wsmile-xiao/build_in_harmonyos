# yell 1.1 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile 仅作参考，构建用等价单次 clang 调用）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4
- 状态: built

## 上游与许可证
- 上游：critical.ch/yell（作者 ehaupt = FreeBSD audio/yell port MAINTAINER），
  经 distcache local-distfiles 分发；tarball 仅 4 文件，919 字节。
- 许可证：BSD2CLAUSE（FreeBSD port 记录）。tarball **无许可证文件**，
  归档侧以 `licenses/LICENSE`（归属说明 + BSD-2-Clause 标准文本）兜底。
- 同名歧义已排除：rudionrails/yell 是 Ruby gem（2.2.2）、jfcg/yell 是 Go
  库，均与 C 版 yell 1.1 无关；版本 1.1 精确匹配 FreeBSD audio/yell。

## 编译步骤
上游 Makefile 的 install 目标硬编码 `/usr/local/bin` + `chown root` +
`chmod 4110`（setuid），不适用；取 port `do-build` 单行命令为等价构建：

```bash
clang -O3 -DNDEBUG -Wall yell.c -o yell
```

（recipe 内编译器 stdio 重定向到 yell-build.log 再回显——/system/bin/sh
做 recipe shell 时直连捕获管道会静默 exit 1，zpaq 7.15 同坑。）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clang 报 `dev/speaker/speaker.h: No such file` | FreeBSD 内核头，OHOS 无 | 补丁 0001：该 include 替换为 `<unistd.h>`（见下） |
| 2 | 删 include 后 `write`/`close` 隐式声明告警 | 二者原经 speaker 头传递引入 | 同一补丁显式加 `<unistd.h>`，仅删不加会留告警 |
| 3 | 运行期无 PC speaker | `/dev/speaker` 在 OHOS 不存在 | 属预期：`play()` 的 `open` 有 `if (handle >= 0)` 守卫，退出码 0 优雅降级，test_package T4–T6 断言该契约 |

## 源码修改

- `patches/0001-speaker-include-unistd.patch`：`yell.c` 的
  `#include <dev/speaker/speaker.h>` → `#include <unistd.h>`。
  speaker.h 中声明未被代码使用（仅 open/write/close 三个 syscall）；
  FreeBSD port 的 `ONLY_FOR_ARCHS=i386 amd64` 来自内核 speaker(4) 设备，
  非 C 源码限制，aarch64 用户态编译干净（-Wall 零告警）。

## 依赖版本

- 零外部依赖（唯一系统要求是 libc：open/write/close）。

## 验证结果

```bash
# conan create 全绿后（见 reports/）：
bin/yell  # ELF64 AArch64, DT_NEEDED 仅 libc.so
# 运行退出码 0（无输出），二次运行幂等
# test_package 6/6 断言通过（T1 安装产物/T2 ELF arch/T3 NEEDED/T4-T6 运行契约）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/yell | 18816 B | ELF64 AArch64 CLI，动态链接 musl libc |

## 注意事项

- 上游无测试套件（Makefile 仅 default/install/deinstall），上游测试 = 0 项，
  功能验证由 test_package 的 6 项端到端断言承担。
- OHOS 无 PC speaker 硬件，yell 在本平台的运行语义是「安全空操作」——
  编译验证可用，实际发声无意义（研判笔记 #16 的 direct⚠️ 预期一致）。
---

**编译结束**: 2026-09-28 14:50
**最终状态**: built
