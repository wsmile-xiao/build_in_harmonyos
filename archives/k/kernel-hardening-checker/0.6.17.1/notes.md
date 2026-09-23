# kernel-hardening-checker 0.6.17.1 适配笔记

## 上游信息
- **仓库**: https://github.com/a13xp0p0v/kernel-hardening-checker
- **版本**: 0.6.17.1（tag `v0.6.17.1`，commit afc376f，对应 Linux v6.17 检查规则）
- **语言**: Pure Python 3（requires-python >= 3.9，设备 python3 3.12.9 满足）
- **构建系统**: pyproject.toml（PEP 517，setuptools >= 77.0.3 后端）
- **许可**: GPL-3.0-only（LICENSE.txt）
- **运行时依赖闭包**: 空（os/gzip/sys/tempfile/subprocess/shutil/argparse/typing/re/json，纯 stdlib）

## 构建方式
纯 Python noarch CLI，无需 C/C++ 编译：
```bash
pip install --break-system-packages setuptools wheel          # 引导构建依赖
pip install --break-system-packages --no-deps --no-build-isolation \
    --prefix=<staging> <src_dir>                              # PEP 517 staging 安装
```
- `--no-build-isolation`：设备已有 setuptools 84.0.0（满足 pyproject 的 >= 77.0.3），
  避免 pip 隔离环境重新从索引拉取 setuptools
- package() 从 staging 复制 `lib/python3.12/site-packages` 与 `bin/`

## 与 py-cpuinfo 同族 recipe 的三点差异
1. **无 `__main__.py`**：`python3 -m kernel_hardening_checker` 不可用。
   wrapper 改为 `exec python3 -c 'import kernel_hardening_checker;
   kernel_hardening_checker.main()' "$@"`（等价上游 bin/kernel-hardening-checker
   免安装 launcher 的行为）。
2. **wrapper 自解析路径**：`bin/kernel-hardening-checker` 内部按自身位置计算
   `$PREFIX/lib/python3.12/site-packages` 并设置 PYTHONPATH，不依赖 conanrun
   环境（CI L2 冒烟直接裸跑 bin/ 下可执行文件）。
3. **防御式补拷 config_files/**：实测上游 wheel 已含全部 94 个
   `kernel_hardening_checker/config_files/` 样例文件
   （defconfigs/distros/kspp-recommendations；pyproject 配置模式下 setuptools
   的 include_package_data 默认 True，叠加 MANIFEST.in 的
   recursive-include，包内数据全部入 wheel，Curator zipfile 清点 94/94 证实）。
   recipe 在 package() 从导出源码幂等补拷作为保险（实测 wheel 已含，补拷仅作
   保险），使 `-c <官方示例 .config>` 开箱可用。

## 上游测试
1. **官方单元测试（权威，14 用例）**：`.github/workflows/engine_unit-test.yml`
   ```bash
   cd <source_root> && python3 -m unittest -v -b
   ```
   `kernel_hardening_checker/test_engine.py` 仅依赖 unittest/unittest.mock/io，
   无平台依赖。test_package 中以
   `python3 -m unittest -v -b kernel_hardening_checker.test_engine`
   对已安装包等价运行（test_engine.py 随包分发）。
2. **功能测试 functional_test.sh（部分不可移植）**：
   - 设备适用子集：`--version`、`-h`、`-p {X86_64,X86_32,ARM64,ARM,RISCV}`
     （含 `-m verbose/json`）、`-g <arch>`、`-c <.config>`（含 `.gz`）、
     `-s <合成 sysctl>`（含 kernel.arch 架构识别）
   - 设备不可用：`-a` autodetect 与 functional_test.sh 整体——依赖
     `/proc/config.gz`（不存在）、`/boot`（不存在）、`/proc/cmdline`
     （EACCES）、`sudo sysctl -a` 改写、coverage、script/tty 仿真
3. **package_test.yml / static_analysis.yml**：打包元数据与开发质量门，
   不属移植验收范围。

## HarmonyOS 适配
- 无任何 patch：上游代码无平台分支，engine/checks 纯数据逻辑，不触碰设备接口
- `-c`/`-p`/`-g`/`-s` 输入均为用户提供的文件，设备实测可用；仅 `-a` 需要
  运行内核暴露配置源（OHOS 不提供）
- python gzip/json/argparse/subprocess 在设备 3.12.9 实测可导入，gzip 读写正常

## 消费者测试（test_package/test_khc.py）
1. import kernel_hardening_checker 并校验 `__version__ == "0.6.17.1"`
2. 上游 14 个单测（对已安装包运行）
3. CLI wrapper `--version` 输出精确匹配
4. CLI `-p ARM64` 输出建议表
5. CLI `-c` 合成 plain Kconfig（版本头 + CONFIG_ARM64=y）
6. CLI `-c` gzip Kconfig（gzip 解压路径）
7. CLI `-c` 包内随发的官方样例 `arm64_defconfig_6.6.config`
8. CLI 错误路径 `-c <不存在文件>` 非零退出且输出 ERROR

## 知识沉淀
- 纯 Python CLI 打包沿用 py-cpuinfo 模式（pip staging + wrapper），本库差异点：
  无 `__main__.py` → wrapper 直接 `import 包; 包.main()`
- console script shebang 指向构建机 Python，必须重写；wrapper 要自解析
  site-packages，避免依赖 conanrun（CI L2 裸跑）
- wheel 数据完整性必须实测（zipfile 清点），不得从“无 package-data 段”推断：
  本例实测 wheel 已含 config_files 全部 94 个文件，recipe 补拷为防御式保险
- 上游 functional 测试以"设备适用子集 + NOT_RUN 穷尽证据"方式覆盖
