# E612: 依赖制品 option 声明 shared=False 却只发布 .so，require.run 为 False 导致下游没有 LD_LIBRARY_PATH

## 基本信息
- **严重度**: 2
- **类别**: conan, packaging, linking, runtime
- **触发工具 / 阶段**: conan|ld|runtime / runtime
- **来源**: libprelude 5.2.0 适配（OHOS aarch64，PR 分支 feat/libprelude-5.2.0，Agent LPR5）
- **状态**: 草稿（未进 index.tsv，待主编 `graph promote`）

## 错误特征
```
Error loading shared library libgnutls\.so\.[0-9]+: \(needed by .*\)|Error relocating .*: gnutls_[a-z_]+: symbol not found
```

## 触发条件
- 构建系统: autotools（libtool 递归/内嵌 libltdl）或 conan/Conan 依赖图场景
- 阶段: runtime
- 平台: HarmonyOS OHOS aarch64（clang 15 / musl / HMDFS），Conan 2.29.1 + ohpcd 制品

## 根因分析
gnutls/3.8.10 配方的 default_options 是 shared=False，package() 却无条件 cp .libs/libgnutls.so.* 进包（无 .a）；Conan 的 VirtualRunEnv 只在 require.run（共享库或可执行）为真时才把该依赖的 libdir 写进 LD_LIBRARY_PATH，因此下游消费者拿到 .so 需求却没有搜索路径，加载 libprelude.so 时先报找不到 libgnutls.so.30、再级联一串 gnutls_* symbol not found

影响范围：所有链接 gnutls/3.8.10（及同类 option/内容不一致制品）的共享库包

## 解决方案

### 推荐方案（consumer-runenv-compensation）
消费方在 package_info() 里遍历 host 依赖，凡其 libdir 内确有 .so 就 self.runenv_info.append_path('LD_LIBRARY_PATH', libdir)；根治方案是由依赖方重新按 shared=True 发布或补 .a，之后可删除该补偿逻辑

### 验证命令
```
conan install --requires=gnutls/3.8.10 -g VirtualRunEnv 后检查 conanrunenv 的 LD_LIBRARY_PATH 是否含 gnutls 包 libdir（现状：不含）
```

### 落地参考
archives/l/libprelude/5.2.0/conanfile.py

## 关键词
require.run, LD_LIBRARY_PATH, VirtualRunEnv, conanrun, shared option 与内容不一致, Error loading shared library, gnutls, package_info, runenv_info
