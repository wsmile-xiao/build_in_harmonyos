// OpenCV 4.12.0 鸿蒙 PC 适配验证。
//
// R34/R40：不做「dlopen + dlsym 看指针非空」的空壳探测——本文件直接 #include OpenCV 公共头、
// 直接链接 opencv_* 共享库，并对每一项接进来的能力做**真实功能调用**且校验结果：
//   · imgproc  高斯模糊/色彩空间转换，校验像素真的被改变
//   · imgcodecs 各图像格式 encode→decode 往返，逐个坐实所接的第三方编解码库：
//       PNG→libpng、JPEG→libjpeg-turbo、WebP→libwebp、TIFF→自带 libtiff、JP2→openjpeg
//   · videoio  VideoWriter 写出视频再 VideoCapture 读回，坐实 ffmpeg 后端真的接上
//   · dnn      blobFromImage 真实前处理（含 vendored protobuf 链接）
//   · features2d / calib3d / gapi 各跑一条真实计算路径
#include <opencv2/core.hpp>
#include <opencv2/core/version.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/videoio.hpp>
#include <opencv2/dnn.hpp>
#include <opencv2/features2d.hpp>
#include <opencv2/calib3d.hpp>
#include <opencv2/gapi.hpp>
#include <opencv2/gapi/core.hpp>
#include <opencv2/gapi/imgproc.hpp>

#include <cmath>      // std::abs(double)——只 include <cstdlib> 会取到 abs(int) 而静默截断
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

static int g_failed = 0;
static int g_total = 0;

static void check(bool ok, const char *what, const std::string &detail = "") {
    g_total++;
    std::printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what,
                detail.empty() ? "" : " — ", detail.c_str());
    if (!ok) g_failed++;
}

// 造一张有结构的彩色测试图（渐变 + 方块 + 圆），便于各编解码器往返后比对。
static cv::Mat makeTestImage() {
    cv::Mat img(120, 160, CV_8UC3);
    for (int y = 0; y < img.rows; ++y)
        for (int x = 0; x < img.cols; ++x)
            img.at<cv::Vec3b>(y, x) = cv::Vec3b((uchar)(x * 255 / img.cols),
                                                (uchar)(y * 255 / img.rows), 128);
    cv::rectangle(img, cv::Rect(20, 20, 50, 40), cv::Scalar(255, 0, 0), -1);
    cv::circle(img, cv::Point(110, 80), 25, cv::Scalar(0, 255, 0), -1);
    return img;
}

// encode→decode 往返：校验解回来的尺寸/通道一致，且内容与原图接近（有损格式放宽阈值）。
// 编解码器缺失时 OpenCV 抛 cv::Exception 而非返回 false，必须就地捕获，
// 否则一个格式没编进去就会中断整个测试、丢掉其余断言的结果。
static void roundTrip(const char *label, const char *ext, const cv::Mat &src,
                      double maxMeanDiff, const std::vector<int> &params = {}) {
    try {
        std::vector<uchar> buf;
        if (!cv::imencode(ext, src, buf, params)) {
            check(false, label, std::string("imencode ") + ext + " 返回 false（该编解码器未编入）");
            return;
        }
        if (buf.size() < 16) {
            check(false, label, "编码结果过小，疑似空数据");
            return;
        }
        cv::Mat back = cv::imdecode(buf, cv::IMREAD_COLOR);
        if (back.empty()) {
            check(false, label, "imdecode 返回空 Mat");
            return;
        }
        if (back.rows != src.rows || back.cols != src.cols) {
            check(false, label, "往返后尺寸不一致");
            return;
        }
        cv::Mat diff;
        cv::absdiff(src, back, diff);
        const cv::Scalar m = cv::mean(diff);          // 一次求值，三通道相加
        double mean = m[0] + m[1] + m[2];
        char d[160];
        std::snprintf(d, sizeof(d), "%zu 字节，往返平均差 %.2f（阈值 %.1f）",
                      buf.size(), mean, maxMeanDiff);
        check(mean <= maxMeanDiff, label, d);
    } catch (const cv::Exception &e) {
        check(false, label, std::string("抛出 cv::Exception: ") + e.what());
    }
}

// 文件往返：imwrite→imread。
// JPEG 2000 必须走这条——OpenCV 的 OpenJPEG 编码器用 opj_stream_create_default_file_stream()
// 建流，**只支持写文件**；走 imencode 的内存缓冲时文件名为空，直接报
// "OpenJPEG2000: Can not create stream"（grfmt_jpeg2000_openjpeg.cpp:790）。这是上游实现限制，
// 不是 openjpeg 没接上。
static void roundTripFile(const char *label, const char *path, const cv::Mat &src,
                          double maxMeanDiff) {
    try {
        if (!cv::imwrite(path, src)) {
            check(false, label, std::string("imwrite ") + path + " 返回 false");
            return;
        }
        cv::Mat back = cv::imread(path, cv::IMREAD_COLOR);
        std::remove(path);
        if (back.empty() || back.rows != src.rows || back.cols != src.cols) {
            check(false, label, "读回为空或尺寸不一致");
            return;
        }
        cv::Mat diff;
        cv::absdiff(src, back, diff);
        const cv::Scalar m = cv::mean(diff);          // 一次求值，三通道相加
        double mean = m[0] + m[1] + m[2];
        char d[160];
        std::snprintf(d, sizeof(d), "往返平均差 %.2f（阈值 %.1f）", mean, maxMeanDiff);
        check(mean <= maxMeanDiff, label, d);
    } catch (const cv::Exception &e) {
        check(false, label, std::string("抛出 cv::Exception: ") + e.what());
    }
}

// 把一段断言包起来：任何 cv::Exception 都记为该项失败，而不是让进程直接退出。
template <typename F>
static void section(const char *label, F body) {
    try {
        body();
    } catch (const cv::Exception &e) {
        check(false, label, std::string("抛出 cv::Exception: ") + e.what());
    }
}

int main() {
    std::printf("OpenCV %s（编译期头 CV_VERSION=%s）\n",
                cv::getVersionString().c_str(), CV_VERSION);

    // 头与库版本必须一致，否则说明链到了别的 OpenCV
    check(cv::getVersionString() == std::string(CV_VERSION), "头/库版本一致");

    // ── core + imgproc：真实计算，校验结果确实变化 ──────────────────────────
    cv::Mat img = makeTestImage();
    check(!img.empty() && img.channels() == 3, "core: Mat 构造 160x120 CV_8UC3");

    cv::Mat blurred;
    cv::GaussianBlur(img, blurred, cv::Size(9, 9), 3.0);
    cv::Mat bdiff;
    cv::absdiff(img, blurred, bdiff);
    check(cv::countNonZero(bdiff.reshape(1)) > 0, "imgproc: GaussianBlur 真实改变了像素");

    cv::Mat gray;
    cv::cvtColor(img, gray, cv::COLOR_BGR2GRAY);
    check(gray.channels() == 1 && gray.size() == img.size(), "imgproc: cvtColor BGR→GRAY");

    // ── imgcodecs：逐个坐实接进来的第三方编解码库 ──────────────────────────
    roundTrip("imgcodecs/PNG  (libpng, 无损)", ".png", img, 0.5);
    roundTrip("imgcodecs/JPEG (libjpeg-turbo, 有损)", ".jpg", img, 30.0,
              {cv::IMWRITE_JPEG_QUALITY, 95});
    roundTrip("imgcodecs/WebP (libwebp, 有损)", ".webp", img, 30.0,
              {cv::IMWRITE_WEBP_QUALITY, 95});
    roundTrip("imgcodecs/TIFF (自带 libtiff, 无损)", ".tiff", img, 0.5);
    roundTripFile("imgcodecs/JP2  (openjpeg, 文件往返)", "opencv_ohos_probe.jp2", img, 30.0);

    // ── videoio：写出再读回，坐实 ffmpeg 后端真的接上 ───────────────────────
    section("videoio: VideoWriter→VideoCapture 往返（ffmpeg）", [&] {
        const std::string path = "opencv_ohos_probe.avi";
        const int fourcc = cv::VideoWriter::fourcc('M', 'J', 'P', 'G');
        cv::VideoWriter w(path, fourcc, 10.0, img.size(), true);
        if (!w.isOpened()) {
            check(false, "videoio: VideoWriter 打开失败（ffmpeg 后端未接上）");
        } else {
            for (int i = 0; i < 12; ++i) w.write(img);
            w.release();
            cv::VideoCapture c(path);
            bool opened = c.isOpened();
            cv::Mat frame;
            bool got = opened && c.read(frame) && !frame.empty();
            char d[160];
            std::snprintf(d, sizeof(d), "读回帧 %dx%d", got ? frame.cols : 0, got ? frame.rows : 0);
            check(got && frame.cols == img.cols && frame.rows == img.rows,
                  "videoio: VideoWriter→VideoCapture 往返（ffmpeg）", d);
            c.release();
            std::remove(path.c_str());
        }
    });

    // ── dnn：真实前处理调用（该模块链接 vendored protobuf）─────────────────
    section("dnn: blobFromImage", [&] {
        cv::Mat blob = cv::dnn::blobFromImage(img, 1.0 / 255.0, cv::Size(64, 64),
                                              cv::Scalar(0, 0, 0), true, false);
        // NCHW：1×3×64×64
        bool ok = blob.dims == 4 && blob.size[0] == 1 && blob.size[1] == 3 &&
                  blob.size[2] == 64 && blob.size[3] == 64;
        char d[128];
        std::snprintf(d, sizeof(d), "blob dims=%d shape=%dx%dx%dx%d", blob.dims,
                      blob.size[0], blob.size[1], blob.size[2], blob.size[3]);
        check(ok, "dnn: blobFromImage 产出 NCHW blob", d);
    });

    // ── features2d：ORB 在合成图上真的检出特征点 ───────────────────────────
    section("features2d: ORB detectAndCompute", [&] {
        cv::Ptr<cv::ORB> orb = cv::ORB::create(200);
        std::vector<cv::KeyPoint> kps;
        cv::Mat desc;
        orb->detectAndCompute(gray, cv::noArray(), kps, desc);
        char d[96];
        std::snprintf(d, sizeof(d), "检出 %zu 个关键点，描述子 %dx%d", kps.size(), desc.rows, desc.cols);
        check(!kps.empty() && desc.rows == (int)kps.size(), "features2d: ORB detectAndCompute", d);
    });

    // ── calib3d：由已知单应变换的点对反解，校验解回的矩阵接近真值 ───────────
    section("calib3d: findHomography", [&] {
        std::vector<cv::Point2f> src = {{0, 0}, {100, 0}, {100, 100}, {0, 100}, {50, 20}};
        std::vector<cv::Point2f> dst;
        const double sx = 2.0, sy = 3.0, tx = 10.0, ty = -5.0;
        for (const auto &p : src) dst.emplace_back(p.x * sx + tx, p.y * sy + ty);
        cv::Mat H = cv::findHomography(src, dst);
        bool ok = !H.empty() && H.rows == 3 && H.cols == 3;
        if (ok) {
            H /= H.at<double>(2, 2);
            ok = std::abs(H.at<double>(0, 0) - sx) < 1e-6 &&
                 std::abs(H.at<double>(1, 1) - sy) < 1e-6 &&
                 std::abs(H.at<double>(0, 2) - tx) < 1e-6 &&
                 std::abs(H.at<double>(1, 2) - ty) < 1e-6;
        }
        check(ok, "calib3d: findHomography 反解出已知变换");
    });

    // ── gapi：编译并执行一条真实图计算 ─────────────────────────────────────
    section("gapi: GComputation blur", [&] {
        cv::GMat in;
        cv::GMat out = cv::gapi::blur(in, cv::Size(5, 5));
        cv::GComputation comp(cv::GIn(in), cv::GOut(out));
        cv::Mat gout;
        comp.apply(cv::gin(img), cv::gout(gout));
        cv::Mat gdiff;
        bool ok = !gout.empty() && gout.size() == img.size();
        if (ok) {
            cv::absdiff(img, gout, gdiff);
            ok = cv::countNonZero(gdiff.reshape(1)) > 0;
        }
        check(ok, "gapi: GComputation 编译并执行 blur 图");
    });

    std::printf("\n%s：%d 项断言，%d 项失败\n", g_failed ? "结论 FAIL" : "结论 PASS",
                g_total, g_failed);
    return g_failed ? 1 : 0;
}
