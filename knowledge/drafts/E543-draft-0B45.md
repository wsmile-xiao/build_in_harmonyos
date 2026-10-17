# E543 — GNU make shell for 循环目标掩盖子目录 make 失败，多目录生成链静默丢产物

## 错误特征

- 顶层 `make <target>` 返回 0（构建"成功"），但后续阶段报生成产物缺失：
  `cp: cannot stat 'dev/marpa.pdf'`、`make[1]: cweave: No such file or directory`（Error 127）
  混在正常输出中被忽略。
- 或消费者/下游编译报 `implicit declaration of function 'marpa_dstack_resize'`
  类错误——子目录生成的头文件缺前置声明块。
- 日志中可见 `for d in ac ami dev tavl public; do (cd $d; make); done` 式循环。

## 触发条件

- 构建系统: 上游 Makefile 用 shell for 循环递归调用子目录 make（literate-programming / 代码生成型项目高发，如 libmarpa 的 CWEB→C 生成链）
- 阶段: make（源码生成）→ 后续 copier/install/consumer 编译时延迟暴露

## 根因分析

子 shell `(cd $$d; $(MAKE))` 中 make 的退出码不会传播到 for 循环：
循环整体退出码只取决于**最后一个**目录的子 make。前面子目录因构建机工具缺失
（OHOS 构建机普遍无 cweave/pdftex/makeinfo/texi2any）失败、跳过生成 CWEB 派生
产物时，顶层 make 仍返回 0。若上游又把输出接管道（`| tail`），失败再被吞一次。
错误推迟到 copier 缺文件或消费者编译缺声明时才爆出，root cause 与报错点相距
数个阶段，极易误判。

libmarpa/11.0.13 实例：`work/Makefile` sources 循环中 dev/、ami/ 因 cweave
缺失失败，marpa_ami.h 的前置声明块（`marpa_dstack_resize`/`resize2` prototypes）
未生成；顶层返回 0 继续，直到消费者以 `-DNDEBUG` 构建时报
implicit declaration + int→void* 转换错误。

## 解决方案

### 推荐方案
per-subdir-make-target：不调用顶层 for 循环目标，改为按子目录逐个调用其
真正的生成目标（`sources`/`all`），使每个子 make 的失败立即以非零退出码显式
暴露。需先甄别各子目录默认 `all` 是否拖入不可用的文档规则（pdf/texi）：
若是则调用纯代码生成目标（`make sources`），或先创建文档占位产物再调用。
在 Conan recipe 中即循环 `self._run("(cd %s && make %s)" % (subdir, target))`。

### 禁止做法
- ❌ `make sources 2>&1 | tail -3`——管道退出码覆盖 make 非零码，双重掩盖
- ❌ touch 伪造生成产物时间戳让 make"通过"——产物从未真实生成，属假适配

## 验证
```bash
cd work && make sources; echo $?   # 子目录失败仍返回 0 → 命中本条
(cd dev && make sources); echo $?  # 逐目录执行立即报 Error 127 → 修复生效
# 修复后各子目录目标逐一非零退出可见，copier/install/消费者链不再缺文件
```

## 关联条目
- 相关: E074（make jobserver FIFO，同为 make 行为差异但根因不同）、E402（toybox gzip 长选项，同为构建机工具能力缺失）
