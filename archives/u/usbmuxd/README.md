# usbmuxd

iPhone/iPod Touch USB 多路复用守护进程（libimobiledevice 生态服务端）。

监听 `/var/run/usbmuxd` Unix 域套接字，将客户端 TCP-over-usbmux 请求
多路复用到 USB Apple Mobile 设备；`iproxy` 工具把本机 TCP 端口转发到
设备端口。

## 版本索引

| 版本 | 状态 | 备注 |
|------|------|------|
| 1.0.8 | built | OHOS 适配（任务 #13997） |

依赖：libusb/1.0.27、libplist/2.7.0、libusbmuxd/2.0.2（iproxy 客户端
链接）。
