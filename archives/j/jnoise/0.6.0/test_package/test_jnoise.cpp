// jnoise 0.6.0 -- consumer-side verification (R34: this program *executes the
// packaged binary*; upstream ships no test suite, see test_package/MANIFEST.yml).
//
// argv[1] = absolute path of the packaged bin/jnoise.
// Exit code 0 only when all six assertions pass.
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#include <string>
#include <vector>

static int g_pass = 0;
static int g_fail = 0;

static void check(bool ok, const char *id, const char *what, const char *detail)
{
  if (ok) {
    g_pass++;
    printf("[PASS] %s %s%s%s\n", id, what, detail && *detail ? " :: " : "", detail ? detail : "");
  } else {
    g_fail++;
    printf("[FAIL] %s %s%s%s\n", id, what, detail && *detail ? " :: " : "", detail ? detail : "");
  }
}

// Read a whole file with open()/read(): on OpenHarmony stat() is unreliable
// for paths under /storage (it even reports "Permission denied" for
// /bin/install, which nevertheless executes), so probes must not use it.
static bool slurp(const char *path, std::vector<unsigned char> &out)
{
  int fd = open(path, O_RDONLY);
  if (fd < 0)
    return false;
  unsigned char buf[65536];
  ssize_t n;
  bool ok = true;
  while ((n = read(fd, buf, sizeof buf)) > 0)
    out.insert(out.end(), buf, buf + n);
  if (n < 0) {
    ok = false;
    out.clear();
  }
  close(fd);
  return ok;
}

struct RunResult {
  int rc;         // -1 unless the child exited normally
  int sig;        // -1 is used as the "watchdog fired" marker
  std::string out;
};

// Run the packaged binary under a watchdog: once attached to a JACK server
// jnoise loops forever, so an unresponsive child must FAIL, never pass.
static RunResult run_binary(const char *bin, const char *const *args, int timeout_s)
{
  RunResult r;
  r.rc = -1;
  r.sig = 0;

  int pfd[2];
  if (pipe(pfd) != 0) {
    perror("pipe");
    return r;
  }

  pid_t pid = fork();
  if (pid < 0) {
    perror("fork");
    close(pfd[0]);
    close(pfd[1]);
    return r;
  }
  if (pid == 0) {
    close(pfd[0]);
    dup2(pfd[1], STDOUT_FILENO);
    dup2(pfd[1], STDERR_FILENO);
    close(pfd[1]);
    char *argv[8];
    int i = 0;
    argv[i++] = (char *) bin;
    for (int k = 0; args && args[k]; k++)
      argv[i++] = (char *) args[k];
    argv[i] = NULL;
    execv(bin, argv);
    fprintf(stderr, "execv-failed:%s\n", strerror(errno));
    _exit(127);
  }

  close(pfd[1]);
  fcntl(pfd[0], F_SETFL, O_NONBLOCK);

  struct timespec t0, t1;
  clock_gettime(CLOCK_MONOTONIC, &t0);
  bool timed_out = false;
  int status = 0;
  for (;;) {
    char buf[4096];
    ssize_t n;
    while ((n = read(pfd[0], buf, sizeof buf)) > 0)
      r.out.append(buf, (size_t) n);
    if (waitpid(pid, &status, WNOHANG) == pid)
      break;
    clock_gettime(CLOCK_MONOTONIC, &t1);
    if ((t1.tv_sec - t0.tv_sec) > timeout_s) {
      kill(pid, SIGKILL);
      waitpid(pid, &status, 0);
      timed_out = true;
      break;
    }
    struct timespec nap;
    nap.tv_sec = 0;
    nap.tv_nsec = 20 * 1000 * 1000;
    nanosleep(&nap, NULL);
  }
  {
    char buf[4096];
    ssize_t n;
    while ((n = read(pfd[0], buf, sizeof buf)) > 0)
      r.out.append(buf, (size_t) n);
  }
  close(pfd[0]);

  if (timed_out)
    r.sig = -1;
  else if (WIFEXITED(status))
    r.rc = WEXITSTATUS(status);
  else if (WIFSIGNALED(status))
    r.sig = WTERMSIG(status);
  return r;
}

int main(int argc, char **argv)
{
  if (argc < 2) {
    fprintf(stderr, "usage: %s <path-to-packaged-jnoise-binary>\n", argv[0]);
    return 2;
  }
  const char *bin = argv[1];
  std::vector<unsigned char> img;
  char note[512];

  // ---- A1: the packaged artifact is a real aarch64 ELF ------------------
  bool loaded = slurp(bin, img);
  if (!loaded) {
    snprintf(note, sizeof note, "open()/read() failed: %s", strerror(errno));
    check(false, "A1", "packaged binary readable", note);
    printf("RESULT: pass=%d fail=%d\n", g_pass, g_fail);
    return 1;
  }
  bool elf_ok = img.size() > 20 && img[0] == 0x7f && img[1] == 'E' &&
                img[2] == 'L' && img[3] == 'F';
  int emachine = (int) img[18] | ((int) img[19] << 8);
  snprintf(note, sizeof note, "size=%zu e_machine=%d (expect 183 = EM_AARCH64)",
           img.size(), emachine);
  check(elf_ok && emachine == 183, "A1", "packaged binary is an aarch64 ELF", note);

  // ---- A2: it declares a NEEDED entry on libjack -----------------------
  std::string text;
  text.assign((const char *) img.data(), img.size());
  size_t pos = text.find("libjack.so");
  std::string soname;
  if (pos != std::string::npos) {
    size_t end = pos;
    while (end < text.size() && text[end] != '\0' && (end - pos) < 64)
      end++;
    soname = text.substr(pos, end - pos);
  }
  snprintf(note, sizeof note, "runtime dependency string '%s'", soname.c_str());
  check(pos != std::string::npos, "A2", "binary needs libjack at runtime", note);

  // ---- A3: that library really loads and exports the client API ---------
  // Positive control for the runtime layer: if libjack could not be loaded at
  // all, jnoise would die in the dynamic loader instead of printing its own
  // error message, so A3 is what lets A6 be attributed to "no server".
  void *h = soname.empty() ? NULL : dlopen(soname.c_str(), RTLD_NOW | RTLD_LOCAL);
  const char *dlerr = h ? NULL : dlerror();
  void *sym = h ? dlsym(h, "jack_client_open") : NULL;
  snprintf(note, sizeof note, "dlopen(%s) handle=%p jack_client_open=%p err=%s",
           soname.c_str(), h, sym, dlerr ? dlerr : "-");
  check(sym != NULL, "A3", "libjack loads and exports jack_client_open", note);
  if (h)
    dlclose(h);

  // ---- A4: level above the ceiling is rejected --------------------------
  {
    const char *args[] = {"0", NULL};
    RunResult r = run_binary(bin, args, 10);
    snprintf(note, sizeof note, "rc=%d sig=%d output=<%s>", r.rc, r.sig, r.out.c_str());
    check(r.rc == 1 && r.out.find("Level is too high, max = -10dB") != std::string::npos,
          "A4", "jnoise 0 rejected as too loud", note);
  }

  // ---- A5: a non-numeric level parses as 0 dB and is rejected -----------
  {
    const char *args[] = {"abc", NULL};
    RunResult r = run_binary(bin, args, 10);
    snprintf(note, sizeof note, "rc=%d sig=%d output=<%s>", r.rc, r.sig, r.out.c_str());
    check(r.rc == 1 && r.out.find("Level is too high") != std::string::npos,
          "A5", "jnoise abc becomes 0 dB via atof and is rejected", note);
  }

  // ---- A6: the -10 dB boundary is accepted and the JACK path is taken ---
  {
    const char *args[] = {"-10", NULL};
    RunResult r = run_binary(bin, args, 10);
    bool too_high = r.out.find("Level is too high") != std::string::npos;
    snprintf(note, sizeof note, "rc=%d sig=%d(-1 means watchdog) output=<%s>",
             r.rc, r.sig, r.out.c_str());
    check(!too_high && r.rc == 1 &&
          r.out.find("Can't connect to JACK") != std::string::npos,
          "A6", "jnoise -10 passes the level check and reaches jack_client_open", note);
  }

  printf("RESULT: pass=%d fail=%d\n", g_pass, g_fail);
  return (g_fail == 0 && g_pass == 6) ? 0 : 1;
}
