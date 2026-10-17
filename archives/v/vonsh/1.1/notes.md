# vonsh 1.1 adaptation notes (GLM-42, 2026-09-17)

- 任务: 11744; 平台: vonsh/1.1 (开源鸿蒙PC专项积分赛-主活动); 分支 feat/vonsh-1.1
- 上游: https://github.com/aurb/vonsh archive/refs/tags/v1.1.tar.gz
  sha256=d607002268408ed98da56136d47830142f81a9e2dbac6f6d891e3357763eac35
- 依赖更正: 原登记备注称"零外部依赖"有误——vonsh 是 SDL2 游戏，硬依赖
  SDL2/SDL2main/SDL2_image/SDL2_mixer/cjson。依赖均已发布（sdl2/2.30.10、
  sdl2-image/2.8.12、sdl2-mixer/2.8.2、cjson/1.7.19）。
- 构建体系: 上游纯 Makefile。CFLAGS 用 `?=`/`+=`、LDLIBS 用 `=`——make 命令行
  变量覆盖会整体替换（`+=` 在命令行变量后失效），故 CFLAGS 完整复刻上游旗标
  （-std=c99 -D_DEFAULT_SOURCE -pedantic -O2 -D_FORTIFY_SOURCE=2
  -fstack-protector-strong -Iinc -DVERSION_STR）并追加各 conan 依赖的 -I；
  LDLIBS 覆盖为 -lSDL2_image -lSDL2_mixer -lSDL2 -lcjson -lm（去 -lSDL2main：
  conan sdl2 包无该垫片库，游戏自带 main()）；STRIP=true（OHOS MAC 拒绝 strip）。
- 版本约束: sdl2-image/2.8.12 与 sdl2/2.30.10.1 冲突，依赖组合用 sdl2/2.30.10。
- 补丁: 无（零补丁）。
- 补丁 0001 (portability): vonsh 启动时硬编码 `SDL_RENDERER_ACCELERATED |
  SDL_RENDERER_TARGETTEXTURE`，无 GPU/无头环境（如 dummy 视频驱动，实证报错
  "Couldn't find matching render driver"）下 renderer 创建失败、游戏静默 exit 1；
  补丁在加速渲染器不可用时回退 `SDL_RENDERER_SOFTWARE | SDL_RENDERER_TARGETTEXTURE`
  （实机仍优先加速，仅兜底）。上游其余行为零改动。
- 测试账本（四维）:
  - 上游静态注册: 0（上游无任何测试目标；src/ 为游戏本体）
  - 实际执行/通过/失败: 0/0/0/0（上游无测试，依规以消费者冒烟补位）
  - 消费者测试: smoke_vonsh.sh 1 个——SDL dummy video/audio 驱动无头启动打包后的
    vonsh，timeout 5s 断言游戏循环存活（exit 124）或正常退出；VirtualRunEnv 提供
    SDL 系动态库运行时路径
- packaging: usr/games/vonsh → bin/vonsh（application 型）。
- 已知限制: 上游默认（small 无关，全量游戏本体）；显示仍需真实 SDL 环境，冒烟仅为无头验证。
- result.json 由 ohc-run.py result 按最终 HEAD 生成。
---

**编译结束**: 2026-09-17 13:06
**最终状态**: built
