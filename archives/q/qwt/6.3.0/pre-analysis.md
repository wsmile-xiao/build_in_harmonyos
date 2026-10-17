# 预分析报告: qwt 6.3.0

> 生成日期: 2026-08-06
> 源码目录: /storage/Users/currentUser/Documents/main/build_in_harmonyos-main (10)/build_in_harmonyos-main/archives/q/qwt-6.3.0/src

## 1. 构建系统

- ⚠️ 未检测到标准构建系统

## 2. 图形依赖

- ⚠️ **Qt**: 鸿蒙PC无此依赖。无X11/Wayland，有ArkUI渲染框架
  - `designer/qwt_designer_plugin.cpp`
  - `playground/svgmap/Plot.h`
  - `playground/svgmap/main.cpp`
  - `playground/svgmap/Plot.cpp`
  - `playground/graphicscale/Canvas.cpp`

## 3. 音视频依赖

- ✅ 未检测到音视频依赖

## 4. 系统集成

- ⚠️ **open_cmd**: 鸿蒙PC可能不支持此功能
  - `src/qwt_plot_tradingcurve.cpp`
  - `src/qwt_samples.h`
  - `doc/Doxyfile`

## 5. 平台特定代码

- ⚠️ **linux_only**: 高: 鸿蒙不是Linux，__linux__未定义
  - `examples/cpuplot/CpuStat.cpp`

## 6. 关联未关闭需求

- ✅ 需求图谱中无关联未关闭需求

## 7. 适配建议

⚠️ 本软件需要平台适配，不能仅编译通过。重点关注:
- 图形: 需替换为ArkUI兼容方案或条件编译跳过
- 系统集成: 需用鸿蒙等价API或降级处理
- 平台代码: 需用#ifdef __OHOS__守卫做兼容

**如遇系统能力缺失，提交需求图谱条目:**
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py req add \
  --title "qwt需要XXX能力" \
  --category graphics \
  --severity 2 \
  --software qwt \
  --description "详细描述" \
  --needed "需要的API/能力"
```