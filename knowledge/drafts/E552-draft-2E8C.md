# E552 — Makefile 型配方消费 pkg-config 依赖需注入 PKG_CONFIG_PATH

## 错误特征
Conan 构建（`conan create`）阶段，Makefile 的 `FLAGS` 内嵌反引号调用
`pkg-config --libs --cflags <dep>`，日志报：

```
Package libgtop-2.0 was not found in the pkg-config search path.
das_watchdog.c:39:10: fatal error: 'glibtop.h' file not found
```

## 触发条件
- 构建系统: Makefile（make 直接调用，无 configure）
- 阶段: build（make 执行期）
- 依赖发现方式: Makefile 内嵌 `pkg-config --cflags --libs <name>`

## 根因分析
1. `PkgConfigDeps(self).generate()` 生成的 `.pc` 文件位于 Conan
   generators_folder（`.../build-release/conan/`），但 VirtualBuildEnv 聚合的
   `conanbuild` 环境默认不包含该目录的 `PKG_CONFIG_PATH`；
2. Makefile `FLAGS` 中的反引号 `pkg-config ...` 在 make 执行期于 shell 中
   解析，因 `PKG_CONFIG_PATH` 缺失而找不到依赖 `.pc`，展开为空 →
   头文件 `-I` 与库 `-L` 全部缺失，报 header not found；
3. 附加陷阱：若以 `environment.vars(self, scope="build").save_script("conanbuild")`
   直接注入，会与 VirtualBuildEnv 自身聚合脚本 `conanbuild.sh` 同名被覆盖，
   PKG_CONFIG_PATH 注入静默失效。

## 解决方案

### 推荐方案
`generate()` 中先 `PkgConfigDeps(self).generate()`，再显式构造
`Environment()`，`append_path("PKG_CONFIG_PATH", self.generators_folder)`，
**以唯一名** `save_script("<software>_pkgconfig")` 且 `scope="build"`，让
VirtualBuildEnv 聚合进 `conanbuild`；build() 以
`make -j1 CC="<conan conf 编译器>"` 执行（R33，不裸用 shell 变量）。
配方内以补丁弱化 `which xmessage` 类 X11 工具硬检查（`which xmessage || true`，
代码存在运行时降级如 `access(WHICH_XMESSAGE,X_OK)` 失败回退 $PATH 时安全）。

### 禁止做法
- 禁止在 `generate()` 把脚本命名为 `conanbuild`（与聚合脚本冲突被覆盖）；
- 禁止把 `gcc`/`$(CC)` 硬编码在配方中不用 conan conf 编译器（R33）；
- 禁止改共享框架的 pkg-config 行为或系统级 `PKG_CONFIG_PATH`。

## 验证
```bash
cd archives/d/das-watchdog/0.9.0
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 修复前: Package libgtop-2.0 was not found ... fatal error glibtop.h not found
# 修复后: exit 0，test_package 1/1 Passed
```

## 关联条目
- 相关: E348（PkgConfigDeps 生成 .pc 话题，面向 meson 消费方）；E075（pkg-config 环境变量陷阱，根因不同）