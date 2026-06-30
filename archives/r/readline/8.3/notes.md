# readline 8.3 编译笔记

## 编译信息

- **软件**: readline (包含 libreadline 和 libhistory)
- **版本**: 8.3
- **日期**: 2026-06-05
- **状态**: published

## 源码下载

- **URL**: ftp://ftp.gnu.org/gnu/readline/readline-8.3.tar.gz
- **格式**: tar.gz

## 编译过程

### 配置

```bash
CFLAGS="-fPIC -O2" ./configure --prefix=$HOME/usr/local --with-curses
```

**关键参数**:
- `CFLAGS="-fPIC -O2"`: 必须设置，否则静态库链接到共享库会报错
- `--with-curses`: 使用 ncurses 库

### 编译

```bash
make -j4
```

### 安装

```bash
make install DESTDIR=$TEST_PREFIX
make install  # 安装到本地
```

## 问题与解决

### 问题 1: config.guess 无法识别 HarmonyOS

**错误信息**:
```
configure: error: cannot guess build type; you must specify one
```

**解决方案**:
应用补丁 `0001-config.guess-harmonyos.patch`，添加 HarmonyOS 系统识别逻辑。

### 问题 2: config.status 临时目录创建失败

**错误信息**:
```
./config.status[742]: can't create ./confXXX/subs1.awk: Permission denied
```

**解决方案**:
修改 config.status 使用绝对路径临时目录 `/storage/Users/currentUser/tmp/confXXXXXX`。

## 产物

- `libreadline.a` - 静态库
- `libreadline.so.8.3` - 动态库
- `libhistory.a` - 历史库静态库
- `libhistory.so.8.3` - 历史库动态库
- `readline.pc` - pkg-config 文件
- `history.pc` - pkg-config 文件

## 依赖

- ncursesw: 终端库

## 验证

```bash
pkg-config --modversion history
# 输出: 8.3
```

---

**编译结束**
**最终状态**: published
---

**编译结束**: 2026-06-05 17:07
**最终状态**: published

## 功能测试结果

**测试日期**: 2026-06-05

### 测试汇总
- 总测试数: 17 个
- 通过测试: 17 个 ✅
- 失败测试: 0 个 ❌
- **测试结论**: 所有测试通过，readline 8.3 在鸿蒙平台完全可用

### 编译测试
| 编译方式 | 状态 | 备注 |
|---------|------|------|
| 静态链接 | ✅ 完全可用 | 推荐使用，测试程序大小 1.4MB |
| 动态链接 | ✅ 编译成功 | 需配置动态链接器路径 |

### 核心功能验证
- ✅ 行编辑功能: 正常
- ✅ 历史记录功能: 正常 (add_history, history_get, clear_history)
- ✅ 自动补全功能: 正常
- ✅ 键绑定功能: 正常
- ✅ pkg-config: 正常 (版本 8.3)

### 详细测试报告
见 `reports/test-report.md`

## 发布状态

- ✅ 预编译包: `readline-8.3-ohos-aarch64.tar.gz` (2.78MB)
- ✅ 补丁: `0001-config.guess-harmonyos.patch`
- ✅ 功能测试: 全部通过
- ✅ 质量门禁: G1-G4 通过
- ✅ 可发布到 cmd-pkgs
