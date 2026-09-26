# DRAFT — test_package .sh 用 bash 数组语法（read -a / <<< / ${arr[@]}），conan 以 /bin/sh（toybox）执行导致依赖闭合误报

> 来源：PR #10748 feat(aghermann): 1.1.2 适配 HarmonyOS PC
> 状态：草稿（待审核 promote）
> 触发实证：CI #59412（worker CI-018）、#59738（worker CI-002）；本地 OpenHarmony-6.1.0.115 同现

## 可复现症状与稳定错误签名

- `ERROR(HarmonyOS): NEEDED lib not resolvable: libsigfile.so`
- `ERROR(HarmonyOS): dynamic dependencies not closed on OHOS`
- 稳定签名：`ERROR\(HarmonyOS\): NEEDED lib not resolvable: lib[a-z0-9_.-]+\.so(\.\d+)*`，
  紧跟 `Error in test() method ... ConanException: Error 1`。

## 根因与最小复现

- conan test_package 的 conanfile.py 用 `self.run('"{}" ...'.format(shell, script, ...))` 执行测试脚本，
  其中 `shell = CONFIG_SHELL or "/bin/sh"`——显式以 `/bin/sh` 调用，**脚本 shebang 被忽略**。
- OHOS 的 `/bin/sh` 是 toybox：不支持 bash 数组 `read -a`、here-string `<<<`、`${arr[@]}`。
  旧实现 `IFS=':' read -r -a DIRS <<< "${LD_LIBRARY_PATH:-}"` 在 toybox 下不建数组
  （`${#DIRS[@]}` 退化为字符串长度），`for d in "${DIRS[@]}"` 拿不到任何目录 →
  LD_LIBRARY_PATH 扫描静默失效，只剩 `/system/lib64`、`/vendor/lib64` →
  包私有库（lib/aghermann）与 fftw/gsl 等依赖库全部误报 "not resolvable"。
- 最小复现：
  ```sh
  # 在 OpenHarmony 上，/bin/sh 直接执行（与 conan 相同）
  IFS=':' read -r -a DIRS <<< "$LD_LIBRARY_PATH"
  echo "count=${#DIRS[@]}"   # toybox: 输出字符串长度(如 1364)而非目录数(22)
  ```
- 触发实例：aghermann 1.1.2 `test_package/test_ohos.sh` 依赖闭合检查误报 6 个
  NEEDED 库（libsigfile/libsigproc/libfftw3/libfftw3_threads/libgsl/libgslcblas）。
  **关键判别**：同一构建里 test_edf.sh 实际运行 `edfhed` 成功（动态装载器经
  conanrun LD_LIBRARY_PATH/RUNPATH 解析到全部库）→ 依赖并未缺失，是脚本自身坏了。

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 原 `read -a` + here-string（bash 语法） | toybox /bin/sh 下数组拆分失效 → 静默误报，CI #59412/#59738 失败 |
| POSIX `set --` 位置参数拆分 + heredoc（采纳） | /bin/sh 直接执行通过，conan create 全绿 |

## 最终方案、输入输出与真实验证

- 输入：`LD_LIBRARY_PATH`（conanrun 注入，含包私有 lib 目录与全部依赖 lib 目录）。
- 处理：`OLDIFS=$IFS; IFS=':'; set -- ${LD_LIBRARY_PATH:-}; IFS=$OLDIFS`，
  `for d in "$@" /system/lib64 /vendor/lib64` 遍历 `[ -e "$d/$lib" ]`；
  逐行 `while IFS= read -r lib` 用 heredoc（`done <<EOF … EOF`）而非 here-string。
- 输出：`[ok] dynamic dependency closure: all DT_NEEDED libs found (path scan)`。
- 真实验证：`/bin/sh test_ohos.sh <bin_dir> <minimal.edf>` 四项断言全过；
  本地 `CI_PACKAGES="archives/a/aghermann/1.1.2" … zsh ci/conan/build_and_test.sh`
  全量复跑：conan create passed，test_edf.sh + test_ohos.sh 均通过，
  Build Summary Success 1 / Failed 0 / Pass rate 100.0%。

## 适用范围、反例、解除条件与风险

- 适用：所有在 test_package/*.sh 里做依赖闭合/路径扫描/环境解析的鸿蒙适配配方；
  任何经 conan `self.run(shell, script)` 执行、且 shell=/bin/sh 的脚本都须 POSIX。
- 反例：假设 worker 必有 bash、或用 `CONFIG_SHELL=/bin/bash` 规避的配方不属于本条
  （仍建议 POSIX 化以兼容无 bash 环境）。
- 解除条件：无（toybox /bin/sh 长期为 OHOS 默认，脚本应始终 POSIX 兼容）。
- 风险：`set -- ${VAR}` 未加引号，若路径含 shell 元字符会误拆——conan 缓存路径
  由 conan 生成（无空格/元字符），实测安全；必要时可 `set -f` 关 glob。
