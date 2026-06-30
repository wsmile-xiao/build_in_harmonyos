# diffutils 3.10 编译笔记

**编译时间**: 2026-05-21
**编译者**: Agent 3CC2
**状态**: built

---

## 编译流程

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build diffutils 3.10
```

### 2. 配置
```bash
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
```

**关键修复**: 修改 configure 中 `umask 077` 为 `umask 022`

### 3. 编译
```bash
make -j1
```

**问题**: gnulib LIBOBJS 机制失效，需手动编译 fnmatch.c 和 fopen.c

### 4. 安装
```bash
make install DESTDIR=$TEST_PREFIX
```

### 5. 验证
手动 G0 验证通过（Python subprocess 环境问题，但手动验证补丁完整）

---

## 遇到的问题

### E011: HMDFS umask 077 权限问题 ⭐
**根因**: HMDFS 文件系统的 UID 映射机制导致 umask 077 创建的临时目录无法写入

**解决方案**: 修改 configure 中 `umask 077` 为 `umask 022`

**影响范围**: 所有 autotools 项目在鸿蒙平台

### E007: config.guess 无法识别 HarmonyOS
**解决方案**: 应用 patch-autotools-ohos.pl 补丁 + 添加 __OHOS__ LIBC 检测

### E072: config.sub 三元组验证失败
**解决方案**: 手动添加 linux-ohos* 到内核列表

### gnulib LIBOBJS 失效
**解决方案**: 手动编译并添加到静态库

---

## 编译产物

- diff (711K)
- diff3 (195K)
- sdiff (179K)
- cmp (155K)

---

**编译结束**: 2026-05-21 12:50
**最终状态**: built