# twclock 3.5 测试报告

## 构建验证
- **conan create**: 通过（WSL + ohos-aarch64-wsl profile）
- **W3 本地 CI 模拟**: 通过（build_and_test.sh）
- **产物**: bin/twclock (aarch64 ELF), share/X11/app-defaults/Twclock, share/man/man1/twclock.1, share/applications/twclock.desktop, share/pixmaps/twclock.png, licenses/COPYING

## 上游测试清点
- twclock 3.5 无正式测试套件（无 test 源文件、无 test: 目标）
- `make check` 为空 pass-through（check-am: all-am），build() 内原样执行并捕获输出
- CHECK_EXIT=0

## 消费者测试（test_package）
- 断言数: 11
- 通过: 11
- 失败: 0
- 覆盖: 二进制存在性/可执行性、ELF DT_NEEDED 链（libXm/libXt/libX11/libpulse-simple/libpulse）、headless 行为、打包产物完整性

## 已知限制
- libxpm 未纳入依赖（track 冲突：libxpm 用 libx11/6.4.0，motif 强制 libx11/1.8.13）
- XPM 窗口图标不可用（上游 configure.ac 有 fallback）
- 本地 WSL 测试通过 qemu-aarch64 执行 aarch64 二进制；CI 原生 aarch64 环境直接执行