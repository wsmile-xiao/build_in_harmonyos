# libnsbmp (NetSurf BMP/ICO decoder)

## 简介
libnsbmp 是 NetSurf 项目的 BMP/ICO 图像解码库，支持 BMP（含 RLE8/RLE4/Bitfields 编码）与 ICO 格式解析与解码，以 MIT 许可发布。

## OHOS 适配
- 构建系统为 NetSurf 私有 NSSHARED（netsurf-buildsystem），非 autotools/cmake/meson，OHOS 未打包该元构建工具
- 以 standalone Makefile 补丁替换 NSSHARED 依赖，复用上游全部编译选项、警告标志与测试规则
- 唯一行为差异：移除 `-Werror`（上游面向 GCC，OHOS clang 警告可能不同，`-Werror` 会在无害警告处中断构建）
- 默认静态库（`COMPONENT_TYPE ?= lib-static`），`package_type = static-library`
- 无外部库依赖；运行期仅需 `libm`
- 不 vendoring 其他项目源码，不链接宿主机 `/usr/local` 库

## 上游正式测试
| 项 | 值 |
|----|----|
| 测试入口 | `test/runtest.sh` |
| 测试程序 | `test_decode_bmp`、`test_decode_ico` |
| BMP 语料 | 1070 文件 |
| ICO 语料 | 611 文件 |
| 合计 | 1681 文件 |

`make check` 在 `conan create` 构建阶段执行，覆盖全部 1681 个上游测试数据文件。

## 消费者测试 (test_package)
内嵌 62 字节 2×1 24-bit BMP（红 + 绿像素），调用 `bmp_create` → `bmp_analyse` → `bmp_decode` → `bmp_finalise` 全链路，校验宽、高、bpp、解码状态及像素字节值（8/8 checks passed）。

## 依赖
- 无编译依赖
- 运行期：`libm`

## 功能验证
```bash
conan create archives/l/libnsbmp/0.1.7 -pr:b default -pr:h ci/conan/profiles/ohos-aarch64
conan test archives/l/libnsbmp/0.1.7/test_package libnsbmp/0.1.7 -pr:b default -pr:h ci/conan/profiles/ohos-aarch64
```

## 参考
- 主页: https://www.netsurf-browser.org/projects/libnsbmp/
- 源码: https://download.netsurf-browser.org/libs/releases/libnsbmp-0.1.7-src.tar.gz
