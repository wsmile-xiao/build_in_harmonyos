# libcvd 0.0-git20221020150751.30e8cfc — HarmonyOS PC 验证记录

- 上游源码：`edrosten/libcvd@30e8cfc1697048c7d8fb48e0b7853a4e2b4b9867`；固定 tarball SHA-256 为 `daf779f6af6d70c493715861326ea4590e5c1bbae65f6371610a2d2b40c0b10e`。
- 环境：HarmonyOS PC，`os=OHOS`、`os.version=6.0`、armv8/arm64、Clang 15.0.4、C++17。
- 配方验证：`conan create recipe -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd --build=libcvd/*` 成功，生成动态库 `libcvd.so`。直接依赖 `libjpeg-turbo/3.2.0`、`libpng/1.6.58`、`libtiff/4.7.0`、`zlib/1.3.1.1` 均来自 ohpcd 已发布包。
- 依赖解析：`libpng/1.6.58.3` 与 `libtiff/4.7.0` 的 zlib 版本需求冲突；选用同样已发布的 `libpng/1.6.58` 与 `libtiff/4.7.0`，二者均使用 `zlib/1.3.1.1`。没有修改依赖包配方。
- 编译修复：初始构建在 `cvd_src/globlist.cxx:26` 因 `GLOB_BRACE` 缺失失败；启用上游现有 `CVD_INTERNAL_GLOB_IS_BAD` 配置，保留 `glob()` 基本匹配。未修改上游源码或测试。
- 图像格式：JPEG、PNG、TIFF 均由 CMake 发现并编译。FFmpeg、OpenCV、采集设备与图形窗口后端不在本次包的功能集内。

## 上游测试清单

上游 `tests/CMakeLists.txt` 声明 8 个 CTest 目标。其中固定功能集启用 5 个：`distance_transform_test`、`fast_corner_test`、`load_and_save`、`convolution`、`flips`。FFmpeg 功能门控 2 个，OpenCV 功能门控 1 个；这 3 个未构建也未冒充通过。目标机构建后运行 `ctest -N` 确认为 5 个活动目标。

在目标机执行 `ctest --output-on-failure -j1`：5/5 通过，0 失败、0 跳过。执行时设置全部 Conan 运行依赖的 `LD_LIBRARY_PATH`；正式配方通过 `VirtualRunEnv` 提供同等闭包。

- 清单证据：`D:/Projects/harmonyPC/evidence/libcvd-0.0-git20221020150751.30e8cfc/upstream-test-inventory.txt`，SHA-256 `cc81c1492a06f99ad43e71d5c0bfea7500a08a3fbf731c0e2921b307fcfe3a9c`。
- 运行证据：`D:/Projects/harmonyPC/evidence/libcvd-0.0-git20221020150751.30e8cfc/upstream-test.log`，SHA-256 `1af38132beebcb3b5c03f90f008c998c6f6482f53ed9b095d55cd709e47c340d`。
- Conan `test_package`：独立使用安装后头文件、链接 `libcvd::libcvd`，检查图像尺寸/像素和非内联计时函数，目标机退出码 0。消费者运行证据 SHA-256 `475bcc2d66fce93dbb1c180c94dd55bc616dc8e849d04f2d61b5614dbbf41ea0`。
- 平台 PR CI：尚未触发；不能以目标机本地成功代表平台 CI 成功。
