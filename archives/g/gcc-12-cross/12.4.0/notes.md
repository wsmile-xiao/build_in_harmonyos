# gcc-12-cross 12.4.0 适配笔记

## lang-preflight 误报留档（R47 边界规则）

2026-09-24 首轮 lang-preflight 曾返回 env_unsupported/detected_language=python，
经核验为工具误报，真实语言为 c/cpp 族，与任务标记 cpp 兼容，正常进入适配主流程：

- 顶层构建系统：`configure.ac` + `Makefile.in` + `configure` 存在（autotools，c/cpp 族 manifest）
- `setup.cfg` 仅存在于 `contrib/gcc-changelog/setup.cfg` 与 `maintainer-scripts/setup.cfg`
  （GCC 源码树自带辅助 Python 工具脚本，非库构建系统；R47 边界规则：辅助脚本不算主体）
- 源码统计（本机全量枚举）：C/C++ 78475 文件占 93.5%，go 5369（libgo 前端运行时），py 49
- 工具缺陷根因：`scripts/ohc/lang_detect.py` 的 `_manifest_scan` 用全树文件名集合
  匹配 setup.cfg（优先级高于 configure.ac），且 `_iter_files` 采样上限 20000 文件致占比失真

## 编译环境
- 构建系统: autotools（自研 conanfile 驱动，参照 gcc-14 先例）
- 编译日期: {2026-09-24}
- 编译器: clang/clang++（OHOS 签名包装 clang-sign）
- 状态: {published|built|failed}

## 编译步骤

- out-of-tree 构建于 $HOME/tmp/builds/gcc-12-cross-12.4.0.build
- configure（--build/--host/--target=aarch64-linux-ohos，C 前端，--disable-threads，
  --with-sysroot=OHOS SDK native/sysroot）RC=0
- make all-gcc + make all-target-libgcc（-j2 pipe jobserver，无限栈 bash）RC=0
- make -C gcc selftest RC=0；staging install（DESTDIR）后安装驱动冒烟 RC=0
- 关键适配：OHOS 平台默认 PIE，GCC 非 PIE 链接 stdout 会 COPY 重定位崩溃，
  测试与消费者编译需 -fPIC -pie（详见 reports/test-report.md 知识候选）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}
---

**编译结束**: 2026-09-24 21:32
**最终状态**: built
