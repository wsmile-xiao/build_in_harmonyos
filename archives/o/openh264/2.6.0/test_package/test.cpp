// openh264 test_package：真实 H.264 编码一帧并取出 NAL，非仅版本查询（R34 / R40 多媒体类要求）
// 用 C++ 而非 C：openh264 是 C++ 库，直接用其 C++ 接口，链接时由 clang++ 带上 C++ 运行时。
#include <wels/codec_api.h>
#include <wels/codec_ver.h>

#include <cstdio>
#include <cstring>
#include <vector>

static const int kW = 320;
static const int kH = 240;

int main() {
    ISVCEncoder *enc = nullptr;
    if (WelsCreateSVCEncoder(&enc) != 0 || enc == nullptr) {
        std::fprintf(stderr, "WelsCreateSVCEncoder failed\n");
        return 1;
    }

    SEncParamBase param;
    std::memset(&param, 0, sizeof(param));
    param.iUsageType     = CAMERA_VIDEO_REAL_TIME;
    param.iPicWidth      = kW;
    param.iPicHeight     = kH;
    param.iTargetBitrate = 200000;
    param.fMaxFrameRate  = 15.0f;

    if (enc->Initialize(&param) != 0) {
        std::fprintf(stderr, "ISVCEncoder::Initialize failed\n");
        WelsDestroySVCEncoder(enc);
        return 1;
    }

    // I420：Y 平面 + U/V 各 1/4
    std::vector<unsigned char> buf(static_cast<size_t>(kW) * kH * 3 / 2);
    for (int y = 0; y < kH; ++y) {                       // 非均匀画面，避免码流退化
        std::memset(&buf[static_cast<size_t>(y) * kW], y & 0xFF, kW);
    }
    std::memset(&buf[static_cast<size_t>(kW) * kH], 0x80, static_cast<size_t>(kW) * kH / 4);
    std::memset(&buf[static_cast<size_t>(kW) * kH * 5 / 4], 0x40, static_cast<size_t>(kW) * kH / 4);

    SSourcePicture pic;
    std::memset(&pic, 0, sizeof(pic));
    pic.iColorFormat = videoFormatI420;
    pic.iPicWidth    = kW;
    pic.iPicHeight   = kH;
    pic.iStride[0]   = kW;
    pic.iStride[1]   = kW / 2;
    pic.iStride[2]   = kW / 2;
    pic.pData[0]     = buf.data();
    pic.pData[1]     = buf.data() + static_cast<size_t>(kW) * kH;
    pic.pData[2]     = buf.data() + static_cast<size_t>(kW) * kH * 5 / 4;

    SFrameBSInfo info;
    std::memset(&info, 0, sizeof(info));

    int rc = enc->EncodeFrame(&pic, &info);
    if (rc != cmResultSuccess) {
        std::fprintf(stderr, "ISVCEncoder::EncodeFrame failed: %d\n", rc);
        enc->Uninitialize();
        WelsDestroySVCEncoder(enc);
        return 1;
    }
    if (info.eFrameType == videoFrameTypeSkip) {
        std::fprintf(stderr, "encoder skipped the frame — no bitstream produced\n");
        enc->Uninitialize();
        WelsDestroySVCEncoder(enc);
        return 1;
    }

    int total = 0;
    for (int i = 0; i < info.iLayerNum; ++i) {
        const SLayerBSInfo &layer = info.sLayerInfo[i];
        for (int n = 0; n < layer.iNalCount; ++n) {
            total += layer.pNalLengthInByte[n];
        }
    }

    enc->Uninitialize();
    WelsDestroySVCEncoder(enc);

    if (total <= 0) {
        std::fprintf(stderr, "openh264 produced empty bitstream\n");
        return 1;
    }

    std::printf("openh264: version=%d.%d.%d  encoded %d bytes (%d layer(s)) from %dx%d  OK\n",
                OPENH264_MAJOR, OPENH264_MINOR, OPENH264_REVISION,
                total, info.iLayerNum, kW, kH);
    return 0;
}
