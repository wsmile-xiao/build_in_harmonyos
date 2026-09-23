# DRAFT-conan-glob-packaging-loses-interpreter-library-scripts：conan 配方按 *.so*/*.a 通配打包丢失解释器/子包库脚本 → 运行失败

> Contributor: combat-0.8.1 适配（依赖 tcl/8.6.16 已发布包） | Status: Draft | Updated: 2026-09-11
> Source: archives/c/combat/0.8.1

## 现象

消费 tcl/8.6.16（已发布二进制包）的包在运行期报：

- `can't find package Itcl`（pkgIndex.tcl 缺失 → 包管理器找不到注册项）
- 裸 load 子包 .so：`Can't find a usable itcl.tcl in the following directories: ...`
  （Itcl_Init 找不到必需库脚本；错误自带"可设 ITCL_LIBRARY"提示）
- 同签名族：`can't find package Thread / tdbc / sqlite3`

## 根因分析

tcl 配方 `package()` 以二进制后缀通配收集 staging lib：`copy *.so*`、
`copy *.a` 只命中二进制/归档；`copytree` 仅显式覆盖 `lib/tcl8.6` 与
`lib/tcl8` 两个运行时目录。内嵌子包目录的 `.tcl` 库脚本与 `pkgIndex.tcl`
不匹配任何通配，被系统性剥离。

设备实查（已发布包 `~/.conan2/p/tcla4d5206af411b/p/lib/`）四个子包目录
全部只剩二进制：

| 子包目录 | 残留内容 | 丢失 |
|---|---|---|
| itcl4.3.2/ | libitcl4.3.2.so、libitclstub4.3.2.a | itcl.tcl、itclHullCmds.tcl、itclWidget.tcl、pkgIndex.tcl |
| sqlite3.47.2/ | .so | 全部脚本/索引 |
| tdbc1.1.10/ | .so、stub .a | 库脚本、pkgIndex.tcl |
| thread2.8.11/ | .so | 库脚本、pkgIndex.tcl |

第二实例（同签名族、独立 run）：同一 tcl 配方早期曾漏拷 `lib/tcl8.6`
运行时目录 → test_package 报 "Can't find a usable init.tcl"（CI 实测，
以 copytree 修复）。证据形态：配方内注释（最早提交 fcc2b3b412 即含），
无独立 run 报告文件。

复发面量化（设备 worktree 仓库根执行，scope 与 pattern 逐字固定）：

```sh
# 宽口径：conanfile.py 含 "*.so*" 字面 glob 的文件数 → 105
grep -rl --include=conanfile.py -e '"\*\.so\*"' archives/ | wc -l
# 窄口径：copy( 调用行匹配 *.so 的文件数 → 63
grep -rlE 'copy\(.*\*\.so' --include=conanfile.py archives/ | wc -l
```

## 解决方案

1. **主案（依赖配方，init.tcl 先例）**：对运行时脚本目录整目录
   `shutil.copytree`（保留 .tcl/pkgIndex.tcl），配"目录必须存在"守卫，
   逐子包核对 .so 之外的运行期必需文件。
2. **fallback（消费方自包含捆绑，仅退路）**：从与依赖 .so 同源同版本的
   上游源码（pinned sha256）提取缺失库脚本，随包放入自身 package 目录，
   并生成 pkgIndex.tcl：load 前先 `set ::env(ITCL_LIBRARY) $dir` 指向该
   目录（Itcl_Init 按编译期前缀与环境变量查库脚本）。权衡：不修依赖包、
   体积重复、同源漂移需锁定版本；combat/0.8.1 即按此退路落地并通过 CI
   （test_package "Itcl support (4.3.2)" PASS）。

## 禁止

- 禁止消费方在 `catch {package require ...}` 里静默回退而不补齐库脚本
  目录/不给出定位诊断——会把"打包剥离"转译成更隐晦的下游错误
  （combat.tcl 的 tcl++ 回退把 Itcl 缺失表现为 `can't find package tcl++`，
  而归档里根本没有 tcl++），根因被掩蔽、缺陷在更多消费方处复发。

## 验证证据

自包含探针（设备实跑验证，任何新 shell 可复现；输出与机理逐字吻合）。

注意：探针引用的 `~/.conan2/p/tcla4d5206af411b` 为已发布 tcl/8.6.16 包的
conan 缓存路径，随设备 cache 状态变化；可用
`conan install --requires=tcl/8.6.16 -g VirtualRunEnv` 重新物化后以实际
包路径替换。

```sh
export LD_LIBRARY_PATH=/storage/Users/currentUser/.conan2/p/tcla4d5206af411b/p/lib
/storage/Users/currentUser/.conan2/p/tcla4d5206af411b/p/bin/tclsh8.6 <<'EOF'
lappend auto_path /storage/Users/currentUser/.conan2/p/tcla4d5206af411b/p/lib
catch {package require Itcl} m1; puts $m1
# => can't find package Itcl
catch {load /storage/Users/currentUser/.conan2/p/tcla4d5206af411b/p/lib/itcl4.3.2/libitcl4.3.2.so Itcl} m2; puts $m2
# => Can't find a usable itcl.tcl ...
catch {package require Thread} m3; puts $m3
# => can't find package Thread
EOF
```

- 端到端佐证：combat/0.8.1 自包含捆绑 itcl 库脚本后，test_package 报
  "PASS Itcl support (4.3.2)"（ci-run1.log / .ci_logs conan 构建日志）。
- 诊断口诀：见 "Can't find a usable <X>.tcl / can't find package <X>"
  先查依赖包 `lib/` 是否被后缀通配剥离，再查代码。

## 相邻条目

- E280（静态构建 Thread 未注册 Tcl_StaticPackage）：同处 pkgIndex 域，
  机理为静态注册缺失，非文件丢失。
- E309（直拷源码漏掉构建生成头）：打包遗漏相邻族，机理为漏"构建生成物"，
  本条为通配后缀漏"运行期脚本"。
- 备注：v1 政策中本问题族曾以 E415 号段引用；当前 graph 无 E41x 号段，
  按相邻族 E280/E309 挂钩。
