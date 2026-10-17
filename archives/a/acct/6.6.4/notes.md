# acct 6.6.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-04
- 编译器: clang 15.0.4
- 状态: built（probe_only_no_upload，首轮探测）

## 编译步骤

1. `ohc-run.py init-build acct 6.6.4 --url=http://ftp.gnu.org/gnu/acct/acct-6.6.4.tar.gz` — 下载、解压、骨架、环境检查全部通过
2. 编写 conanfile.py（AutotoolsToolchain，package_type=application）+ conandata.yml + test_package/
3. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing`
   - 首轮失败：configure 的 config.status 阶段 `./confNoHAhc/subs1.awk: Permission denied`
   - 根因：HarmonyOS 上 `mktemp -d` 创建目录权限为 `drwx--S---`，config.status 无法写入临时 awk 脚本
   - 修复：generate() 中创建 mktemp wrapper（exit 1），强制 autoconf AS_TMPDIR 走 mkdir fallback（与 bash 5.3 同源方案）
   - 二轮通过：configure → make → make install → make check → package → test_package 全部成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: `./confNoHAhc/subs1.awk: Permission denied` | HarmonyOS mktemp -d 生成 `drwx--S---` 权限目录 | generate() 中 mktemp wrapper exit 1，强制 mkdir fallback（与 bash 5.3 同源方案） |

## SYS_acct / accton(2) 核验

- `accton.c` 通过 libc 的 `acct()` 函数启用/关闭进程记账（`acct(ACCT_FILE_LOC)` / `acct(NULL)` / `acct(file)`），并未直接调用 `accton(2)`/`SYS_acct` 系统调用号
- 编译链接通过，`readelf -s` 显示 `acct` 为 UND 符号（由 libc 提供），无 undefined reference
- 结论：SYS_acct 编译无问题，无需 patch；accton 运行时是否受内核 syscall 限制需后续人工验证（属运行期行为，非编译期问题）

## 上游测试核验

- 上游无测试用例：源码包无 `tests/` 目录，`Makefile.am` 无 `TESTS` 定义，tar 包内无测试文件，无 `gltests` 目录
- `make check` 为空目标（`check-am: all-am`，子目录 "Nothing to be done"），退出码 0
- 上游测试通过率：`0/0（N/A，上游无测试用例）`
- 新增测试：`test_package` 冒烟测试 `ac --version` → `ac: GNU Accounting Utilities (release 6.6.4)` 通过

## 依赖版本

- 无第三方依赖（叶子库）
- 编译器: clang 15.0.4；make 4.4.1；autoconf 2.72；automake 1.16.5

## 验证结果

```bash
conan create . --build=missing  # 通过（含 make check 空目标 + test_package smoke）
ac --version                    # ac: GNU Accounting Utilities (release 6.6.4)
```

## 路径判断

- 路径 A 候选（1 分）：普通基础适配，纯 C + Autotools，无第三方依赖，一次闭环
- 测试框架/工具链 10 分候选：不申报（上游无测试用例，仅有空 make check 目标）
- HarmonyOS 系统差异新发现候选：mktemp -d 权限问题与 bash 5.3 完全相同，属已沉淀场景，非新发现；SYS_acct 编译期无差异
---

**编译结束**: 2026-08-04 17:45
**最终状态**: built
