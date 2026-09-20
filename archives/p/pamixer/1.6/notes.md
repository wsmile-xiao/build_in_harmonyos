# pamixer 1.6 编译笔记

## 基本信息
- 软件: pamixer
- 版本: 1.6
- 状态: published
- 上游: https://github.com/cdemoulins/pamixer

## 构建系统
- 上游使用 meson 构建系统 (meson.build)
- 由于 cxxopts 不在 Conan 制品仓中（header-only 库），采用直接编译方式
- 编译4个源文件: callbacks.cc, device.cc, pamixer.cc, pulseaudio.cc
- cxxopts v3.1.1 以 exports_sources 方式内嵌配方（cxxopts.hpp），避免 CI 下载 GitHub 超时

## 依赖
- pulseaudio/17.0 (Conan 制品仓已发布) — 提供 libpulse 头文件和库
- cxxopts/3.3.1.1 (Conan 制品仓已发布，header-only) — 2026-09-15 已发布，取代早前内嵌
  cxxopts.hpp 的做法（内嵌副本无供应链锚定，AI 检视 P2 意见）

## 编译过程
1. 创建 config.hh (meson configure_file 的等效物，定义 VERSION 宏)
2. 直接用 profile 指定的 clang++ (tools.build:compiler_executables) 编译4个 .cc 文件，链接 libpulse 和 libpulsecommon
3. 安装 pamixer 二进制到 bin/，man page 到 share/man/man1/

## 源码 URL（R39）
conandata.yml 只写官方 GitHub URL；CI 会自动为 GitHub URL 注入 gh-proxy 镜像
fallback（build_and_test.sh 的 mirror rewrite 步骤），无需手写镜像前缀。

## 关键平台问题: lld 与 libxml2.so.16（E501）

CI 现象: `clang++ -o pamixer` 链接时报
`Error loading shared library libxml2.so.16: (needed by .../ohos/native/llvm/bin/lld)`
`Error relocating lld: xmlFreeDoc: symbol not found` 等一串 xml 符号错误。

根因（本地实测复现）:
1. OHOS SDK 自带的 lld 通过 RUNPATH($ORIGIN/../lib) 从 SDK 自己的 llvm/lib 加载
   libxml2.so.16 —— 干净环境下链接正常。
2. musl 动态加载器搜索顺序: LD_LIBRARY_PATH 优先于 DT_RUNPATH。任何 LD_LIBRARY_PATH
   条目中存在"不可加载"的 libxml2.so.16（如 Conan 缓存中的共享库副本，实测从缓存
   目录或任意复制的位置加载均失败），都会遮蔽 SDK 的好副本，导致所有链接命令失败。
3. 曾经尝试的 `tool_requires libxml2` 方案恰恰是雪上加霜: tool 依赖的 libdir 会被
   注入 conanbuild 环境的 LD_LIBRARY_PATH，把不可加载的副本放到最前面。

修复（E501 模式，同 lua/5.1，PR !4635 已验证）:
- 移除 libxml2 tool_requires 与 VirtualBuildEnv/VirtualRunEnv 生成器
- 链接命令用 `Environment().prepend_path("LD_LIBRARY_PATH", <SDK>/ohos/native/llvm/lib)`
  包裹 (`with env.vars(self).apply()`)，让 SDK 自己的好 libxml2.so.16 排在最前

## test_package 平台限制说明
- Conan 缓存中的 .so 在运行时无法被动态加载器加载（实测），因此动态链接了
  libpulse 的 pamixer 二进制无法在本平台直接执行 —— 与 pulseaudio/17.0 的
  test_package 处理方式一致: 二进制存在性 + ELF 校验 + 尝试执行，若失败原因是
  共享库加载类错误则视为已知平台限制通过
- 上游 pamixer 无测试套件（无 meson test），test_package 即消费侧测试

## 上游测试清点（R51）
- 上游源码 tarball 内无 tests/ 目录，meson.build 未定义 test() —— pamixer 是无
  测试套件的 CLI 工具（清点证据: tar 包仅含 COPYING/README.rst/meson.build/pamixer.1/src）

## 历史
- 2026-06-05: 首次编译成功 (status=built, makefile)
- 2026-08-26: 添加 Conan 配方 (conanfile.py + conandata.yml + test_package/)，status=published
- 2026-08-27: 多轮修复 CI 链接失败（fuse-ld/全路径/meson/libxml2 tool_requires 均未解决）
- 2026-09-18: 定位根因为 LD_LIBRARY_PATH 遮蔽 SDK libxml2（E501），改用 SDK llvm/lib
  prepend 方案；修复 test_package self.run(env=dict) 断言崩溃地雷（Conan 2 env 参数
  只接受字符串/列表）；按 AI 检视意见改为依赖制品仓 cxxopts/3.3.1.1（删除内嵌头文件）、
  conandata.yml 只保留官方 URL（R39）、test_package 增加可执行位检查并收窄平台限制豁免

---
**编译结束**: 2026-08-27
**最终状态**: published
---

## PR Update
- 2026-08-26: Fixed cxxopts dependency (not in registry), vendored header-only library
- 2026-09-18: E501 fix — SDK llvm/lib LD_LIBRARY_PATH prepend for lld; test_package env fix
