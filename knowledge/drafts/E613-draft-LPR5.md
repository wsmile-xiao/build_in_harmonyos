# E613: 从父目录 make -C <subdir> check 时 libtool wrapper 的 getcwd 反查失败，测试整批假失败 127

## 基本信息
- **严重度**: 2
- **类别**: hmdfs, autotools, testing
- **触发工具 / 阶段**: make|test / testing
- **来源**: libprelude 5.2.0 适配（OHOS aarch64，PR 分支 feat/libprelude-5.2.0，Agent LPR5）
- **状态**: 草稿（未进 index.tsv，待主编 `graph promote`）

## 错误特征
```
shell-init: error retrieving current directory: getcwd: cannot access parent directories|sh_makepath: error retrieving current directory
```

## 触发条件
- 构建系统: autotools（libtool 递归/内嵌 libltdl）或 conan/Conan 依赖图场景
- 阶段: testing
- 平台: HarmonyOS OHOS aarch64（clang 15 / musl / HMDFS），Conan 2.29.1 + ohpcd 制品

## 根因分析
HMDFS 上 libtool 生成的 wrapper 脚本靠 getcwd() + /data/service/hnp/bin/bash 反推 ；由父目录以 make -C tests check 递归时 /data/service/hnp/bin/bash 变成相对路径，getcwd 又返回 ENOTSUP，wrapper 把程序解析成 <top_builddir>/.libs/<test>（并不存在）→ 全部 exit 127，与被测代码无关

影响范围：所有在 OHOS 上跑 autotools parallel-tests 的配方（libprelude 5.2.0 实测：同一批测试在子目录内跑 9/9 通过）

## 解决方案

### 推荐方案（cd-into-test-dir）
conanfile.build() 里用 self.run('make check', cwd=<build>/<testdir>) 进入测试目录执行，而不是 autotools.make(target='check') 或 make -C <subdir> check

### 验证命令
```
cd <build>/tests && make check    # 9/9 PASS；而顶层 make -C tests check 9/9 FAIL(127)
```

### 落地参考
archives/l/libprelude/5.2.0/conanfile.py

## 关键词
make -C, shell-init, getcwd, cannot access parent directories, libtool wrapper, 假失败, exit status 127, sh_makepath, make check
