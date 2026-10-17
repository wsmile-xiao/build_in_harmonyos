// test_kauth5_ohos.cpp — HarmonyOS-specific test for kauth5 5.116.0.
//
// The recipe pins KAUTH_BACKEND_NAME=FAKE on OHOS (PolkitQt-1 is not published
// to ohpcd and needs a running polkit daemon). This test asserts the
// observable runtime behaviour of that adaptation path, so a regression in the
// backend selection or in BackendsManager would be caught:
//
//   - BackendsManager::init() finds neither a backend nor a helper plugin in
//     the package prefix and falls back to FakeBackend (NoCapability).
//   - Therefore Action(name).status() == DeniedStatus and isValid() is still
//     true (the FAKE backend still answers actionStatus()).
//   - execute() returns a job whose exec() fails with
//     ActionReply::BackendError.
//   - No helper is bound (helperId() stays empty unless set explicitly).
//
// Compiled only for OHOS; fails closed with #error elsewhere.
#ifndef __OHOS__
#error "test_kauth5_ohos.cpp is the HarmonyOS-specific test and must only be built on OHOS"
#endif

#include <iostream>

#include <QCoreApplication>

#include <KAuth/Action>
#include <KAuth/ActionReply>
#include <KAuth/ExecuteJob>
#include <kauth_version.h>

namespace {

int fail(const char *what)
{
    std::cerr << "FAIL: " << what << "\n";
    return 1;
}

} // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // 1. FAKE backend: an action with a well-formed name is still "valid"
    //    (the backend answers actionStatus()), but the status is denied.
    KAuth::Action action(QStringLiteral("org.kde.kf5auth.ohos.test"));
    if (!action.isValid()) {
        return fail("Action with a well-formed name is not valid under the FAKE backend");
    }
    if (action.status() != KAuth::Action::DeniedStatus) {
        return fail("FAKE backend did not report DeniedStatus");
    }

    // 2. An explicitly set helper id round-trips (the FAKE backend binds no
    //    helper, so this is consumer state, not backend state).
    if (!action.helperId().isEmpty()) {
        return fail("helperId() is not empty without setHelperId()");
    }
    action.setHelperId(QStringLiteral("org.kde.kf5auth.ohos.helper"));
    if (action.helperId() != QStringLiteral("org.kde.kf5auth.ohos.helper")) {
        return fail("helperId() round-trip failed");
    }
    if (!action.hasHelper()) {
        return fail("hasHelper() is false after setHelperId()");
    }

    // 3. execute() must fail with BackendError: there is no backend able to
    //    authorize or dispatch the action on OHOS.
    KAuth::ExecuteJob *job = action.execute();
    if (!job) {
        return fail("Action::execute() returned nullptr");
    }
    if (job->exec()) {
        return fail("ExecuteJob::exec() unexpectedly succeeded on OHOS");
    }
    if (job->error() != (int)KAuth::ActionReply::BackendError) {
        std::cerr << "FAIL: expected BackendError, got error() == " << job->error() << "\n";
        return 1;
    }

    // 4. The empty-name action stays invalid regardless of the backend.
    KAuth::Action empty;
    if (empty.isValid()) {
        return fail("default-constructed Action is valid");
    }
    if (empty.status() != KAuth::Action::InvalidStatus) {
        return fail("default-constructed Action status is not InvalidStatus");
    }

    std::cout << "test_kauth5_ohos: PASS (KF5AuthCore " << KAUTH_VERSION_STRING
              << ", FAKE backend fallback verified)\n";
    return 0;
}
