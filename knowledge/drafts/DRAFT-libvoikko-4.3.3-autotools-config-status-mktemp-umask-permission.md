# Autoconf config.status 在 HarmonyOS /storage 上因 umask-077 临时目录权限失败：Permission denied 与 shim 被 buildenv PATH 遮蔽

- **草稿 ID**: DRAFT-libvoikko-4.3.3-autotools-config-status-mktemp-umask-permission
- **来源**: libvoikko 4.3.3 HarmonyOS PC 原生构建（autoconf 配置阶段连续 3 个环境坑的定位与修复）
- **分类**: autotools / ohos / filesystem / umask / mktemp / config-shell / shim
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

在 OHOS（aarch64，非 root 的 currentUser）上用 Conan AutotoolsToolchain 原生构建 autoconf 包，configure 跑完所有特性测试后卡在生成阶段：

```
./config.status[1090]: can't create ./confMms9TI/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

三个相互关联的签名，按出现顺序：

1. **configure 重执行 127**：`configure[139]: /data/service/hnp/bin/bash: inaccessible or not found`。
2. **编译器探测失败**：`configure: error: C++ compiler cannot create executables`（profile 的
   `tools.build:compiler_executables` 指向不存在的 `/data/service/hnp/bin/clang++`）。
3. **config.status 临时目录 Permission denied**：上面修好后，配置已推进到 config.status，
   却在写 `subs1.awk` 时被拒（本条目主体）。

## 根因

1. **CONFIG_SHELL 自重执行**：autoconf 生成的 configure 在开头检测到非预期 shell 时会
   `exec $CONFIG_SHELL ...` 自重执行。ohos-aarch64 profile 的 `[buildenv]` 把
   `CONFIG_SHELL=/data/service/hnp/bin/bash` 写进 conanbuild.sh，而该路径在这台设备上
   不存在（设备上真实可用的是 `/bin/sh`（Toybox ash）和 `/storage/.../usr/local/bin/bash`）。
2. **config.status 的安全临时目录**：config.status 固定执行
   `(umask 077 && mktemp -d "./confXXXXXX")`，然后往该目录写 subs1.awk 等 awk 脚本。
   在 HarmonyOS `/storage/Users/currentUser` 挂载上，非属主 currentUser（实测 euid 20020108）
   创建的 umask-077 目录出来是 `drwx--S---`（属主显示为 file_manager uid 20001006），
   当前进程既不是属主也不在 file_manager 组，且**非属主无法 chmod**——写文件直接
   `Permission denied`。默认 umask(022) 建的目录（`drwxr-s--x`）则可正常写。
3. **recipe 里的 shim 被 buildenv 遮蔽**：在 `build()` 里 `os.environ['PATH'] = shim:PATH`
   没用——AutotoolsToolchain 生成的 conanbuild.sh 用 `PATH=+(path)<profile路径>` **前置**
   自己的目录，最终 PATH 里 profile 路径排在 shim 前面，mktemp/uname 仍解析到真实程序。

## 最小修复方案

在 `archives/l/libvoikko/4.3.3/conanfile.py` 的 build() 内：

1. **CONFIG_SHELL 内联到 configure 命令行**（不依赖 os.environ）：
   ```sh
   CONFIG_SHELL=/bin/sh SHELL=/bin/sh ../configure ...
   ```
2. **mktemp shim**：在 build_folder 下写一个 `mktemp`，内部重置 umask 再调真实 mktemp：
   ```sh
   #!/bin/sh
   umask 022
   exec /storage/Users/currentUser/usr/local/bin/mktemp "$@"
   ```
3. **shim 目录用命令行 PATH 内联前置**（让子进程 config.status/make 都继承）：
   ```python
   self.run(f'PATH={_shim}:$PATH CONFIG_SHELL=/bin/sh SHELL=/bin/sh ../configure ...')
   ```
4. **-Werror**：configure.ac 追加的 `-Werror` 会把 OHOS 链接期专用 flag
   （`-Wl,--code-sign`、`-fuse-ld=lld`）在 `-c` 纯编译期的 unused-argument 警告升级成错误；
   先 `sed -i 's/ -Werror//g' ../configure`（正式 PR 应转为 patches/*.patch）。
5. **安装前缀**：绕过 autotools.configure() 手动调 configure 时必须显式
   `--prefix=/ --libdir=/lib --includedir=/include`，否则库落到 `$pkg/usr/local/...`，
   conan cpp_info 找不到。

## 实际验证结果

- **修复前**：configure 在 config.status 阶段 `Permission denied`，连编译都进不去。
- **修复后**：真机（frp-tip.com，OHOS aarch64，conan create）configure→make(-j1)→
  make install→test_package 全流程通过；产物 `lib/libvoikko.so.1.16.3`、`include/libvoikko/*.h`、
  `lib/pkgconfig/libvoikko.pc` 齐全。
- 定位方法（可复用）：
  - `config.status` 报错时，先 `ls -ld <build-release>` 看父目录 setgid，再手动复现
    `(umask 077 && mktemp -d ./confX)` 后写文件，确认是 umask-077 目录不可写，而非磁盘满/只读。
  - shim 不生效时，在 configure 命令里 `echo $PATH | tr ':' '\n' | head`，确认 shim 是否排在最前；
    buildenv 的 `PATH=+(path)` 会前置，必须在命令行内联 `PATH=<shim>:$PATH` 才能压住。

## 适用范围

- 在 OHOS PC（aarch64，非 root 的 currentUser，home 在 `/storage/Users/currentUser`）上
  原生构建（build==host）任何 GNU Autotools 包；
- 用 Conan AutotoolsToolchain，且 profile/镜像里 CONFIG_SHELL 或 compiler_executables 路径
  与实际设备不一致；
- 报错特征是 configure 已通过全部特性测试、却在 config.status 生成 awk 脚本时 Permission denied。

## 非适用边界

- 以 root 运行（root 绕过文件属主检查，umask-077 目录可写，本问题不出现）；
- CMake/Meson 包（不走 autoconf/config.status，无此 mktemp 路径）；
- 真·只读文件系统或磁盘满（那是另一类 Permission denied，先 df/du 确认）；
- `mktemp` 本身缺失（本设备 toybox mktemp 在 usr/local/bin，/system/bin/mktemp 不可执行）。

## 查重差异

- 知识库中 autotools OHOS 条目多集中在 config.sub/config.guess 平台三元组识别（aalib/gmp/4ti2
  先例），以及 hnp bash 路径问题；本条目新增的是 **/storage 挂载下 umask-077 临时目录
  属主映射导致 config.status 写 awk 脚本被拒**这一签名，以及"buildenv PATH=+ 前置会遮蔽
  recipe shim，需命令行内联 PATH"这一机制。

## 关联交付

- 本草稿与 `archives/l/libvoikko/4.3.3/**` 同属一次交付（分支 `feat/libvoikko-4.3.3`，
  conan create + test_package 真机通过）。
- 正式 E 编号由知识库主编审核后分配。

## 禁止模式

1. **在 build() 里只设 `os.environ['PATH'] = shim:PATH` 就指望 configure 用到 shim**：
   conanbuild.sh 的 `PATH=+(path)` 会把 profile 目录前置，shim 被排到后面，mktemp/uname
   仍解析到真实程序。必须在 self.run 命令行内联 `PATH=<shim>:$PATH`。
2. **试图在 umask-077 目录里 `chmod 777` 修复**：非属主 chmod 返回 EPERM（被 2>/dev/null
   吞掉），目录仍是 drwx--S---，问题依旧。正确做法是让 mktemp 建目录前 umask 回到 022。

## 推荐模式

```python
# build() 内：写 mktemp shim（umask 022），命令行内联 PATH 与 CONFIG_SHELL
_shim = os.path.join(self.build_folder, '_shim')
os.makedirs(_shim, exist_ok=True)
open(os.path.join(_shim, 'mktemp'), 'w').write(
    '#!/bin/sh\numask 022\nexec /storage/Users/currentUser/usr/local/bin/mktemp "$@"\n')
os.chmod(os.path.join(_shim, 'mktemp'), 0o755)
self.run(f'PATH={_shim}:$PATH CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
         '../configure --prefix=/ --libdir=/lib --includedir=/include <其他禁用后端参数>')
```

## 关联原则

- P020：消费者/构建用例必须在真机真实跑通；configure 过了不等于 install/test_package 过。
- 环境 workaround（shim 绝对路径、compiler_executables 覆盖）应尽量收敛为 patches/ 与
  profile 修正，而非散落在配方逻辑里。

## 相似条目

- E 系 autotools/config.sub OHOS 三元组识别（上位主题）；4ti2 的 mktemp 兜底（相邻，但本条目
  给出的是 /storage umask 属主映射这一新根因）。
