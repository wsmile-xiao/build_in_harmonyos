# SDL2_ttf 2.22.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang/clang++ (HarmonyOS SDK)
- 状态: built

## 编译步骤

1. 加载 openharmony-compile-agent skill
2. 下载源码 SDL2_ttf-2.22.0.tar.gz
3. 初始化编译环境：`ohc-run.py init-build SDL2_ttf 2.22.0`
4. 修改 config.guess 和 config.sub 添加 HarmonyOS 支持
5. 修复 config.status tmpdir 问题（sed 替换 $ac_tmp）
6. 运行 configure：`./configure --prefix=$HOME/usr/local`
7. 运行 make：`make -j4`
8. 运行 make install：`make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 缺少 HarmonyOS 三元组检测 | 添加 `*:HarmonyOS:*:*)` 分支 |
| 2 | config.sub 不支持 ohos | 缺少 ohos 操作系统白名单 | 添加 ohos-linux 映射和 ohos* 白名单 |
| 3 | config.status 无法创建临时文件 | $ac_tmp 变量为空（shell限制） | sed 替换 $ac_tmp 为固定目录 |

## 源码修改

### 补丁文件
- patches/0001-config.guess.patch: 添加 HarmonyOS 系统检测
- patches/0002-config.sub.patch: 添加 ohos 操作系统支持

### hints 文件
- hints/configure.sh: 修复 config.status tmpdir 问题

## 依赖版本

- SDL2: 2.30.0 (已安装)
- freetype: 内置版本 (使用 included FreeType)
- harfbuzz: 内置版本 (使用 included HarfBuzz)

## 验证结果

```bash
# pkg-config 验证
pkg-config --modversion SDL2_ttf
# 输出: 2.22.0

pkg-config --cflags SDL2_ttf
# 输出: -D_REENTRANT -I~/usr/local/include/SDL2

pkg-config --libs SDL2_ttf
# 输出: -L~/usr/local/lib -lSDL2_ttf -lSDL2

# 文件验证
ls -la ~/usr/local/lib/libSDL2_ttf*
# libSDL2_ttf-2.0.so.0.2200.0 (18.3MB)
# libSDL2_ttf.a (38.6MB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libSDL2_ttf-2.0.so.0.2200.0 | 18.3MB | 动态库 |
| libSDL2_ttf.a | 38.6MB | 静态库 |
| SDL_ttf.h | 87KB | 头文件 |
| SDL2_ttf.pc | 348B | pkg-config 文件 |

## 注意事项

1. G0 干净构建验证通过
2. SDL2_ttf 使用内置的 FreeType 和 HarfBuzz，不需要额外安装依赖
3. 需要确保 SDL2 2.30.0 已正确安装并通过 pkg-config 可识别

## 知识提取记录

- E072: config.sub 三元组验证失败 → 已应用（添加 ohos 支持）
- 配置文件 tmpdir 问题 → 创建 hints/configure.sh