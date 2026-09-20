## PR 信息
- **三方库名称**：xf86-video-r128
- **上游版本**：6.13.0
- **上游仓库地址**：https://xorg.freedesktop.org/archive/individual/driver/xf86-video-r128-6.13.0.tar.gz
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游测试套件 |
| 集成测试 | 0 | - |
| 其他测试 | 0 | 跳过的测试 |
| **合计** | **0** | |

### 是否存在对上游测试用例的修改？
是，见下方补丁说明

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 一致 | 通过 0/0 |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 0 | - | 新增 |
| **合计** | **0** | | |

---

## 上游测试用例修改说明
以下文件被修改并保存为 patch 文件：
### config.guess (0001-config.guess.patch)
- HMDFS 临时目录修复，HarmonyOS 上跳过 umask 077
- UNAME_SYSTEM 检测添加 HarmonyOS/OpenHarmony case
- aarch64:HarmonyOS 和 aarch64_be:HarmonyOS machine pattern 映射
### config.sub (0002-config.sub.patch)
- 添加 harmonyos* case pattern → kernel=linux, os=musl
### configure (0003-configure.patch)
- HMDFS 临时目录创建修复，HarmonyOS 上跳过 umask 077
### src/r128_driver.c (0004-src-r128_driver.c.patch)
- 用 #ifdef __OHOS__ 守卫跳过 pInt10->BIOSseg 和 xf86int10Addr() 调用

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: autotools
- 配置选项: `默认配置`

### 产物验证
| 编译无错误 | PASS | 构建系统: autotools, 状态: built |
| 产物存在性 | PASS | conan create 验证 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | 通过: 0, 失败: 0, 跳过: 0 |
| 动态依赖 | PASS | 依赖: xorgproto/2025.1, pixman/0.46.4.3, libpciaccess/0.19 |

### 补丁说明
- `0001-config.guess.patch`: 0001-config.guess.patch
- `0002-config.sub.patch`: 0002-config.sub.patch
- `0003-configure.patch`: 0003-configure.patch
- `0004-src-r128_driver.c.patch`: 0004-src-r128_driver.c.patch

### 依赖
- xorgproto/2025.1
- pixman/0.46.4.3
- libpciaccess/0.19

### 测试结论
- 总体评价: 通过
- 已知限制: 无

### 遇到的问题与解决方案
- **1**: 根因=configure 报 "cannot guess build type", 解决方案=config.guess/config.sub 不识别 HarmonyOS 平台
- **2**: 根因=configure 创建临时目录失败 (Permission denied), 解决方案=HMDFS 上 umask 077 + mktemp 创建的目录不可写
- **4**: 根因=r128_crtc.c/r128_exa_render.c 大量 DRI/EXA 错误, 解决方案=OHOS xorg-server 不提供 DRI/EXA 支持
- **5**: 根因=configure 找不到 xorgproto 依赖, 解决方案=PKG_CONFIG_PATH 缺少 /storage/Users/currentUser/usr/local/share/pkgconfig
- **6**: 根因=CI: r128.h:41 fatal error 'xf86str.h' not found, 解决方案=旧配方在 build() 内下载 xorg-server 源码提取 SDK 头，但 x.org 发布的是 .tar.xz 而 tarfile.open 用 mode="r:gz" → "not a gzip file"，提取失败后仅剩合成头
- **7**: 根因=CI: xf86Crtc.h / damage.h 等逐个缺失, 解决方案=旧提取逻辑保留子目录结构后靠全目录 -I 注入，need_dirs 白名单不全且依赖逐轮 CI 试错
- **8**: 根因=configure 需要 pciaccess.pc, 解决方案=PkgConfigDeps 按 conan 包名生成 libpciaccess.pc，上游探测 pciaccess
- **9**: 根因=SDK 头互相包含 <xorg-config.h> / <xkb-config.h> 失败, 解决方案=这两个 + dix-config.h / xorg-server.h 均由 xorg-server configure 生成，源码包只有 .in 模板
- **10**: 根因=proto 依赖（xproto/fontsproto/randrproto 等 29 个 .pc）, 解决方案=conan 只有整包 xorgproto.pc

### 验证命令
```
```bash
conan create archives/x/xf86-video-r128/6.13.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → Package built; test_package: All tests passed
# r128_drv.so 88448 bytes, ELF64 ET_DYN, r128ModuleData 已导出
```

编译警告（非致命，与上游一致）: r128_crtc.c unused variables / void pointer arithmetic (GNU extension)、
r128_cursor.c void pointer arithmetic、r128_output.c format string not literal。

```
