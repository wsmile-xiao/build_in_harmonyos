# E324 — libtoolize hardcoded SED path breaks aux-dir resolution

## 错误特征
- `autoreconf -fi` 输出 `libtoolize: putting auxiliary files in '../..'.`
- `automake: error: required file './ltmain.sh' not found`
- 附带 `libtoolize: line 448: /storage/Users/currentUser/usr/local/bin/sed: No such file or directory`
- 结果：`ltmain.sh` 出现在源码目录**上一层或上两层**，而不是源码根目录

## 触发条件
- 构建系统: autotools（git archive 无 configure，需 `autoreconf -fi` 引导）
- 阶段: configuration（bootstrap）
- 环境: 精简 OHOS 镜像，`/storage/Users/currentUser/usr/local/bin` 下没有 `sed`，
  但 libtoolize/automake 脚本在安装时把 SED 硬编码成该绝对路径

## 根因分析
- 安装的 `libtoolize` 脚本第 47 行 `: ${SED="/storage/Users/currentUser/usr/local/bin/sed"}` 硬编码了 SED 默认值。
- 当环境变量 `SED` 未设置时，libtoolize 内部对 configure.ac 的 `extract-trace`
  （AC_CONFIG_AUX_DIR 提取）与 `func_require_aux_dir` 启发式都会失败，
  随后按 `.` → `..` → `../..` 逐级向上找 `install-sh`，最终把辅助文件（ltmain.sh）
  复制到了源码目录的父目录/祖父目录。
- automake 在源码根目录找不到 `./ltmain.sh` → 直接报错退出。

## 解决方案

### 推荐方案
在 `autoreconf -fi` 之前把工具环境变量指向真实路径：
```bash
export SED=$(command -v sed) \
       AUTOCONF=$(command -v autoconf) \
       AUTOHEADER=$(command -v autoheader) \
       AUTOM4TE=$(command -v autom4te)
autoreconf -fi
```
- conanfile.py 中 `_prepare_autotools_env()` 在 `generate()`/`build()` 里完成同样的设置。
- 效果：libtoolize 的 `$SED` 指向真实 sed，aux-dir 启发式正确解析为 `.`，
  `ltmain.sh` 复制到源码根目录。

### 回退方案
手动把 libtool 的 ltmain.sh 复制进源码根目录：
```bash
cp /storage/Users/currentUser/usr/local/share/libtool/build-aux/ltmain.sh .
autoreconf -fi
```

### 禁止做法
- ❌ 不设置 SED 就运行 `autoreconf -fi`（libtoolize 会向上走目录放错 ltmain.sh）
- ❌ 用 `ACLOCAL=/bin/true` 之类跳过 aclocal（后续 automake 仍会失败）

## 关联
- similar_to: E209（"ltmain.sh not found" 的另一根因：autogen.sh/libtool 版本不匹配）
- 平台陷阱: E114（HMDFS umask 077 导致 config.status 失败，configure 后仍需处理）
