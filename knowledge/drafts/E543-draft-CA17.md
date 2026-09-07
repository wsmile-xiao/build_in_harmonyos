# E543 — OHOS/HarmonyOS-PC strip 后的 ELF 无法执行

> 贡献者草稿（contributor: CA17），来源：noweb 2.13 HarmonyOS-PC 适配。

## 错误特征（典型日志）

对 `make install` 里被 `strip` 裁剪后装进 `bin/`/`lib/` 的 C 工具，直接执行报：

```text
/bin/sh: /path/to/nt: Operation not permitted        # 直接执行被拒
$ ./nt; echo $?                                      # rc=126
126
# wrapper 脚本调用管道件时报同样错误，且子进程退出码 126
/path/bin/noweave[291]: /path/lib/markup: Operation not permitted
```

注意：文件权限 `rwxrwx---`、`chmod +x` 均正常，仍报 Operation not permitted——
不是 chmod/SELinux 权限问题，而是**可执行内容被 strip 裁剪**导致的平台拒绝。

## 触发条件

- 构建系统：任何在 `install`/`install-code` 目标中对 C 产物调用
  `strip` / `llvm-strip` 的 Makefile（如 noweb 2.13 的 `src/Makefile`）
- 阶段：`make install`（installation）→ 之后所有调用该产物的环节（runtime）
- 平台：HarmonyOS PC (OHOS, aarch64 / armv8)

## 根因分析

HarmonyOS-PC (OHOS) 对可执行 ELF 的可执行性判定依赖其未裁剪的元数据
（符号表/代码段布局/.codesign 等）。经 `strip`/`llvm-strip` 裁剪后的 ELF
在 `exec` 时被 loader/内核拒绝，shell 报 `Operation not permitted`、退出码 126。
典型路径：Makefile `install` 中 `strip <产物>` → 裁剪后拷贝进 lib/bin →
wrapper/用户调用全部 EPERM。该症状容易被误诊为 chmod/SELinux/HMDFS 权限问题
（详见 similar_to E077：OHOS ELF 需保留可执行性相关元数据）。

## 解决方案

### 推荐方案（no-strip-on-ohos）
构建/打包阶段禁用 strip：

- 删除或注释 Makefile `install`/`install-code` 里的 `strip …` 行，保留未裁剪二进制；
- 二进制瘦身/签名交给发布流水线（CI `sign.sh` 等），不在本地构建阶段 strip；
- 修改后必须从干净对象重新 `make clean && make all && make install…` 验证
  （strip 不可逆，不能只重装）。

验证命令：

```bash
make CC=clang clean && make CC=clang all
make CC=clang install-code BIN=<prefix>/bin LIB=<prefix>/lib/noweb ELISP=/dev/null
<prefix>/lib/noweb/nt </dev/null ; echo "rc=$?"    # 应正常退出（非 126）
```

### 禁止做法
- ❌ 继续在 install 中 strip 产物后直接打包——OHOS 上产物全部不可执行；
- ❌ 用 chmod/chown/SELinux 处理来"修"这个问题——方向错误，strip 不可逆；
- ❌ 用空壳/dummy 可执行替代——掩盖真实产物不可执行的问题。

## 关联条目
- similar_to: [E077]（OHOS ELF 可执行性依赖 `.codesign`/签名等未裁剪元数据）
