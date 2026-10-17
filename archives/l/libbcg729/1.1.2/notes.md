# libbcg729 1.1.2 适配笔记

## 软件信息
- **名称**: libbcg729 (Belledonne Communications bcg729)
- **版本**: 1.1.2 (2026-07-10 正式 release tag)
- **描述**: ITU G.729 Annex A/B 语音编解码开源实现（C99，支持并发编解码通道）
- **License**: GPL-3.0-only
- **上游**: https://github.com/BelledonneCommunications/bcg729

## 编译环境
- 构建系统: cmake（上游原生 CMakeLists.txt，未重造）
- 编译日期: 2026-08-26
- 编译器: clang/clang++（OHOS profile clang 15）
- 状态: built

## 源码核实
- **真实上游**: BelledonneCommunications/bcg729（linphone.org 官方镜像）
- **正式 1.1.2 版本**: GitHub release tag `1.1.2`（CHANGELOG.md 确认 2026-07-10 发布）
- **真实 URL**: https://github.com/BelledonneCommunications/bcg729/archive/refs/tags/1.1.2.tar.gz
- **真实 sha256**: `9c22d98c2debc1e37163b8a703f05278ad5d9c03f1c6b373629d8a072092184a`
- 验证方式: git clone tag 1.1.2 + 下载 GitHub tag archive，内容一致（diff 无差异）

## 构建配置
上游 CMake 选项（conanfile.py generate() 设置）：
- `ENABLE_STRICT=OFF` — 上游默认 YES 会加 `-Werror -Wextra`，在 OHOS 交叉工具链上把无害 warning 变成硬失败，关闭 strict（但保留真实编译错误的可见性）
- `ENABLE_UNIT_TESTS=OFF` — 上游测试需 `test/bin/` 下大规模语音测试数据，且访问内部私有符号（会强制 `-fvisibility=hidden` 关闭），不适合交叉编译 L1 测试
- `BUILD_SHARED_LIBS=ON` — 默认动态库

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub tarball 下载超时 | OHOS 真机 curl 无法直连 github.com（DNS/网络限制），但 git 可达 | 最终 conandata.yml 仅保留上游 GitHub HTTPS 源码地址；本地验证期间通过开发环境缓存解决网络访问限制，本地缓存及路径不进入提交 |
| 2 | ENABLE_STRICT 导致 -Werror 失败风险 | 上游默认 `-Werror -Wextra` | `ENABLE_STRICT=OFF`（不屏蔽真实编译错误） |
| 3 | 上游 ENABLE_UNIT_TESTS 不适合交叉 | 需语音测试数据 + 访问私有符号 | 关闭，改用自定义 test_package 覆盖公开 ABI |

## 补丁
无补丁（零 patch）。上游原生 CMake 直接可用。

## 依赖版本
无外部依赖（纯 C 库，仅 libc）。

## test_package
自定义 L1 测试，调用真实公开 API 完成编解码 round-trip：
1. `initBcg729EncoderChannel(0)` — 创建编码器 context
2. `bcg729Encoder(enc, silence, bitStream, &len)` — 编码 80 样本静音帧，验证 bitStreamLength>0
3. `initBcg729DecoderChannel()` — 创建解码器 context
4. `bcg729Decoder(dec, bitStream, len, 0,0,0, output)` — 解码，验证 80 样本输出有效
5. `closeBcg729EncoderChannel` / `closeBcg729DecoderChannel` — 释放资源

不加载上游大规模语音测试数据，用静音帧即可验证 context 创建 + API 返回行为 + 资源释放。

## 验证结果
```bash
bash ci/conan/build_and_test.sh archives/l/libbcg729/1.1.2
```
（结果见最终汇报）

## 交付物
| 文件 | 说明 |
|------|------|
| `libbcg729.so` | 动态库（上游 VERSION=0） |
| `bcg729/encoder.h`, `bcg729/decoder.h` | 公开头文件 |
| `libbcg729.pc` | pkg-config 文件 |
| `libbcg729Config.cmake` + `libbcg729Targets.cmake` | CMake config 包 |

---
**编译结束**: 2026-08-26
**最终状态**: built
