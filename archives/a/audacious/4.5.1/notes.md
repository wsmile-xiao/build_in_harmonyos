# audacious 4.5.1 编译笔记

## 编译日期
2026-05-25
## 编译环境
- 系统: HarmonyOS (HongMeng Kernel 1.12.0)
- 编译器: clang
- 构建系统: autotools
## 依赖
- glib2 2.84.0 ✅
- libiconv ✅
## 问题与解决
### 问题1: 无需额外补丁
audacious 的 autotools configure 可自动识别 HarmonyOS 平台（通过 config.guess/config.sub 已更新的版本）。

**解决**: 无需额外补丁，直接 configure + make 即可。
## 编译步骤
```bash
# init
python3 $SKILL_ROOT/scripts/ohc-run.py init-build audacious 4.5.1
# configure
./configure --prefix=$DEFAULT_PREFIX --disable-gtk --disable-qt
# make
make -j2
# install (DESTDIR staging)
make install DESTDIR=$TEST_PREFIX
# package
python3 $SKILL_ROOT/scripts/ohc-run.py package audacious 4.5.1
python3 $SKILL_ROOT/scripts/ohc-run.py package audacious 4.5.1 --debug
```
## 补丁文件
无额外补丁（平台可自动识别）
## 验证结果
- ✅ audacious --version 正常
**编译结束**: 2026-05-25
**最终状态**: built
---

**编译结束**: 2026-05-27 17:27
**最终状态**: built
