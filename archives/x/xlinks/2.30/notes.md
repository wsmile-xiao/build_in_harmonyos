# xlinks 2.30（Links 文本终端模式）

## 来源与范围

- 官方源码：<https://links.twibright.com/download/links-2.30.tar.gz>
- SHA-256：`7f0d54f4f7d1f094c25c9cbd657f98bc998311122563b1d757c9aeb1d3423b9e`
- 许可证：GPL-2.0-or-later；上游许可证文件另含 OpenSSL 链接例外。
- 本 Conan 包名为 `xlinks/2.30`，安装命令为 `links`。
- 只构建文本终端模式，不启用图形界面或 X11 驱动。

## 构建选择

- 使用上游 Autotools 构建系统，通过 Conan 的 AutotoolsToolchain、PkgConfigDeps 和 AutotoolsDeps 注入编译与依赖路径。HarmonyOS 真机 host/build 均为 aarch64，configure 检测为原生构建（非交叉编译）。
- 按 `knowledge/ARCHIVE-SPEC.md` §2.2 的终端工具要求，AutotoolsToolchain 设置 `LDFLAGS=-static`。上游支持 `--without-brotli`；该选项用于规避已发布 Brotli 配方固定生成共享库、无法满足全静态链接的问题。
- 直接依赖为 `openssl/3.5.8.1` 与 `zlib/1.3.2.1`；开始实现前已确认这些配方存在于 `ohpcd`。Brotli 压缩不启用。
- 显式关闭上游可选的 libevent、GPM、Zstandard、bzip2、LZMA、Lzip 和 OpenMP 支持，避免隐式链接设备系统库。
- 上游没有 `TESTS` 注册、测试目录或独立测试程序。生成的 `make check` 仅依赖 `all-am`，不执行测试，因此 Conan 构建只运行编译与安装步骤；此事实记录在 `test_package/MANIFEST.yml`。
- `patches/0001-accept-double-dash-version.patch` 为上游 `-version` 选项增加 `--version` 别名，以兼容仓库通用 CLI smoke gate；真机 Conan test_package 和 G0 clean build 均验证了该补丁。

## HarmonyOS 验证

- HarmonyOS 6.0 aarch64 真机上完成 Conan 构建和 consumer test，回环网页行为及 `links --version` 共 6 项全部通过。
- 仓库 W3 本地 CI 的 L0、L1、L2、L4、L5 门禁全部通过；L2 实际运行 `links --version`。
- 全仓测试在设备 staging 中以进程级 Git 临时仓库信任设置运行，12 个测试套件全部通过。该设置只对测试进程生效。
- finish 的 W3 测试门禁通过；其最终收尾另报告归档就绪/知识完整性警告。`knowledge/ARCHIVE-SPEC.md` v3.0 已将手工 `packaging/` 和 `.staging-verified` 标为废弃，相关文件未加入归档。
