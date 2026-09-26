# kic 2.4c 适配笔记

## 编译环境
- 构建系统: autotools（GNU configure，autoconf 2.63 生成；2.4 起弃用 Imake）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4（OHOS aarch64 设备工具链）
- 状态: built（本地 conan create EXIT=0 + test_package 8/8；conan-verify 全绿后待 CI）
- 平台: OpenHarmony PC（aarch64，三元组 aarch64-linux-ohos）

## 编译步骤

```bash
# 1. 依赖消费性验证（R35/R36：conan download，禁止 conan list 判定）
conan download "libx11/6.4.0" -r=ohpcd --only-recipe      # exit 0，rev 63e25e48

# 2. 解压源码并应用补丁
# 3. configure（X11 头/库由 --x-includes/--x-libraries 注入；
#    --build 与 --host 显式同为 aarch64-linux-ohos，规避 2013 年
#    config.guess 在 HarmonyOS 宿主探测失败）
CC=clang ./configure --build=aarch64-linux-ohos --host=aarch64-linux-ohos \
    --prefix=<pkg> --x-includes=<libx11>/include --x-libraries=<libx11>/lib

# 4. make（上游 configure.in 硬编码 CFLAGS，依赖 -I 在 make 阶段覆盖注入，
#    保留上游 -DUSE_OLD_MALLOC 语义）
make -C src/bin CFLAGS="-O -Wall -DUSE_OLD_MALLOC -DHAVE_SYS_IOCTL_H \
    -I<xorgproto>/include -I<libx11>/include"

# 5. install（INSTALL_USER 置空，规避 -o root -g bin）
make -C src/bin install prefix=<pkg> INSTALL_USER=
```

产物 8 个可执行文件：kic（X11 GUI）、kichelp、ciftokic、kictocif、kictostr、
strtokic、strmtext、kicscale，均为 aarch64 OHOS ELF（musl 动态链接）。

## 上游测试清点与执行（R51）

- 清点：顶层 Makefile 仅 dummy/install/uninstall/clean/distclean 五个目标；
  src/{bin,cd,convert,ginterf,help,kic,xmfb}/Makefile* 均无 check/test 目标；
  仓库内无 tests/ 目录、无 ctest/pytest 注册 —— **上游无自动化测试入口**。
- 执行：无可执行测试（依据上文清点证据）。
- 补全：test_package 新增鸿蒙消费者端到端用例（8 项断言）——真实执行
  ciftokic（CIF→kic 单元文件）与 kictocif（kic→CIF 回转，KIC_LIB_DIR 指向
  包内启动文件），并断言几何数据 B 100 100 50 50 端到端一致。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `Invalid configuration 'aarch64-linux-ohos': system 'ohos' not recognized` | config.sub（2013）白名单无 linux-ohos | 补丁 0001：basic_machine 与 os 两处加入 linux-ohos*（aarch64 已内建） |
| 2 | config.guess 报 unable to guess（uname -s = HarmonyOS） | 2013 年 config.guess 不认识鸿蒙内核 | configure 显式传 --build=aarch64-linux-ohos（与 host 相同），跳过 config.guess |
| 3 | 链接报 `ld.lld: error: unable to find library -lX11`，Makefile 中 `LIBS = -L -lX11` | 上游 configure.in:105 沿用 autoconf 2.13 变量 `$ac_x_libraries`（2.63 中已更名 `$x_libraries`，ac_ 前缀变量恒为空）→ `-L` 后无路径 | 补丁 0002：configure/configure.in 中替换为 `$x_libraries` |
| 4 | xmfb 编译报 `X11/X.h file not found` | X.h 不在 libx11 conan 包内（该包仅 13 个核心头），X.h/Xatom.h 属 xorgproto | make CFLAGS 追加 `-I<xorgproto>/include`（Xlib.h 仍由 --x-includes 注入的 libx11 路径提供） |
| 5 | 探索期误覆盖 CFLAGS 抹掉 -DUSE_OLD_MALLOC 后，ciftokic 报 OUT OF MEMORY | 非上游语义路径：nmalloc 自研分配器（sbrk + 指针→int 截断）在 64 位 OHOS 损坏 freelist。上游默认 -DUSE_OLD_MALLOC 使 nmalloc 编译排除、走系统 malloc | 保持上游 CFLAGS 字面值覆盖注入（不丢 -DUSE_OLD_MALLOC），nmalloc 分支不激活；未对 nmalloc 打补丁 |
| 6 | make install 报 `install -o root -g bin` | 上游 INSTALL_USER 默认 root:bin，CI worker 非 root | install 时 `INSTALL_USER=` 置空 |
| 7 | CI Worker 上 config.status 报 `./confCMKChb/subs1.awk: Permission denied` / `could not setup config files machinery`（本地构建通过、CI #59912 失败） | HMDFS 对目录强制 setgid：configure/config.status 的 `umask 077 && mktemp -d "./confXXXXXX"` 产生 drwx--S--- 临时目录，经 UID 映射后属主进程也无法写入（知识库 E114/E011，aaphoto 0.45 同型先例） | 补丁 0003：去掉 configure 临时目录创建中的 umask 077，使 confXXXXXX 以可写权限创建（config.status 由 configure 生成，随之修复） |

## 源码修改

- patches/0001-config-sub-ohos.patch：config.sub 加 linux-ohos 三元组（2 处）
- patches/0002-fix-x-library-path.patch：configure + configure.in 的
  `$ac_x_libraries` → `$x_libraries`（修复 -lX11 链接）
- patches/0003-configure-hmdfs-umask.patch：configure 临时目录创建
  `umask 077 && mktemp -d` → `mktemp -d`（HMDFS setgid 规避，CI 必需）
- 无平台宏（R8）：三补丁均不含 `__OHOS__`

## 依赖版本

- libx11/6.4.0（ohpcd，rev 63e25e48c3af73db324ce61d0dba9cce）
  传递依赖：xorgproto/2025.1、xtrans/1.6.0、libxcb/1.16

## 验证结果

```bash
# 设备端真实执行（CIF→kic→CIF 往返）
$ ciftokic good.cif && echo OK          # exit 0，生成 Root/Symbol1
Translation of good.cif succeeded.
$ printf 'Root\n\n' | KIC_LIB_DIR=<pkg>/lib/kic kictocif
Translation of Root succeeded.          # Root.cif 含 B 100 100 50 50
```

test_package 消费者用例 8 项断言全部通过（鸿蒙 aarch64 实测）。

## 注意事项

- kic GUI 本体需 X 显示，OHOS 无显示环境；包价值与测试落在转换 CLI
  （ciftokic/kictocif/kictostr/strtokic/strmtext/kicscale）与 libcd/libconvert。
- 运行期需 `KIC_LIB_DIR=<pkg>/lib/kic`（kic_tech/ltab 启动文件），图层名
  以 startup/kic_tech 的 LayerName 为准（CWP/CWN/CMF/...，非任意字符串）。
- kic 格式是目录型单元文件（Root + Symbol1...），转换工具在 CWD 读写。
---

**编译结束**: 2026-09-22 01:41
**最终状态**: built
