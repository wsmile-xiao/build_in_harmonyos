# pslib 0.4.8 适配笔记

- 构建：Autotools，OHOS 6.0/aarch64、Clang 15、Conan 2.29.1。
- 源码：Debian 正式镜像归档，SHA-256 `4806d1b9f2cfa6245b2ba54735ce9d306570e891a75621cafe7c8079bce01c17`。
- 依赖：libpng/1.6.58.3、libjpeg/10；构建工具 intltool/0.51.0、gettext/0.22.5.1，均从 ohpcd 制品仓取得。
- 配方：对旧 `config.sub` 精确加入 `linux-ohos` 识别；用目标编译器 `-dumpmachine` 得到同一 build/host tuple；PNG/JPEG 检测必须在 `config.h` 中同时为 1，否则失败。禁用 GIF/TIFF 与 NLS。
- 旧 intltool 问题：制品 shebang 指向已不存在的 Perl，任务构建目录生成三条包装器；`configure` 的 XML::Parser 守卫仅在 `USE_NLS=yes` 时保留。`make check` 的 po 阶段仍使用真实 intltool/gettext，不使用假成功 stub。
- 包：安装后修正 `libps.pc` 为可重定位 prefix，并声明 `Requires.private: libpng libjpeg`；对外 CMake target 为 `pslib::pslib`。
- 验证：W3 `pslib-w3-20260926T024600Z` 12/12 PASS；上游注册测试 0/0（不适用）而 `make check -j1` 成功；安装后消费者 1/1 PASS。原始日志 SHA-256 `84af84194ee531e6db199fcf2cca9baa96f6d1760113dd881f6e342cfb1cef69`。
- 提交状态：仅完成目标机验证；Issue、PR、平台 AI Review 和 CI 需按合同另行执行。
