# acpi-support 0.143 — 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | acpi-support(笔记本 ACPI 事件"胶水"脚本集) |
| 版本 | 0.143(上游 tag upstream/0.143,Debian orig tarball) |
| 状态 | built |
| 构建系统 | 无(零编译,纯 shell/配置包) |
| 源码 | https://deb.debian.org/debian/pool/main/a/acpi-support/acpi-support_0.143.orig.tar.gz |
| sha256 | 12e0a2c74def29a0cce98222cf63e05a5c64fe87cee32b12e4c0ba35d7f3643f |

## 上游形态
- 20 个文件:主配置 `acpi-support`(143 行,挂 /etc/acpi)、`events/` 8 个 acpid 事件定义、
  5 个 `.sh` 处理脚本(华硕/IBM/东芝 无线与背光、undock)、`lib/state-funcs` 无线状态函数库、
  `key-constants` 键值常量表、`asus_acpi.modprobe`、README/COPYING。
- **无构建系统、无编译产物**:上游不携带 configure/Makefile;唯一 C 程序 acpi_fakekey 是
  Debian 下游 addons(debian/addons/fakekey/),不在 orig tarball。

## 配方设计(零编译 application 型)
1. **build() = 验证而非编译**:`bash -n` 全量语法校验 5 个处理脚本 + state-funcs;
   主配置 grep 断言关键节(Suspend/hibernate method);每个 events 文件断言 `^action=` 键。
   截断/损坏源在 build 阶段即被拦截,不进入 package。
2. **package() 按 Debian 布局安装**:`/etc/acpi/`(处理脚本 0755、主配置 0644)、
   `/etc/acpi/events/`(7 个事件)、`/usr/share/acpi-support/`(key-constants、state-funcs 0644)、
   `licenses/COPYING`。tarball 内权限位混杂(644/755 并存),显式 os.chmod 对齐 Debian rules
   (find -name "*.sh" -exec chmod a+x;state-funcs chmod a-x)。
3. **零依赖**:Debian control 的 Build-Depends(libsystemd-dev 等)属下游打包依赖,上游源码
   不含 systemd 头引用,配方不声明任何 requires。
4. **test_package 真实探针**:安装产物存在性断言、`bash -n` 语法复验、source state-funcs 后
   实际执行 `isAnyWirelessPoweredOn`(遍历 /sys/class/net,函数可加载可执行,返回值 0/1 均正常)。

## 验证
- Windows 本机 bash 语法校验与 grep 断言全部通过(与 CI build() 同一逻辑)。
- OH CI:conan create → test_package 探针(见上)。

## 依赖
- 无(acpid 本体为运行时协作方,非构建依赖)。

## 【知识库扩展】
- 见 knowledge/drafts/DRAFT-acpi-support-0.143-zero-compile-shell-package-recipe-pattern.kv/.md:
  零编译 shell/配置包的"验证即构建"配方模式,可复用于其余纯脚本/配置类任务。
