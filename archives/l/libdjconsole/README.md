# libdjconsole

`libdjconsole` is the C++ library from DJPlay for Hercules DJ Console devices.
The OHOS package builds the original library and installs its public headers,
device mapping data, and udev rule. It uses the published
`libusb-compat/0.1.7` package for the upstream libusb 0.1 API.

The consumer test exercises the hardware-independent `Delta` and `Bitfield`
classes. The build and test do not claim that an ordinary OHOS application can
access USB hardware; the platform application sandbox restricts USB device I/O.
