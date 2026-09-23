/*
 * OHOS 专项测试: geographiclib 2.7 — Geodesic 库 API 消费验证
 *
 * 本测试为 HarmonyOS 平台专项用例(非复述上游测试):
 *   1. 链接真实 libGeographicLib, 调用 Geodesic::WGS84().Inverse() 计算
 *      (0,0) -> (0,1) 的 WGS84 测地线距离;
 *   2. 与独立参考值 111319.49079327 m 比对(该值由上游 GeodSolve -p 8
 *      实测取得, 相对误差 < 1e-12);
 *   3. 校验 DMS/GeoCoords 头文件可编译链接(消费者视角 include 可用)。
 */
#include <cmath>
#include <cstdio>
#include <GeographicLib/Geodesic.hpp>
#include <GeographicLib/GeoCoords.hpp>

int main() {
    using namespace GeographicLib;
    double lat1 = 0, lon1 = 0, lat2 = 0, lon2 = 1;
    double s12 = 0, azi1 = 0, azi2 = 0;
    Geodesic::WGS84().Inverse(lat1, lon1, lat2, lon2, s12, azi1, azi2);

    const double expected = 111319.4907932736;  // GeodSolve -p 8 参考值
    double rel = std::fabs(s12 - expected) / expected;
    std::printf("geodesic (0,0)->(0,1): s12=%.12f azi1=%.6f azi2=%.6f rel_err=%.3e\n",
                s12, azi1, azi2, rel);
    if (rel > 1e-9) {
        std::printf("FAIL: geodesic distance mismatch (rel_err=%.3e)\n", rel);
        return 1;
    }

    // 额外消费验证: GeoCoords 坐标解析 (消费者视角 include/链接均可用)
    GeoCoords c("38SMB4484");
    std::printf("GeoCoords MGRS 38SMB4484 -> lat=%.6f lon=%.6f\n", c.Latitude(), c.Longitude());
    if (!(std::fabs(c.Latitude() - 33.3) < 0.01 && std::fabs(c.Longitude() - 44.4) < 0.01)) {
        std::printf("FAIL: GeoCoords parse mismatch\n");
        return 1;
    }

    std::printf("PASS: geographiclib 2.7 OHOS consumer test OK\n");
    return 0;
}
