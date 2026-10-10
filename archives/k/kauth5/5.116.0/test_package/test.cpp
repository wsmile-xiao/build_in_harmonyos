// test.cpp — kauth5 5.116.0 test_package consumer (R34: must call the tested
// package's API, not just print).
//
// Exercises the installed KF5AuthCore public API the way an application does:
// construct a KAuth::Action, inspect its name/details/status/validity, set
// arguments and read them back, and run an ExecuteJob through the FAKE
// backend that this package is built with. With the FAKE backend the backend
// reports NoCapability -> Action::DeniedStatus and execute() fails with
// KAuth::ActionReply::BackendError, which is the documented behaviour of that
// backend, so the assertions below are stable on OHOS.
#include <iostream>

#include <QCoreApplication>
#include <QVariantMap>

#include <KAuth/Action>
#include <KAuth/ActionReply>
#include <KAuth/ExecuteJob>
#include <kauth_version.h>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // 1. Construction + name round-trip.
    KAuth::Action::DetailsMap details;
    details.insert(KAuth::Action::AuthDetail::DetailOther, QStringLiteral("details"));
    KAuth::Action action(QStringLiteral("org.kde.kf5auth.testpackage"), details);
    if (action.name() != QStringLiteral("org.kde.kf5auth.testpackage")) {
        std::cerr << "FAIL: Action::name() mismatch\n";
        return 1;
    }

    // 2. Details round-trip (setDetailsV2 / detailsV2).
    if (action.detailsV2() != details) {
        std::cerr << "FAIL: Action::detailsV2() mismatch\n";
        return 1;
    }

    // 3. Arguments round-trip (setArguments / arguments).
    QVariantMap args;
    args.insert(QStringLiteral("answer"), 42);
    args.insert(QStringLiteral("path"), QStringLiteral("/tmp/x"));
    action.setArguments(args);
    if (action.arguments() != args) {
        std::cerr << "FAIL: Action::setArguments/arguments round-trip mismatch\n";
        return 1;
    }
    if (action.arguments().value(QStringLiteral("answer")).toInt() != 42) {
        std::cerr << "FAIL: Action::arguments() value mismatch\n";
        return 1;
    }

    // 4. Helper id round-trip.
    action.setHelperId(QStringLiteral("org.kde.kf5auth.testpackage"));
    if (action.helperId() != QStringLiteral("org.kde.kf5auth.testpackage")) {
        std::cerr << "FAIL: Action::setHelperId/helperId round-trip mismatch\n";
        return 1;
    }

    // 5. An empty-name action is invalid.
    KAuth::Action invalidAction;
    if (invalidAction.isValid()) {
        std::cerr << "FAIL: default-constructed Action reports isValid()\n";
        return 1;
    }

    // 6. With the FAKE backend (KAUTH_BACKEND_NAME=FAKE) every action is
    //    denied, and executing it reports BackendError via the ExecuteJob.
    if (action.status() != KAuth::Action::DeniedStatus) {
        std::cerr << "FAIL: FAKE backend action status is not DeniedStatus\n";
        return 1;
    }
    KAuth::ExecuteJob *job = action.execute();
    if (!job) {
        std::cerr << "FAIL: Action::execute() returned nullptr\n";
        return 1;
    }
    if (job->exec()) {
        std::cerr << "FAIL: ExecuteJob::exec() succeeded with the FAKE backend\n";
        return 1;
    }
    if (job->error() != (int)KAuth::ActionReply::BackendError) {
        std::cerr << "FAIL: ExecuteJob error is not BackendError (got "
                  << job->error() << ")\n";
        return 1;
    }
    // The FAKE backend never dispatches to a helper, so the job carries no
    // result data (upstream SetupActionTest asserts the same: data().isEmpty()).
    if (!job->data().isEmpty()) {
        std::cerr << "FAIL: ExecuteJob::data() is not empty with the FAKE backend\n";
        return 1;
    }

    // 7. ActionReply factory helpers are usable from a consumer.
    const KAuth::ActionReply denied = KAuth::ActionReply::AuthorizationDeniedReply();
    if (denied.errorCode() != KAuth::ActionReply::AuthorizationDeniedError) {
        std::cerr << "FAIL: ActionReply::AuthorizationDeniedReply() errorCode\n";
        return 1;
    }

    std::cout << "kauth5 test_package OK (KF5AuthCore " << KAUTH_VERSION_STRING
              << ")\n";
    return 0;
}
