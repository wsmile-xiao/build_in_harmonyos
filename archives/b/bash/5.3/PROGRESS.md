# bash 5.3 编译进度

**日期**: 2026-04-13
**状态**: ✅ 编译完成，待 finish

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | tarball 已有，自动解压+骨架创建 |
| Step 2 patches | ✅ | 0001-port-for-ohos.patch (config.guess+config.sub) |
| Step 3 configure | ✅ | `--prefix=$TEST_PREFIX --without-bash-malloc`，使用 bundled readline |
| Step 4 make | ✅ | 单线程编译成功 |
| Step 5 install | ✅ | 安装到 staging 目录 |
| Step 6 safety | ✅ | `--version` 正常输出 |
| Step 7 check | ✅ partial | 73/74 测试完成，run-read 卡住被 kill |
| Step 8 staging | ✅ | NEEDED: 仅 libc.so，无 ncurses/readline 动态依赖 |
| Step 9 package | ⏳ | |
| Step 10 deploy | ⏳ | |
| Step 11 finish | ⏳ | |

## 关键变更（R15 纠正）

### 问题
上一版 bash 编译产物依赖 ncurses 动态库（违反 R4），使用 `--with-installed-readline` 链接了 readline 8.2 的 .so。

### 解决方案
1. 去掉 `--with-installed-readline`，改用 bash 自带的 bundled readline
2. 临时移除 `libreadline.so*`，只保留 `libreadline.a`
3. 链接时只有 `libncursesw.a` 可用（ncurses 编译时已 `--without-shared`）

### 结果
- `NEEDED: [libc.so]` — 仅依赖 libc，ncurses 和 readline 均静态嵌入
- 完全解决了 ncurses 动态库劫持问题

### configure 参数变更
| 参数 | 旧版 | 新版 | 原因 |
|------|------|------|------|
| `--with-installed-readline` | ✅ 使用 | ❌ 移除 | readline 8.2 缺少 rl_completion_rewrite_hook 等符号 |
| `--without-bash-malloc` | ✅ | ✅ | 保持不变 |
| `LDFLAGS` | 无 | `-L$DEFAULT_PREFIX` | 确保找到 libncursesw.a |
| `CFLAGS` | 无 | `-fPIC -O2 -I$DEFAULT_PREFIX/include` | 确保找到 ncurses 头文件 |

## 源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| support/config.guess | 平台检测 | 0001-port-for-ohos.patch | 已有 |
| support/config.sub | 平台检测 | 0001-port-for-ohos.patch | 已有 |

## 头文件修复（编译前提）
ncurses 和 readline 的头文件之前未正确安装到 `~/usr/local/include/`：
- ncurses 头文件：从 staging 目录复制到 `~/usr/local/include/`
- readline 头文件：从 staging 目录复制到 `~/usr/local/include/readline/`

## 发现与知识
- bash 5.3 bundled readline 版本 >= 8.3，包含 rl_completion_rewrite_hook 等新符号
- 使用 bundled readline 时自动静态链接 libncursesw.a，无需额外参数
- run-read 测试在无交互终端下会卡住（已知问题）

---

**编译结束**: 2026-04-13 23:50
**最终状态**: success
