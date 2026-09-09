# pipebench

管道吞吐测速工具：坐在管道中间，把 stdin 数据转发到 stdout，同时在 stderr 显示传输速率与汇总（Thomas Habets，GPL-2.0-or-later）。

- 上游：https://github.com/ThomasHabets/pipebench
- 版本：0.4（对应上游发布 0.40，tarball 名 pipebench-0.40.tar.gz）
- 许可证：GPL-2.0-or-later

## 构建要点（OHOS aarch64）

- 裸 Makefile 项目（无 configure）：配方执行
  `make CC="<conan conf c 编译器>" CFLAGS="-Wall -pedantic -O2" -j1 pipebench`。
- 不调用上游 `make install`（其 install 规则依赖 GNU `install -D`），
  package() 手动 copy `pipebench` 到 `bin/`、`pipebench.1` 到 `share/man/man1/`。
- 上游无测试套件（Makefile 无 check/test 目标，无 tests/ 目录），
  已按 no_tests 审计处理；test_package 自建 3 个直通/冒烟用例覆盖核心行为。

## 典型用法

```sh
tar cf - . | pipebench | (cd /mnt/backup && tar xf -)
dd if=/dev/zero bs=80k count=60k 2>/dev/null | pipebench -q > /dev/null
```
