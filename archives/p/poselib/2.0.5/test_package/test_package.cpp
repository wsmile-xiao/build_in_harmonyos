// test_package.cpp — poselib 2.0.5 consumer test (R34: substantive tests)
//
// Links against the packaged libPoseLib.a and verifies real solver behaviour
// on synthetic ground-truth data:
//   1. poselib_info() reports the library version string
//   2. P3P: synthetic 3-point pose problem — builds a known camera pose
//      (rotation + translation), back-projects 3 camera-frame points (positive
//      depth) into the world frame, solves p3p() and asserts that one of the
//      returned solutions reproduces the ground-truth pose to < 1e-6
//      (translation norm) and < 1e-6 degrees (rotation angle error)
//   3. homography_4pt: synthetic planar 4-point correspondences generated
//      from a known H — asserts the solver recovers H (up to scale) to < 1e-9
#include <PoseLib/poselib.h>  // umbrella header (all public headers)
#include <PoseLib/camera_pose.h>
#include <PoseLib/solvers/homography_4pt.h>
#include <PoseLib/solvers/p3p.h>

#include <Eigen/Dense>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static Eigen::Matrix3d rotation_axis(double ax, double ay, double az, double theta) {
    Eigen::Vector3d a(ax, ay, az);
    a.normalize();
    return Eigen::AngleAxisd(theta, a).toRotationMatrix();
}

int main() {
    int failures = 0;

    // ---------- 1. poselib_info() version string ----------
    // NOTE: upstream tag is v2.0.5 but project(PoseLib VERSION 2.0.4), so the
    // generated version.h reports "2.0.4" — upstream inconsistency, kept
    // as-is (see notes.md); the conan package version is 2.0.5 (R37: tag).
    const std::string info = poselib_info();
    if (info.find("PoseLib") == std::string::npos ||
        info.find("2.0.4") == std::string::npos ||
        info.find("RELEASE") == std::string::npos) {
        std::printf("[FAIL] poselib_info() unexpected: '%s'\n", info.c_str());
        ++failures;
    } else {
        std::printf("[PASS] poselib_info(): %s\n", info.c_str());
    }

    // ---------- 2. P3P synthetic pose recovery ----------
    {
        const Eigen::Matrix3d R_true = rotation_axis(0.3, -0.7, 0.6, 0.85);
        const Eigen::Vector3d t_true(0.4, -1.2, 0.9);

        // Camera-frame points with strictly positive depth (2.5 .. 4.0)
        const std::vector<Eigen::Vector3d> xc = {
            Eigen::Vector3d(0.2, 0.1, 3.0),
            Eigen::Vector3d(-0.5, 0.4, 4.0),
            Eigen::Vector3d(0.7, -0.3, 2.5),
        };

        // World points: xc = R*X + t  =>  X = R^T * (xc - t)
        std::vector<Eigen::Vector3d> X;
        // Image observations as UNIT-LENGTH bearing vectors (README: "the
        // image points are represented as unit-length bearings vectors";
        // upstream estimators call x.homogeneous().normalized())
        std::vector<Eigen::Vector3d> x;
        for (const Eigen::Vector3d &p : xc) {
            X.push_back(R_true.transpose() * (p - t_true));
            x.push_back(p.normalized());
        }

        std::vector<poselib::CameraPose> solutions;
        const int n = poselib::p3p(x, X, &solutions);
        if (n <= 0) {
            std::printf("[FAIL] p3p returned %d solutions (expected >= 1)\n", n);
            ++failures;
        } else {
            bool matched = false;
            double best_trans = 1e9, best_rot_deg = 1e9;
            for (const poselib::CameraPose &sol : solutions) {
                const double trans_err = (sol.t - t_true).norm();
                const Eigen::Matrix3d Rrel = sol.R() * R_true.transpose();
                double c = (Rrel.trace() - 1.0) / 2.0;
                c = std::max(-1.0, std::min(1.0, c));
                const double rot_err_deg = std::acos(c) * 180.0 / M_PI;
                if (trans_err < best_trans) {
                    best_trans = trans_err;
                    best_rot_deg = rot_err_deg;
                }
                if (trans_err < 1e-6 && rot_err_deg < 1e-6) {
                    matched = true;
                    break;
                }
            }
            if (matched) {
                std::printf("[PASS] p3p recovered ground-truth pose among %d solutions "
                            "(trans err < 1e-6, rot err < 1e-6 deg)\n", n);
            } else {
                std::printf("[FAIL] p3p: no solution matches ground truth; best trans=%.3e, rot=%.3e deg\n",
                            best_trans, best_rot_deg);
                ++failures;
            }
        }
    }

    // ---------- 3. homography_4pt synthetic recovery ----------
    {
        // Planar points (z = 1 homogeneous); H_true keeps z strictly positive
        const std::vector<Eigen::Vector3d> x1 = {
            Eigen::Vector3d(0.0, 0.0, 1.0),
            Eigen::Vector3d(1.0, 0.0, 1.0),
            Eigen::Vector3d(1.0, 1.0, 1.0),
            Eigen::Vector3d(0.0, 1.0, 1.0),
        };
        Eigen::Matrix3d H_true;
        H_true << 1.2, 0.1, 0.3,
                 -0.05, 0.9, 0.2,
                  0.001, -0.002, 1.0;

        std::vector<Eigen::Vector3d> x2;
        for (const Eigen::Vector3d &p : x1) {
            Eigen::Vector3d q = H_true * p;
            q /= q.z();
            x2.push_back(q);
        }

        Eigen::Matrix3d H;
        const int ok = poselib::homography_4pt(x1, x2, &H);
        if (ok != 1) {
            std::printf("[FAIL] homography_4pt returned %d (expected 1)\n", ok);
            ++failures;
        } else {
            // H is defined up to scale — normalize by H(2,2) before comparing
            const Eigen::Matrix3d Hn = H / H(2, 2);
            const Eigen::Matrix3d Htn = H_true / H_true(2, 2);
            const double err = (Hn - Htn).norm();
            if (err < 1e-9) {
                std::printf("[PASS] homography_4pt recovered H up to scale (err %.3e < 1e-9)\n", err);
            } else {
                std::printf("[FAIL] homography_4pt normalized error %.3e >= 1e-9\n", err);
                ++failures;
            }
        }
    }

    if (failures == 0) {
        std::printf("HMBS_TEST_PACKAGE_RESULT: PASS (poselib consumer: poselib_info + p3p pose recovery + homography_4pt)\n");
        return 0;
    }
    std::printf("HMBS_TEST_PACKAGE_RESULT: FAIL (%d test(s) failed)\n", failures);
    return 1;
}
