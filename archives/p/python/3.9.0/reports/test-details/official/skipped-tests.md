# Python 3.9.0 OpenHarmony 跳过测试详情

## 跳过测试列表 (25个)

### 1. GUI 相关 (8个)

| 测试 | 跳过原因 |
|------|----------|
| test_tk | No module named '_tkinter' |
| test_tcl | No module named '_tkinter' |
| test_idle | No module named '_tkinter' |
| test_turtle | No module named '_tkinter' |
| test_tix | No module named '_tkinter' |
| test_ttk_guionly | No module named '_tkinter' |
| test_ttk_textonly | No module named '_tkinter' |
| test_curses | Use of the 'curses' resource not enabled |

**原因**：OpenHarmony 未安装 Tcl/Tk GUI 库，GUI 应用需要其他框架

### 2. Linux 特有功能 (3个)

| 测试 | 跳过原因 |
|------|----------|
| test_nis | No module named 'nis' |
| test_ossaudiodev | No module named 'ossaudiodev' |
| test_spwd | No module named 'spwd' |

**原因**：这些是 Linux 特有的系统功能：
- `nis`: NIS/YP 网络信息服务，已过时
- `ossaudiodev`: OSS 音频设备，OpenHarmony 使用 OpenSL ES
- `spwd`: 影子密码文件，OpenHarmony 不使用

### 3. Windows 特有功能 (5个)

| 测试 | 跳过原因 |
|------|----------|
| test_winreg | No module named 'winreg' |
| test_winsound | Use of the 'audio' resource not enabled |
| test_winconsoleio | test only relevant on win32 |
| test_startfile | No module named 'os.startfile' |
| test_msilib | No module named '_msilib' |

**原因**：这些是 Windows 特有的功能

### 4. 其他 Unix 特有功能 (2个)

| 测试 | 跳过原因 |
|------|----------|
| test_devpoll | test works only on Solaris OS family |
| test_kqueue | test works only on BSD systems |

**原因**：这些是特定 Unix 系统的功能

### 5. 网络资源未启用 (6个)

| 测试 | 跳过原因 |
|------|----------|
| test_socketserver | resource 'network' not enabled |
| test_timeout | resource 'network' not enabled |
| test_smtpnet | resource 'network' not enabled |
| test_urllib2net | resource 'network' not enabled |
| test_urllibnet | resource 'network' not enabled |
| test_xmlrpc_net | resource 'network' not enabled |

**原因**：测试需要实际网络连接，默认未启用网络资源

### 6. 大文件资源未启用 (1个)

| 测试 | 跳过原因 |
|------|----------|
| test_zipfile64 | resource 'largefile' not enabled |

**原因**：测试需要处理大文件，默认未启用

## 跳过原因统计

| 分类 | 测试数量 | 占比 |
|------|----------|------|
| GUI (无 Tcl/Tk) | 8 | 32% |
| Windows 特有 | 5 | 20% |
| 网络资源未启用 | 6 | 24% |
| Linux 特有 | 3 | 12% |
| 其他 Unix 特有 | 2 | 8% |
| 大文件资源未启用 | 1 | 4% |

## 影响评估

| 跳过类型 | 影响程度 | 说明 |
|----------|----------|------|
| GUI 相关 | ⚠️ 中等 | 需要移植 Tcl/Tk 或使用其他 GUI 框架 |
| Windows/Linux 特有 | ✅ 无影响 | 这些功能在 OpenHarmony 上不需要 |
| 网络资源未启用 | ✅ 可选 | 可通过 `-u network` 启用 |
| 大文件资源未启用 | ✅ 可选 | 可通过 `-u largefile` 启用 |

## 如何运行被跳过的网络测试

```bash
./python3.9 -m test -u network test_socketserver test_timeout
```

## 如何运行被跳过的大文件测试

```bash
./python3.9 -m test -u largefile test_zipfile64
```