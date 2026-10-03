#define _XOPEN_SOURCE 600

// Parse libc wait declarations before final.h exposes HarmonyOS linux/keyboard.h
// macros such as P_ALL.
#include <sys/wait.h>

#include <final/final.h>

#include <cerrno>
#include <chrono>
#include <clocale>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <string>

#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <termios.h>
#include <unistd.h>

#if !defined(__OHOS__) || !defined(__aarch64__)
#error "This consumer test must be compiled for HarmonyOS aarch64"
#endif

namespace
{

constexpr const char* kCjkText = "\xE9\xB8\xBF\xE8\x92\x99";
constexpr const char* kFlowMarker = "OHOS_FINALCUT_UI_FLOW_OK\n";
constexpr auto kFlowTimeout = std::chrono::seconds(15);

void reportChildFailure(const char* message)
{
    const auto length = std::strlen(message);
    (void)::write(STDERR_FILENO, message, length);
    (void)::write(STDERR_FILENO, "\n", 1);
}

int runFinalCutUi()
{
    if (std::setlocale(LC_ALL, "C.UTF-8") == nullptr)
    {
        reportChildFailure("OHOS C.UTF-8 locale is unavailable");
        return 10;
    }

    char program[] = "test_ohos_unicode";
    char* argv[] = {program, nullptr};
    int argc = 1;

    finalcut::FApplication app{argc, argv};
    finalcut::FDialog dialog{&app};
    finalcut::FString title{std::string("HarmonyOS Unicode input: ") + kCjkText};
    dialog.setText(title);
    dialog.setSize(finalcut::FSize{60, 8});

    finalcut::FLineEdit input{&dialog};
    input.setLabelText("Input");
    input.setGeometry(finalcut::FPoint{4, 2}, finalcut::FSize{42, 1});

    finalcut::FButton accept{"&Accept", &dialog};
    accept.setGeometry(finalcut::FPoint{45, 5}, finalcut::FSize{10, 1});
    const auto quitApplication = [] (const auto& application)
    {
        application.quit();
    };
    accept.addCallback("clicked", quitApplication, std::ref(app));

    finalcut::FWidget::setMainWidget(&dialog);
    dialog.show();
    const auto appResult = app.exec();
    if (appResult != EXIT_SUCCESS)
    {
        reportChildFailure("FINAL CUT application returned a failure status");
        return 11;
    }

    const auto entered = input.getText();
    if (entered.getLength() != 2 || entered.toString() != kCjkText)
    {
        reportChildFailure("FINAL CUT did not preserve the typed CJK input");
        return 12;
    }

    (void)::write(STDOUT_FILENO, kFlowMarker, std::strlen(kFlowMarker));
    return EXIT_SUCCESS;
}

bool contains(const std::string& text, const char* needle)
{
    return text.find(needle) != std::string::npos;
}

}  // namespace

int main()
{
    const int master = ::posix_openpt(O_RDWR | O_NOCTTY);
    if (master < 0)
    {
        std::perror("posix_openpt");
        return EXIT_FAILURE;
    }

    if (::grantpt(master) != 0 || ::unlockpt(master) != 0)
    {
        std::perror("grantpt/unlockpt");
        (void)::close(master);
        return EXIT_FAILURE;
    }

    char* slaveName = ::ptsname(master);
    if (slaveName == nullptr)
    {
        std::perror("ptsname");
        (void)::close(master);
        return EXIT_FAILURE;
    }

    winsize terminalSize{};
    terminalSize.ws_row = 24;
    terminalSize.ws_col = 80;
    if (::ioctl(master, TIOCSWINSZ, &terminalSize) != 0)
    {
        std::perror("TIOCSWINSZ");
        (void)::close(master);
        return EXIT_FAILURE;
    }

    const pid_t child = ::fork();
    if (child < 0)
    {
        std::perror("fork");
        (void)::close(master);
        return EXIT_FAILURE;
    }

    if (child == 0)
    {
        (void)::close(master);
        const int slave = ::open(slaveName, O_RDWR | O_NOCTTY);
        if (slave < 0)
        {
            reportChildFailure("could not open PTY slave");
            _exit(20);
        }

        for (int fd = STDIN_FILENO; fd <= STDERR_FILENO; ++fd)
        {
            if (::dup2(slave, fd) < 0)
            {
                reportChildFailure("could not attach FINAL CUT to the PTY");
                _exit(21);
            }
        }
        if (slave > STDERR_FILENO)
            (void)::close(slave);

        (void)::setenv("TERM", "xterm-256color", 1);
        (void)::setenv("LANG", "C.UTF-8", 1);
        (void)::setenv("LC_ALL", "C.UTF-8", 1);
        return runFinalCutUi();
    }

    const int masterFlags = ::fcntl(master, F_GETFL);
    if (masterFlags < 0 || ::fcntl(master, F_SETFL, masterFlags | O_NONBLOCK) != 0)
    {
        std::perror("fcntl(O_NONBLOCK)");
        (void)::kill(child, SIGKILL);
        (void)::waitpid(child, nullptr, 0);
        (void)::close(master);
        return EXIT_FAILURE;
    }

    const std::string renderedTitle = std::string("HarmonyOS Unicode input: ") + kCjkText;
    std::string terminalOutput;
    bool textSent = false;
    bool tabSent = false;
    bool enterSent = false;
    bool timedOut = false;
    int childStatus = 0;
    bool childExited = false;
    const auto start = std::chrono::steady_clock::now();
    auto textSentAt = start;
    auto tabSentAt = start;

    while (!childExited)
    {
        pollfd descriptor{master, POLLIN, 0};
        const int pollResult = ::poll(&descriptor, 1, 100);
        if (pollResult < 0 && errno != EINTR)
        {
            std::perror("poll");
            (void)::kill(child, SIGKILL);
            (void)::waitpid(child, &childStatus, 0);
            (void)::close(master);
            return EXIT_FAILURE;
        }

        if (pollResult > 0 && (descriptor.revents & (POLLIN | POLLHUP | POLLERR)) != 0)
        {
            char buffer[4096];
            const auto count = ::read(master, buffer, sizeof(buffer));
            if (count > 0 && terminalOutput.size() < 1024 * 1024)
                terminalOutput.append(buffer, static_cast<std::size_t>(count));
        }

        const auto now = std::chrono::steady_clock::now();
        if (!textSent && contains(terminalOutput, renderedTitle.c_str())
                      && contains(terminalOutput, "Input"))
        {
            // Send real terminal input in separate steps so the UI event loop
            // processes text, focus traversal, and button activation in order.
            const auto count = ::write(master, kCjkText, std::strlen(kCjkText));
            textSent = count == static_cast<ssize_t>(std::strlen(kCjkText));
            textSentAt = now;
        }
        if (textSent && !tabSent && now - textSentAt >= std::chrono::milliseconds(200))
        {
            const char tab = '\t';
            tabSent = ::write(master, &tab, 1) == 1;
            tabSentAt = now;
        }
        if (tabSent && !enterSent && now - tabSentAt >= std::chrono::milliseconds(200))
        {
            const char enter = '\r';
            enterSent = ::write(master, &enter, 1) == 1;
        }

        const auto waited = ::waitpid(child, &childStatus, WNOHANG);
        if (waited == child)
            childExited = true;
        else if (waited < 0 && errno != EINTR)
        {
            std::perror("waitpid");
            (void)::close(master);
            return EXIT_FAILURE;
        }

        if (!childExited && std::chrono::steady_clock::now() - start > kFlowTimeout)
        {
            timedOut = true;
            (void)::kill(child, SIGKILL);
            (void)::waitpid(child, &childStatus, 0);
            childExited = true;
        }
    }

    // Drain output buffered by the PTY before the child exited.
    char buffer[4096];
    for (;;)
    {
        const auto count = ::read(master, buffer, sizeof(buffer));
        if (count < 0 && errno == EINTR)
            continue;
        if (count <= 0)
            break;
        if (terminalOutput.size() < 1024 * 1024)
            terminalOutput.append(buffer, static_cast<std::size_t>(count));
    }
    (void)::close(master);

    if (timedOut)
    {
        std::fprintf(stderr,
                     "HarmonyOS FINAL CUT UI flow timed out; rendered_title=%d, "
                     "input_label=%d, text_sent=%d, tab_sent=%d, enter_sent=%d, "
                     "captured_bytes=%zu\n",
                     contains(terminalOutput, renderedTitle.c_str()),
                     contains(terminalOutput, "Input"), textSent, tabSent, enterSent,
                     terminalOutput.size());
        const auto diagnosticStart = terminalOutput.size() > 512
                                     ? terminalOutput.size() - 512 : std::size_t{0};
        for (std::size_t index = diagnosticStart; index < terminalOutput.size(); ++index)
        {
            const auto byte = static_cast<unsigned char>(terminalOutput[index]);
            if (byte >= 0x20 && byte <= 0x7e)
                std::fputc(byte, stderr);
            else
                std::fprintf(stderr, "\\x%02x", byte);
        }
        std::fputc('\n', stderr);
        return EXIT_FAILURE;
    }
    if (!enterSent)
    {
        std::fputs("the rendered UI did not receive the complete keyboard sequence\n", stderr);
        return EXIT_FAILURE;
    }
    if (!contains(terminalOutput, kCjkText))
    {
        std::fputs("the terminal output did not contain the rendered CJK text\n", stderr);
        return EXIT_FAILURE;
    }
    if (!contains(terminalOutput, kFlowMarker))
    {
        std::fputs("the UI did not complete the input, activation, and shutdown flow\n", stderr);
        return EXIT_FAILURE;
    }
    if (!WIFEXITED(childStatus) || WEXITSTATUS(childStatus) != EXIT_SUCCESS)
    {
        std::fprintf(stderr, "FINAL CUT UI child exited with status %d\n", childStatus);
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
