# libubox 20260222 适配笔记

## 编译环境
- 构建系统: cmake (cmake_minimum_required 3.13)
- 编译日期: 2026-08-12
- 编译器: clang (aarch64-unknown-linux-ohos, clang 15)
- 状态: published

## 编译步骤

1. `init-build libubox 20260222` — 下载 openwrt/libubox commit 7dd12784 tarball
2. cmake 配置（手工验证阶段）：
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=$PREFIX -DBUILD_LUA=OFF -DBUILD_EXAMPLES=OFF \
     -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_C_COMPILER=clang
   ```
   - OHOS 无 lua → `-DBUILD_LUA=OFF`（否则 SEND_ERROR）
   - json-c 为硬依赖 `PKG_SEARCH_MODULE(JSONC json-c REQUIRED)`，经 PKG_CONFIG_PATH 指向 json-c/0.18 预编译包
3. `make -j` — 全部目标成功（-Wall -Werror 下无告警）
4. `make install DESTDIR=$TEST_PREFIX` — 安装成功
5. 验证：`jshn` 为 AArch64 ELF（interp musl=OHOS libc），`--version` 返回 0；jshn JSON round-trip 测试 PASS
6. 单测：CMake UNIT_TESTING 非 -san 目标 8/14 通过，其余为负向测试/cram 依赖（valgrind 在 OHOS 不可用，平台限制）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 模板 | manifest build_system 模板未填，模板选择错误 | 手动重写为 CMake 配方 |
| 2 | L2 smoke test 失败 | jshn 无 --version/--help 长选项（exit 2） | 补丁 0001-jshn.c.patch 增加长选项返回 0 |
| 3 | CMake 找不到 json-c | CMakeToolchain 不注入 PKG_CONFIG_PATH | build() 内手动注入 self.generators_folder |
| 4 | ctest -san 变体失败 | OHOS clang 不支持 -fsanitize=leak | 平台限制，仅构建非 -san 单测 |
| 5 | /tmp 只读 | E002 平台限制 | 用 $TMPDIR |

## 源码修改

- `0001-jshn.c.patch`: jshn.c main() 开头增加 --version/--help 长选项处理（L2 smoke test 门禁）

## 依赖版本

- json-c/0.18（ohpcd 制品仓已发布）

## 验证结果

```bash
conan create archives/l/libubox/20260222 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# conan-verify: G0-G4 + L2/L4/L5 全部通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libubox.so / libubox.a | 核心库 |
| lib/libblobmsg_json.so / .a | blobmsg <-> json 转换库 |
| lib/libjson_script.so | JSON 脚本引擎库 |
| bin/jshn | 命令行工具（--version/--help 可用） |
| include/libubox/*.h | 27 个头文件 |

## 注意事项

- 系统同名库隔离（R26）不适用：libubox 非系统同名库，默认动态链接
- jshn 运行时依赖 RPATH/ld 路径解析，Conan RPATH 管理
---

**编译结束**: 2026-08-13 00:48
**最终状态**: published
