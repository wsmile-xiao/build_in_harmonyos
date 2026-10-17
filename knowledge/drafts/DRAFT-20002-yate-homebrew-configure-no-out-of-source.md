# DRAFT-20002: yate 自研 configure 不支持 out-of-source 子目录构建（需 in-source）

- 条目主题：yate 的 configure/config.status 是自研轻量版（autogen.sh 仅 autoconf 生成），子目录 Makefile 的 `@srcdir@` 模式规则与 `MKDEPS := ../../config.status` 相对前置只在 in-source 布局下自洽——Conan 默认 out-of-source 布局必现 "No rule to make target"。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：yate 6.4.1；同范式适用于"预生成 configure + 子目录 Makefile 用 @srcdir@ 模式规则"的其他包。

## 错误特征
- `make: *** No rule to make target 'audio/common/resampler/resampler.o', needed by 'libminiwebrtc.a'`
- 主目录 .o 编译正常，进入**第一个子目录 make** 即死
- 多个全新 conan build 区域（无增量缓存干扰）同错 → 排除缓存污染，判定布局性错误

## 根因
1. 子目录 Makefile（libs/miniwebrtc/Makefile）：`MKDEPS := ../../config.status` + 模式规则 `%.o: @srcdir@/%.c|.cc $(MKDEPS) $(INCFILES)`。
2. in-source：`@srcdir@=.`，相对路径自洽。
3. out-of-source（build_folder ≠ source_folder）：子目录内 `@srcdir@` 指向**源根**而非对应源子目录，模式规则无法找到 `resampler.cc`（实际是 `resampler.cc` 大写 C 也需检查；此处为路径断裂）。

## 修复
```python
def generate(self):
    tc = AutotoolsToolchain(self)   # 仅生成构建环境(CC/CXX/CONFIG_SHELL/PATH)
    tc.generate()                   # 不用 Autotools helper 的 configure()/make()

def build(self):
    apply_conandata_patches(self)
    self.run("chmod +x autogen.sh", cwd=self.source_folder)
    self.run(autogen_cmd, cwd=self.source_folder)          # PATH 前缀注入(见 DRAFT-20001)
    self.run("./configure --prefix={}".format(self.package_folder) + " " + " ".join(cfg),
             cwd=self.source_folder)
    self.run("make -j{N} DEFS=...".format(N=n), cwd=self.source_folder)

def package(self):
    self.run("make install", cwd=self.source_folder)  # configure-time prefix 已指 package_folder
```

## 验证
- yate 6.4.1：out-of-source 四个全新 build 区域必现 miniwebrtc 失败；in-source 全绿（2026-09-30 实测，425 编译 0 错误 + 7 .so + 77 .yate 打包）。
