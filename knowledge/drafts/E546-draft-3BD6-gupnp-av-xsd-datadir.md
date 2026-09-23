# E546：gupnp-av 的 XSD 运行时寻址——GUPNP_AV_DATADIR 必须指向包内 share/gupnp-av

## 错误特征

```
I/O warning : failed to load "/share/gupnp-av/didl-lite-v2.xsd"
Schemas parser error : Failed to locate the main schema resource
```

## 根因

gupnp-av 的 DIDL-Lite 校验器（fragment-util.c get_data_dir）按 **GUPNP_AV_DATADIR 环境变量 > 编译期 DATADIR 宏**的顺序寻址 XSD。DATADIR 宏是编译期 prefix+datadir+'gupnp-av'（conan 下 prefix=/ → "/share/gupnp-av"），而 conan 包安装路径不在 "/"——消费者运行时不设 GUPNP_AV_DATADIR 的话 libxml2 加载 XSD 失败。上游 tests/gtest/meson.build 正是用 GUPNP_AV_DATADIR 指向源码 data/ 目录跑测试的——这是上游设计的运行时寻址机制，不是适配 bug。

## 解法

conanfile.py `package_info()` 里：

```python
self.runenv_info.define_path("GUPNP_AV_DATADIR",
    os.path.join(self.package_folder, "share", "gupnp-av"))
```

VirtualRunEnv 自动注入消费者环境；test_package 的 test() 用 env="conanrun" 运行（conanrun.sh 聚合了依赖包 runenv_info）；独立验证也可手动 export。

## 推广

带编译期数据目录宏的库（.xsd/.dtd/locale 数据）在 conan 打包后都需检查运行时寻址是否断裂，用 runenv_info.define_path 注入包内绝对路径。

## 实证

gupnp-av 0.14.5（PR !7999，上游 meson test 8/8 全过 + test_package 实调验证，CI 全绿）。
