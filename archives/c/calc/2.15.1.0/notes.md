# calc 2.15.1.0 适配笔记

## 编译环境
- 构建系统: makefile（自定义 Makefile，无 configure 脚本）
- 编译日期: 2026-08-22
- 编译器: clang
- 状态: built

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build calc 2.15.1.0 \
  --url=https://github.com/lcn2/calc/releases/download/v2.15.1.0/calc-2.15.1.0.tar.bz2
```

### 2. 安装依赖
readline 8.2 预编译包（可选，不装则编译不带 readline 支持的 calc）:
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- readline 8.2
```

### 3. 编译
calc 是纯 Makefile 项目，上游明确说明不支持并行编译:
```bash
cd $BUILD_SRC_DIR
make -j1       # 编译（必须串行，E074 FIFO 约束）
```

如需禁用 readline:
```bash
make -j1 USE_READLINE= READLINE_EXTRAS= READLINE_INCLUDE= READLINE_LIB=
```

### 4. 测试
```bash
make check -j1  # 回归测试 (~9998+ tests)
```

### 5. 安装
```bash
make install PREFIX=$DEFAULT_PREFIX
```

### 6. 打包
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package calc 2.15.1.0
```

## 使用知识
- E074: make -j 并行构建失败（FIFO 禁止），需 -j1
- readline 8.2/8.3: OHOS 适配（config.guess/config.sub 补丁）
- bcal 2.5: 同类纯 Makefile + readline 项目适配经验

## 注意事项
- 上游明确说明不支持并行编译（Makefile 第 379-383 行）
- 编译时使用 clang 默认无警告
- 回调测试套件 cal/regress.cal 约 11011 行，~9998+ 测试用例
### 对话 #1 — 首次适配与 fpos_t 修复

- **日期**: 2026-08-22
- **配置参数**: target=Linux CC=clang LCC=clang LN=cp calc-static-only BLD_TYPE=calc-static-only USE_READLINE=
- **编译耗时**: ~5 min
- **编译结果**: 通过，calc-static 2.2MB，libcalc.a 3.5MB
- **上游测试**: make check -j1 9998/9998 通过（修复前 9976/9998，22 失败）
- **新增测试**: test_fpos.cal 13 断言全部通过
- **补丁**: 0001 off_t FILEPOS; 0002 ftello/fseeko
- **门禁**: conan create exit 0, conan-verify G1-G4 PASS, W3 通过
---

**编译结束**: 2026-08-23 17:50
**最终状态**: built
