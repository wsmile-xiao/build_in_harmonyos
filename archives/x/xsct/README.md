# xsct 2.3 — HarmonyOS PC 适配

## 软件信息

| 字段 | 值 |
|------|-----|
| 名称 | xsct |
| 版本 | 2.3 |
| 类型 | 命令行工具 (CLI) |
| 许可证 | Unlicense |
| 上游仓库 | https://github.com/faf0/sct |
| 描述 | X11 set color temperature — 设置屏幕色温的小工具 |

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libx11 | 6.4.0 | X11 客户端库 |
| libxrandr | 1.5.5.1 | X RandR 扩展库 |
| libxrender | 0.9.12 | X Render 扩展库 |
| xorgproto | 2025.1 | X.Org 协议头文件 |

## 适配说明

xsct 是一个简单的 Makefile 项目，构建产物为单个可执行文件 `xsct`。

### OHOS 适配要点

1. **编译器覆盖**：通过 `make CC=clang` 覆盖 Makefile 中的 `CC ?= gcc`
2. **头文件路径**：通过 `CFLAGS` 传递 libx11/libxrandr/libxrender/xorgproto 的 include 路径
3. **库路径**：通过 `LDFLAGS` 传递 libx11/libxrandr 的 lib 路径
4. **移除 strip**：OHOS 需要签名二进制，不能 strip

### 构建命令

```bash
make CC=clang CFLAGS="-I/path/to/includes" LDFLAGS="-L/path/to/libs"
```

## 验证结果

- conan create: ✅ PASS
- conan-verify: ✅ PASS (G0/G1/G2/G3/G4 + L2/L4/L5)
- W3 本地 CI: ✅ PASS (L0/L1/L2/L4/L5)
- test_package: ✅ PASS (消费者端到端用例 `consumer_test.sh`：A 鸿蒙特有非断言测试 + B 原生真实执行)

## 测试

### 上游测试

xsct 没有自动化测试套件（无 `make check` 目标）。

### 适配后测试

test_package 通过 `consumer_test.sh` 执行消费者端到端用例（每步校验退出码，不使用 Python assert）：

**A. 鸿蒙特有非断言测试 —— 原生 ELF 与动态依赖闭包加载**

1. xsct 为 OHOS aarch64 原生 ELF 可执行文件（`readelf -h`）
2. DT_NEEDED 动态闭包含 libX11.so.6 / libXrandr.so.2（`readelf -d`）
3. 闭包在本机**真实加载**：由本机动态加载器逐个 `dlopen` 整个 DT_NEEDED 列表（python3 ctypes），非静态字符串检查

**B. 端到端消费者用例（原生进程真实执行）**

4. 无 DISPLAY 原生执行 xsct：动态闭包完整加载并运行到 X11 运行时路径，按上游源码语义优雅返回 `EXIT_FAILURE(1)`
5. 伪造不可达 `DISPLAY=:9999` 执行 xsct：仍优雅失败（非崩溃 / 非信号终止）

## 使用方式

```bash
xsct 3700 0.9   # 设置色温 3700K，亮度 0.9
xsct 0          # 重置为默认 6500K
xsct            # 估算当前色温
```

## PR 信息

- 分支：`feat/xsct-2.3`
- 状态：built
