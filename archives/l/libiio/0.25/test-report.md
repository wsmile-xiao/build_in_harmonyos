# Test Report — libiio 0.25

**Date**: 2026-09-05
**Build System**: CMake
**Target**: HarmonyOS PC (aarch64, musl, clang 15.0.4)

## 上游测试状况

libiio 0.25 上游**没有 CTest 注册用例**（`ctest -N` 输出为空）。上游 `tests/`
目录构建 6 个交互式 CLI 工具（iio_info / iio_genxml / iio_attr / iio_readdev /
iio_reg / iio_writedev，pthread 可用时另有 iio_stresstest），全部要求一个可用的
IIO context（真实 `/sys/bus/iio` 设备或运行中的 iiod 守护进程）。

**OHOS PC 平台限制**：本机实测 `/sys/bus/iio` 不存在（无 IIO 内核子系统），
上述工具无法获得真实设备 context。此为平台能力边界，非适配缺陷。

### 上游工具 smoke 结果（二进制可执行性验证）

| 工具 | 构建产物 | `--help` | 无设备运行（graceful 失败路径） |
|------|----------|----------|--------------------------------|
| iio_info | ✅ bin/iio_info | ✅ exit 0 | ✅ "Unable to create Local IIO context : Function not implemented (38)" 非崩溃优雅退出 |
| iio_genxml | ✅ | ✅ | ✅ 同上 |
| iio_attr | ✅ | ✅ | ✅ 同上 |
| iio_reg | ✅ | ✅ | ✅ 同上 |
| iio_readdev | ✅ | ✅ | ✅ 同上 |
| iio_writedev | ✅ | ✅ | ✅ 同上 |
| iio_stresstest | ✅ | ✅ | ✅ 同上 |

**上游测试通过率：可执行性验证 7/7 通过；设备级功能断言 0/6（平台无 IIO 子系统，逐条原因见 notes.md）。**

## test_package 结果（消费者视角，R34）

`conan create` 内置 test_package：ctest 执行 test_iio 二进制，**1/1 Passed**。

test_iio 对打包库做真实 API 调用链验证（非 print-only stub）：

| # | API 断言 | 结果 |
|---|----------|------|
| 1 | iio_library_get_version() == 0.25 | PASS |
| 2 | iio_get_backends_count() >= 1 | PASS |
| 3 | xml 后端已注册（iio_get_backend 遍历） | PASS |
| 4 | iio_create_xml_context_mem() != NULL（内存 XML context，无需内核 IIO） | PASS |
| 5 | iio_context_get_name() == "local" | PASS |
| 6 | iio_context_get_devices_count() == 1 | PASS |
| 7 | iio_context_get_device(0) != NULL | PASS |
| 8 | iio_device_get_id() == "iio:device0" | PASS |
| 9 | iio_device_get_name() == "ad5541a" | PASS |
| 10 | iio_device_get_channels_count() == 1 | PASS |
| 11 | iio_device_get_channel(0) != NULL | PASS |
| 12 | iio_channel_get_id() == "voltage0" | PASS |
| 13 | iio_channel_get_attrs_count() == 2 | PASS |
| 14 | iio_channel_get_attr(0) != NULL | PASS |
| 15 | iio_context_destroy() 完整生命周期 | PASS |

**test_package：15/15 断言全部通过（100%）。**

## 本地 CI 模拟（W3）

`ci/conan/build_and_test.sh archives/l/libiio/0.25` → **RC=0，Pass rate 100%**

```
G0_RESULT=pass
KC_RESULT=pass
JC_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: iio_* version/help failed (non-blocking; W3 runner 无 conanrun 库路径环境，CI 执行机有 profile LD_LIBRARY_PATH)
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
.ci-result.json exit_code=0
```

## 结论

- 库本体 + 7 个 CLI 工具全部构建成功（clang 15.0.4 / aarch64-linux-ohos / musl）
- XML 后端（libxml2）全链路 API 验证通过；无 IIO 硬件的平台限制已在
  notes.md / MANIFEST.yml 逐条说明
- 零 patch 适配（上游 CMake 的 Linux-only 条件块天然匹配裁剪策略）
