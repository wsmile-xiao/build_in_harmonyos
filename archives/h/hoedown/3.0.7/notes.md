# hoedown 3.0.7 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure）
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4（OHOS profile: /data/service/hnp/bin/clang）
- 状态: built（W3 本地 CI 模拟 L0-L5 通过 + conan-verify G0-G4 通过；CI upload 成功后方转 published）

## 编译步骤

```bash
# 1. 源码获取（官方 tag 3.0.7，sha256=01b6021b…6ba920 经下载校验一致）
#    本地 GitHub 直连不可达，经 gh-proxy.com 镜像下载官方字节；配方 conandata.yml 保留官方 URL，
#    本地 conan create 由 conan_verify E017 机制临时注入 ghfast.top 镜像并在 finally 恢复。
make all          # 产物: libhoedown.a / libhoedown.so.3(+symlink) / hoedown / smartypants
python3 test/runner.py   # 上游 MarkdownTest 1.0.3 套件: 28/28 OK
make install DESTDIR=$TEST_PREFIX   # staging 验证（本机缺 coreutils install，用 busybox install shim）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试套件报 FileNotFoundError: 'tidy' | 测试 runner 用 tidy 归一化 HTML，本机未安装 | cmd-pkgs 安装 tidy-html5 5.8.0；另本机 posix_spawn 不做 PATH 搜索（clang/git 等按名 spawn 均失败），runner.py 的 TIDY 改绝对路径（仅本地 work 副本，不入库） |
| 2 | make install 报 "install: No such file or directory" | 本机无 coreutils install 命令 | 环境 shim 用 busybox install（/tmp/shims/install）；配方 package() 不依赖 install，用 conan copy 手工复制 |
| 3 | conan create test_package 运行期报 libhoedown.so.3 找不到 | 默认 shared=False 但包内含 .so，test 链接 .so 后运行环境 LD_LIBRARY_PATH 不含包 lib | 配方 package() 按 shared 选项条件打包：静态只装 .a，shared 才装 .so.3+symlink；默认静态链接后测试通过 |

## 源码修改

无补丁（patches/ 为空）。上游测试仅本地运行，未改动上游源码或测试期望。

## 依赖版本

无外部依赖（纯 C 库，仅 libc）。

## 验证结果

```bash
# 上游测试（R51）: MarkdownTest 1.0.3 套件 config.json 注册 28 用例
python3 test/runner.py   # Ran 28 tests in 1.969s — OK（28/28 通过）
# Conan 验证
python3 scripts/ohc-run.py conan-verify hoedown 3.0.7   # G0-G4 + L2/L4/L5 全 PASS
# 产物（package 内）
libhoedown.a (static) / hoedown / smartypants / include/hoedown/*.h
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 型配方（AutotoolsToolchain 环境 + make 命令行传 CFLAGS/LDFLAGS） |
| conandata.yml | 官方 GitHub tag 3.0.7 + sha256 |
| test_package/ | CMake 消费者测试：调用 hoedown API 渲染 Markdown 并断言 <h1> |
| commands.json | hoedown/smartypants 命令行工具声明（R38） |

## 注意事项

- 版本核验：官方 tag 3.0.7（gitcode 镜像 refs/tags/3.0.7 = 467001de…f446a；Homebrew/haikuports 同源 sha256 一致）。
- 本机环境怪癖（不入库）：posix_spawn 不做 PATH 搜索、无 coreutils install、HMDFS chmod 固定 660。
- R36 依赖检查：hoedown 无 requires，无依赖发布问题；L0i 检查对象为 hoedown 自身依赖集（空）。
---

**编译结束**: 2026-09-07 11:53
**最终状态**: built
