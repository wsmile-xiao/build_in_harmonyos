# E481 — SDL_image.h 引号包含命中项目 sdl.h 环形包含

## 错误特征
- `unknown type name 'SDL_Texture'`（SDL_image.h/SDL_ttf.h 内展开处）
- `SDL_image.h: ... unknown type name`
- `non-portable path to file ... differ in case`（-I. 与项目自身头文件大小写碰撞）

## 触发条件
- 构建系统: autotools
- 阶段: compilation

## 根因分析
SDL_image.h/SDL_ttf.h 内部用引号 `#include "SDL.h"`。当项目自身头文件也叫 sdl.h（如 lbreakouthd 的 src/sdl.h）且编译命令含 `-I.` 时，在大小写不敏感文件系统（HMDFS）上 `"SDL.h"` 先解析到项目 sdl.h 而非真实 SDL.h，产生环形包含与 SDL 类型未定义。上游在大小写敏感 Linux 上无此问题。

## 解决方案

### 推荐方案
调整项目 include 顺序：先 `#include <SDL2/SDL.h>` 再含 SDL_image.h/SDL_ttf.h，使真实 SDL.h 已完整处理，后续引号 SDL.h 命中项目 sdl.h 时被 include guard 跳过。

### 禁止做法
- （草稿，待主编合入时补充）

## 验证
```bash
```

## 关联条目
- 相关: （无）
