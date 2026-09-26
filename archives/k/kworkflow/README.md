# kworkflow

## 简介

kworkflow（命令名 `kw`）是一套面向 Linux 内核开发者的 bash 工具集，由上游 kworkflow 项目维护，
覆盖内核构建（`kw build`）、部署（`kw deploy`）、代码探索（`kw explore`）、远程设备管理
（`kw remote`/`kw ssh`）、配置管理（`kw config`/`kw env`）、维护者查询（`kw maintainers`）、
补丁流程（`kw send-patch`/`kw patch-hub`）等日常开发动作。

## OHOS 适配

- 纯 bash 脚本项目，零编译产物。上游 `setup.sh` 不可原样执行：它依赖 rsync/sphinx、联网 clone
  patch-hub、并安装到 `$HOME`；本配方按 `setup.sh` 的安装布局手动打包：
  `bin/kw`（入口，保持 `#!/usr/bin/env bash` 可移植 shebang，见知识 E049）+ `lib/kw/`（src 全树，
  含重新生成的 `VERSION`）+ `etc/kw/`（配置模板）+ `share/kw/{sound,database}` + bash 补全。
- 硬依赖 bash>=4.3（`local -n` 命名引用 x47、`declare -A` x18、`mapfile` x6）：直接
  `requires("bash/5.3")`（制品仓已发布 armv8 静态二进制包）。`bash/5.3` 的 package_info 只声明
  `cpp_info.libs=["bash"]`、不暴露 bin PATH，因此消费者（test_package）用
  `self.dependencies["bash"].package_folder` 拼 bin 路径注入 PATH；本包 `package_info()` 同时用
  `buildenv_info`/`runenv_info` 传播 `PATH` 与 kw 的环境契约。
- OHOS 用户态为 toybox，与 GNU 长选项不兼容。`patches/ohos-toybox-longopts.patch` 做等价改写：
  `sort --dictionary-order→sort -d`、`ln --symbolic --force→ln -sf`、`rm --recursive --force→rm -rf`、
  `sed --in-place [--follow-symlinks] [--regexp-extended]→sed -i [-r]`、`grep --line-regexp→grep -x`、
  `date --date @→date -d @`、`cut --delimiter=… --fields=→-d… -f…`、`tr --delete→tr -d`、
  `base64 --wrap=0→base64`、explore 的非 git 回退路径 `grep --line-number --recursive/--context→-n -r/-C`、
  `diff` 丢弃 `--color=always`。其中 `sed --follow-symlinks` 在 toybox 无等价物，裸 `sed -i`
  会以普通文件替换链接本体；`kw_remote.sh` 已由补丁引入 `sed_in_place` 助手（`-L` 探测 +
  `readlink -f` 解析目标后原位编辑），恢复了"保持符号链接语义"的编辑行为
  （kw_remote_test 的链接保持用例实测通过，实际行为优于单纯"丢弃"）。
  另：`/dev/shm` 在 OHOS 上可通过 -d/-w 探测但 mktemp 实际被 MAC 拒绝，
  `create_shared_memory_dir` 补丁为失败时回落默认临时目录（与函数文档语义一致）。
- GNU date 的字符串解析与日期算术（`date --date='X + N day'`）toybox 完全不支持
  （探针：`date -d '2026/01/01'` → `bad date`；`date -d @epoch` 正常）。因此 kw 的周/月统计、
  `get_week_day` 一类日历功能在 OHOS 受限；秒级换算（`sec_to_format`）可用。
- sparse/smatch/cscope 纠偏：这些不是 kw 0.10 的依赖（源码零引用），未写入依赖闭包。

## 运行环境契约

`kw` 入口按 `${KW_LIB_DIR}/kw`、`${XDG_CONFIG_HOME}/kw`、`${XDG_DATA_HOME}/kw` 组织目录
（变量缺省时回落 `$HOME`）。包内布局与之对应，消费者通过 conanrun 环境或显式导出：

```bash
export KW_LIB_DIR=<pkg>/lib            # kw 自动追加 /kw
export XDG_CONFIG_HOME=<pkg>/etc       # -> <pkg>/etc/kw 配置模板
export XDG_DATA_HOME=<pkg>/share       # -> <pkg>/share/kw/{sound,database}
export PATH=<bash 包>/bin:<pkg>/bin:$PATH
kw --version
```

未打包：fish 补全（OHOS 无 fish）、man/doc（需 sphinx 构建，非运行期必需）、tracing（开发期
代码追踪钩子，空目录）。sound/database 属可选功能数据，随包提供但依赖的 sqlite3/play 工具
OHOS 缺失时相应子功能不可用。

## 功能验证

```bash
kw --version          # 输出 0.10
kw --help             # 输出 Usage: kw
kw env --create X && kw env --use X   # 走 mktemp/ln 路径
```

## 参考

- 源码: https://github.com/kworkflow/kworkflow（tag 0.10）
- 上游测试: `run_tests.sh` + shunit2（tests/unit 纯脚本子集真实运行；集成套件依赖 podman，OHOS 不可行）
