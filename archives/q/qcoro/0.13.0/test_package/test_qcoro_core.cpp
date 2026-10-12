// SPDX-License-Identifier: MIT
//
// Consumer smoke test for the packaged QCoro6::Core library.
//
// It exercises the public coroutine API (QCoro::Task + QCoro::waitFor) instead
// of printing a fixed string, so an empty or stub package fails to link/run.

#include <QCoro/QCoroTask>

#include <QCoreApplication>
#include <QDebug>

#include <cstdlib>

static QCoro::Task<int> computeAnswer()
{
    co_return 42;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    const int answer = QCoro::waitFor(computeAnswer());
    qInfo() << "QCoro::waitFor(computeAnswer()) =" << answer;

    return answer == 42 ? EXIT_SUCCESS : EXIT_FAILURE;
}
