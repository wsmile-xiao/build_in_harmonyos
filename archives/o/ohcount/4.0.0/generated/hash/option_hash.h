/* ANSI-C code produced by gperf version 3.1 */
/* Command-line: gperf -L ANSI-C -E -D -K key -H ohcount_hash_options -N ohcount_hash_command_from_flag -t options.gperf  */
/* Computed positions: -k'$' */

#if !((' ' == 32) && ('!' == 33) && ('"' == 34) && ('#' == 35) \
      && ('%' == 37) && ('&' == 38) && ('\'' == 39) && ('(' == 40) \
      && (')' == 41) && ('*' == 42) && ('+' == 43) && (',' == 44) \
      && ('-' == 45) && ('.' == 46) && ('/' == 47) && ('0' == 48) \
      && ('1' == 49) && ('2' == 50) && ('3' == 51) && ('4' == 52) \
      && ('5' == 53) && ('6' == 54) && ('7' == 55) && ('8' == 56) \
      && ('9' == 57) && (':' == 58) && (';' == 59) && ('<' == 60) \
      && ('=' == 61) && ('>' == 62) && ('?' == 63) && ('A' == 65) \
      && ('B' == 66) && ('C' == 67) && ('D' == 68) && ('E' == 69) \
      && ('F' == 70) && ('G' == 71) && ('H' == 72) && ('I' == 73) \
      && ('J' == 74) && ('K' == 75) && ('L' == 76) && ('M' == 77) \
      && ('N' == 78) && ('O' == 79) && ('P' == 80) && ('Q' == 81) \
      && ('R' == 82) && ('S' == 83) && ('T' == 84) && ('U' == 85) \
      && ('V' == 86) && ('W' == 87) && ('X' == 88) && ('Y' == 89) \
      && ('Z' == 90) && ('[' == 91) && ('\\' == 92) && (']' == 93) \
      && ('^' == 94) && ('_' == 95) && ('a' == 97) && ('b' == 98) \
      && ('c' == 99) && ('d' == 100) && ('e' == 101) && ('f' == 102) \
      && ('g' == 103) && ('h' == 104) && ('i' == 105) && ('j' == 106) \
      && ('k' == 107) && ('l' == 108) && ('m' == 109) && ('n' == 110) \
      && ('o' == 111) && ('p' == 112) && ('q' == 113) && ('r' == 114) \
      && ('s' == 115) && ('t' == 116) && ('u' == 117) && ('v' == 118) \
      && ('w' == 119) && ('x' == 120) && ('y' == 121) && ('z' == 122) \
      && ('{' == 123) && ('|' == 124) && ('}' == 125) && ('~' == 126))
/* The character set is not based on ISO-646.  */
#error "gperf generated tables don't work with this execution character set. Please report a bug to <bug-gperf@gnu.org>."
#endif

#line 1 "options.gperf"

#include "../ohcount.h"
#line 4 "options.gperf"
struct OhcountOption { const char *key; int value; };
/* maximum key range = 16, duplicates = 0 */

#ifdef __GNUC__
__inline
#else
#ifdef __cplusplus
inline
#endif
#endif
static unsigned int
ohcount_hash_options (register const char *str, register size_t len)
{
  static unsigned char asso_values[] =
    {
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18,  3, 18, 18,
      14,  0, 18, 18,  9, 15, 18, 18,  0, 18,
      18, 18,  0, 18, 18,  5,  0, 18, 18, 18,
      18,  5, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18, 18, 18, 18, 18,
      18, 18, 18, 18, 18, 18
    };
  return len + asso_values[(unsigned char)str[len - 1]];
}

struct OhcountOption *
ohcount_hash_command_from_flag (register const char *str, register size_t len)
{
  enum
    {
      TOTAL_KEYWORDS = 13,
      MIN_WORD_LENGTH = 2,
      MAX_WORD_LENGTH = 12,
      MIN_HASH_VALUE = 2,
      MAX_HASH_VALUE = 17
    };

  static struct OhcountOption wordlist[] =
    {
#line 14 "options.gperf"
      {"-l", COMMAND_LICENSES},
#line 16 "options.gperf"
      {"-re", COMMAND_RAWENTITIES},
#line 6 "options.gperf"
      {"-a", COMMAND_ANNOTATE},
#line 11 "options.gperf"
      {"--help", COMMAND_HELP},
#line 17 "options.gperf"
      {"-s", COMMAND_SUMMARY},
#line 9 "options.gperf"
      {"--detect", COMMAND_DETECT},
#line 15 "options.gperf"
      {"--license", COMMAND_LICENSES},
#line 7 "options.gperf"
      {"--annotate", COMMAND_ANNOTATE},
#line 10 "options.gperf"
      {"-h", COMMAND_HELP},
#line 13 "options.gperf"
      {"--individual", COMMAND_INDIVIDUAL},
#line 18 "options.gperf"
      {"--summary", COMMAND_SUMMARY},
#line 8 "options.gperf"
      {"-d", COMMAND_DETECT},
#line 12 "options.gperf"
      {"-i", COMMAND_INDIVIDUAL}
    };

  static signed char lookup[] =
    {
      -1, -1,  0,  1, -1,  2,  3,  4,  5,  6,  7,  8,  9, -1,
      10, -1, 11, 12
    };

  if (len <= MAX_WORD_LENGTH && len >= MIN_WORD_LENGTH)
    {
      register unsigned int key = ohcount_hash_options (str, len);

      if (key <= MAX_HASH_VALUE)
        {
          register int index = lookup[key];

          if (index >= 0)
            {
              register const char *s = wordlist[index].key;

              if (*str == *s && !strcmp (str + 1, s + 1))
                return &wordlist[index];
            }
        }
    }
  return 0;
}
