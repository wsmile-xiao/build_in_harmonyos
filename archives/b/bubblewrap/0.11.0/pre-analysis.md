# 预分析报告: bubblewrap 0.11.0

> 生成日期: 2026-08-10
> 源码目录: /storage/Users/currentUser/runner/build_in_harmonyos/archives/b/bubblewrap-0.11.0/src

## 1. 构建系统

- ✅ **meson**

## 2. 图形依赖

- ✅ 未检测到图形依赖

## 3. 音视频依赖

- ✅ 未检测到音视频依赖

## 4. 系统集成

- ⚠️ **open_cmd**: 鸿蒙PC可能不支持此功能
  - `bind-mount.c`
  - `bubblewrap.c`
  - `bwrap.xml`
  - `utils.c`
  - `tests/test-seccomp.py`

## 5. 平台特定代码

- ⚠️ **linux_only**: 高: 鸿蒙不是Linux，__linux__未定义
  - `bind-mount.c`
  - `bubblewrap.c`
  - `utils.c`
  - `demos/userns-block-fd.py`
  - `tests/libtest.sh`
- ⚠️ **posix_ext**: 中: 需确认_POSIX_C_SOURCE在musl下的行为
  - `meson.build`
- ⚠️ **syscall_direct**: 高: 鸿蒙syscall行为可能与Linux不同
  - `utils.c`
  - `tests/try-syscall.c`
  - `README.md`
  - `bubblewrap.c`
  - `completions/zsh/_bwrap`

## 6. 关联未关闭需求

- ✅ 需求图谱中无关联未关闭需求

## 7. 适配建议

⚠️ 本软件需要平台适配，不能仅编译通过。重点关注:
- 系统集成: 需用鸿蒙等价API或降级处理
- 平台代码: 需用#ifdef __OHOS__守卫做兼容

**如遇系统能力缺失，提交需求图谱条目:**
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py req add \
  --title "bubblewrap需要XXX能力" \
  --category graphics \
  --severity 2 \
  --software bubblewrap \
  --description "详细描述" \
  --needed "需要的API/能力"
```