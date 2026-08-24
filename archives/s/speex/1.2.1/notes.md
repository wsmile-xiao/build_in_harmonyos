# speex 1.2.1 — HarmonyOS PC (aarch64) 适配笔记

## 结论
- **状态**: published（本地 conan-verify 全门禁 PASS：G0-G4 + L2/L4/L5）
- **交付物**: libspeex.a（Speex 语音编解码器，autotools 构建）
- 源码包: `speex-1.2.1.tar.gz`（xiph.org 官方发布）

## 编译环境
- 构建系统: autotools（configure + make）
- 编译日期: 2026-08-23
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）
- Conan: 2.29.1（OHOS 适配版），profile `ohos-aarch64`（os=OHOS, arch=armv8, clang 15, libc++）
- 目标: HarmonyOS PC aarch64（aarch64-unknown-linux-ohos triplet）

## 依赖
| 依赖 | 版本 | 作用 | 备注 |
|------|------|------|------|
| libogg | 1.3.6 | Ogg 容器（speex 可选依赖链） | 已在 ohpcd 制品仓 |

## 编译步骤
1. `conan create archives/s/speex/1.2.1`（AutotoolsToolchain，`--enable-static --disable-shared`，R26 静态）。
2. 补丁应用（4 个，见下）后 configure + make -j1。
3. 产物 `libspeex.a` 经 `make install` 落入 conan package。

## 补丁（4 个，refresh-patch --auto 生成）
| 补丁 | 内容 |
|------|------|
| 0002-config.guess.patch | config.guess 增加 HarmonyOS 检测分支（aarch64-unknown-linux-ohos） |
| 0003-config.h.in.patch | 预填 config.h.in 中 OHOS 相关宏 |
| 0004-config.sub.patch | config.sub 识别 ohos-linux triplet |
| 0005-include-speex-speex_config_types.h.patch | 新建 include/speex/speex_config_types.h（stdint 类型映射） |

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 新建文件补丁应用失败 | refresh-patch 对新建文件生成 `--- a/<path>` 头，Conan2 patch_ng 要求 `--- /dev/null` | conanfile.py build() 在 apply_conandata_patches 前按 export_sources_folder/source_folder 双路径就地改写头行（目标文件在源码树不存在即判定为新建文件补丁） |
| 2 | 本地 dev 环境生成的 env 脚本指向 CI 工具链路径 | CI profile 设置 /data/service/hnp/bin/* | conanfile.py 检测 /data/service/hnp/bin/bash 不存在时，将生成器 .sh 中的工具链路径替换为 which 探测结果 |
| 3 | config.status 写临时文件失败（HMDFS） | configure 用 umask 077 建临时目录，HMDFS setgid 位导致目录不可写 | conanfile.py 运行时把 configure 中 umask 077 替换为 022 |

## 验证结果
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify speex 1.2.1
# G0-G4 + L2/L4/L5 全部 PASS → status: published
```
- conan create 干净构建成功。
- test_package 真实 API 检查（R34）：test.c 调用 `speex_lib_get_mode`/`speex_bits_init`/
  `speex_encoder_init`/`speex_encoder_ctl`/`speex_encoder_destroy` 并断言非空，CMake test
  1/1 Passed（0.03s）。
- 产物: libspeex.a（静态库）。

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | 完整配方（Fix 0 新文件补丁格式修复 / Fix 1 dev env 脚本 / Fix 2 umask 022） |
| conandata.yml | 源码 sha256 与 4 个补丁声明 |
| patches/0002-0005 | OHOS 平台适配补丁 |
| test_package/ | R34 真实 API 消费者测试 |

## 注意事项
- libogg/1.3.6 已在 ohpcd 制品仓（依赖发布预检通过）。
- 上游测试：源码含 libspeex/testenc*.c（3 个）与 ti/ 平台测试（2 个），均面向主机编码器验证，
  本适配以 test_package 消费者真实 API 调用作为验证（R34）。
