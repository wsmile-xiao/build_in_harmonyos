/* ANSI-C code produced by gperf version 3.1 */
/* Command-line: gperf -L ANSI-C -E -D -K key -H ohcount_hash_disambiguatefunc -N ohcount_hash_disambiguate_func_from_id -t disambiguatefuncs.gperf  */
/* Computed positions: -k'1-2' */

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

#line 1 "disambiguatefuncs.gperf"

#include "../detector.h"
#include "../sourcefile.h"

const char *disambiguate_aspx(SourceFile *sourcefile);
const char *disambiguate_asx(SourceFile *sourcefile);
const char *disambiguate_b(SourceFile *sourcefile);
const char *disambiguate_basic(SourceFile *sourcefile);
const char *disambiguate_cs(SourceFile *sourcefile);
const char *disambiguate_dat(SourceFile *sourcefile);
const char *disambiguate_def(SourceFile *sourcefile);
const char *disambiguate_fortran(SourceFile *sourcefile);
const char *disambiguate_fs(SourceFile *sourcefile);
const char *disambiguate_h(SourceFile *sourcefile);
const char *disambiguate_in(SourceFile *sourcefile);
const char *disambiguate_inc(SourceFile *sourcefile);
const char *disambiguate_m(SourceFile *sourcefile);
const char *disambiguate_mod(SourceFile *sourcefile);
const char *disambiguate_pl(SourceFile *sourcefile);
const char *disambiguate_pp(SourceFile *sourcefile);
const char *disambiguate_pro(SourceFile *sourcefile);
const char *disambiguate_r(SourceFile *sourcefile);
const char *disambiguate_rs(SourceFile *sourcefile);
const char *disambiguate_st(SourceFile *sourcefile);
#line 26 "disambiguatefuncs.gperf"
struct DisambiguateFuncsMap { const char *key; const char* (*value)(SourceFile*); };
/* maximum key range = 37, duplicates = 0 */

#ifdef __GNUC__
__inline
#else
#ifdef __cplusplus
inline
#endif
#endif
static unsigned int
ohcount_hash_disambiguatefunc (register const char *str, register size_t len)
{
  static unsigned char asso_values[] =
    {
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38,  0, 10, 30,
      20,  5, 15, 38, 15,  5, 38, 38, 25,  0,
       5, 15,  0, 38,  5,  0, 20, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38, 38, 38, 38, 38,
      38, 38, 38, 38, 38, 38
    };
  register unsigned int hval = len;

  switch (hval)
    {
      default:
        hval += asso_values[(unsigned char)str[1]];
      /*FALLTHROUGH*/
      case 1:
        hval += asso_values[(unsigned char)str[0]];
        break;
    }
  return hval;
}

struct DisambiguateFuncsMap *
ohcount_hash_disambiguate_func_from_id (register const char *str, register size_t len)
{
  enum
    {
      TOTAL_KEYWORDS = 20,
      MIN_WORD_LENGTH = 1,
      MAX_WORD_LENGTH = 7,
      MIN_HASH_VALUE = 1,
      MAX_HASH_VALUE = 37
    };

  static struct DisambiguateFuncsMap wordlist[] =
    {
#line 40 "disambiguatefuncs.gperf"
      {"m", disambiguate_m},
#line 43 "disambiguatefuncs.gperf"
      {"pp", disambiguate_pp},
#line 29 "disambiguatefuncs.gperf"
      {"asx", disambiguate_asx},
#line 28 "disambiguatefuncs.gperf"
      {"aspx", disambiguate_aspx},
#line 45 "disambiguatefuncs.gperf"
      {"r", disambiguate_r},
#line 46 "disambiguatefuncs.gperf"
      {"rs", disambiguate_rs},
#line 44 "disambiguatefuncs.gperf"
      {"pro", disambiguate_pro},
#line 30 "disambiguatefuncs.gperf"
      {"b", disambiguate_b},
#line 38 "disambiguatefuncs.gperf"
      {"in", disambiguate_in},
#line 39 "disambiguatefuncs.gperf"
      {"inc", disambiguate_inc},
#line 31 "disambiguatefuncs.gperf"
      {"basic", disambiguate_basic},
#line 37 "disambiguatefuncs.gperf"
      {"h", disambiguate_h},
#line 36 "disambiguatefuncs.gperf"
      {"fs", disambiguate_fs},
#line 41 "disambiguatefuncs.gperf"
      {"mod", disambiguate_mod},
#line 47 "disambiguatefuncs.gperf"
      {"st", disambiguate_st},
#line 33 "disambiguatefuncs.gperf"
      {"dat", disambiguate_dat},
#line 42 "disambiguatefuncs.gperf"
      {"pl", disambiguate_pl},
#line 34 "disambiguatefuncs.gperf"
      {"def", disambiguate_def},
#line 32 "disambiguatefuncs.gperf"
      {"cs", disambiguate_cs},
#line 35 "disambiguatefuncs.gperf"
      {"fortran", disambiguate_fortran}
    };

  static signed char lookup[] =
    {
      -1,  0,  1,  2,  3, -1,  4,  5,  6, -1, -1,  7,  8,  9,
      -1, 10, 11, 12, 13, -1, -1, -1, 14, 15, -1, -1, -1, 16,
      17, -1, -1, -1, 18, -1, -1, -1, -1, 19
    };

  if (len <= MAX_WORD_LENGTH && len >= MIN_WORD_LENGTH)
    {
      register unsigned int key = ohcount_hash_disambiguatefunc (str, len);

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
