# 上游测试实跑证据（R51 台账）

## 内容

- `summary.txt` — 63/63 测试一行一结果（rc + 首行关键输出）
- `test-*.out` — 63 份完整原始输出（stdout+stderr，各测试 10s 超时）
- `run-upstream-tests.py` — 批量 runner（python subprocess，可复现）

## 实测结论（2026-09-28，OHOS aarch64，conan 交叉构建产物）

| 项 | 值 |
|---|---|
| 清点（tests/meson.build `test_names`） | **63** 项，构建全部成功（535 目标 0 FAILED） |
| 实跑 | **63/63** |
| 通过 | **0** |
| 失败模式（63/63 同因） | `gtk_test_init` → `gtk_init` → `Gtk-WARNING: Failed to open display` → g_log fatal → `__builtin_trap()` → **SIGTRAP（rc=-5）** |
| 分类（E471 口径） | display 阻塞 63/63——OHOS 无显示服务（GTK4 Broadway-only 后端，broadwayd 签名约束下不可运行） |
| 次要环境问题（非致命） | `Fontconfig error: Cannot load default config file`（fontconfig/2.18.1.1 包缺默认 fonts.conf，显示链路可用前需处理） |

## 上游纯计算子集移植执行（本次新增）

63 项中仅 **2 项为纯计算测试**（无 widget/显示依赖）：`test-easing`、
`test-accent-color`。其公共 API 断言已 1:1 移植到
`test_package/test.c`（无显示上下文执行）：

| 上游测试 | 断言数 | 可移植性 | 移植执行结果 |
|---|---|---|---|
| test-easing（35 值 × f(0)/f(1)，eps 0.005 契约） | 70 | 公共 API（adw_easing_ease） | **70/70 PASS** |
| test-accent-color：to_rgba 9 + to_standalone_rgba 18 + rgba_to_standalone 8 | 35 | 公共 API | **35/35 PASS** |
| test-accent-color：nearest_from_rgba roundtrip 10 + 调色板 127 | 137 | **私有 API**（见下） | 消费者上下文不可执行（分类留证） |
| **公共 API 合计** | **105** | — | **105/105（100%）PASS** |

**137 条不可移植的原因（实证）**：`adw_accent_color_nearest_from_rgba()`
仅声明于私有头 `src/adw-accent-color-private.h`（公共头 adwaita/ 无声明），
且未从 libadwaita-1.so 导出（`nm -D libadwaita-1.so.0 | grep nearest`
为空；同文件的 to_rgba/to_standalone_rgba/rgba_to_standalone 均正常导出）。
上游测试二进制可用该符号是因为 meson 将 tests 链接到内部静态库
libadwaita-1-internal.a（全部符号，无可见性过滤）；conan test_package
作为消费者只能链接已安装的 .so。

## 复现

```sh
# 1) 构建（-Dtests=true 已启用，63 个测试二进制位于 conan 包构建目录 tests/）
conan create archives/l/libadwaita/1.8.8 --build=missing

# 2) 实跑（BUILD_DIR = conan 构建根目录，其下含 build-release/tests/；
#    缺省值为本次实测机器的 conan 缓存目录，换机器/清缓存后必须传参。
#    env 由 runner 内部固定为实测值，无需外部设置；
#    找不到测试二进制时 runner 以非零码退出，不会静默空跑）
python3 upstream-tests/run-upstream-tests.py <BUILD_DIR> [OUT_DIR]

# 3) 无显示移植执行（conan create 的 test_package 阶段自动执行，
#    或手动运行包内 test_libadwaita 二进制）
```
