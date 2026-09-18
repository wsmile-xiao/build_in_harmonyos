# 草稿：OHOS mksh 启动重置 LD_LIBRARY_PATH——conan self.run 环境链整体失效

## 错误特征
```
configure:3575: ./conftest
Error loading shared library libc++_shared.so: (needed by ./conftest)
configure: error: cannot run C++ compiled programs
```
（conanbuild.sh 里明明 export 了正确的 LD_LIBRARY_PATH；bash 手动 source 同链一切正常）

## 根因
OHOS /bin/sh（mksh 定制）**启动时重置 LD_LIBRARY_PATH**——父进程注入的正确值被静默丢弃。
conan 2.x `ConanFile.run()` 的包装命令（`. conanbuild.sh && cmd`）经
`subprocess.Popen(cmd, shell=True)` 执行，POSIX 上即 /bin/sh → 整条 conanbuild
环境链（toolchain environment、E467 依赖 libdirs、SDK libc++ 路径）全部失效。
config.log 的环境 dump 不含 LD_LIBRARY_PATH，source 链本身无错——极难定位。

## 定性实验
```bash
env LD_LIBRARY_PATH=/x /bin/sh -c 'echo $LD_LIBRARY_PATH'              # 丢失 /x
env LD_LIBRARY_PATH=/x /data/service/hnp/bin/bash -c 'echo $...'       # 保留
```

## 解法
构建步骤不走 conan 默认 run()：写 run_build_step.sh（source env 链 + export
E467 路径 + 业务命令），`self.run("<hnp bash> script", env=None)` 显式 bash 驱动。
先例：sdcc/4.6.0、ntl/11.6.0；logstalgia/1.1.4 固化为 _run_bash() 助手。

## 关联
- E467（AutotoolsDeps/LIBS conftest 闭包）：本条是其"修了环境还是不行"的深层根因
- E435（mksh here-doc 挂起）：同属 mksh 行为差异家族，症状不同机制不同
