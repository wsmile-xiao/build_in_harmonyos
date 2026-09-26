# E483 — SDL_CreateRenderer 返回 NULL 崩溃，需软件渲染回退

## 错误特征
- `Couldn't find matching render driver`
- `SDL_CreateRenderer ... NULL`
- `renderer ... is invalid`（sdl.cpp 渲染循环）

## 触发条件
- 构建系统: autotools
- 阶段: runtime / testing（无头、无 GPU 环境）

## 根因分析
`SDL_CreateRenderer(mw, -1, SDL_RENDERER_ACCELERATED)` 在 dummy 视频驱动或未提供 OpenGL 加速的环境返回 NULL；上游游戏不处理 NULL renderer，后续 SDL_Render* / SDL_CreateTexture 全部失败并在渲染循环 SIGSEGV。

## 解决方案

### 推荐方案
创建加速渲染器失败时回退 `SDL_CreateRenderer(mw, -1, SDL_RENDERER_SOFTWARE)`。SDL 软件渲染器在 dummy 驱动下可用，支持 SDL_TEXTUREACCESS_TARGET 渲染目标，可支撑无头冒烟测试（SDL_VIDEODRIVER=dummy + timeout 运行不崩溃）。

### 禁止做法
- （草稿，待主编合入时补充）

## 验证
```bash
```

## 关联条目
- 相关: （无）
