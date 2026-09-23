# E556 — 纯 Makefile 项目 pkg-config 依赖探测回退与 make 命令行 LDFLAGS 接管

## 错误特征
plain GNU Makefile 的 C 项目（无 configure/cmake）在 OHOS 上原生构建时链接阶段报：

```
ld.lld: error: unable to find library -lssl
ld.lld: error: unable to find library -lcrypto
```

或 Makefile 输出 `/bin/sh: pkg-config: not found` 后仍继续（探测失败被静默忽略），
或链接成功但运行时找不到符号（`undefined reference to SSL_new`）。

## 触发条件
- 构建系统: plain GNU Makefile（CC/CFLAGS/LDFLAGS 均为可覆盖 make 变量）
- 阶段: linking（make + ld）
- 典型 Makefile 形态：`SSL_LIBS := $(shell pkg-config --libs openssl 2>/dev/null || echo "-lssl -lcrypto")` + `LDFLAGS += $(SSL_LIBS)`

## 根因分析
上游 Makefile 假设系统装有 openssl 开发库：用 pkg-config 探测头文件/库路径，
失败时回退为裸 `-lssl -lcrypto`（依赖链接器默认搜索路径）。OHOS 设备无系统
openssl 开发库（pkg-config 不可用），裸库名在默认路径自然找不到。

## 解决方案

### 推荐方案
**make 命令行变量接管（零补丁）**：make 命令行传入的变量优先级高于 Makefile
内部的任何赋值（包括 `+=` 追加），因此可整体接管：

```bash
make -j1 CC=clang \
  CFLAGS="-fPIC -O2 -I$(conan cache path openssl/3.5.6.1)/include" \
  LDFLAGS="-L$(conan cache path openssl/3.5.6.1)/lib -lssl -lcrypto"
```

conanfile.py 中等价写法（build() 内）：

```python
openssl = self.dependencies["openssl"]
self.run(make -j{jobs} CC={cc} CFLAGS=... -I{openssl.include_paths[0]}
        LDFLAGS=... -L{openssl.lib_paths[0]} -lssl -lcrypto)
```

### 禁止做法
- ❌ 在 OHOS 上安装系统 openssl 开发包来满足 pkg-config（违反 R26 系统同名库隔离）
- ❌ 直接复用上游 `make install` 目标（常驱动 docs/man 页生成，依赖 asciidoc+xmlto 等 CI 缺失工具链；打包应直接 copy 二进制）
- ❌ 依赖 Makefile 的 pkg-config 回退（裸库名在本机链接成功也不代表指向 conan 依赖）

## 验证
```bash
conan create ... -pr:h=ci/conan/profiles/ohos-aarch64
readelf -d $(conan cache path proxytunnel/1.13.0)/bin/proxytunnel   # 无 libssl.so NEEDED → 静态链接成功
proxytunnel -V                                                      # 正常输出版本横幅
proxytunnel -e ... && echo rc=$?                                    # SSL_connect 路径被真实调用 → libssl 真实链接
```

## 关联条目
- 相关: E538（conan/meson/pkg-config 依赖解析）、E017 系列（GitHub 源码下载镜像）
- 实证: proxytunnel 1.13.0（零补丁适配，W3 本地 CI 全绿，2026-09-07）
