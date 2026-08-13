// karchive test_package 测试：调用 karchive 公开 API（KCompressionDevice）
// 验证库可实际编译链接运行（非空壳测试，R34）。
#include <cstdio>

#include <QBuffer>
#include <QIODevice>

#include <kcompressiondevice.h>

int main() {
    QBuffer buffer;
    if (!buffer.open(QIODevice::WriteOnly)) {
        std::fprintf(stderr, "FAIL: QBuffer open failed\n");
        return 1;
    }
    // 构造 GZip 压缩设备并写入数据，验证压缩功能（非仅构造函数）。
    // QIODevice* 构造函数需 3 参数（autoDeleteInputDevice），2 参数不匹配
    KCompressionDevice device(&buffer, false, KCompressionDevice::GZip);
    if (!device.open(QIODevice::WriteOnly)) {
        std::fprintf(stderr, "FAIL: KCompressionDevice open failed\n");
        return 1;
    }
    const char data[] = "karchive compression test data";
    if (device.write(data, sizeof(data) - 1) < 0) {
        std::fprintf(stderr, "FAIL: KCompressionDevice write failed\n");
        return 1;
    }
    device.close();
    // 压缩输出应有数据（GZip 流写入 buffer）
    if (buffer.size() == 0) {
        std::fprintf(stderr, "FAIL: no compressed output produced\n");
        return 1;
    }
    std::printf("PASS: KCompressionDevice compressed %zu -> %lld bytes\n",
                sizeof(data) - 1, static_cast<long long>(buffer.size()));
    return 0;
}
