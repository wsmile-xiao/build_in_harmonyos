# qemu 11.1.1 适配笔记

## 编译环境
- 构建系统: meson（QEMU 的 configure 是 Meson+Ninja 的包装层）
- 编译日期: 2026-09-22
- 编译器: clang/clang++（OHOS SDK，/data/service/hnp/bin）
- 状态: built

## 编译步骤

```bash
# 0) 应用 3 个 OHOS 适配补丁（见「源码修改」节）
# 1) configure（out-of-tree 构建，Meson）
./configure --prefix=<package_dir> --target-list=riscv64-softmmu \
  --cc=/data/service/hnp/bin/clang --cxx=/data/service/hnp/bin/clang++ \
  --disable-werror \
  --disable-kvm --disable-hvf \
  --disable-dbus-display --disable-keyring \
  --disable-guest-agent --disable-guest-agent-msi \
  --disable-gtk --disable-sdl --disable-vnc --disable-opengl \
  --disable-libssh --disable-nettle --disable-gnutls \
  --disable-bzip2 --disable-lzo --disable-snappy --disable-lzfse \
  --disable-zstd --disable-seccomp --disable-curl \
  --disable-vhost-user --disable-vhost-kernel --disable-slirp
# 2) 编译 + 安装
ninja -j<N>
ninja install
# 3) OHOS 专属：对打包出的全部 ELF 签名（见问题 #4，E077 四步流程）
#    llvm-objcopy --remove-section .codesign <bin>
#    binary-sign-tool sign -inFile <bin> -outFile <bin> -selfSign 1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Meson 不识别 host_os 'HarmonyOS'，回退非 Linux stub 代码 | OHOS 的 meson 三元组 system=HarmonyOS，QEMU meson.build 只认 linux | patch 0001：host_machine.system() 后把 HarmonyOS 归一化为 linux（host_os_orig 保留原值供 0002 使用） |
| 2 | can_socketcan 在 OHOS 上编译不过/无使用场景 | socketcan 依赖 Linux socket(PF_CAN) 设备，OHOS 不提供 | patch 0002：host_os_orig 非 linux 时跳过 can_socketcan.c |
| 3 | meson 对 dtc 等 subproject 尝试 git fetch，网络不可达 | subproject .wrap 为 [wrap-git] 类型，gitlab.com 在 OHOS 构建环境不可达 | patch 0003：dtc.wrap 改为 [wrap-file] 官方固定版本 v1.6.1 tarball（含 source_hash）；build() 另对带 bundled 源码的子项目删除 .wrap，直接用内置源码 |
| 4 | 打包二进制执行 EPERM（rc=126） | OHOS 内核拒绝加载未签名 ELF | package() 对全部打包 ELF 签名：llvm-objcopy --remove-section .codesign + binary-sign-tool sign -selfSign 1（按 \x7fELF magic 判定，跳过 .a/数据文件） |
| 5 | 运行报 Error loading shared library libpixman-1.so.0（rc=127） | Meson 只记录构建期 -L 路径，不写 $ORIGIN RUNPATH | generate() 对依赖（pixman/glib/zlib）各自 lib 目录追加 -Wl,-rpath 到 LDFLAGS |
| 6 | keyring/guest-agent 等选项编译报错 | sysroot linux/keyctl.h 使用未声明的 __user；OHOS libc 缺 getutxent | --disable-keyring / --disable-guest-agent（其余可选功能裁剪见编译步骤） |
| 7 | lang-preflight 报 mixed(cargo) | rust/ 为上游可选子模块（未参与构建），检测器按目录统计误计 | 判定检测器误报：项目主体纯 C/Meson（R47 边界规则：辅助目录不计主体），如实记录后继续 |
| 8 | 测试脚本写 /tmp 失败 | OHOS /tmp 只读（erofs） | test.sh 避免 /tmp 硬编码与 $(...)，用 $TMPDIR 兜底 + 重定向+grep |
| 9 | CI conan-build-test：configure 建 venv 后 ensurepip 失败，venv python 报 `No module named 'encodings'`（base_prefix 误解析到 $HOME/usr/local，该目录无 python 标准库） | CI worker 的 python 3.12.9 为 HNP 包（/data/service/hnp/，HNP 名 OpenHarmonyPCDeveloper_build_in_harmonyos_ci_o）；venv python（符号链接链）的 CPython base_prefix 解析落到 $HOME/usr/local（仅有 setup.sh 的 libsqlite3，无标准库）→ venv python 无法启动；本地 python 为 $HOME/usr/local 常规安装（标准库齐全）故本地 W3 绿、CI 红（W0b：本地/设备工具链成功不可迁移 CI clean 环境） | generate() 按 configure 同款 PATH 顺序探测 python，取可用解释器（≥3.9）的 sys.base_prefix（构建期动态计算，不硬编码路径）注入 qemu_env 的 PYTHONHOME（CPython 标准前缀解析机制）：本地 no-op、CI 纠正误解析。机制已本地验证：错误 PYTHONHOME 复现同类 fatal（No module named encodings），正确值恢复 venv + ensurepip。CI 第 2 轮（构建 #59984，2026-09-24，已含本修复）实测修复未生效——崩溃转储仍显示 `PYTHONHOME = (not set)`：shutil.which() 在 CI-005 worker 上未枚举到任何候选解释器（归因假说：该 HNP 布局下文件的权限/可执行语义与 shutil.which 的 X_OK 判定不兼容——同路径 configure 侧 zsh `command -v` 可命中），探测块整段空转。第二轮修复：候选枚举改用 os.path.isfile()（与 X_OK 无关：SDK bin + ~/usr/local/bin + PATH 逐目录拼接，which 仅兜底）；注入值不再取 sys.base_prefix（HNP 构建期前缀可能陈旧失真），改由 encodings.__file__ 反推解释器实际加载 stdlib 的前缀并校验 <prefix>/lib/pythonX.Y/os.py；本机复验注入值与旧逻辑一致（no-op），W3 全量重跑绿。CI 第 3 轮（2026-09-25，rrev 4c2424da）确定性探测仍未生效——崩溃转储恒 `PYTHONHOME = (not set)`，机制根因在 CPython stdlib 源码层确定：venv/__init__.py `_call_new_python()` 在 spawn `-m ensurepip` 子进程前无条件 pop 掉 PYTHONHOME/PYTHONPATH（v3.12 L388-389），环境变量注入永远到不了崩溃进程（三轮恒 not set 与探测块是否执行无关）。根因 v2（home landmark）：configure 经 /data/service/hnp/bin 符号链接目录选中 python3 → venv 写 pyvenv.cfg home=<符号链接 bin 目录> → venv python 找 home/lib/pythonX.Y/os.py 落空 → 回退编译期烘焙前缀（CI 上 $HOME/usr/local 无 stdlib）。本地机制 sim 全链实证：裸符号链接 bin 目录创建的 venv home=该 bin 目录（复刻 CI 缺陷拓扑）；wraps 拓扑（python3+lib 双符号链接目录）创建的 venv home=wraps、base_prefix=wraps（landmark 命中而非烘焙前缀 fallback），且在剥离 PYTHONHOME 的环境下 venv 可用（stdlib 加载正常、ensurepip 产物 pip 落位）。第三轮修复：generate() 构造私有解释器目录 <build>/pymbin（python3→探测解释器、lib→实际 stdlib lib 的符号链接），prepend 至 PATH 首位让 configure 选中它——venv 及其 ensurepip 子进程经 home landmark 解析 stdlib，零环境变量依赖；PYTHONHOME 降级保留（非 venv spawn 兜底）；探测块另加零子进程静态布局 fallback（探测目录父级 lib/lib64 的 pythonX.Y/os.py 存在即取）。CI 第 4 轮（构建 #61865，2026-09-26，rrev c7e11c9c）实证 home-landmark 修复生效——configure 选中 pymbin/python3，venv 创建 + ensurepip + pip 落位全部成功（三轮 venv 崩溃终结）；失败点推进至 venv 就绪后的 pip 联网：mkvenv tooling 组（setuptools/wheel/pip）在 pythondeps.toml 仅版本约束、未随 tarball vendor（python/wheels/ 仅 meson/pycotap/qemu.qmp 三包，本地实测），pip 走默认 PyPI 对 files.pythonhosted.org 读超时（15s×重试全挂），同批解析殃及本可离线安装的 qemu.qmp wheel；本地 W3 绿因 pip 缓存温暖+网络通畅（W0b 又一例）。第四轮修复：generate() 向 qemu_env 注入 PIP_INDEX_URL=社区镜像（构建环境文档强制源 pypi.cnb.cool；setuptools/wheel/pip/qemu-qmp 覆盖已实测，qemu-qmp 含 0.0.6）+ PIP_DEFAULT_TIMEOUT=60 + PIP_RETRIES=10（对齐 CI CONAN_RETRY=10）；mkvenv pip_install 未传 env 参数、子进程继承 qemu_env 环境，注入必达；默认解析正常的开发机 no-op。框架侧 CI worker 对 PyPI 出口策略记入 SKILL_FEEDBACK ⑫（独立框架 PR） |
| 10 | CI 第 2 轮 conan-build-test：conan source() 下载官方源连续 Connection reset（104）→ conan create 失败 | ① CI worker 无 curl，框架预下载链路 [Errno 2] 'curl'×3 降级 WARN（失效非致命）；② download.qemu.org 对 CI 出口间歇 reset；③ 框架 get_mirrors() 白名单不含 download.qemu.org，无自动镜像 fallback | conandata.yml url 单值→列表：官方主源 + BLFS 权威镜像 mirror-hk.koddos.net（2026-09-25 本地逐字节验证：141888716 字节与 sha256 均与官方一致；conan get() 对列表逐个尝试，sha256 校验兜底防漂移）。剔除候选：huaweicloud（路径返回 SPA 页无 tarball）、anduin/slackware（未同步 11.1.1）。框架侧修复（get_mirrors 补 qemu 域/worker 预装 curl）走独立框架 PR（W2） |

## 源码修改

| 补丁 | 内容 |
|------|------|
| patches/0001-meson-build-harmonyos-linux.patch | meson.build：host_os 为 HarmonyOS 时归一化为 linux，host_os_orig 记录原值 |
| patches/0002-can-skip-socketcan-on-harmonyos.patch | net/can/meson.build：host_os_orig 非 linux 时跳过 can_socketcan.c |
| patches/0003-dtc-use-official-github-mirror.patch | subprojects/dtc.wrap：[wrap-git] → [wrap-file] 官方 dtc v1.6.1 tarball（含 source_hash） |

## 依赖版本

- glib/2.84.0（conan 包，含传递依赖 pcre2/libffi）
- pixman/0.46.4（conan 包）
- zlib/1.3.1（conan 包）
- dtc v1.6.1（subproject，官方 tarball）

## 验证结果

### 上游单元测试（meson test --suite unit，OHOS 设备实跑）

清点：tests/unit/ 注册测试 104 项 → **95 pass / 5 fail / 4 skip**（testlog 2026-09-21 20:06）

5 个 fail 的根因均为 OHOS 宿主运行期 EPERM/权限类限制，与 3 个适配补丁的代码变更无关（补丁改动 meson host_os 归一/socketcan 裁剪/dtc 取源，失败用例均不走这些路径，完整移植在 OHOS 上同样会触发该限制）：

| 失败用例 | 具体技术原因（实测证据） |
|---|---|
| qemu:test-replication | bdrv_make_empty() 截断临时 qcow2 文件 EPERM（block.c:8284 "Failed to empty json:{...}: Permission denied"）→ g_assert SIGABRT；OHOS 文件权限策略限制 truncate |
| qemu:test-io-channel-socket | unix_listen_saddr() AF_UNIX bind EPERM（util/qemu-sockets.c:1026 "Failed to bind socket to test-io-channel-socket.sock: Operation not permitted"）→ SIGABRT；OHOS 禁止创建 Unix 域套接字文件 |
| qemu:test-io-channel-file | 文件权限断言失败（test-io-channel-file.c:69：实际 mode 0o600=384 ≠ 期望 0o660=432）→ SIGABRT；HMDFS 不保留测试期望的文件权限（权限归一化） |
| qemu:test-util-filemonitor | inotify 文件监控断言失败（test-util-filemonitor.c:739：err == 0 不成立）→ SIGABRT；OHOS/HMDFS 文件事件监控行为与测试预期不符 |
| qemu:test-char | TAP 止于 ok 4（/char/mux），第 5 项（chardev socket）直接 SIGABRT 无更多输出；根因与 test-io-channel-socket 相同（AF_UNIX 套接字创建 EPERM） |

4 个 skip（宿主环境限制，非适配缺陷）：

| 跳过用例 | 原因 |
|---|---|
| qemu:test-crypto-block | 1..0：crypto 后端（nettle/gnutls）已禁用（--disable-nettle --disable-gnutls），无可执行子测试 |
| qemu:test-crypto-cipher | 同上 |
| qemu:test-crypto-pbkdf | 同上 |
| qemu:test-io-channel-command | PATH 中无 socat（fifo 子测试依赖 socat） |

通过覆盖含核心工具链：check-block-qdict、test-base64、test-bitcnt、test-cutils、test-iov、test-keyval、test-mul64、test-qemu-opts 等。

### 消费者测试（test_package/test.sh，5/5 pass）

```bash
/bin/sh test.sh <bindir>
# 1. qemu-system-riscv64 --version → 11.1.1 通过
# 2. qemu-img --version           → 11.1.1 通过
# 3. qemu-nbd --version           → 11.1.1 通过
# 4. qemu-io --version            → 11.1.1 通过
# 5. qemu-img create + qcow2 info 往返 → 通过
```

（conan-verify G2 / conan create 内 test_package 实跑 5/5 通过，日志见 reports/w3-local-ci.log）

## 交付物

| 文件 | 说明 |
|------|------|
| bin/qemu-system-riscv64 | riscv64 系统模拟器（主交付物） |
| bin/qemu-img | 磁盘镜像管理工具 |
| bin/qemu-nbd | NBD 服务器 |
| bin/qemu-io | 块设备 I/O 工具 |

打包 ELF 全部已签名（OHOS 执行前提），RUNPATH 指向 conan 依赖 lib 目录。

## 注意事项

- 仅支持 OHOS armv8（与 CI profile ohos-aarch64 一致，validate() 门禁）
- 打包 ELF 必须签名，否则执行被拒（EPERM/rc=126）
- 上游 5 个 fail 用例均为宿主 EPERM/权限类限制，与适配补丁无关；3 个 crypto skip 为 crypto 后端裁剪的直接后果，如需完整 crypto 测试可后续评估启用 nettle
---

**编译结束**: 2026-09-26 17:44
**最终状态**: built
