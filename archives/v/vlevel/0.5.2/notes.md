# vlevel 0.5.2 adaptation notes (GLM-42, 2026-09-17)

- 任务: 11725; 平台: vlevel/0.5.2 (开源鸿蒙PC专项积分赛-主活动); 分支 feat/vlevel-0.5.2
- 上游: https://github.com/radiocicletta/vlevel archive/refs/tags/v0.5.2.tar.gz
  sha256=a0245608d5c6e072488ffcec42ebc260c88407469ce007ffe7888da351bd4769
- 包定位: application（CLI 工具）；commands.json 置于包级目录（R38/L0k 口径）。
- 构建体系: 顶层递归 Makefile（4 个前端）。本配方只构建 core 两件：
  - volumeleveler/：动态音量归一化算法对象（volumeleveler.o）
  - vlevel-bin/：raw PCM stdin→stdout 过滤器（CLI 产物）
  明确跳过 vlevel-ladspa / vlevel-jack / vlevel-winamp：分别是 LADSPA 插件、
  JACK 客户端与 Winamp 插件，依赖宿主插件环境/专有 SDK，非 OHOS 目标。
- 交叉构建要点: vlevel-bin/Makefile 用 `CC = $(CXX)` 让隐式规则走 g++，
  需显式 `CXX=<profile clang++>`；顶层 CXXFLAGS（-Wall -O3 -fPIC -DPIC
  -DVLEVEL_VERSION）需在命令行复刻（子目录不继承 export 之外的值）。
- 补丁: 无（零补丁）。
- 测试账本（四维）:
  - 上游静态注册: 0（上游无任何测试目标）
  - 实际执行/通过/失败: 0/0/0/0（上游无测试，依规以消费者冒烟补位）
  - 消费者测试: smoke_vlevel.sh 1 个——生成 30 万个 int16 单声道常量样本
    (值 1000) 管道输入，断言：①过滤器退出码 0；②输出与输入字节数一致
    （流帧格式保持）；③输出峰值 > 输入峰值（动态归一化确实放大弱信号）
- packaging: bin/vlevel-bin（application 型），licenses/COPYING。
- 已知限制: 仅 core CLI；插件前端不打包（理由见上）。
- result.json 由 ohc-run.py result 按最终 HEAD 生成。
---

**编译结束**: 2026-09-17 13:22
**最终状态**: built
