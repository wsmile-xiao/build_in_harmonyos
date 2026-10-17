# 3d-ascii-viewer-c 1.4.0 适配笔记

## 编译环境
- 构建系统: makefile（原始 Makefile，无 configure）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4（OHOS aarch64，/data/service/hnp/bin/clang）
- 状态: published

## 编译步骤

1. init-build 下载官方源码 https://github.com/autopawn/3d-ascii-viewer-c/archive/refs/tags/v1.4.0.tar.gz
   （本机直连 GitHub 超时，经 ghfast.top 镜像拉取后 SHA-256 与官方一致：
   c390cbd4c80f6a7c5bdd9cab02174aaa8d63c0eeb18134deb8ed85463395d81c，
   conandata.yml 恢复官方 HTTPS URL，禁止镜像地址入仓）
2. lang-preflight：检测语言 c（cpp 兼容族），通过
3. 依赖 ncurses/6.4（ohpcd 制品仓已发布，W0 通过）；本机无 ncurses 头文件，
   用 conan install 获取二进制包（includedirs/libdirs 指向缓存）
4. 编译：make CC=clang CFLAGS="-Wall -fPIC -O2 -I<ncurses include>" LDFLAGS="-L<ncurses lib> -lm -lncursesw"
   （上游 Makefile 硬编码 CC := gcc 与 -lncurses，需在变量层覆盖；-j1）
5. 运行验证：--help rc=0；12 个样例模型（models/*.obj + *.stl）--snap 渲染全部 rc=0，
   输出 ASCII 帧非空（需 TERM=xterm TERMINFO=<ncurses>/p/lib/terminfo）
6. conan-init 生成配方后人工重写：
   - conanfile.py：原模板误判 autotools，改为原始 Makefile 构建 + requires ncurses/6.4 + package_type=application
   - package()：bin/3d-ascii-viewer + share/3d-ascii-viewer-c/models 样例模型
   - test_package：改为消费者 CLI 验证（--help + --snap 渲染 fox.obj），删除库式 CMake test
   - commands.json（软件级）：R38 CLI 声明 {type: tool, versions.1.4.0.ref: 3d-ascii-viewer-c/1.4.0}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 直连 github.com 超时 | 网络策略限制直连 | ghfast.top 镜像拉取，SHA-256 核对与官方一致，配方内恢复官方 URL |
| 2 | 生成配方误判 autotools | 默认模板猜测逻辑（有 Makefile 即猜 autotools） | 人工重写为原始 Makefile + make 变量覆盖 |
| 3 | 上游 -lncurses 链接失败 | ohpcd ncurses/6.4 仅打包 libncursesw.a（宽字符版） | LDFLAGS 用 -lncursesw（头文件 ncurses.h 同名） |
| 4 | 运行报 "Error opening terminal: dumb" | ncurses initscr 需要有效 TERM/TERMINFO | TERM=xterm + TERMINFO=<ncurses pkg>/lib/terminfo |
| 5 | make -j2 报 jobserver mkfifo 失败 | HMDFS 不支持 fifo（Gotchas） | 改 -j1（R9 也要求 -j1） |

## 源码修改

无补丁（patches/ 为空）：构建适配全部在 conanfile.py 变量层完成。

## 依赖版本

- ncurses/6.4（ohpcd 制品仓，conan 缓存二进制包）

## 验证结果

```bash
# 本机编译（clang 15 OHOS aarch64）
make CC=clang CFLAGS='-Wall -fPIC -O2 -I<ncurses include>' LDFLAGS='-L<ncurses lib> -lm -lncursesw' -j1
# --help
./3d-ascii-viewer --help  → rc=0
# 12 个样例模型 --snap 渲染
for m in models/*.obj models/*.stl; do ./3d-ascii-viewer --snap 30 20 -w 60 -h 24 $m; done  → 全部 rc=0
# 日志: tmp/oh-runner-logs/3d-ascii-viewer-c-1.4.0/run-models.log (sha256 00f31bc4f25e4a4ad12bd620cf54af8fc74fabe71ad9960510d1a880fe3bca99)
```

上游无独立测试用例（无 tests/、无 ctest/meson/autotools 测试注册）；样例模型 12 个为数据文件。

## 上游测试双口径台账（R51 / 高难度挑战硬门禁）

上游源码包（36 个非目录文件）无任何测试框架/测试源/测试注册入口：
`tar tzf` 全量枚举结果无 test/check/spec/fixture/bench 类文件；源码树无 tests/ 目录。

| 口径 | 数量 | 说明 |
|------|------|------|
| source_declared_total（源码声明测试总数） | 0 | 官方 tag v1.4.0 源码无测试声明（无 TEST_CASE/注册宏/测试脚本） |
| configured_executable_total（当前配置实例化可执行用例） | 0 | 无测试目标可实例化 |
| executed_passed_total | 0 | 无上游测试可执行 |
| 失败 / 未运行 / 未实例化 | 0/0/0 | 空集合，无缺失项 |

- 通过率口径：0/0 全量（空集合，不适用百分比）；当前配置可执行集合 0/0 (100%)
- 枚举证据：`tar tzf 3d-ascii-viewer-c-1.4.0.tar.gz`（36 文件：src/ 5 个 C 源 + models/ 20 个样例 + Makefile/README/LICENSE/.gitignore/capture*.gif）
- 上游入口逐项映射（源码声明 -> 预处理 -> 构建目标 -> 注册 -> 执行）：空链，全部 N/A
- 样例模型（models/*.obj, *.stl，20 个）为数据文件非测试用例，已在本轮全量实跑
  （12 个 obj/stl --snap 渲染全部 rc=0，日志见 run-models.log）作为功能验证，不计入测试计数
- 消费者用例（test_consumer/consumer_use_case.sh，C1-C3 全过）与鸿蒙专项
  （test_ohos/run_ohos_test.sh，T1-T5 全过）分别计数，不重复充数

## 鸿蒙专项测试 test_ohos（5/5 PASS）

日志: tmp/oh-runner-logs/3d-ascii-viewer-c-1.4.0/test_ohos.log
(sha256 057f792ca18321edb92e06304640ddc132554948f0db1e5cd8487d567e3a9583)

T1 aarch64 ELF（readelf AArch64） / T2 无宿主绝对路径泄漏 / T3 --snap 渲染 fox.obj /
T4 --snap 渲染二进制 STL / T5 --help 输出核验

## 消费者用例 test_consumer（3/3 PASS）

日志: tmp/oh-runner-logs/3d-ascii-viewer-c-1.4.0/consumer_use_case.log
(sha256 07e94d39c576e99a027cf43c044ffc9c42b4ff86e848559cbf6697b301960ba7)

C1 --snap 渲染 fox.obj 输出 12 行非空帧 / C2 --help 含 Usage 与 --snap 说明 / C3 非法模型文件返回非 0
公开 API：CLI 运行时产物 3d-ascii-viewer 的 --snap/--help 选项与退出码契约

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 原始 Makefile 构建配方 + ncurses/6.4 依赖 + application 包 |
| conandata.yml | 官方 URL + sha256 c390cbd4... |
| test_package/ | 消费者 CLI 验证（--help + --snap） |
| commands.json | R38 CLI 声明（软件级） |

## 注意事项

- 运行需 TERM/TERMINFO（消耗 ncurses terminfo）；未提供时 --snap 会报 "dumb" 终端错误
- 上游 README 依赖 libncurses-dev；本配方由 conan 管理 ncurses/6.4，不自带系统头文件
---

**编译结束**: 2026-09-24 04:15
**最终状态**: published
