// ---------------------------------------------------------------------------
// libguytools2 consumer functional test — conan test_package (CI level L1)
//
// Upstream ships no test suite at all: the release tarball (tools-2.1.0.tar.gz)
// contains no tests/ directory, no test_*.cpp and no check/test target in
// tools.pro (Debian's debian/rules builds only).  This file therefore drives
// the *packaged* library through its public API with real inputs (files on
// disk, real signals, real uname()/ioctl queries) and verifies the real
// results.  A broken package - missing symbol, wrong/ mismatched build, broken
// configuration parser, mis-packaged headers - makes `conan create` fail here
// instead of passing silently.
//
// Covered modules and the behaviour that is actually exercised:
//
//   ToolError     registry lifecycle (init/de-init, not-initialised, duplicate),
//                 message lookup + errno translation, ToolErrorCheck() logging,
//                 and the unregistered-code behaviour introduced by
//                 patches/0001 (regression guard for the OHOS port)
//   t_Log         real log file on disk, per-level routing (Debug/Info/Error),
//                 printf formatting, version string, singleton semantics and
//                 the open/close markers written by the ctor/dtor
//   ToolSysInfo   uname() result cross-checked field by field against the OS,
//                 MAC address cross-checked between AddrVal[] and AddrStr[]
//                 (this is the net/if.h ioctl path fixed by patches/0003)
//   ToolCfg       real SECTION/ENDSECTION parsing of every parameter type
//                 (STRING/INTEGER/DOUBLE/PRESENCE/SET/HMS), command-line
//                 options and their priority over the configuration file,
//                 template generation, and the documented error paths
//                 (wrong type, out of range, unknown keyword, unknown section,
//                 missing mandatory parameter, missing file)
//   ToolSignal    real SIGHUP/SIGTERM round trip through the guard thread,
//                 including the threading model (handler runs in the guard
//                 thread, not in main)
//   HarmonyOS     platform-specific behaviour (uname identity, TMPDIR
//                 contract, OHOS file system I/O, MAC enumeration); reported
//                 as one SKIP when the test does not run on HarmonyOS
//
// Every check verifies an observable result of a real call; main() returns the
// number of failures, so any regression fails the build.
// ---------------------------------------------------------------------------

#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <sys/utsname.h>
#include <unistd.h>

// toolsysinfo.h exposes QString in its public API without including it
// upstream, so consumers have to pull in the QtCore header themselves.
#include <qstring.h>

#include "tooltypes.h"
#include "toolglobalid.h"
#include "toolerror.h"
#include "toollog.h"
#include "toolcfg.h"
#include "toolsignal.h"
#include "toolsysinfo.h"

// ----------------------------------------------------------------- test driver

static int gPassed  = 0;
static int gFailed  = 0;
static int gSkipped = 0;

static void Check (bool Condition, const char *pName, const char *pDetail = "")
{
   if (Condition)
   {
      printf ("  PASS  %s\n", pName);
      gPassed++;
   }
   else
   {
      printf ("  FAIL  %s%s%s\n", pName, pDetail[0] ? "   -- " : "", pDetail);
      gFailed++;
   }
}

static void Skip (const char *pName, const char *pReason)
{
   printf ("  SKIP  %s   (%s)\n", pName, pReason);
   gSkipped++;
}

static void Section (const char *pName)
{
   printf ("\n=== %s\n", pName);
}

// Temporary directory: honour TMPDIR (exported by the OHOS platform) with a
// portable fallback, so the suite runs on any worker.
static std::string TempDir ()
{
   const char *pTmp = getenv ("TMPDIR");
   if (pTmp != nullptr && pTmp[0] != '\0')
      return std::string (pTmp);
   return std::string ("/tmp");
}

static std::string JoinPath (const std::string &Dir, const char *pName)
{
   return Dir + "/" + pName;
}

static bool WriteFile (const std::string &Path, const std::string &Text)
{
   FILE *pFile = fopen (Path.c_str (), "wb");
   if (pFile == nullptr)
      return false;
   bool Ok = (fwrite (Text.data (), 1, Text.size (), pFile) == Text.size ());
   Ok = (fclose (pFile) == 0) && Ok;
   return Ok;
}

static std::string ReadFile (const std::string &Path)
{
   std::string Content;
   FILE *pFile = fopen (Path.c_str (), "rb");
   if (pFile == nullptr)
      return Content;
   char Buff[4096];
   size_t Rd;
   while ((Rd = fread (Buff, 1, sizeof (Buff), pFile)) > 0)
      Content.append (Buff, Rd);
   fclose (pFile);
   return Content;
}

// Returns the first line of Path that contains pNeedle (empty when absent).
static std::string LineWith (const std::string &Path, const char *pNeedle)
{
   FILE *pFile = fopen (Path.c_str (), "r");
   if (pFile == nullptr)
      return std::string ();
   char Line[2048];
   std::string Found;
   while (fgets (Line, sizeof (Line), pFile) != nullptr)
   {
      if (strstr (Line, pNeedle) != nullptr)
      {
         Found = Line;
         break;
      }
   }
   fclose (pFile);
   return Found;
}

static std::string Replace (std::string Text, const std::string &From, const std::string &To)
{
   size_t Pos = Text.find (From);
   if (Pos != std::string::npos)
      Text.replace (Pos, From.size (), To);
   return Text;
}

// ===========================================================================
// 1. ToolError — error registry (including the behaviour fixed by patch 0001)
// ===========================================================================

static int  gErrorLogCalls = 0;
static char gErrorLogLast[512] = "";

static void TestErrorLogFn (const char * /*pFileName*/, const char * /*pFunctionName*/,
                            int /*LineNr*/, const char *pFormat, va_list pArguments)
{
   gErrorLogCalls++;
   vsnprintf (gErrorLogLast, sizeof (gErrorLogLast), pFormat, pArguments);
}

static const int TEST_ERROR_OK   = ERROR_BASE_TOOL_ERROR + 500;   // registered
static const int TEST_ERROR_GONE = ERROR_BASE_TOOL_ERROR + 501;   // never registered

static void TestError (void)
{
   Section ("1. ToolError — error registry");

   const char *pMessage = (const char *) 1;
   APIRET rc = ToolErrorGetMessage (TEST_ERROR_GONE, &pMessage);
   Check (rc == TOOL_ERROR_ENTRY_NOT_FOUND && pMessage == nullptr,
          "unregistered code -> TOOL_ERROR_ENTRY_NOT_FOUND and a NULL message",
          pMessage ? pMessage : "");

   // Before ToolErrorInit() the registry does not exist.
   Check (ToolErrorRegisterError (TEST_ERROR_OK, "too early") == TOOL_ERROR_NOT_INITIALISED,
          "ToolErrorRegisterError() before ToolErrorInit() -> TOOL_ERROR_NOT_INITIALISED");

   Check (ToolErrorInit (64) == NO_ERROR, "ToolErrorInit(64) -> NO_ERROR");
   Check (ToolErrorInit (64) == TOOL_ERROR_ALREADY_INITIALISED,
          "second ToolErrorInit() -> TOOL_ERROR_ALREADY_INITIALISED");
   Check (ToolErrorSetLogFn (TestErrorLogFn) == NO_ERROR, "ToolErrorSetLogFn() accepted");

   Check (ToolErrorRegisterError (TEST_ERROR_OK, "libguytools2 functional test error") == NO_ERROR,
          "ToolErrorRegisterError() registers a new code");

   pMessage = nullptr;
   rc = ToolErrorGetMessage (TEST_ERROR_OK, &pMessage);
   Check (rc == NO_ERROR && pMessage != nullptr &&
          strcmp (pMessage, "libguytools2 functional test error") == 0,
          "ToolErrorGetMessage() returns the registered text", pMessage ? pMessage : "()");

   Check (ToolErrorRegisterError (TEST_ERROR_OK, "duplicate") == TOOL_ERROR_DUPLICATE_ENTRY,
          "duplicate ToolErrorRegisterError() -> TOOL_ERROR_DUPLICATE_ENTRY");
   Check (strcmp (ToolErrorMessage (TEST_ERROR_OK), "libguytools2 functional test error") == 0,
          "rejected duplicate does not overwrite the registered text");

   // Patch 0001: unregistered codes must be reported, and a NULL ppMsg must be
   // tolerated instead of dereferencing the null pointer.
   pMessage = (const char *) 1;
   rc = ToolErrorGetMessage (TEST_ERROR_GONE, &pMessage);
   Check (rc == TOOL_ERROR_ENTRY_NOT_FOUND && pMessage == nullptr,
          "[patch 0001] unregistered code -> TOOL_ERROR_ENTRY_NOT_FOUND, message cleared");
   rc = ToolErrorGetMessage (TEST_ERROR_GONE, nullptr);
   Check (rc == TOOL_ERROR_ENTRY_NOT_FOUND,
          "[patch 0001] ToolErrorGetMessage(code, NULL) survives the call");

   Check (strcmp (ToolErrorMessage (NO_ERROR), "NO_ERROR") == 0,
          "ToolErrorMessage(NO_ERROR) -> \"NO_ERROR\"");
   Check (strcmp (ToolErrorMessage (TEST_ERROR_GONE), "[100501]") == 0,
          "ToolErrorMessage(unregistered) -> \"[<code>]\" via the patched path",
          ToolErrorMessage (TEST_ERROR_GONE));

   Check (strcmp (ToolErrorTranslateErrno (ENOENT), "No such file or directory") == 0,
          "ToolErrorTranslateErrno(ENOENT) -> \"No such file or directory\"");
   Check (strcmp (ToolErrorTranslateErrno (EACCES), "Permission denied") == 0,
          "ToolErrorTranslateErrno(EACCES) -> \"Permission denied\"");
   Check (strstr (ToolErrorTranslateErrno (9999), "None of the standard error codes") != nullptr,
          "ToolErrorTranslateErrno(unknown) -> documented fallback text");

   // ToolErrorCheck() returns NO_ERROR by design but must log through the
   // registered log function.
   gErrorLogCalls = 0;
   rc = ToolErrorCheck (__FFL__, TEST_ERROR_OK);
   Check (rc == NO_ERROR && gErrorLogCalls == 1 &&
          strstr (gErrorLogLast, "libguytools2 functional test error") != nullptr,
          "ToolErrorCheck(registered) logs \"Error <code>: <text>\"", gErrorLogLast);
   gErrorLogCalls = 0;
   rc = ToolErrorCheck (__FFL__, TEST_ERROR_GONE);
   Check (rc == NO_ERROR && gErrorLogCalls == 1 &&
          strstr (gErrorLogLast, "unregistered error code") != nullptr,
          "ToolErrorCheck(unregistered) logs the unregistered-code notice", gErrorLogLast);
   gErrorLogCalls = 0;
   ToolErrorLog (__FFL__, "value=%d/%s", 7, "text");
   Check (gErrorLogCalls == 1 && strcmp (gErrorLogLast, "value=7/text") == 0,
          "ToolErrorLog() forwards printf formatting to the log function", gErrorLogLast);

   // The registry stays alive for the sibling modules: their Init() registers
   // their error codes through ToolErrorRegisterError().
}

// ===========================================================================
// 2. t_Log — logging facility (real file on disk)
// ===========================================================================

static void TestLog (void)
{
   Section ("2. t_Log — logging facility");

   const std::string LogPath   = JoinPath (TempDir (), "libguytools2-functional.log");
   const std::string OtherPath = JoinPath (TempDir (), "libguytools2-rejected.log");
   unlink (LogPath.c_str ());
   unlink (OtherPath.c_str ());

   Check (!t_Log::IsInitialised (), "t_Log::IsInitialised() is false before construction");

   const char *pVersion = nullptr;
   t_Log::GetLibGuyToolsVersion (&pVersion);
   Check (pVersion != nullptr && strcmp (pVersion, EXPECTED_VERSION) == 0,
          "t_Log::GetLibGuyToolsVersion() reports the version the package claims "
          "(EXPECTED_VERSION=" EXPECTED_VERSION ")", pVersion ? pVersion : "()");

   APIRET rc = NO_ERROR;
   t_Log *pLog = new t_Log (LogPath.c_str (), rc);
   Check (rc == NO_ERROR && t_Log::IsInitialised (), "t_Log construction reports NO_ERROR");

   // The ctor itself logs "Log file opened" -> the file must exist on disk.
   Check (strstr (ReadFile (LogPath).c_str (), "Log file opened") != nullptr,
          "the log file is created on disk and carries the open marker");

   LOG_DEBUG ("marker-debug %d", 1);
   LOG_INFO  ("marker-info %d", 2);
   LOG_ERROR ("marker-error %d", 3);
   t_Log::Entry (t_Log::Info, __FFL__, "marker-version %s", pVersion);

   std::string Line = LineWith (LogPath, "marker-debug 1");
   Check (!Line.empty () && Line.find ("Debug - ") != std::string::npos,
          "LOG_DEBUG entry routed with the Debug level tag", Line.c_str ());
   Line = LineWith (LogPath, "marker-info 2");
   Check (!Line.empty () && Line.find ("Info  - ") != std::string::npos,
          "LOG_INFO entry routed with the Info level tag", Line.c_str ());
   Line = LineWith (LogPath, "marker-error 3");
   Check (!Line.empty () && Line.find ("Error - ") != std::string::npos,
          "LOG_ERROR entry routed with the Error level tag", Line.c_str ());
   Line = LineWith (LogPath, "marker-version");
   Check (!Line.empty () && Line.find (EXPECTED_VERSION) != std::string::npos,
          "printf formatting and the version string reach the log file", Line.c_str ());
   Line = LineWith (LogPath, "marker-info 2");
   Check (Line.find ("test_libguytools2.cpp") != std::string::npos,
          "log entries carry file/function/line information", Line.c_str ());

   // Singleton semantics: the second instance is rejected and must not touch
   // the state of the first one (deleting it would tear that state down).
   APIRET rcSecond = NO_ERROR;
   t_Log *pLogSecond = new t_Log (OtherPath.c_str (), rcSecond);
   Check (rcSecond == t_Log::TOOLLOG_ERROR_INITIALISED_TWICE,
          "second t_Log construction -> TOOLLOG_ERROR_INITIALISED_TWICE");
   Check (t_Log::IsInitialised (), "the rejected instance leaves the first one initialised");
   Check (access (OtherPath.c_str (), F_OK) != 0,
          "the rejected instance does not open its own log file");
   (void) pLogSecond;   // deliberately not deleted, see comment above

   delete pLog;
   Check (!t_Log::IsInitialised (), "t_Log::IsInitialised() is false after destruction");
   Check (strstr (ReadFile (LogPath).c_str (), "Log file closed") != nullptr,
          "the destructor writes the close marker to the log file");
   unlink (LogPath.c_str ());
   unlink (OtherPath.c_str ());
}

// ===========================================================================
// 3. ToolSysInfo — system information (cross-checked against the OS)
// ===========================================================================

static void TestSysInfo (void)
{
   Section ("3. ToolSysInfo — system information");

   Check (ToolSysInfoInit () == NO_ERROR, "ToolSysInfoInit() -> NO_ERROR");
   Check (ToolSysInfoInit () == (APIRET) TOOLSYSINFO_ALREADY_INITIALISED,
          "second ToolSysInfoInit() -> TOOLSYSINFO_ALREADY_INITIALISED");

   QString Uname;
   APIRET rc = ToolSysInfoUname (Uname);
   std::string U = (rc == NO_ERROR) ? std::string (Uname.toUtf8 ().constData ()) : std::string ();
   Check (rc == NO_ERROR && !U.empty (), "ToolSysInfoUname() returns a non-empty result", U.c_str ());

   // Cross-check the library result against the real uname() syscall.
   struct utsname SysInfo;
   memset (&SysInfo, 0, sizeof (SysInfo));
   Check (uname (&SysInfo) == 0, "uname(2) available for the cross-check");
   Check (U.find (SysInfo.sysname) != std::string::npos,
          "Uname() contains the real sysname", SysInfo.sysname);
   Check (U.find (SysInfo.release) != std::string::npos,
          "Uname() contains the real kernel release", SysInfo.release);
   Check (U.find (SysInfo.machine) != std::string::npos,
          "Uname() contains the real machine architecture", SysInfo.machine);
   Check (U.find (SysInfo.nodename) != std::string::npos,
          "Uname() contains the real host name", SysInfo.nodename);

   t_ToolSysInfoMacAddr MacAddr;
   memset (&MacAddr, 0, sizeof (MacAddr));
   rc = ToolSysInfoGetMacAddr (&MacAddr);
   Check (rc == NO_ERROR || rc == (APIRET) TOOLSYSINFO_ERROR_NO_ADDR,
          "ToolSysInfoGetMacAddr() -> NO_ERROR or TOOLSYSINFO_ERROR_NO_ADDR");
   if (rc == NO_ERROR)
   {
      // Cross-check the string representation against the raw bytes.
      char Expected[TOOLSYSINFO_MACADDRLEN_STR + 1];
      for (int i = 0; i < TOOLSYSINFO_MACADDRLEN_VAL; i++)
         snprintf (&Expected[2 * i], 3, "%02X", MacAddr.AddrVal[i]);
      Expected[TOOLSYSINFO_MACADDRLEN_STR] = '\0';
      Check (strcmp (MacAddr.AddrStr, Expected) == 0 && strlen (MacAddr.AddrStr) == TOOLSYSINFO_MACADDRLEN_STR,
            "AddrStr matches AddrVal (12 hex digits, NUL terminated)", MacAddr.AddrStr);
   }
   else
   {
      Skip ("MAC address format", "no hardware address on this host");
   }

   Check (ToolSysInfoDeInit () == NO_ERROR, "ToolSysInfoDeInit() -> NO_ERROR");
}

// ===========================================================================
// 4. ToolCfg — configuration file and command line parser
// ===========================================================================

static char gCfgLog[16384] = "";

static void TestCfgLogFn (t_pcchar /*pFileName*/, t_pcchar /*pFunction*/, t_int /*LineNr*/,
                          t_pcchar pFormat, va_list pArguments)
{
   char Buff[512];
   vsnprintf (Buff, sizeof (Buff), pFormat, pArguments);
   size_t Len = strlen (gCfgLog);
   if (Len + strlen (Buff) + 4 < sizeof (gCfgLog))
   {
      strcpy (&gCfgLog[Len], Buff);
      strcat (gCfgLog, " | ");
   }
}

// One SECTION with every supported parameter type.  Note the upstream syntax:
// SECTION/ENDSECTION, single-quoted strings, PRESENCE parameters carry no value.
static const char *CFG_SECTION =
   "SECTION Global\n"
   "   StringParam   = 'hello-world'\n"
   "   IntParam      = 42\n"
   "   DoubleParam   = 3.5\n"
   "   PresenceParam\n"
   "   SetParam      = on\n"
   "   HmsParam      = 01:02:03\n"
   "ENDSECTION\n";

static const t_pcchar CFG_SECTION_OTHER = (t_pcchar) "SECTION Other\n"
   "   StringParam   = 'other-world'\n"
   "   IntParam      = 99\n"
   "   DoubleParam   = 7.25\n"
   "   PresenceParam\n"
   "   SetParam      = off\n"
   "   HmsParam      = 00:00:10\n"
   "ENDSECTION\n";

static void TestCfg (void)
{
   Section ("4. ToolCfg — configuration and command line parser");

   const std::string CfgPath = JoinPath (TempDir (), "libguytools2-functional.cfg");
   const std::string TplPath = JoinPath (TempDir (), "libguytools2-template.cfg");
   unlink (TplPath.c_str ());

   // --- command line (scanned before the configuration file) ---------------
   Check (ToolCfgInit (0, nullptr) == NO_ERROR, "ToolCfgInit() -> NO_ERROR");
   const char *pArgv[] = { "test_libguytools2",
                           "CmdOnlyParam='cli-cmd-value'",
                           "LoggingParam='on'",
                           "BothParam='cli-both-value'",
                           "Both2Param='cli-both2-value'",
                           nullptr };
   Check (ToolCfgUseAdjustedCommandLine (5, (char **) pArgv) == NO_ERROR,
          "ToolCfgUseAdjustedCommandLine() accepted");
   Check (ToolCfgSetLogFn (TestCfgLogFn) == NO_ERROR, "ToolCfgSetLogFn() accepted");

   const char *pValue = nullptr;
   APIRET rc = ToolCfgGetCmdLineOption ((t_pcchar) "LoggingParam", &pValue);
   Check (rc == NO_ERROR && pValue != nullptr && strcmp (pValue, "'on'") == 0,
          "ToolCfgGetCmdLineOption() returns the raw command line value", pValue ? pValue : "()");
   Check (ToolCfgGetCmdLineOption ((t_pcchar) "NoSuchOption", &pValue) ==
          TOOLCFG_ERROR_CMDLINE_OPTION_NOT_FOUND,
          "ToolCfgGetCmdLineOption() unknown option -> TOOLCFG_ERROR_CMDLINE_OPTION_NOT_FOUND");

   // --- parameter table ----------------------------------------------------
   t_char   StringBuf[64]    = "";
   t_int    IntValue         = 0;
   t_double DoubleValue      = 0.0;
   t_int    PresenceValue    = 0;
   t_int    SetValue         = -1;
   t_int    HmsValue         = -1;
   t_char   BothBuf[64]      = "";
   t_char   Both2Buf[64]     = "";
   t_char   CmdOnlyBuf[64]   = "";
   t_char   LoggingBuf[64]   = "";
   t_ToolCfgSet SetArray[]   = { { (t_pcchar) "off", 0 }, { (t_pcchar) "on", 1 }, { nullptr, 0 } };

   t_ToolCfgParamDesc Params[] =
   {
      { CFGASSIGN_CFG_ONCE, nullptr,
        { (t_pcchar) "StringParam",   CFGTYPE_STRING,   (long) StringBuf,     sizeof (StringBuf) - 1,   0.0,    0.0, nullptr }, 0, 0 },
      { CFGASSIGN_CFG_ONCE, nullptr,
        { (t_pcchar) "IntParam",      CFGTYPE_INTEGER,  (long) &IntValue,     0,                    -1000.0, 1000.0, nullptr }, 0, 0 },
      { CFGASSIGN_CFG_ONCE, nullptr,
        { (t_pcchar) "DoubleParam",   CFGTYPE_DOUBLE,   (long) &DoubleValue,  0,                       0.0,  100.0, nullptr }, 0, 0 },
      { CFGASSIGN_CFG_ONCE, nullptr,
        { (t_pcchar) "PresenceParam", CFGTYPE_PRESENCE, (long) &PresenceValue, 0,                      0.0,    0.0, nullptr }, 0, 0 },
      { CFGASSIGN_CFG_ONCE, nullptr,
        { (t_pcchar) "SetParam",      CFGTYPE_SET,      (long) &SetValue,     0,                       0.0,    0.0, SetArray }, 0, 0 },
      { CFGASSIGN_CFG_ONCE, nullptr,
        { (t_pcchar) "HmsParam",      CFGTYPE_HMS,      (long) &HmsValue,     0,                       0.0, 86399.0, nullptr }, 0, 0 },
      { CFGASSIGN_BOTH_ONCE, nullptr,
        { (t_pcchar) "BothParam",     CFGTYPE_STRING,   (long) BothBuf,       sizeof (BothBuf) - 1,     0.0,    0.0, nullptr }, 0, 0 },
      { CFGASSIGN_BOTH_TWICE, nullptr,
        { (t_pcchar) "Both2Param",    CFGTYPE_STRING,   (long) Both2Buf,      sizeof (Both2Buf) - 1,    0.0,    0.0, nullptr }, 0, 0 },
      { CFGASSIGN_CMD, nullptr,
        { (t_pcchar) "CmdOnlyParam",  CFGTYPE_STRING,   (long) CmdOnlyBuf,    sizeof (CmdOnlyBuf) - 1,  0.0,    0.0, nullptr }, 0, 0 },
      { CFGASSIGN_OPTIONAL, nullptr,
        { (t_pcchar) "LoggingParam",  CFGTYPE_STRING,   (long) LoggingBuf,    sizeof (LoggingBuf) - 1,  0.0,    0.0, nullptr }, 0, 0 },
      { CFGASSIGN_CFG_ONCE, nullptr,
        { nullptr, CFGTYPE_NULL, 0, 0, 0.0, 0.0, nullptr }, 0, 0 }
   };

   // --- real configuration file -------------------------------------------
   const std::string FullCfg = std::string (CFG_SECTION) + std::string (CFG_SECTION_OTHER);
   Check (WriteFile (CfgPath, FullCfg), "test configuration file written");

   memset (gCfgLog, 0, sizeof (gCfgLog));
   rc = ToolCfgScanConfiguration ((t_pcchar) CfgPath.c_str (), (t_pcchar) "Global", Params, nullptr);
   Check (rc == NO_ERROR, "ToolCfgScanConfiguration(Global) -> NO_ERROR");
   Check (strcmp (StringBuf, "hello-world") == 0, "CFGTYPE_STRING parsed", StringBuf);
   Check (IntValue == 42, "CFGTYPE_INTEGER parsed");
   Check (DoubleValue > 3.49 && DoubleValue < 3.51, "CFGTYPE_DOUBLE parsed");
   Check (PresenceValue != 0, "CFGTYPE_PRESENCE parsed");
   Check (SetValue == 1, "CFGTYPE_SET parsed ('on' -> 1)");
   Check (HmsValue == 1 * 3600 + 2 * 60 + 3, "CFGTYPE_HMS parsed (01:02:03 -> 3723 s)");
   Check (strcmp (BothBuf, "cli-both-value") == 0,
          "command line value applied to a CFGASSIGN_BOTH_ONCE parameter", BothBuf);
   Check (strcmp (CmdOnlyBuf, "cli-cmd-value") == 0,
          "command line only parameter assigned from the command line", CmdOnlyBuf);
   Check (strcmp (LoggingBuf, "on") == 0, "optional parameter assigned from the command line", LoggingBuf);
   Check (Params[0].CfgAssignments == 1 && Params[0].CmdAssignments == 0,
          "assignment counters reflect the configuration file assignment");
   Check (Params[6].CfgAssignments == 0 && Params[6].CmdAssignments == 1,
          "assignment counters reflect the command line assignment");

   // ToolCfgPrintParamContents() renders the *parsed* values -> real output check
   t_char Buff[256];
   rc = ToolCfgPrintParamContents (Params, (t_pchar) "StringParam", Buff);
   Check (rc == NO_ERROR && strcmp (Buff, "hello-world") == 0,
          "ToolCfgPrintParamContents(StringParam) renders the parsed value", Buff);
   rc = ToolCfgPrintParamContents (Params, (t_pchar) "IntParam", Buff);
   Check (rc == NO_ERROR && strcmp (Buff, "42 (0x2A)") == 0,
          "ToolCfgPrintParamContents(IntParam) renders decimal and hex", Buff);
   rc = ToolCfgPrintParamContents (Params, (t_pchar) "PresenceParam", Buff);
   Check (rc == NO_ERROR && strcmp (Buff, "present") == 0,
          "ToolCfgPrintParamContents(PresenceParam) renders the presence state", Buff);
   Check (ToolCfgPrintParamContents (Params, (t_pchar) "Bogus", Buff) ==
          TOOLCFG_ERROR_UNKNOWN_PARAMETER,
          "ToolCfgPrintParamContents(unknown) -> TOOLCFG_ERROR_UNKNOWN_PARAMETER");
   Check (ToolCfgLogConfiguration (Params) == NO_ERROR,
          "ToolCfgLogConfiguration() reports all mandatory parameters as initialised");

   // A second section of the same file must be re-scanned from scratch.
   IntValue = 0;
   StringBuf[0] = '\0';
   rc = ToolCfgScanConfiguration ((t_pcchar) CfgPath.c_str (), (t_pcchar) "Other", Params, nullptr);
   Check (rc == NO_ERROR && IntValue == 99 && strcmp (StringBuf, "other-world") == 0 &&
          SetValue == 0 && HmsValue == 10,
          "re-scan of another section assigns its values (counters reset)");

   // --- documented error paths --------------------------------------------
   // Destination variables hold sentinels before each scan, so a rejected
   // assignment can be detected: the parser must not write anything.
   enum Destination { DEST_NONE, DEST_STRING, DEST_INT, DEST_DOUBLE, DEST_SET, DEST_HMS };
   struct ErrorCase
   {
      const char *pLabel;   // what is broken
      const char *pFrom;    // fragment of the valid section
      const char *pTo;      // broken replacement
      const char *pLogText; // text the parser must log
      Destination Dest;     // destination that must keep its sentinel
   };
   const ErrorCase Cases[] =
   {
      { "integer out of range", "   IntParam      = 42",           "   IntParam      = 5000",
        "Value out of range: -1000 <= IntParam <= 1000", DEST_INT },
      { "integer not a number",  "   IntParam      = 42",          "   IntParam      = abc",
        "Invalid entry, decimal or hexadecimal number expected", DEST_INT },
      { "unquoted string",       "   StringParam   = 'hello-world'", "   StringParam   = hello",
        "String expected", DEST_STRING },
      { "invalid set value",     "   SetParam      = on",          "   SetParam      = maybe",
        "Invalid set value", DEST_SET },
      { "HMS out of range",      "   HmsParam      = 01:02:03",    "   HmsParam      = 25:99:99",
        "Value out of range: 00:00:00 <= HmsParam <= 23:59:59", DEST_HMS },
      { "invalid double",        "   DoubleParam   = 3.5",         "   DoubleParam   = 3.5.7",
        "two decimal points", DEST_DOUBLE },
      { "unknown keyword",       "   IntParam      = 42",          "   IntParam      = 42\n   BogusParam    = 1",
        "Invalid keyword", DEST_NONE },
      { "command line only in file", "   IntParam      = 42",      "   IntParam      = 42\n   CmdOnlyParam  = 'x'",
        "not allowed in configuration file", DEST_NONE },
      { "parameter assigned twice", "   IntParam      = 42",       "   IntParam      = 42\n   BothParam     = 'x'",
        "only allowed once", DEST_NONE },
      { "missing ENDSECTION",    "ENDSECTION\n",                   "",
        "Missing statement ENDSECTION", DEST_NONE },
   };

   for (unsigned i = 0; i < sizeof (Cases) / sizeof (Cases[0]); i++)
   {
      WriteFile (CfgPath, Replace (std::string (CFG_SECTION), Cases[i].pFrom, Cases[i].pTo));
      StringBuf[0]  = '\0';
      IntValue      = 1234;
      DoubleValue   = 0.0;
      SetValue      = -1;
      HmsValue      = -1;
      memset (gCfgLog, 0, sizeof (gCfgLog));
      rc = ToolCfgScanConfiguration ((t_pcchar) CfgPath.c_str (), (t_pcchar) "Global", Params, nullptr);
      char Detail[640];
      snprintf (Detail, sizeof (Detail), "rc=%d log=%s", rc, gCfgLog);
      Check (rc == TOOLCFG_ERROR_CONFIG_ERROR && strstr (gCfgLog, Cases[i].pLogText) != nullptr,
            (std::string ("rejected configuration: ") + Cases[i].pLabel).c_str (), Detail);

      bool Untouched = true;
      switch (Cases[i].Dest)
      {
         case DEST_STRING: Untouched = (StringBuf[0] == '\0'); break;
         case DEST_INT:    Untouched = (IntValue == 1234);     break;
         case DEST_DOUBLE: Untouched = (DoubleValue == 0.0);   break;
         case DEST_SET:    Untouched = (SetValue == -1);       break;
         case DEST_HMS:    Untouched = (HmsValue == -1);       break;
         case DEST_NONE:   break;
      }
      Check (Untouched, (std::string ("rejected value is not written to the destination: ") +
                         Cases[i].pLabel).c_str ());
   }

   // Missing mandatory parameter (mandatory = no OPTIONAL flag).
   WriteFile (CfgPath, Replace (std::string (CFG_SECTION), "   IntParam      = 42\n", ""));
   memset (gCfgLog, 0, sizeof (gCfgLog));
   rc = ToolCfgScanConfiguration ((t_pcchar) CfgPath.c_str (), (t_pcchar) "Global", Params, nullptr);
   Check (rc == TOOLCFG_ERROR_CONFIG_ERROR &&
          strstr (gCfgLog, "Parameter IntParam has not been initialized") != nullptr,
          "unassigned mandatory parameter -> TOOLCFG_ERROR_CONFIG_ERROR", gCfgLog);

   // Unknown section and missing file.
   WriteFile (CfgPath, FullCfg);
   memset (gCfgLog, 0, sizeof (gCfgLog));
   rc = ToolCfgScanConfiguration ((t_pcchar) CfgPath.c_str (), (t_pcchar) "NoSuchSection", Params, nullptr);
   Check (rc == TOOLCFG_ERROR_CONFIG_ERROR &&
          strstr (gCfgLog, "has not been initialized") != nullptr,
          "unknown section -> TOOLCFG_ERROR_CONFIG_ERROR (nothing was assigned)");
   rc = ToolCfgScanConfiguration ((t_pcchar) JoinPath (TempDir (), "libguytools2-no-such.cfg").c_str (),
                                  (t_pcchar) "Global", Params, nullptr);
   Check (rc == TOOLCFG_ERROR_OPEN_FAILED,
          "missing configuration file -> TOOLCFG_ERROR_OPEN_FAILED");

   // Command line has priority over the configuration file for a parameter
   // that may be assigned once in each source (CFGASSIGN_BOTH_TWICE).
   WriteFile (CfgPath, Replace (std::string (CFG_SECTION), "   IntParam      = 42",
                                "   IntParam      = 42\n   Both2Param    = 'cfg-both2-value'"));
   rc = ToolCfgScanConfiguration ((t_pcchar) CfgPath.c_str (), (t_pcchar) "Global", Params, nullptr);
   Check (rc == NO_ERROR && strcmp (Both2Buf, "cli-both2-value") == 0,
          "command line wins over the configuration file (documented priority)", Both2Buf);
   Check (Params[7].CmdAssignments == 1 && Params[7].CfgAssignments == 0,
          "the lower-priority assignment is not counted");

   // Hex / negative integers and doubled quotes are part of the upstream syntax.
   WriteFile (CfgPath, Replace (Replace (std::string (CFG_SECTION), "   IntParam      = 42", "   IntParam      = 0x2A"),
                                "   StringParam   = 'hello-world'", "   StringParam   = 'it''s ok'"));
   rc = ToolCfgScanConfiguration ((t_pcchar) CfgPath.c_str (), (t_pcchar) "Global", Params, nullptr);
   Check (rc == NO_ERROR && IntValue == 42 && strcmp (StringBuf, "it's ok") == 0,
          "hexadecimal integers and doubled string quotes are parsed", StringBuf);

   // --- template generation ------------------------------------------------
   rc = ToolCfgBuildTemplate ((t_pcchar) TplPath.c_str (), (t_pcchar) "generated by the functional test",
                              (t_pcchar) "Global", Params, nullptr);
   const std::string Tpl = ReadFile (TplPath);
   Check (rc == NO_ERROR && Tpl.find ("SECTION Global") != std::string::npos &&
          Tpl.find ("ENDSECTION") != std::string::npos,
          "ToolCfgBuildTemplate() writes a template with the section skeleton");
   Check (Tpl.find ("generated by the functional test") != std::string::npos,
          "the template carries the caller comment");
   Check (Tpl.find ("StringParam") != std::string::npos && Tpl.find ("IntParam") != std::string::npos &&
          Tpl.find ("HmsParam") != std::string::npos && Tpl.find ("SetParam") != std::string::npos,
          "the template lists every configuration file parameter");
   Check (Tpl.find ("[-1000..1000]") != std::string::npos,
          "the template documents the declared value range");
   Check (Tpl.find ("[00:00:00..23:59:59]") != std::string::npos && Tpl.find ("[off, on]") != std::string::npos,
          "the template documents HMS and SET value domains");
   size_t TplCmdOnly = Tpl.find ("Options, that can only be entered on command line");
   Check (TplCmdOnly != std::string::npos &&
          Tpl.find ("CmdOnlyParam", TplCmdOnly) != std::string::npos &&
          Tpl.find ("CmdOnlyParam", 0) >= TplCmdOnly,
          "command line only parameters are listed in their own template block");
   unlink (TplPath.c_str ());

   // --- set string mapping -------------------------------------------------
   pValue = nullptr;
   Check (ToolCfgGetSetString (SetArray, 1, &pValue) == NO_ERROR && pValue != nullptr &&
          strcmp (pValue, "on") == 0,
          "ToolCfgGetSetString() maps a value to its string", pValue ? pValue : "()");
   pValue = (const char *) 1;
   Check (ToolCfgGetSetString (SetArray, 7, &pValue) == NO_ERROR && pValue == nullptr,
          "ToolCfgGetSetString() unknown value -> NO_ERROR and a NULL string");

   // --- global section names ----------------------------------------------
   Check (ToolCfgAddGlobalSectionName ((t_pcchar) "Global") == NO_ERROR,
          "ToolCfgAddGlobalSectionName() accepted");
   Check (ToolCfgDelGlobalSectionName ((t_pcchar) "Global") == NO_ERROR,
          "ToolCfgDelGlobalSectionName() removes the entry");
   Check (ToolCfgDelGlobalSectionName ((t_pcchar) "Global") == TOOLCFG_ERROR_SECTIONNAME_NOTFOUND,
          "ToolCfgDelGlobalSectionName() unknown name -> TOOLCFG_ERROR_SECTIONNAME_NOTFOUND");

   Check (ToolCfgDeInit () == NO_ERROR, "ToolCfgDeInit() -> NO_ERROR");
   unlink (CfgPath.c_str ());
}

// ===========================================================================
// 5. ToolSignal — signal guard thread (real signal round trip)
// ===========================================================================

static volatile sig_atomic_t gSignalSeen   = -1;
static volatile int          gSignalCalls  = 0;
static pthread_t             gSignalThread;

static void TestSignalHandler (int Signal)
{
   gSignalThread = pthread_self ();   // which thread runs the handler?
   gSignalSeen   = Signal;
   gSignalCalls++;
}

static bool  gSignalLogSeen = false;
static char  gSignalLogLast[512] = "";
static unsigned long long gSignalLogThread = 0;

static void TestSignalLogFn (bool /*Error*/, unsigned long long ThreadId, const char * /*pFileName*/,
                             const char * /*pFunction*/, int /*LineNr*/, const char *pFormat, va_list pArguments)
{
   vsnprintf (gSignalLogLast, sizeof (gSignalLogLast), pFormat, pArguments);
   gSignalLogThread = ThreadId;
   gSignalLogSeen   = true;
}

static bool WaitForSignal (sig_atomic_t Wanted, int TimeoutMs = 3000)
{
   for (int i = 0; i < TimeoutMs / 50; i++)
   {
      if (gSignalSeen == Wanted)
         return true;
      usleep (50 * 1000);
   }
   return gSignalSeen == Wanted;
}

static void TestSignal (void)
{
   Section ("5. ToolSignal — signal guard thread");

   Check (ToolSignalDeInit () == ERROR_TOOLSIGNAL_NOT_INITIALISED,
          "ToolSignalDeInit() before init -> ERROR_TOOLSIGNAL_NOT_INITIALISED");

   unsigned long long ThreadId = 0;
   pthread_t MainThread = pthread_self ();
   int rc = ToolSignalInit (TestSignalLogFn, TestSignalHandler, &ThreadId);
   Check (rc == NO_ERROR, "ToolSignalInit() -> NO_ERROR");
   Check (ThreadId == (unsigned long long) MainThread,
          "ToolSignalInit() reports the calling thread id");
   Check (ToolSignalInit (TestSignalLogFn, TestSignalHandler, &ThreadId) ==
          ERROR_TOOLSIGNAL_ALREADY_INITIALISED,
          "second ToolSignalInit() -> ERROR_TOOLSIGNAL_ALREADY_INITIALISED");

   if (rc != NO_ERROR)
   {
      Skip ("signal round trip", "ToolSignalInit() failed");
      return;
   }

   // SIGTERM/SIGINT make the guard thread leave its loop, so SIGHUP is used
   // first: the guard thread must deliver it to the handler and keep running.
   gSignalSeen = -1;
   gSignalLogSeen = false;
   Check (kill (getpid (), SIGHUP) == 0, "SIGHUP sent to the process");
   Check (WaitForSignal (SIGHUP), "the guard thread delivered SIGHUP to the handler");
   Check (gSignalThread != 0 && !pthread_equal (gSignalThread, MainThread),
          "the handler runs in the guard thread, not in the main thread");
   Check (gSignalLogSeen && strstr (gSignalLogLast, "Caught signal") != nullptr &&
          strstr (gSignalLogLast, strsignal (SIGHUP)) != nullptr,
          "the signal log function received the signal name", gSignalLogLast);
   Check (gSignalLogThread != 0 && gSignalLogThread != (unsigned long long) MainThread,
          "signal log entries come from the guard thread as well");

   gSignalSeen = -1;
   Check (kill (getpid (), SIGTERM) == 0, "SIGTERM sent to the process");
   Check (WaitForSignal (SIGTERM), "the guard thread delivered SIGTERM to the handler");

   Check (ToolSignalDeInit () == NO_ERROR, "ToolSignalDeInit() -> NO_ERROR");
}

// ===========================================================================
// 6. HarmonyOS (OHOS) platform behaviour
//
// Behaviour that only exists on (or only matters for) OpenHarmony: the OS and
// kernel identity, the platform TMPDIR contract, logging onto OHOS user
// storage and MAC enumeration through the portable <net/if.h> ioctl path that
// patches/0003 switched to.  On any other platform the group reports one SKIP.
// ===========================================================================

static void TestOhosPlatform (void)
{
   Section ("6. HarmonyOS (OHOS) platform behaviour");

   QString Uname;
   APIRET rc = ToolSysInfoUname (Uname);
   std::string U = (rc == NO_ERROR) ? std::string (Uname.toUtf8 ().constData ()) : std::string ();
   printf ("        uname: %s\n", U.c_str ());
   if (U.find ("HarmonyOS") == std::string::npos)
   {
      Skip ("HarmonyOS platform group", "not running on HarmonyOS / OHOS");
      return;
   }

   Check (U.find ("HarmonyOS") != std::string::npos,
          "uname reports the HarmonyOS OS identity");
   Check (U.find ("HongMeng") != std::string::npos,
          "uname reports the HongMeng kernel");
   Check (U.find ("aarch64") != std::string::npos,
          "uname reports the aarch64 userland");

   const char *pTmp = getenv ("TMPDIR");
   Check (pTmp != nullptr && pTmp[0] != '\0',
          "the platform exports TMPDIR", pTmp ? pTmp : "(unset)");
   Check (pTmp != nullptr && strncmp (pTmp, "/storage/", 9) == 0,
          "TMPDIR points into the OHOS user storage tree", pTmp ? pTmp : "");

   // t_Log must be able to create and re-read a log file on OHOS storage.
   APIRET LogRc = NO_ERROR;
   const std::string LogPath = JoinPath (TempDir (), "libguytools2-ohos.log");
   unlink (LogPath.c_str ());
   t_Log *pLog = new t_Log (LogPath.c_str (), LogRc);
   Check (LogRc == NO_ERROR && t_Log::IsInitialised (),
          "t_Log opens a log file on OHOS user storage");
   LOG_INFO ("OHOS storage marker %d", 4711);
   Check (strstr (ReadFile (LogPath).c_str (), "OHOS storage marker 4711") != nullptr,
          "the log entry is persisted on the OHOS file system");
   delete pLog;
   unlink (LogPath.c_str ());

   // MAC enumeration goes through the <net/if.h> ioctl code path fixed by
   // patches/0003: a result must be a consistent 12-hex-digit string, an
   // absent address must be reported with the documented error code.
   t_ToolSysInfoMacAddr MacAddr;
   memset (&MacAddr, 0, sizeof (MacAddr));
   rc = ToolSysInfoGetMacAddr (&MacAddr);
   printf ("        mac: rc=%d addr=%s\n", rc, MacAddr.AddrStr);
   Check (rc == NO_ERROR || rc == (APIRET) TOOLSYSINFO_ERROR_NO_ADDR,
          "MAC enumeration returns an address or TOOLSYSINFO_ERROR_NO_ADDR");
   if (rc == NO_ERROR)
   {
      bool AllHex = (strlen (MacAddr.AddrStr) == TOOLSYSINFO_MACADDRLEN_STR);
      for (int i = 0; AllHex && i < TOOLSYSINFO_MACADDRLEN_STR; i++)
      {
         const char c = MacAddr.AddrStr[i];
         AllHex = ((c >= '0' && c <= '9') || (c >= 'A' && c <= 'F'));
      }
      Check (AllHex, "net/if.h ioctl path yields 12 upper-case hex digits", MacAddr.AddrStr);
   }
}

// ===========================================================================

int main (void)
{
   printf ("libguytools2 " EXPECTED_VERSION " — consumer functional test\n");
   printf ("==========================================================\n");

   TestError ();
   TestLog ();
   TestSysInfo ();
   TestCfg ();
   TestSignal ();
   TestOhosPlatform ();

   printf ("\n==========================================================\n");
   printf ("checks: %d   passed: %d   failed: %d   skipped: %d\n",
           gPassed + gFailed + gSkipped, gPassed, gFailed, gSkipped);

   return gFailed == 0 ? 0 : 1;
}
