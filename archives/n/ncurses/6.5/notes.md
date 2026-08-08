# ncurses 6.5 适配笔记

## 2026-08-01 适配（Conan 配方化）

### 库信息
- **软件**: ncurses
- **版本**: 6.5
- **构建系统**: autotools
- **许可证**: X11
- **上游**: https://invisible-island.net/ncurses/
- **源码**: https://invisible-mirror.net/archives/ncurses/ncurses-6.5.tar.gz
- **SHA256**: `136d91bc269a9a5785e5f9e980bc76ab57428f604ce3e5a5a90cebc767971cc6`

### 背景
multitail/7.1.5（PR #3237）CI 失败根因：conanfile.py 声明 `requires("ncurses/6.5")`，
但 ncurses/6.5 从未适配发布到 ohpcd registry（`conan list "*ncurses*" -r ohpcd` 为空，
仓库 archives/n/ncurses/6.5/ 只有模板 manifest/notes，无 conanfile.py）。
CI 日志明确提示"请先提交依赖包的 PR 并等待 CI 通过"。
仓库中 aamath/joe/nethogs/progress 等 4+ 包也声明依赖 ncurses/6.5，发布后一并解锁。

### 编译配置（继承 6.4 经验）
| 配置项 | 说明 |
|--------|------|
| `--without-shared` | 🔴 必须静态编译，共享库会劫持系统 libncursesw.so.6 导致 zsh 崩溃 |
| `--enable-widec` | 宽字符版本 libncursesw（readline/multitail 依赖） |
| `--enable-overwrite` | 头文件安装到顶层 include/ 而非 include/ncursesw/ |
| `--without-debug/ada/manpages/tests/cxx-binding` | 精简依赖 |

### 补丁
- `0001-port-for-ohos.patch`：config.guess + config.sub 添加 HarmonyOS/OHOS 识别
  - config.guess：`*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`
  - config.sub：OS 列表加 `ohos*`，内核列表加 `linux-ohos*-`
  - ⚠️ 6.5 与 6.4 行号不同（6.4 补丁直接应用报 FAILED 969/1754），
    需基于 6.5 源码重新生成（逻辑一致，仅行号偏移）

### 依赖版本
- 无第三方依赖（纯 C 库）

### 验证结果
```bash
# conan create 后 test_package 验证（本地实测）
ncurses ncurses 6.5.20240427: wide-char roundtrip ok
# test_package：curses_version() 版本检查 + setcchar/getcchar 宽字符往返，1/1 通过
```
- 构建方式：out-of-source（Autotools 类默认）+ umask 022 补丁（0002）+ as_expr=false 补丁（0003）
- ⚠️ 关键坑：OHOS 沙箱 toybox expr 0.8.12 的 `\|` 多分支链有 bug（首个分支匹配时输出
  垃圾字节但退出码为 0，sed fallback 不触发），污染 config.status 的 ac_dir 提取 → top_srcdir
  乱码。0003 补丁强制 as_expr=false 走 sed fallback（sed 提取结果正确）

### 注意事项
- 发布后 registry 将同时解锁 multitail(#3237)、aamath、joe、nethogs、progress 等包
- package_info 输出 4 个宽字符静态库：libncursesw/libpanelw/libmenuw/libformw
