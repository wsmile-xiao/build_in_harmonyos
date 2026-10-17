#include <QGLViewer/qglviewer.h>
#include <QApplication>
#include <cmath>
#include <cstdio>

int main(int argc, char **argv) {
    QApplication application(argc, argv);
    QGLViewer viewer;
    if (viewer.camera() == nullptr)
        return 2;
    const qglviewer::Vec axis(1.0, 2.0, 3.0);
    const qglviewer::Vec other = axis.orthogonalVec();
    if (other.squaredNorm() < 0.1 || std::fabs(axis * other) > 1e-8)
        return 1;
    std::puts("CONSUMER_1_OF_1_PASS");
    return 0;
}
