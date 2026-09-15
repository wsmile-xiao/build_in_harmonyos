# boost-1.85

Boost C++ Libraries（1.85.0-b2-nodocs 变体）。本目录是独立的包名变体（带横杠），
与 `boost/`（元包系列）和 `boost1.84-*/`（组件拆分包系列）平行。

## 1.85.0-b2-nodocs

**b2 直跑 OHOS 首例**。历史上 boost 系在本仓库全部绕过 b2 手动编译
（E068/E099：b2 SHELL 执行机制/编译器探测在 OHOS 不兼容）。本版本实证
b2 可以在 OHOS 交叉环境直接运行——阻塞机制被定位并细化（见 notes.md
路径 C 探索报告）：b2 的 clang toolset 会注入 `--target=arm64-pc-linux`
破坏 OHOS clang 默认 sysroot 探测，改用 gcc toolset 名字注册 OHOS
clang++ 即可绕过，b2 引擎本身完全正常。

- 9 个非 header-only 库由 b2 构建（静态、threading=multi）：atomic、
  chrono、filesystem、iostreams、program_options、random、regex、
  system、thread
- 其余库 header-only，随完整 `boost/` 头文件树安装（nodocs：不装文档、
  不导出 cmake-config）
- 上游测试通过 b2 原生测试框架（testing.capture-output）真实运行
- 依赖：zlib/1.3.1（iostreams gzip）；构建依赖：boost-build/1.90.0
  （b2 引擎，制品仓已发布）
