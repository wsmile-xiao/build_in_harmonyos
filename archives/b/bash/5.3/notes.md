# bash 5.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-13
- 编译器: clang
- 状态: success

## 编译步骤
```bash
./configure --prefix=$TEST_PREFIX --without-bash-malloc
make -j$(nproc)
make install
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | uname -s 返回 HarmonyOS | 补丁添加 __OHOS__ 宏检测和 HarmonyOS case |
| 2 | 内存分配器不兼容 | bash malloc 与 musl libc 冲突 | `--without-bash-malloc` |
| 3 | ncurses 动态依赖 | readline 8.2 缺少新符号 | 使用 bundled readline（>= 8.3），静态链接 ncursesw |

## 验证结果
- `bash --version` ✅ GNU bash 5.3.0(1)-release (aarch64-unknown-linux-ohos)
- 73/74 测试通过（run-read 因无交互终端被 kill）
- NEEDED: [libc.so] ✅

## 注意事项
- 首次运行会弹窗确认（鸿蒙安全机制）
- /tmp 只读，需设置 TMPDIR=$HOME/tmp
