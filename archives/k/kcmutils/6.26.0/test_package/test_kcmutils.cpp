// kcmutils 6.26.0 consumer test (R34: exercises real API).
// Constructs a KCModuleData through KF6::KCMUtilsCore and checks the
// default-relevance query path. The forwarding header is reached through
// the target's INTERFACE_INCLUDE_DIRECTORIES (include/KF6/KCMUtilsCore).
#include <KCModuleData>

#include <QApplication>

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    KCModuleData data;
    return data.isRelevant() ? 0 : 1;
}
