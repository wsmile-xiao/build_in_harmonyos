# Autotools `DESTDIR` 不会屏蔽安装钩子中的系统级操作

## 错误特征

Conan 配方通过 `make install DESTDIR=<package-folder>` 收集文件时，安装钩子仍可能执行 `chown root:root`、设置 setuid，或递归进入 systemd、init 脚本等平台专用子目录。典型结果是非 root 构建在安装阶段报 `Operation not permitted`；即使安装成功，暂存目录也可能含不符合目标平台策略的权限位或系统服务文件。

`DESTDIR` 的语义是给安装路径加暂存前缀。它不拦截 Makefile 中显式写出的命令，也不保证每个子目录的安装目标都适用于目标系统。

## 触发条件

- 上游使用 Automake，并在 `install-exec-hook` 或自定义 install 目标内改所有者、改权限或加载内核模块。
- Conan 以非 root 用户将应用安装到 `package_folder`。
- 上游的 `SUBDIRS` 含有目标系统不支持或不使用的 Linux sysinit/systemd 子目录。

## 根因与实测

cryptmount 6.4.0 的 `Makefile.am` 在 `install-exec-hook` 中无条件对 `$(DESTDIR)$(bindir)/cryptmount` 执行 `chown root:root` 和 setuid chmod，并将 `sysinit` 列入 `SUBDIRS`。在 HarmonyOS PC 进行 Conan staging 时，安装流程还会进入该 Linux 子目录并尝试安装 `modules-load.conf`。同一安装钩子从顶层构建目录执行时，`cmtab.example` 也必须通过 `$(srcdir)` 定位。

这几项分别属于安装时权限副作用、平台专属目标和源/构建目录混用。修复前的打包错误日志确认安装阶段仍执行这些目标；修复后以真实 HarmonyOS PC Conan 配置完成 package 与 test_package，最终结果和暂存权限会在随 PR 的验证报告中记录。

## 推荐方案

1. 只在直接系统安装（`DESTDIR` 为空或 `/`）时运行 root 所有权和 setuid 操作；保留其余文件安装流程。
2. 从 `SUBDIRS` 中移除目标平台不使用的 Linux init/systemd 子目录。不要为消除错误而整体跳过顶层安装。
3. 在递归构建触发的顶层安装钩子中，用 `$(srcdir)` 引用源文件，避免把源目录误认为当前构建目录。
4. 检查最终 package 文件树的权限位和文件清单；成功执行 `make install` 本身不足以证明暂存产物安全。

## 禁止做法

- 不要对整个 `DESTDIR` 强制 `chown -R root` 或无条件设置 setuid。非 root staging 会失败；若命令被提权执行，则可能把特权位带入可分发包。
- 不要把 systemd/init 文件移到 HarmonyOS PC 的系统目录来“通过”安装；仅删除不适用的安装子目标，并保留命令行应用及文档。
- 不要把 Linux 设备映射或挂载能力从用户态编译成功推断为目标内核支持。

## 可复现检查

```sh
grep -nE 'install-exec-hook|chown|chmod|SUBDIRS|cmtab.example' Makefile.am
conan create archives/c/cryptmount/6.4.0 --profile:host=ohos-aarch64 --profile:build=default --build=missing
find <package-folder> -type f -perm /6000 -print
find <package-folder> -type f | sort
```

预期：root 所有权与 setuid 操作不作用于 staging 树；HarmonyOS PC 包不含 Linux sysinit 安装文件；命令行程序和文档仍正常进入包。直接系统安装的特权步骤仍由上游钩子保留。

## 与既有知识的边界

E453 记录 HarmonyOS 文件系统和权限位策略对运行时 setuid/chmod 的约束。本条目关注更早的打包阶段：Automake hook 在 Conan `DESTDIR` 中执行特权变更，并混入平台专属 install 目标。验证重点是非 root `package()` 阶段及最终包内容，不替代 E453 的设备权限语义说明。

本证据来自 cryptmount 6.4.0 的真实上游安装目标和 HarmonyOS PC Conan staging。结论适用于具有同类 Automake hook 的配方；遇到其他软件时仍需检查其 Makefile 和目标平台用途，不能机械删掉全部 `SUBDIRS` 或权限处理。

## 元信息

- 来源：`rwpenney/cryptmount` tag `v6.4.0`
- 任务：#13966
- 贡献者：`iKalous_OscarP`
- 状态：草稿，随对应适配 PR 提交
