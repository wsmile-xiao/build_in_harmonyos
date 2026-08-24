# celt 1.0.0 适配笔记

## 版本说明

- **配方版本**: 1.0.0（项目内版本号）
- **上游源码**: celt-0.11.3（Xiph.Org 最后独立发布版本）
- **上游 URL**: `http://downloads.xiph.org/releases/celt/celt-0.11.3.tar.gz`
- **备注**: celt 上游版本范围为 0.0.1 ~ 0.11.3，不存在 1.0.0。0.11.3 之后 CELT 技术合并入 Opus（RFC 6716）。

## 构建系统

- **类型**: Autotools（configure.ac + Makefile.am）
- **语言**: C99
- **库名**: `libcelt0`（LIBCELT_SUFFIX=0 → SONAME libcelt0.so.0）
- **头文件**: `celt.h`, `celt_types.h`, `celt_header.h`（pkgincludedir = `$includedir/celt/`）
- **pkgconfig**: `celt.pc`

## 依赖

| 依赖 | 必需 | 说明 |
|------|------|------|
| libm | 是 | 数学库（AC_CHECK_LIB m sin） |
| libogg | 否 | 仅 celtenc/celtdec 工具需要，配方中 `--without-ogg` 关闭 |

## 构建策略

- `--without-ogg`：关闭 libogg 依赖 → 不构建 celtenc/celtdec 命令行工具
- 仅构建 libcelt0 静态库（`--disable-shared` 可按需开启）
- `make check` 运行 8 个上游测试

## 上游测试清单

| 测试 | 文件 | 描述 |
|------|------|------|
| type-test | tests/type-test.c | celt 类型定义验证 |
| ectest | tests/ectest.c | 熵编码单元测试 |
| cwrs32-test | tests/cwrs32-test.c | CWRS 32 位单元测试 |
| dft-test | tests/dft-test.c | DFT 单元测试 |
| laplace-test | tests/laplace-test.c | Laplace 编码单元测试 |
| mdct-test | tests/mdct-test.c | MDCT 单元测试 |
| mathops-test | tests/mathops-test.c | 数学运算单元测试 |
| tandem-test | tests/tandem-test.c | 编解码器串联集成测试 |

## OHOS 适配注意事项

1. CELT 是纯 C99 库，无 C++ 依赖，无 POSIX 线程取消 API，OHOS 兼容性风险低。
2. configure 脚本检查 alloca / C99 VLA，OHOS clang 均支持。
3. 无 symlink / hardlink / FIFO 依赖。
4. 无网络依赖。

## 阻塞点

- [ ] 真机验证未执行（需真机空闲窗口）
- [ ] SHA256 待真机二次确认（本机已计算）
- [ ] issue 编号待补

## 下一步命令

```sh
# 真机 shadow CI 验证
CI_PACKAGES="archives/c/celt/1.0.0" zsh ci/conan/build_and_test.sh

# 或真机 conan create
cd archives/c/celt/1.0.0
conan create . --user=ohpcd --channel=stable -pr:h=$HOME/.conan2/profiles/ohos -pr:b=$HOME/.conan2/profiles/ohos --build=missing
```
