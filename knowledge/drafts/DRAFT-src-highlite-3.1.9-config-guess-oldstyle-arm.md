# DRAFT-src-highlite-3.1.9-config-guess-oldstyle-arm

## 症状（可复现 + 稳定签名）

对 config.guess 版本 ≤2017 的 autotools 包运行 `patch-autotools-ohos.pl` 后：

- 脚本报告打补丁（config.guess 内能 grep 到 HarmonyOS 分支）；
- 但执行 `sh build-aux/config.guess` 仍报 `unable to guess system type`；
- `sh -x` 追踪可见 `+ GUESS=aarch64-unknown-linux-ohos` 赋值发生，随后仍落脚本末尾的失败分支。

触发实例：src-highlite 3.1.9（config.guess timestamp 2017-08-08）。

## 根因与最小复现

`patch-autotools-ohos.pl` 插入的 HarmonyOS 分支是**新式写法**：
`GUESS=${MACHINE}-unknown-linux-ohos` + `;;`，依赖 2018+ config.guess 在
case 结束后的统一 `echo "$GUESS"`。旧式（≤2017）脚本每个分支自己
`echo <结果>; exit`，case 结束后直接是错误处理——于是新式分支赋值后
**静默滑落到兜底**，输出 "unable to guess"。

最小复现：任意含 2017 版 config.guess 的源码树 + patch 脚本 + 执行
`sh build-aux/config.guess`。

## 已尝试方案（含失败）

- `patch-autotools-ohos.pl` 一键补丁：config.guess 的 HarmonyOS arm 插入成功
  （grep 可见），但脚本自检 Score 1/5、实际执行仍 unable to guess——
  **脚本对该年代文件半失效**（config.sub 的三处编辑 regex 也未命中）。
- 用 `--build/--host` 绕过：按 E007 forbid_1 放弃（误判交叉编译，
  AC_RUN_IFELSE 运行时检测全跳过）。

## 最终方案（真实验证）

1. config.guess：把插入分支改为**旧式**——arm 内
   `echo ${MACHINE}-unknown-linux-ohos` + `exit ;;`；
2. config.sub（2019 版）：maybe_os kernel 表加 `linux-ohos*`；OS 表加
   `| -linux-ohos*`。规范化输出 `aarch64-unknown-linux-gnu-ohos`
   （注入 gnu 是标准归一化，`$host_os` 仍以 linux* 匹配）；
3. 以 31 行定点 patch 随 `patches/0001-config-scripts-ohos.patch` 交付
   （禁整文件替换补丁，防 PR 膨胀）。

验证：src-highlite 3.1.9 真机探索构建 configure 原生识别（无 --host 绕过），
conan create + 上游 tests 自定义 check 全绿（CHECK_RC=0）。

## 适用范围 / 反例 / 解除条件 / 风险

- 适用：config.guess ≤2017（旧式 echo+exit 风格）的 autotools 包。
- 反例/例外：脚本 ≥2018（GUESS 风格）继续用 patch-autotools-ohos.pl 原样输出，
  不要套用本条目（会因重复 echo 破坏输出解析）。
- 风险：若上游 configure 对 host_os 做精确匹配（==linux-ohos），
  config.sub 归一化注入的 gnu 需单独适配。

## 查重与新增价值

- E007 记录了 "config.guess 不识别 HarmonyOS → 用 patch 脚本" 的主路径；
  本条目是其在**旧式脚本上的失效模式与修正**（脚本的盲区）：
  打了补丁≠补丁生效，必须实跑 config.guess 验证。
- 与 E507 无冲突；同任务还发现 E507 的宏在 boost ≥1.85 更名为
  `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`（原记录
  `BOOST_SP_THREAD_SLEEP_NO_PTHREAD_SETCANCELSTATE` 已不存在），
  该更新另行走 E507 相关草稿/评审。
