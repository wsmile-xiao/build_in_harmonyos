# detachtty 11.0.0 适配笔记

## 编译环境

- 构建系统: makefile（上游纯 Makefile，无 configure）
- 编译日期: 2026-09-11
- 编译器: clang/clang++（来自 Conan conf tools.build:compiler_executables）
- 状态: built（待真机 conan create 验证后由 HMBS 更新）

## 编译步骤

上游构建即 `make` 默认目标（`detachtty` 与 `attachtty`），安装即
`make install DESTDIR=<pkg> INSTALL_DIR=/bin`。配方在 OHOS 上等价执行：

```sh
make -j1 CC=<ohos-clang> OS_LDLIBS=
make install DESTDIR=<package_folder> INSTALL_DIR=/bin
```

man 页与许可证另行复制到 `share/man/man1` 与 `licenses/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Makefile 写死 `OS_LDLIBS=-lutil` | OHOS musl 把 forkpty/openpty 并入 libc，sysroot 仅保留空壳 libutil.a（E563）；保留亦无害，但按语义等价应去除 | OHOS 时 `make OS_LDLIBS=` 覆盖为空，Linux 保持上游默认 |
| 2 | 不得依赖 shell 裸变量 CC | CI worker 上 `${CC}` 为空（R33） | 从 `self.conf tools.build:compiler_executables:c` 获取并以 `CC=` 传入 make |
| 3 | 上游无测试套件 | tarball 无 tests 目录、无 check/test 目标 | test_package 以 3 用例功能测试替代，并在 MANIFEST.yml 留完整审计 |

## 源码修改

无补丁。`patches/` 未创建，`conandata.yml patches: []`。

## 依赖版本

无 Conan 依赖。运行期仅 libc；跨机模式可选 ssh（不声明为包依赖）。

## 验证结果

待 HMBS 真机预检（conan create + test_package + 上游测试标记复发）。
本地未运行 conan（按任务守则，验证由真机执行）。

```bash
# 真机将执行（HMBS 后台）：
# conan create archives/d/detachtty/11.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 期望：test_detachtty.py RESULT: 3 passed, 0 failed；
# HMBS_TEST_PACKAGE_RESULT discovered=3/passedCount=3；
# HMBS_UPSTREAM_TEST_RESULT status=no_tests
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/detachtty | 会话服务端 |
| bin/attachtty | 会话客户端 |
| share/man/man1/detachtty.1 | 手册页 |
| licenses/COPYING | GPL-2.0 许可证文本 |

## 注意事项

- Windows 检出注意：上游 main 同时存在 `archives/l/libXext` 与
  `archives/l/libxext`（仅大小写差异），Windows 单目录无法共存；
  本机已对其中一个置 `assume-unchanged`，切勿提交该路径。
- `commands.json` 中 `binary: false`，制品仓发布后由发布流程翻为 true。
- 证伪提醒：用例 3 要求真实 socket 文件出现且 attachtty exit 0；
  若二进制被换成桩，`--version` 断言与 socket 连接将同时失败，
  不存在静默通过路径。
