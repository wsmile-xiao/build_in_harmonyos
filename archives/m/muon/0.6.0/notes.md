# muon 0.6.0 适配笔记

## 编译环境
- 构建系统: bootstrap（自举）— bootstrap.sh 编译 src/amalgam.c 产出 muon-bootstrap，再 setup/compile 完整构建
- 编译日期: 2026-08-07
- 编译器: clang 15.0.4 (OHOS SDK, aarch64-linux-ohos)
- 状态: built

## 编译步骤

1. 下载官方 tarball：https://muon.build/releases/v0.6.0/muon-v0.6.0.tar.gz（sha256 90a8428bc2178c59b9f7ddd1cb1cc6355f4df0c3ac023f7eefd159ae4f054024），放入 $HOME/tmp/builds/ 复用
2. 引导构建：`CC=clang ./bootstrap.sh ./build`（产出 ./build/muon-bootstrap）
3. 配置最终构建：`./build/muon-bootstrap setup -Dlibarchive=disabled -Dlibcurl=disabled -Dsamurai=enabled -Dprefix=$DEFAULT_PREFIX build-final`
4. 编译：`ninja -C build-final -j1`（bootstrap 版 muon 不支持默认构建动作，需外部 ninja 或后续 muon -C build samu）
5. 安装：`./build/muon-bootstrap -C build-final install`（DESTDIR staging 隔离）
6. 测试：`./build-final2/muon -C build-final2 test`（部分环境限制，见验证结果）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bootstrap 版 muon 报 `error missing command` / `invalid command 'compile'` | bootstrap 版不支持默认构建动作，构建命令集受限 | 用外部 `ninja -C build-final -j1`，或完整版 `muon -C build samu` |
| 2 | `muon test` 报 `ninja: Permission denied` | 鸿蒙 hmdfs 上 /storage/Users/currentUser/usr/local/bin/ninja 被 SELinux 域拒绝执行 | 用 /data/service/hnp/bin/ninja（1.13.1）或 muon 内嵌 samurai 后端 |
| 3 | conan test_package 中 `muon setup` 报 `/system/bin/sh: syntax error: unexpected '('` | 工作目录路径含 `(1)`（build_in_harmonyos-main (1)），/bin/sh -c 把 `(1)` 解析为子 shell 语法 | test_package 中 cd 路径加引号；conan-verify 用 OHC_PROJECT_DIR 指向无括号符号链接路径 |
| 4 | `muon setup` 编译器检测脚本在鸿蒙 sh 下失败 | 鸿蒙 /system/bin/sh 对部分 bash 语法不兼容 | test_package 中设置 SHELL/CONFIG_SHELL=/data/service/hnp/bin/bash |
| 5 | /tmp 已满（100% 只读），mkstemp 失败 | /tmp 磁盘满 | 设置 TMPDIR=$HOME/tmp |
| 6 | conan create 报 `settings.os.version 未定义` | 默认 profile 无 os.version | 使用 ci/conan/profiles/ohos-aarch64（含 os.version=6.0） |

## 依赖版本

- 无编译依赖（纯 C 工具，libarchive/libcurl/libpkgconf 均禁用；samurai 内嵌）

## 验证结果

- conan create：PASS（bootstrap → setup → ninja compile → install → test_package 实质测试通过）
- conan-verify 8 道门禁：G0-G4 + L2/L4/L5 全部 PASS
- test_package 实质测试：muon version + 最小 meson.build 项目 setup + samu 编译（hello 可执行）
- 上游测试：396 个用例（fmt/lang/lsp/project 等），fmt 子集 10/10 PASS，internal eval 采样 75/80 PASS（93.8%）；project 集成测试依赖 ninja/ar 后端，鸿蒙环境部分受限未完整执行

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | bootstrap 构建配方（application 类型） |
| conandata.yml | 源码 URL + sha256 |
| test_package/ | 消费者测试（version + setup + samu 编译最小项目） |
| commands.json | R38 命令行工具声明 |
| manifest.yaml / notes.md | 归档元数据 |

## 注意事项

- 鸿蒙 PC 上 ninja 执行受限时，优先用 /data/service/hnp/bin/ninja 或 muon 内嵌 samurai（-Dsamurai=enabled）
- conan-verify 在含 `(1)` 的路径下 /bin/sh -c 会解析失败，需 OHC_PROJECT_DIR 指向无括号路径
