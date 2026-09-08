# bmk 0.1 适配笔记

## 编译环境

- 构建系统：手写 configure + Mkfile
- 编译日期：2026-09-05
- 编译器：clang 15
- 状态：built

## 编译步骤

```bash
CC=<profile target clang> CPP="<profile target clang> -E" CFLAGS="-fPIC -O2 <profile tools.build:cflags>" LDFLAGS="<profile tools.build:exelinkflags>" sh ./configure --prefix=/ --bindir=/bin --mandir=/share/man
make -j1
./mk clean all  # native OHOS runtime only; skipped during cross-build
make DESTDIR=<package_folder> install
```

## 依赖版本

无第三方依赖，仅使用 OHOS libc、clang 和 make。

## 上游测试核验

上游 0.1 源码不含正式单元测试或集成测试，也没有 `check`/`test` 目标，因此正式上游测试用例数为 0。上游 CI 的唯一可迁移验证语义是 bootstrap 构建和 self-host 重建；配方全部保留执行。PCC/TCC 与多操作系统任务是同一验证的环境矩阵，不作为额外用例虚增统计。

## 验证结果

- bootstrap：通过
- self-host `./mk clean all`：通过
- 消费者测试：OHOS 本机 W3 中执行 4/4 通过；纯交叉编译且无目标运行器时明确记录为 skipped，不宣称通过

## 对话记录

### 对话 #1

- 任务：适配 bmk 0.1 并按积分赛事模板准备 PR。
- 结果：无第三方依赖；上游正式测试 0 个；上游 bootstrap/self-host 验证通过；OHOS 本机 W3 消费者测试 4/4 通过。
---

**编译结束**: 2026-09-05 19:25
**最终状态**: built
