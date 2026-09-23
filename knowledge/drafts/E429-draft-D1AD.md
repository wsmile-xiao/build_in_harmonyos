# E429-draft: 无 dummy 后端、无可链接库 API 的 GUI/音频应用在 OHOS 无显示沙箱的 test_package 静态验证策略

## 基本信息
- **严重度**: 2（🟡 非阻塞，但反复踩坑浪费多轮迭代）
- **类别**: testing, ohos, platform, limitation, conan
- **作者**: HouYuxuan <f24011422@st.sandau.edu.cn>
- **来源事件**: zita 0.2.2（上游 zita-rev1，JACK+X11 混响器 GUI 程序）适配

## 错误特征
```
Error loading shared library libc++_shared.so: (needed by ...)
Error relocating ...: symbol not found
output missing version banner
Can't open display
Permission denied
Error 127 while executing
Error 3 while executing
```
test() 阶段反复失败，loader 无法加载 GUI 动态依赖链；或检查器自身因 libc++_shared.so
缺失无法启动。

## 触发条件
- 待测包是**纯应用型** GUI/音频程序（无可链接库 API；test_package 无法用
  `find_package` + 链接库调 API 的方式验证，只能执行二进制）
- OHOS CI/沙箱：无显示后端、无 JACK 服务、无 X11/Wayland
- 应用的完整动态依赖链（libXft/libX11/libcairo/libjack 等）在沙箱内无法加载

## 与既有条目关系（部分重复，本条目为补充）
- **E471**（gtkmm 4.0.0 无显示测试分类 + no-display API probes）：覆盖**库型** GUI
  程序——上游自带 meson 测试，可将显示依赖测试分 suite 排除 + 增补不依赖显示器的
  API 探针。**差异**：zita-rev1 是纯应用无可链接 API，无法"探测公开 API"。
- **E472**（SDL_kitchensink dummy drivers + self.run）：SDL 类库有 **dummy 后端**可用
  （SDL_VIDEODRIVER=dummy）。**差异**：zita-rev1 的 X11/JACK 依赖无 dummy 后端可注入，
  只能静态验证。
- 本条目补充场景：**无 dummy 后端、无库 API、只能执行二进制的纯应用**。

## 根因分析
zita-rev1 是 JACK+X11 GUI 混响器**应用**（无库 API）。OHOS CI/沙箱无显示后端、无 JACK
服务，GUI 程序的完整动态依赖链（libXft/libX11/libcairo/libjack 等）加载失败：
musl 加载器解析全部 NEEDED 失败，`-h` 帮助路径虽在 X/JACK 连接之前，但动态链接阶段
即失败，版本横幅无法输出。

## 推荐方案
**方法**: headless-application-static-checker

**说明**: test_package 改用**纯 C 检查器**（消除 C++ libc++_shared.so 运行依赖），
4 项检查全部为确定性静态断言：
1. `fopen` 验证 `bin/<可执行文件>` 存在；
2. 读 ELF header 验证 64 位小端 AArch64（`e_machine == EM_AARCH64`）；
3. `memmem` 验证版本字面量——注意 help() 以 `%s-%s` 运行时拼接 PROGNAME/VERSION，
   二进制内嵌的是**两个独立字面量**（"zita-rev1" 与 "0.2.2"），不存在连续串
   "zita-rev1-0.2.2"；
4. 解析 ELF PT_DYNAMIC/DT_NEEDED，逐个确认所需共享库在 LD_LIBRARY_PATH 中
   可解析为真实文件（动态依赖链完整）——确定性静态断言，不依赖显示环境。

**用例级口径**：conan test 进程 rc=0 完整通过（1/1, 100%）；4 项检查点仅参考补充，
不作为独立用例计数、不替代用例级通过率。`-h` 尽力运行仅作诊断信息打印
（headless 沙箱加载 GUI 依赖链失败属平台限制），不进入断言判定、不影响 rc。

test() 环境注入：conanrun 生成的 `conanrunenv-*` 不含 `/system/lib64`，需追加
（libc++_shared.so 所在目录）。可靠做法：`self.run(..., env=['conanrun','zita_sysenv'])`
`（generate() 内 Environment().append_path("LD_LIBRARY_PATH", "/system/lib64") +
save_script("zita_sysenv")）`；或子 shell `source conanrun.sh; export
LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/system/lib64"`。注意 **不能**用 os.environ 覆盖
LD_LIBRARY_PATH 再 `env="conanrun"`（conanrun 会重建子进程环境，丢弃 os.environ 注入，
且只列直接依赖缺传递依赖路径）。

## 验证/命令
```
conan create archives/z/zita/0.2.2 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --user=ohpcd --channel=stable
# 预期：test_package 构建 + test() 通过（用例级：conan test 进程 rc=0 完整通过；
#        4 项确定性静态断言：二进制存在/ELF AArch64/版本字面量/DT_NEEDED 依赖链完整）
```

## 适用边界
- ✅ 纯应用型 GUI/音频程序（无库 API、无 dummy 后端）
- ✅ OHOS 无显示/无 JACK 服务沙箱
- ⚠️ 库型 GUI（gtkmm/SDL）→ 优先 E471/E472 方案（dummy 驱动 / API 探针）
- ⚠️ 有 dummy 后端可注入 → 优先 E472

## 关键词
test_package, GUI 应用, JACK, X11, 无显示, headless, dummy 后端, libc++_shared,
/system/lib64, LD_LIBRARY_PATH, ELF 静态验证, 纯 C 检查器, self.run, can_run,
无库 API, reverb, zita-rev1, kokkinizita