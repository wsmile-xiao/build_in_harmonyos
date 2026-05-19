# readosm 1.1.0a

## 软件描述
ReadOSM 是一个简单的库，用于从 Open Street Map 文件中提取有效数据。
支持两种输入格式：
- .osm：基于 XML 的格式
- .osm.pbf：基于 Google Protocol Buffer 序列化的格式

## 编译方法

### 依赖
- expat >= 2.0
- zlib

### 编译步骤
```bash
# 设置环境变量（如果依赖安装在非标准路径）
export CPPFLAGS="-I$HOME/usr/local/include"
export LDFLAGS="-L$HOME/usr/local/lib"

# 配置
./configure --prefix=$HOME/usr/local

# 编译
make -j4

# 测试
make check

# 安装
make install
```

### HarmonyOS 特殊处理
1. 需要替换 config.guess 和 config.sub 为较新版本
2. 在 config.guess 中添加 HarmonyOS 检测逻辑
3. 可能需要修改 config.status 的临时目录创建逻辑

## 已知问题
- autotools 的 config.guess 无法识别 HarmonyOS，需要手动添加检测
- config.status 创建临时文件可能因权限问题失败，需要特殊处理

## 库文件
- libreadosm.so.1.0.1 - 动态库
- libreadosm.a - 静态库
- readosm.h - 头文件

## 项目信息
- 源码: https://download.savannah.nongnu.org/releases/readosm/readosm-1.1.0a.tar.gz
- 官网: https://www.gaia-gis.it/gaia-sins/readosm.html
