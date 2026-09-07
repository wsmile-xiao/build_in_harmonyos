# E550 — 多编解码后端图像库 OHOS 交叉适配组合方案（libtiff 4.7.0 实证）

## 现象

多可选后端图像库（libtiff：zlib/libdeflate/jpeg/zstd/webp/lerc/jbig/lzma 八个
编解码后端）在 OHOS aarch64 交叉编译时：

```
# 场景 A：直接用 conan CMakeToolchain
CMake Error: System is unknown to cmake   ← ML-0035

# 场景 B：绕开 conan_toolchain 但不接线依赖
Could NOT find ZLIB / JPEG / WebP / LERC / JBIG / liblzma / Deflate
# 或者更隐蔽：configure "成功"，但后端全部被静默禁用
#   -- zlib support:                        0 (requested) 0 (availability)
```

构建可能绿，但产物是**功能残缺**的——压缩格式运行期不可用。

## 根因（两层）

1. **conan_toolchain 在 os=OHOS 下不可用**：CMAKE_SYSTEM_NAME 映射成 cmake 不认的值
   （ML-0035），必须绕开。
2. **ohos.toolchain.cmake 的交叉链 FIND_ROOT_PATH_MODE=ONLY**：忽略命令行传入的
   conan 依赖路径（-DCMAKE_PREFIX_PATH / -D<pkg>_ROOT），上游自带 Find 模块的
   find_path/find_library 只在 sysroot 内搜索 → conan 包不可见 → 后端被静默禁用
   （libtiff 的 option() 默认取 *_FOUND 探测结果）。

单后端修一个路径不够——八个后端的 Find 模块缓存变量名各不相同，必须全量接线。

## 修复（三件套组合方案）

```python
# conanfile.py build() 内：
# ① 裸 cmake + 自发现 ohos.toolchain.cmake（profile user_toolchain > OHOS_NDK_HOME > glob SDK）
# ② 后端开关表：全部 -D{backend}=ON（显式声明，不靠探测默认值）
defs = ["-Dzlib=ON", "-Dlibdeflate=ON", "-Djpeg=ON", "-Dzstd=ON",
        "-Dwebp=ON", "-Dlerc=ON", "-Djbig=ON", "-Dlzma=ON"]
# ③ 逐后端 find 缓存变量预设（已设的 cache 变量 find_* 不再搜索 → 绕过 ONLY 限制）
#    (conan依赖, INCLUDE变量, [LIBRARY变量...], [lib文件候选])
wire = [
    ("zlib",          "ZLIB_INCLUDE_DIR",    ["ZLIB_LIBRARY"],                 ["libz.a", "libz.so"]),
    ("libdeflate",    "Deflate_INCLUDE_DIR", ["Deflate_LIBRARY", "..._RELEASE"],["libdeflate.so", "libdeflate.a"]),
    ("libjpeg-turbo", "JPEG_INCLUDE_DIR",    ["JPEG_LIBRARY"],                 ["libjpeg.so", "libjpeg.a"]),
    ("zstd",          "ZSTD_INCLUDE_DIR",    ["ZSTD_LIBRARY", "..._RELEASE"],  ["libzstd.so", "libzstd.a"]),
    ("libwebp",       "WebP_INCLUDE_DIR",    ["WebP_LIBRARY", "..._RELEASE"],  ["libwebp.so", "libwebp.a"]),
    ("lerc",          "LERC_INCLUDE_DIR",    ["LERC_LIBRARY"],                 ["libLerc.so", "libLerc.a"]),
    ("jbigkit",       "JBIG_INCLUDE_DIR",    ["JBIG_LIBRARY", "..._RELEASE"],  ["libjbig.a", "libjbig.so"]),
    ("xz",            "LIBLZMA_INCLUDE_DIR", ["LIBLZMA_LIBRARY", "..._RELEASE"],["liblzma.so", "liblzma.a"]),
]
for dep, incv, libvs, names in wire:
    pkg = self.dependencies[dep].package_folder
    defs += [f'-D{incv}="{pkg}/include"', ...]  # include + 实际 lib 文件全预设
# ④ 链接期注入 -L + -Wl,-rpath-link（lerc 的 libc++_shared.so 等传递 NEEDED）
os.environ["LDFLAGS"] = " ".join(f"-L{d} -Wl,-rpath-link,{d}" for d in ldirs)
# ⑤ 裸 cmake 构建
self.run(f'cmake -B "{bdir}" -S "{src}" {" ".join(defs)}')
self.run(f'cmake --build "{bdir}"')
```

附加：产物 .so 需 `llvm-objcopy --remove-section .codesign` +
`binary-sign-tool sign -selfSign 1` 重签（鸿蒙 XPM 校验）。

## 验证

```bash
conan create . -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
# 后端全开确认（configure 输出）+ test_package 逐后端写读回环断言
# 8/8 codecs roundtrip OK: none/packbits/deflate/adobe_deflate/lzma/zstd/lerc/webp
```

test_package 按后端逐个验证（每后端 write→read→tag 校验→像素 memcmp），
杜绝"构建绿但后端残缺"。

## 查重覆盖判断（vs E447 / E300）

- **E447**（SDL2 系 vendored Find 模块桥接）：单库多 target 的 INTERFACE 变量桥接
  （SDL2_INCLUDE_DIRS 等供上游 include_directories 消费），核心矛盾是
  CMAKE_FIND_PACKAGE_PREFER_CONFIG 下 MODULE/CONFIG 模式切换。
- **E300**（FFTW 自定义 Find 模块桥接）：通用机制条目（upstream Find module 忽略
  conan target 时预设缓存变量）。
- **本条（E550）增量**：①"多可选后端"组合场景——8 个后端一次性全量接线的
  **映射表方法**（conan 依赖 → 各 Find 模块的 INCLUDE/LIBRARY 缓存变量名 →
  lib 文件候选优先级）；② **静默禁用风险**（option 默认取 *_FOUND，漏接=功能
  残缺而非构建失败）及其测试对策（逐后端 roundtrip 断言）；③ 链接期传递
  NEEDED 的 rpath-link 处理；④ conan_toolchain→ohos.toolchain 绕开的组合上下文。
  同词（find 缓存变量桥接）不同题（多后端组合 + 静默失效模式），互补非重复。

## 实证

libtiff 4.7.0（archives/l/libtiff/4.7.0，PR #8326，2026-09-05）：
conan create 全绿，8/8 后端 roundtrip 全过；CI #39997 全步骤通过；AI review 零意见。
下游消费方（leptonica/gdal/libgeotiff 等依赖 libtiff 的库）可直接复用此接线方法。

## 关键词

libtiff, codec backends, 多后端, 交叉编译, conan_toolchain, ohos.toolchain.cmake,
FIND_ROOT_PATH_MODE_ONLY, find cache variable, ZLIB_INCLUDE_DIR, WebP_LIBRARY,
LERC_LIBRARY, 静默禁用, rpath-link, roundtrip test
