# flashrom 1.6.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-06
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

```bash
# 使用 meson 构建 flashrom，只启用 dummy programmer
meson setup builddir \
  --prefix=/storage/Users/currentUser/usr/local \
  -Dprogrammer=dummy \
  -Drpmc=disabled \
  -Dtests=disabled \
  -Dclassic_cli=enabled \
  -Ddocumentation=disabled

ninja -C builddir -j2
meson install -C builddir --destdir $TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | llvm-ar not found | Meson 无法在默认 PATH 中找到 llvm-ar | 在 conanfile.py 的 generate() 中设置 tc.ar = "/data/service/hnp/bin/llvm-ar" |
| 2 | meson_layout import error | conan 2.29.1 (OHOS-adapted) 没有 meson_layout 函数 | 改用 basic_layout(self, src_folder="src") |
| 3 | meson.compile() AttributeError | conan 2.29.1 的 Meson 类用 build() 而非 compile() | 改用 meson.build() |
| 4 | libusb-1.0/1.0.27 依赖不存在 | 制品仓中没有 libusb，但 dummy programmer 不需要它 | 移除 libusb 依赖声明 |
| 5 | GitHub 下载失败 (BadZipFile) | ghfast.top 镜像不支持 codeload.github.com URL | 改用 github.com/archive URL 格式 |

## 源码修改

无补丁，无源码修改。flashrom 1.6.0 在 HarmonyOS 上原生兼容（使用 dummy programmer）。

## 依赖版本

无外部依赖。flashrom 使用 dummy programmer 时不需要 libusb、libpci 或其他外部库。

## 验证结果

```bash
$ flashrom --version
flashrom v1.6.0 on HarmonyOS HongMeng Kernel 1.12.0 (aarch64)
flashrom is free software, get the source code at https://flashrom.org
```

## 交付物

| 文件 | 类型 | 说明 |
|------|------|------|
| conanfile.py | Conan 配方 | Meson 构建系统，dummy programmer |
| conandata.yml | 源码声明 | GitHub URL + SHA256 |
| test_package/test.c | 测试 | 调用 flashrom_init/flashrom_shutdown API |
| commands.json | 工具声明 | flashrom CLI binary |

## 注意事项

- flashrom 1.6.0 的 meson.build 中有 `host_machine.system() == 'linux'` 检查，但只影响 Linux 特有 programmer（如 linux_mtd、linux_spi），dummy programmer 不受影响
- conan 2.29.1 (OHOS-adapted) 的 API 与标准 conan 2.x 有差异（meson_layout 不可用，Meson.build() 而非 compile()）
- 产物包含：libflashrom.a/libflashrom.so（库）+ flashrom（CLI 工具）+ libflashrom.h（头文件）

---

**编译结束**: 2026-08-06 11:29
**最终状态**: built
