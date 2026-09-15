# E479 — 上游 tag 可声明未实现的自检选项或 BROKEN 构建目标（不可据此判定可测）

## 错误特征

- 运行上游自带自检选项（如 `./digitemp_DS9097 -T`）**恒返回非零退出码**（实测 exit 3），且无任何测试输出
- `Makefile` 中不存在 `check` / `test` / `installcheck` 目标（`make test` 无事可做）
- 上游 CI workflow（如 `.github/workflows/tests.yml`）里出现的命令，在当前 tag 上不可用
- 某个构建目标被上游注释为 `BROKEN`（如 digitemp 的 `ds2490`，且依赖 libusb）

## 触发条件

- 构建系统: make / 手写 Makefile
- 阶段: testing（判定"上游是否有可执行测试套件"时）

## 根因分析

上游**主分支**与**已发布的 tag** 能力并不一致：

- digitemp v3.7.2 的 `src/digitemp.c:2423` 只执行 `case 'T': opts |= OPT_TEST;`
  把标志位置 1，全树对 `OPT_TEST`（`src/digitemp.h:33` 定义）**再无任何引用**——
  自检实现（`test_build_af()`、`exit(test_build_af())`）是 master 后续提交才加入的。
- 上游 workflow 的 `make ds9097 && ./digitemp_DS9097 -T` 是 2023 年加上去的，
  对 2018 年的 v3.7.2 tag 不成立。
- Makefile 的 `ds2490` 目标被标注 BROKEN 且需要 libusb，不应纳入构建目标集合。

因此"上游 workflow 里有测试命令"≠"该 tag 存在可执行测试"。若据此宣称已有上游测试，
会把一个必然失败的测试写进 L1，污染 CI 判定。

## 解决方案

1. **先证伪再下结论**：在源码中检索该选项的处理分支与测试目标
   ```bash
   grep -rn "OPT_TEST\|case 'T'" src/            # 看是否有后续处理
   grep -nE "^(check|test|installcheck):" Makefile   # 看是否存在测试目标
   ```
2. 确认无实现后，按仓库机制申报**无官方测试**：在 `ci/config/no_official_test.txt`
   追加条目（该文件头明文允许各包自行添加），并在 `reports/test-report.md` 中
   **保留实际执行证据**（命令 + 真实退出码），同时说明该 tag 与上游 master 的差异。
3. 构建目标集合只保留可用目标（本例仅 `ds9097` / `ds9097u`），BROKEN 目标不构建。
4. 消费者侧测试用 `test_package/` 自建（调用被测二进制/API），弥补上游空白。

## 验证

```bash
./digitemp_DS9097 -T ; echo "exit=$?"     # v3.7.2 实测 exit=3，无测试输出
grep -cE "^test:|^check:" Makefile        # v3.7.2 = 0
```

## 关联

- 实例: digitemp 3.7.2（`T_9097_exit=3`、`T_9097U_exit=3`、`maketest_targets=0`）
- 机制: `ci/config/no_official_test.txt` + `ci/conan/build_and_test.sh` L1 判定
