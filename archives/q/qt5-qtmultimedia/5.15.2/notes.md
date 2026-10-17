# qt5-qtmultimedia 5.15.2 适配笔记

## 编译环境
- 构建系统: qmake
- 编译日期: 2026-09-19
- 编译器: clang/clang++ (OHOS llvm 15)
- 状态: built

## 编译步骤

1. `init-archive` 生成归档骨架（archives/q/qt5-qtmultimedia/5.15.2/），复制 cache 导出配方（~/.conan2/p/qt5-q3f53f33dcd55b/e/）
2. 换源：conandata.yml 的 URL 从本地 file:// 路径改为清华 tuna 镜像（qt 官方 submodule tar.xz），sha256=0c375881...（与 cache 原哈希完全一致，补丁无需重生成）
3. qmake 构建沿用 qt5-qtcharts 模式：私有可写 Qt prefix 镜像 qtbase（symlink + 重写 mkspecs 中 .pri 的 build-dir 引用）+ `qmake -spec linux-clang`
4. `make install STRIP=true`（qmake strip --strip-unneeded 会破坏动态符号表导致 dlopen 失败）
5. 打包后重写 .prl/.la/.pc 中残留的 build-dir/source-dir 路径为 package_folder
6. test_package 参考 qt5-qtcharts：find_package(Qt5Multimedia) + QMediaPlayer/QAudioDeviceInfo 冒烟测试，OHOS 需 -stdlib=libc++ 与 libc++/libc++abi/libunwind 运行时链接
7. `finish built` → W3 本地 CI 全门禁 PASS，生成 .ci-result.json

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 首版用了 Qt6 API | QMediaContent::isValid()/QMediaMetaData::Key 是 Qt6 才有的 | 改 Qt5.15 API：media().isNull() + state() |
| 2 | W3 L0 报 commands_json_r38 | commands.json 放错位置（版本目录下） | 移到软件级 archives/q/qt5-qtmultimedia/commands.json（与 qtbase/strace 一致） |
| 3 | W3 JC 检测失败 | 分支无提交→JC 回退 full 模式，命中主仓 cloog 遗留状态文件 | 生成 pr.diff 仅含本包文件，切回 prdiff 模式 |
| 4 | 运行期无多媒体后端 | OHOS 无 pulse/alsa/gstreamer | test_package 只做构造/查询冒烟（QT_QPA_PLATFORM=offscreen），MANIFEST.yml 申报豁免 |

## 源码修改

- 无补丁（patches_applied 为空），仅配方层适配

## 依赖版本

- qt5-qtbase/5.15.2.2（已发布）

## 验证结果

```bash
conan-verify: G0-G4 + L2/L4/L5 全 PASS（Verdict=PASS）
test_package: RUN ./test_qt5_qtmultimedia → exit 0（QMediaPlayer 无后端警告属预期）
.ci-result.json: exit_code=0, step=W3_local_ci, integrity_hash=dfff20a49998fbc2（真实）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | qmake 配方（私有 prefix 镜像 + STRIP=true + .prl/.pc 重写） |
| conandata.yml | tuna 新源 URL + sha256 |
| test_package/ | 冒烟测试（QMediaPlayer/QAudioDeviceInfo，Qt5.15 API） |
| commands.json | 软件级命令声明（R38，type=tool, binary:false） |
| reports/conan-verify-report.md | 门禁报告 PASS |

## 注意事项

- **发布未完成**：conan upload 到 ohpcd 因制品仓无认证凭据失败（本机非 Release 机器，.conan2/.conan.db 的 users_remotes 为空，.gitcode-token 登录被拒）——待提供 CNB 制品仓凭据后补 upload，成功后 manifest 改 published
- tuna 镜像对 UA 不敏感、哈希稳定，Qt 官方 submodule 优先走 tuna；gitee archive 需 UA 注入
