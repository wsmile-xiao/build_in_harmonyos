# lyaml

## 简介
lyaml 是 LibYAML 的 Lua 绑定库，提供 YAML 格式数据的解析和生成功能。

## OHOS 适配
- **构建系统**: 使用 luke（基于 Lua 的构建工具），但在 HarmonyOS 环境下存在兼容性问题
- **平台限制**: `os.tmpname` 函数在 HarmonyOS 上无法正常工作（/tmp 只读），导致 luke 构建失败
- **解决方案**: 手动编译 C 模块（yaml.c, emitter.c, parser.c, scanner.c），创建共享库 yaml.so

### 与 Linux 的差异
- Linux 下可直接使用 `luke build` 构建
- HarmonyOS 需手动编译 C 文件并安装模块

## 排除与替代
- 不推荐使用 luke 构建系统（平台限制）
- 推荐使用手动编译流程（见 notes.md）

## 依赖
- Lua 5.4.x
- LibYAML >= 0.2.5

## 功能验证
```bash
# 设置 Lua 搜索路径
export LUA_PATH="$PREFIX/share/lua/5.4/?.lua;$PREFIX/share/lua/5.4/?/init.lua;;"
export LUA_CPATH="$PREFIX/lib/lua/5.4/?.so;;"

# 加载模块测试
lua -e 'local lyaml = require "lyaml"; print(lyaml.dump({{foo = "bar"}}))'
```

## 参考
- 官网: https://github.com/gvvaughan/lyaml
- LibYAML: https://github.com/yaml/libyaml