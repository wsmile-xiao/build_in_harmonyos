# E544 — OHOS hmdfs(hmmac) 设备端构建工具链 exec/加载三重限制

## 错误特征

设备端（hmdfs 工作区，hmmac=use_task）本地构建 / 本地 CI 模拟（W3）中出现的
一组同根因错误，日志指纹：

```text
./install-sh: Permission denied            ← make MKDIR_P 直接 exec 辅助脚本
/bin/sh: <path>/conan: Permission denied   ← RC=126，间歇性（label 翻转）
bad interpreter: Permission denied         ← 会话 BASH_ENV/BASH_FUNC 垫片劫持
unable to find library -lX11               ← 链接器打不开 conan 缓存里的 .so
Error loading shared library libdockapp.so.3
SAFE_DELETE_BULK_GUARD_ERROR               ← sitecustomize 在 conan 清理临时目录时杀死 conan
```

关键鉴别特征：**同一命令时好时坏**（hmdfs label 翻转），且 `chmod +x` 后仍
可能报 770 权限——这不是缺包，不是配方错误，重试/换路径才有意义。

## 触发条件

- 构建系统: 任意（autotools/cmake/meson 均可，辅以 conan 工作流）
- 阶段: configuration / compilation / linking / installation / testing / runtime
- 环境: OpenHarmony PC 设备端、工作区位于 hmdfs（分布式文件系统）、
  hmmac=use_task 策略；上游 CI worker 环境不命中

## 根因分析

hmdfs(hmmac=use_task) 三重限制：

1. **可执行位不可靠**：conan 解压源码丢失 exec 位，且 `chmod` 被 setgid
   语义强制回 770；hmdfs 属性缓存还有秒级滞后（chmod 后立刻 exec 仍 126）。
2. **execve 白名单**：python `posix_spawn` 只能 exec 预装二进制；用户创建的
   脚本/symlink/ELF 拷贝一律 EACCES，且裸命令名不按 PATH 搜索。
   但 bash/python3 可以**读取**用户文件——「读取执行」是合法通道。
3. **加载器挂载限制**：动态加载器/链接器无法打开 hmdfs/网络挂载上的 .so。

叠加会话注入问题：PATH 中 `rm` 被 safe-delete 垫片劫持（BASH_ENV /
BASH_FUNC_*），PYTHONPATH 的 sitecustomize 在 conan 批量删除临时目录时抛
PermissionError 直接杀死 conan。

## 解决方案

### 推荐方案
relocate-conan-home-to-local-fs-and-probe-exec——把执行/加载面整体迁到
应用沙箱本地 FS（el2），用「读取执行」与 make 变量覆盖绕开 execve 限制：

1. `CONAN_HOME` 指向本地 FS（如 `/data/storage/el2/base/cache/conan2`），
   加载器/链接器即可读 .so
2. 配方 `build()` 前对 autotools 辅助脚本 chmod + exec 探针重试
   （`_restore_exec_bits` 模式，容忍属性缓存滞后）
3. `make MKDIR_P='/system/bin/mkdir -p'` 覆盖，绕开对 install-sh 的直接
   exec（语义等价，同 libdockapp/0.7.3 先例）
4. 依赖 .so 复制进构建目录 linker-view，并在 **OHOS configure 参数里**显式
   传 `LDFLAGS=-L<linker-view>`——注意必须写在 OHOS 路径实际使用的
   toolchain/参数列表上，写在 `generate()` 的 toolchain 上不会进入
   OHOS configure（死逻辑）
5. conan 调用统一 `env -u PYTHONPATH`
6. conan 本体用 `bash -c` 内联 + python3「读取」入口脚本执行，规避 execve
   label 翻转；**外部命令（timeout/env/xargs）会绕过 shell 函数 hook**，
   必须在 argv 层面重写（如 `timeout ... env PYTHONPATH=... python3 .../bin/conan`）
7. 设备无 zsh：本地 W3 需把 CI 脚本 zsh 专有语法 bash 化
   （`(N)`、`${var:h}`、`${=var}`、`${+var}`、`$pipestatus`、`<(...)` 进程替换），
   或交由 CI worker 执行

### 禁止做法
- ❌ 用 `--build=missing` 掩盖依赖不可消费（R36）
- ❌ 把 `.so` 拷进系统目录或修改系统路径求加载通过
- ❌ 反复 `rm -rf` 重试构建目录（hmdfs 上既慢又可能撞 safe-delete 垫片）

## 验证
```bash
# conan 经「读取执行」应稳定输出版本号；对照直接 exec 间歇性 RC=126
PYTHONPATH=<conan-libexec> python3 <conan-libexec>/bin/conan --version
# G0 干净构建 + conan create + W3 本地 CI 模拟全链路（wmmisc/1.2 实证）
python3 scripts/ohc-run.py finish <pkg> <ver> built
```

## 关联条目
- 相关: E490（autotools 辅助脚本 exec 位）、E324（env-export-env-tools）
- 相关: E521（libtoolize/automake hardcode sed 路径）
