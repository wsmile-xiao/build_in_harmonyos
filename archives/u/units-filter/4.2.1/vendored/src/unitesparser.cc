/* A Bison parser, made by GNU Bison 3.8.2.  */

/* Bison implementation for Yacc-like parsers in C

   Copyright (C) 1984, 1989-1990, 2000-2015, 2018-2021 Free Software Foundation,
   Inc.

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <https://www.gnu.org/licenses/>.  */

/* As a special exception, you may create a larger work that contains
   part or all of the Bison parser skeleton and distribute that work
   under terms of your choice, so long as that work isn't itself a
   parser generator using the skeleton or a modified version thereof
   as a parser skeleton.  Alternatively, if you modify or redistribute
   the parser skeleton itself, you may (at your option) remove this
   special exception, which will cause the skeleton and the resulting
   Bison output files to be licensed under the GNU General Public
   License without this special exception.

   This special exception was added by the Free Software Foundation in
   version 2.2 of Bison.  */

/* C LALR(1) parser skeleton written by Richard Stallman, by
   simplifying the original so-called "semantic" parser.  */

/* DO NOT RELY ON FEATURES THAT ARE NOT DOCUMENTED in the manual,
   especially those whose name start with YY_ or yy_.  They are
   private implementation details that can be changed or removed.  */

/* All symbols defined below should begin with yy or YY, to avoid
   infringing on user name space.  This should be done even for local
   variables, as they might otherwise be expanded by user macros.
   There are some unavoidable exceptions within include files to
   define necessary library symbols; they are noted "INFRINGES ON
   USER NAME SPACE" below.  */

/* Identify Bison output, and Bison version.  */
#define YYBISON 30802

/* Bison version string.  */
#define YYBISON_VERSION "3.8.2"

/* Skeleton name.  */
#define YYSKELETON_NAME "yacc.c"

/* Pure parsers.  */
#define YYPURE 0

/* Push parsers.  */
#define YYPUSH 0

/* Pull parsers.  */
#define YYPULL 1




/* First part of user prologue.  */
#line 1 "unites.y"

/* inclusions, définition */
#include <string.h>
#include <stdio.h>
#include <sstream>
#include <stdlib.h>
#include "unites.h"
#include <math.h>

using namespace std;

  int yylex();
  int yyerror(const char * msg);

  const char * unit_names[BU_LAST]={"m","kg","s","A","K","mol","cd"};

  /**
   * values returned by the lexer are instances of the class yystype
   **/
  class yystype{
  public:
    /* integer property */
    int i;
    /**
     * mutiplicators are mutiprecisions decimals.
     *
     * multip:        multiplicator to apply to the SI monome to get the unit
     * maxmultip:     an accumulator used for mixed units expressions
     * wanted_multip: a desired multiplier when a unit wish is expressed
     **/
    double multip, maxmultip, wanted_multip;
    /* standard or non-standard unit index -- see unites.h */
    uniteSI unite;
    /* vector of powers (a unit is expressed as a monome of bse units)) */
    int base[BU_LAST];
    /* cstr properties */
    char * s, * v;
    /* name of a wanted unit */
    string wanted_unit;
    /* values are mutiprecisions rationals */
    Decimal val;
    /* how many significant numbers? */
    int signif;
    /* percent tolerance */
    int pcent;
    /**
     * the construcror initializes at least cstr properties to avoid
     * dangling links.
     **/
    yystype(){
      s=(char*) NULL;
      v=(char*) NULL;
    }
  };

  /**
   * display to stream operator, useful to debug yystype objects
   **/
  ostream & operator << (ostream & o, yystype data);
  ostream & operator << (ostream & o, yystype data){
    o << "YYSTYPE[" <<"i="<<data.i<<", multip="<<data.multip;
    o<<", maxmultip="<<data.maxmultip<<", wanted_multip="<<data.wanted_multip;
    o<<", unite="<<data.unite<<", base={";
    for (int i=0;i<BU_LAST;i++){
      o<<data.base[i]<<" ";
    }
    o<<"}";
    if(data.s!=NULL){ o<<", s="<<data.s;}else{o<<", s=NULL";}
    if(data.v!=NULL){o<<", v="<<data.v;}else{o<<", v=NULL";}
    o<<", wanted_unit="<<data.wanted_unit;
    o<<", val="<<data.val<<", signif="<<data.signif<<", pcent="<<data.pcent;
    o<<"] ";
    return o;
  }
  
#define YYSTYPE yystype 

 extern FILE * yyin;

/* variables globales */
#define MAXBUF 255
 char buffer[MAXBUF+1], buffer2[MAXBUF+1];
 yystype result;
 Decimal val_decimal; /* a multiprecision rational */
 int val_int, count_signif=0;
 long pos;

 /**
  * SI and non-SI units list
  * source: Handbook of Chemistry & Physics 78, CRC Press 1997, page 1-20
  * full names of the units are in French, with a Latin-1 encoding
  **/
unite_data unites[TU_LAST] ={
/*TUh*/   {"h",      "seconde",   3600.0,     { 0, 0, 1, 0, 0, 0, 0}},
/*TUmin*/ {"min",    "seconde",   60.0,       { 0, 0, 1, 0, 0, 0, 0}},
/*TUm*/   {"m",      "mètre",     1.0,        { 1, 0, 0, 0, 0, 0, 0}},
/*TUg*/   {"g",      "kilogramme",1.0e-3,     { 0, 1, 0, 0, 0, 0, 0}},
/*TUs*/   {"s",      "seconde",   1.0,        { 0, 0, 1, 0, 0, 0, 0}},
/*TUA*/   {"A",      "ampère",    1.0,        { 0, 0, 0, 1, 0, 0, 0}},
/*TUK*/   {"K",      "kelvin",    1.0,        { 0, 0, 0, 0, 1, 0, 0}},
/*TUmol*/ {"mol",    "mol",       1.0,        { 0, 0, 0, 0, 0, 1, 0}},
/*TUcd*/  {"cd",     "candela",   1.0,        { 0, 0, 0, 0, 0, 0, 1}},
/*TUHz*/  {"Hz",     "hetrz",     1.0,        { 0,-1, 0, 0, 0, 0, 0}},
/*TUN*/   {"N",      "newton",    1.0,        { 1, 1,-2, 0, 0, 0, 0}},
/*TUPa*/  {"Pa",     "pascal",    1.0,        {-1, 1,-2, 0, 0, 0, 0}},
/*TUJ*/   {"J",      "joule",     1.0,        { 2, 1,-2, 0, 0, 0, 0}},
/*TUW */  {"W",      "watt",      1.0,        { 2, 1,-3, 0, 0, 0, 0}},
/*TUVA*/  {"VA",     "voltampere",1.0,        { 2, 1,-3, 0, 0, 0, 0}},
/*TUvar*/ {"var",    "var",       1.0,        { 2, 1,-3, 0, 0, 0, 0}},
/*TUC*/   {"C",      "coulomb",   1.0,        { 0, 0, 1, 1, 0, 0, 0}},
/*TUV*/   {"V",      "volt",      1.0,        { 2, 1,-3,-1, 0, 0, 0}},
/*TUohm*/ {"\\Omega","ohm",       1.0,        { 2, 1,-3,-2, 0, 0, 0}},
/*TUS*/   {"S",      "siemens",   1.0,        {-2,-1, 3, 2, 0, 0, 0}},
/*TUF*/   {"F",      "farad",     1.0,        {-2,-1, 4, 2, 0, 0, 0}},
/*TUT*/   {"T",      "tesla",     1.0,        { 0, 1,-2,-1, 0, 0, 0}},
/*TUWb*/  {"Wb",     "weber",     1.0,        { 2, 1,-2,-1, 0, 0, 0}},
/*TUH*/   {"H",      "henry",     1.0,        { 2, 1,-2,-2, 0, 0, 0}},
/*TUlm*/  {"lm",     "lumen",     1.0,        { 0, 0, 0, 0, 0, 0, 1}},
/*TUlx*/  {"lx",     "lux",       1.0,        {-2, 0, 0, 0, 0, 0, 1}},
/*TUBq */ {"Bq",     "becquerel", 1.0,        { 0, 0,-1, 0, 0, 0, 0}},
/*TUGy*/  {"Gy",     "gray",      1.0,        { 2, 0,-2, 0, 0, 0, 0}},
/*TUSv*/  {"Sv",     "sievert",   1.0,        { 2, 0,-2, 0, 0, 0, 0}},
/*TUrad*/ {"rad",    "radian",    1.0,        { 0, 0, 0, 0, 0, 0, 0}},
/*TUsr*/  {"sr" ,    "stéradian", 1.0,        { 0, 0, 0, 0, 0, 0, 0}},
/*TUnull*/{"" ,      "sans unité",1.0,        { 0, 0, 0, 0, 0, 0, 0}},
/*TUda*/  {"°",      "degré",     M_PI/180.0, { 0, 0, 0, 0, 0, 0, 0}},
/*TUma*/  {"'",      "minute",    M_PI/10800, { 0, 0, 0, 0, 0, 0, 0}},
/*TUsa*/  {"''",     "seconde",   M_PI/648000,{ 0, 0, 0, 0, 0, 0, 0}},
/*TUtr*/  {"tr",     "degré",     2*M_PI,     { 0, 0, 0, 0, 0, 0, 0}},
/*TUrpm*/ {"rpm",  "tour/minute", 2*M_PI/60,  { 0, 0, -1, 0, 0, 0, 0}},
/*TUangs*/{"\\o{A}", "angström",  1e-10,      { 1, 0, 0, 0, 0, 0, 0}},
/*TUbarn*/{"b",      "barn",      1e-28,      { 2, 0, 0, 0, 0, 0, 0}},
/*TUare*/ {"a",      "are",       1e2,        { 2, 0, 0, 0, 0, 0, 0}},
/*TUl*/   {"L",      "litre",     1e-3,       { 3, 0, 0, 0, 0, 0, 0}},
/*TUt*/   {"t",      "tonne",     1e3,        { 0, 1, 0, 0, 0, 0, 0}},
/*TUbar*/ {"bar",    "bar",       1e5,        {-1, 1,-2, 0, 0, 0, 0}},
/*TUeV*/  {"eV",     "eV",        1.60218e-19,{ 2, 1,-2, 0, 0, 0, 0}},
/*TUuam*/ {"uma",    "uma",       1.66054e-27,{ 0, 1, 0, 0, 0, 0, 0}}
};

 /**
  * preferred SI units list
  * source: Handbook of Chemistry & Physics 78, CRC Press 1997, page 1-20
  * full names of the units are in French, with a Latin-1 encoding
  **/
unite_data pref_units[] ={
/*TUm*/   {"m",      "mètre",   1.0,     { 1, 0, 0, 0, 0, 0, 0}},
/*   */   {"kg",    "kilogramme",1.0,    { 0, 1, 0, 0, 0, 0, 0}},
/*TUs*/   {"s",      "seconde", 1.0,     { 0, 0, 1, 0, 0, 0, 0}},
/*TUA*/   {"A",      "ampère",  1.0,     { 0, 0, 0, 1, 0, 0, 0}},
/*TUK*/   {"K",      "kelvin",  1.0,     { 0, 0, 0, 0, 1, 0, 0}},
/*TUmol*/ {"mol",    "mol",     1.0,     { 0, 0, 0, 0, 0, 1, 0}},
/*TUcd*/  {"cd",     "candela", 1.0,     { 0, 0, 0, 0, 0, 0, 1}},
/*TUHz*/  {"Hz",     "hetrz",   1.0,     { 0,-1, 0, 0, 0, 0, 0}},
/*TUN*/   {"N",      "newton",  1.0,     { 1, 1,-2, 0, 0, 0, 0}},
/*TUPa*/  {"Pa",     "pascal",  1.0,     {-1, 1,-2, 0, 0, 0, 0}},
/*TUJ*/   {"J",      "joule",   1.0,     { 2, 1,-2, 0, 0, 0, 0}},
/*TUW */  {"W",      "watt",    1.0,     { 2, 1,-3, 0, 0, 0, 0}},
/*TUC*/   {"C",      "coulomb", 1.0,     { 0, 0, 1, 1, 0, 0, 0}},
/*TUV*/   {"V",      "volt",    1.0,     { 2, 1,-3,-1, 0, 0, 0}},
/*TUohm*/ {"ohm",    "ohm",     1.0,     { 2, 1,-3,-2, 0, 0, 0}},
/*TUS*/   {"S",      "siemens", 1.0,     {-2,-1, 3, 2, 0, 0, 0}},
/*TUF*/   {"F",      "farad",   1.0,     {-2,-1, 4, 2, 0, 0, 0}},
/*TUT*/   {"T",      "tesla",   1.0,     { 0, 1,-2,-1, 0, 0, 0}},
/*TUWb*/  {"Wb",     "weber",   1.0,     { 2, 1,-2,-1, 0, 0, 0}},
/*TUH*/   {"H",      "henry",   1.0,     { 2, 1,-2,-2, 0, 0, 0}},
/*TUlm*/  {"lm",     "lumen",   1.0,     { 0, 0, 0, 0, 0, 0, 1}},
/*TUlx*/  {"lx",     "lux",     1.0,     {-2, 0, 0, 0, 0, 0, 1}},
};

int significative(char* text);
/**
 * returns the number of significative digits of a decimal number
 * @param text the decimal number as a cstr
 * @return number of significative nubers; leading zeroes are not taken
 * in account. A true zero is a special case.
 **/
int significative(char* text){
  unsigned int i,j;
  int result=0;
  char *end = text+strlen(text);
  while (end>text && *(end-1)==' '){ // removes the rightmost spaces
    end--;
    *end=0;
  }
  for(i=0;
      i<strlen(text)&&(text[i]=='0'||text[i]=='.'|| text[i]=='+'||text[i]=='-');
      i++){
    //skip leading plus,minus,zeros and the decimal point
  }
  if (i==strlen(text)){ // the number is probably zero
    result=1;
    char * dot = strchr(text,'.');
    if (dot != NULL && *dot == '.') result += (end-dot)-1;
  } else { // the number is not zero
    for(j=i;j<strlen(text) && ((text[j]>='0'&&text[j]<='9') || text[j]=='.');j++){
      if (text[j]!='.') {
	result++;
      } else {
	//skip the decimal point
      }
    }
  }
  return result;
}


#line 279 "unitesparser.cc"

# ifndef YY_CAST
#  ifdef __cplusplus
#   define YY_CAST(Type, Val) static_cast<Type> (Val)
#   define YY_REINTERPRET_CAST(Type, Val) reinterpret_cast<Type> (Val)
#  else
#   define YY_CAST(Type, Val) ((Type) (Val))
#   define YY_REINTERPRET_CAST(Type, Val) ((Type) (Val))
#  endif
# endif
# ifndef YY_NULLPTR
#  if defined __cplusplus
#   if 201103L <= __cplusplus
#    define YY_NULLPTR nullptr
#   else
#    define YY_NULLPTR 0
#   endif
#  else
#   define YY_NULLPTR ((void*)0)
#  endif
# endif


/* Debug traces.  */
#ifndef YYDEBUG
# define YYDEBUG 0
#endif
#if YYDEBUG
extern int yydebug;
#endif

/* Token kinds.  */
#ifndef YYTOKENTYPE
# define YYTOKENTYPE
  enum yytokentype
  {
    YYEMPTY = -2,
    YYEOF = 0,                     /* "end of file"  */
    YYerror = 256,                 /* error  */
    YYUNDEF = 257,                 /* "invalid token"  */
    EE = 258,                      /* EE  */
    DECIMAL = 259,                 /* DECIMAL  */
    INT = 260,                     /* INT  */
    SPC = 261,                     /* SPC  */
    COLON = 262,                   /* COLON  */
    Uh = 263,                      /* Uh  */
    Umin = 264,                    /* Umin  */
    Um = 265,                      /* Um  */
    Ug = 266,                      /* Ug  */
    Us = 267,                      /* Us  */
    UA = 268,                      /* UA  */
    UK = 269,                      /* UK  */
    Umol = 270,                    /* Umol  */
    Ucd = 271,                     /* Ucd  */
    UHz = 272,                     /* UHz  */
    UN = 273,                      /* UN  */
    UPa = 274,                     /* UPa  */
    UJ = 275,                      /* UJ  */
    UW = 276,                      /* UW  */
    UC = 277,                      /* UC  */
    UVA = 278,                     /* UVA  */
    Uvar = 279,                    /* Uvar  */
    UV = 280,                      /* UV  */
    Uohm = 281,                    /* Uohm  */
    US = 282,                      /* US  */
    UF = 283,                      /* UF  */
    UT = 284,                      /* UT  */
    UWb = 285,                     /* UWb  */
    UH = 286,                      /* UH  */
    Ulm = 287,                     /* Ulm  */
    Ulx = 288,                     /* Ulx  */
    UBq = 289,                     /* UBq  */
    UGy = 290,                     /* UGy  */
    USv = 291,                     /* USv  */
    Urad = 292,                    /* Urad  */
    Usr = 293,                     /* Usr  */
    PUIS = 294,                    /* PUIS  */
    PP = 295,                      /* PP  */
    POINT = 296,                   /* POINT  */
    BARRE = 297,                   /* BARRE  */
    Uda = 298,                     /* Uda  */
    Uma = 299,                     /* Uma  */
    Usa = 300,                     /* Usa  */
    Utr = 301,                     /* Utr  */
    Urpm = 302,                    /* Urpm  */
    Uangs = 303,                   /* Uangs  */
    Ubarn = 304,                   /* Ubarn  */
    Uare = 305,                    /* Uare  */
    Ul = 306,                      /* Ul  */
    Ut = 307,                      /* Ut  */
    Ubar = 308,                    /* Ubar  */
    UeV = 309,                     /* UeV  */
    Uuam = 310,                    /* Uuam  */
    Signif = 311,                  /* Signif  */
    PlusminPC = 312                /* PlusminPC  */
  };
  typedef enum yytokentype yytoken_kind_t;
#endif

/* Value type.  */
#if ! defined YYSTYPE && ! defined YYSTYPE_IS_DECLARED
typedef int YYSTYPE;
# define YYSTYPE_IS_TRIVIAL 1
# define YYSTYPE_IS_DECLARED 1
#endif


extern YYSTYPE yylval;


int yyparse (void);



/* Symbol kind.  */
enum yysymbol_kind_t
{
  YYSYMBOL_YYEMPTY = -2,
  YYSYMBOL_YYEOF = 0,                      /* "end of file"  */
  YYSYMBOL_YYerror = 1,                    /* error  */
  YYSYMBOL_YYUNDEF = 2,                    /* "invalid token"  */
  YYSYMBOL_EE = 3,                         /* EE  */
  YYSYMBOL_DECIMAL = 4,                    /* DECIMAL  */
  YYSYMBOL_INT = 5,                        /* INT  */
  YYSYMBOL_SPC = 6,                        /* SPC  */
  YYSYMBOL_COLON = 7,                      /* COLON  */
  YYSYMBOL_Uh = 8,                         /* Uh  */
  YYSYMBOL_Umin = 9,                       /* Umin  */
  YYSYMBOL_Um = 10,                        /* Um  */
  YYSYMBOL_Ug = 11,                        /* Ug  */
  YYSYMBOL_Us = 12,                        /* Us  */
  YYSYMBOL_UA = 13,                        /* UA  */
  YYSYMBOL_UK = 14,                        /* UK  */
  YYSYMBOL_Umol = 15,                      /* Umol  */
  YYSYMBOL_Ucd = 16,                       /* Ucd  */
  YYSYMBOL_UHz = 17,                       /* UHz  */
  YYSYMBOL_UN = 18,                        /* UN  */
  YYSYMBOL_UPa = 19,                       /* UPa  */
  YYSYMBOL_UJ = 20,                        /* UJ  */
  YYSYMBOL_UW = 21,                        /* UW  */
  YYSYMBOL_UC = 22,                        /* UC  */
  YYSYMBOL_UVA = 23,                       /* UVA  */
  YYSYMBOL_Uvar = 24,                      /* Uvar  */
  YYSYMBOL_UV = 25,                        /* UV  */
  YYSYMBOL_Uohm = 26,                      /* Uohm  */
  YYSYMBOL_US = 27,                        /* US  */
  YYSYMBOL_UF = 28,                        /* UF  */
  YYSYMBOL_UT = 29,                        /* UT  */
  YYSYMBOL_UWb = 30,                       /* UWb  */
  YYSYMBOL_UH = 31,                        /* UH  */
  YYSYMBOL_Ulm = 32,                       /* Ulm  */
  YYSYMBOL_Ulx = 33,                       /* Ulx  */
  YYSYMBOL_UBq = 34,                       /* UBq  */
  YYSYMBOL_UGy = 35,                       /* UGy  */
  YYSYMBOL_USv = 36,                       /* USv  */
  YYSYMBOL_Urad = 37,                      /* Urad  */
  YYSYMBOL_Usr = 38,                       /* Usr  */
  YYSYMBOL_PUIS = 39,                      /* PUIS  */
  YYSYMBOL_PP = 40,                        /* PP  */
  YYSYMBOL_POINT = 41,                     /* POINT  */
  YYSYMBOL_BARRE = 42,                     /* BARRE  */
  YYSYMBOL_Uda = 43,                       /* Uda  */
  YYSYMBOL_Uma = 44,                       /* Uma  */
  YYSYMBOL_Usa = 45,                       /* Usa  */
  YYSYMBOL_Utr = 46,                       /* Utr  */
  YYSYMBOL_Urpm = 47,                      /* Urpm  */
  YYSYMBOL_Uangs = 48,                     /* Uangs  */
  YYSYMBOL_Ubarn = 49,                     /* Ubarn  */
  YYSYMBOL_Uare = 50,                      /* Uare  */
  YYSYMBOL_Ul = 51,                        /* Ul  */
  YYSYMBOL_Ut = 52,                        /* Ut  */
  YYSYMBOL_Ubar = 53,                      /* Ubar  */
  YYSYMBOL_UeV = 54,                       /* UeV  */
  YYSYMBOL_Uuam = 55,                      /* Uuam  */
  YYSYMBOL_Signif = 56,                    /* Signif  */
  YYSYMBOL_PlusminPC = 57,                 /* PlusminPC  */
  YYSYMBOL_YYACCEPT = 58,                  /* $accept  */
  YYSYMBOL_but = 59,                       /* but  */
  YYSYMBOL_valeur_mixte = 60,              /* valeur_mixte  */
  YYSYMBOL_style = 61,                     /* style  */
  YYSYMBOL_valeur = 62,                    /* valeur  */
  YYSYMBOL_sans_unite = 63,                /* sans_unite  */
  YYSYMBOL_spc = 64,                       /* spc  */
  YYSYMBOL_unite = 65,                     /* unite  */
  YYSYMBOL_suiv_unit = 66,                 /* suiv_unit  */
  YYSYMBOL_point = 67,                     /* point  */
  YYSYMBOL_prim_unit1 = 68,                /* prim_unit1  */
  YYSYMBOL_prim_unit = 69,                 /* prim_unit  */
  YYSYMBOL_puissance01 = 70,               /* puissance01  */
  YYSYMBOL_decimal = 71,                   /* decimal  */
  YYSYMBOL_prefixe = 72,                   /* prefixe  */
  YYSYMBOL_base_unite = 73                 /* base_unite  */
};
typedef enum yysymbol_kind_t yysymbol_kind_t;




#ifdef short
# undef short
#endif

/* On compilers that do not define __PTRDIFF_MAX__ etc., make sure
   <limits.h> and (if available) <stdint.h> are included
   so that the code can choose integer types of a good width.  */

#ifndef __PTRDIFF_MAX__
# include <limits.h> /* INFRINGES ON USER NAME SPACE */
# if defined __STDC_VERSION__ && 199901 <= __STDC_VERSION__
#  include <stdint.h> /* INFRINGES ON USER NAME SPACE */
#  define YY_STDINT_H
# endif
#endif

/* Narrow types that promote to a signed type and that can represent a
   signed or unsigned integer of at least N bits.  In tables they can
   save space and decrease cache pressure.  Promoting to a signed type
   helps avoid bugs in integer arithmetic.  */

#ifdef __INT_LEAST8_MAX__
typedef __INT_LEAST8_TYPE__ yytype_int8;
#elif defined YY_STDINT_H
typedef int_least8_t yytype_int8;
#else
typedef signed char yytype_int8;
#endif

#ifdef __INT_LEAST16_MAX__
typedef __INT_LEAST16_TYPE__ yytype_int16;
#elif defined YY_STDINT_H
typedef int_least16_t yytype_int16;
#else
typedef short yytype_int16;
#endif

/* Work around bug in HP-UX 11.23, which defines these macros
   incorrectly for preprocessor constants.  This workaround can likely
   be removed in 2023, as HPE has promised support for HP-UX 11.23
   (aka HP-UX 11i v2) only through the end of 2022; see Table 2 of
   <https://h20195.www2.hpe.com/V2/getpdf.aspx/4AA4-7673ENW.pdf>.  */
#ifdef __hpux
# undef UINT_LEAST8_MAX
# undef UINT_LEAST16_MAX
# define UINT_LEAST8_MAX 255
# define UINT_LEAST16_MAX 65535
#endif

#if defined __UINT_LEAST8_MAX__ && __UINT_LEAST8_MAX__ <= __INT_MAX__
typedef __UINT_LEAST8_TYPE__ yytype_uint8;
#elif (!defined __UINT_LEAST8_MAX__ && defined YY_STDINT_H \
       && UINT_LEAST8_MAX <= INT_MAX)
typedef uint_least8_t yytype_uint8;
#elif !defined __UINT_LEAST8_MAX__ && UCHAR_MAX <= INT_MAX
typedef unsigned char yytype_uint8;
#else
typedef short yytype_uint8;
#endif

#if defined __UINT_LEAST16_MAX__ && __UINT_LEAST16_MAX__ <= __INT_MAX__
typedef __UINT_LEAST16_TYPE__ yytype_uint16;
#elif (!defined __UINT_LEAST16_MAX__ && defined YY_STDINT_H \
       && UINT_LEAST16_MAX <= INT_MAX)
typedef uint_least16_t yytype_uint16;
#elif !defined __UINT_LEAST16_MAX__ && USHRT_MAX <= INT_MAX
typedef unsigned short yytype_uint16;
#else
typedef int yytype_uint16;
#endif

#ifndef YYPTRDIFF_T
# if defined __PTRDIFF_TYPE__ && defined __PTRDIFF_MAX__
#  define YYPTRDIFF_T __PTRDIFF_TYPE__
#  define YYPTRDIFF_MAXIMUM __PTRDIFF_MAX__
# elif defined PTRDIFF_MAX
#  ifndef ptrdiff_t
#   include <stddef.h> /* INFRINGES ON USER NAME SPACE */
#  endif
#  define YYPTRDIFF_T ptrdiff_t
#  define YYPTRDIFF_MAXIMUM PTRDIFF_MAX
# else
#  define YYPTRDIFF_T long
#  define YYPTRDIFF_MAXIMUM LONG_MAX
# endif
#endif

#ifndef YYSIZE_T
# ifdef __SIZE_TYPE__
#  define YYSIZE_T __SIZE_TYPE__
# elif defined size_t
#  define YYSIZE_T size_t
# elif defined __STDC_VERSION__ && 199901 <= __STDC_VERSION__
#  include <stddef.h> /* INFRINGES ON USER NAME SPACE */
#  define YYSIZE_T size_t
# else
#  define YYSIZE_T unsigned
# endif
#endif

#define YYSIZE_MAXIMUM                                  \
  YY_CAST (YYPTRDIFF_T,                                 \
           (YYPTRDIFF_MAXIMUM < YY_CAST (YYSIZE_T, -1)  \
            ? YYPTRDIFF_MAXIMUM                         \
            : YY_CAST (YYSIZE_T, -1)))

#define YYSIZEOF(X) YY_CAST (YYPTRDIFF_T, sizeof (X))


/* Stored state numbers (used for stacks). */
typedef yytype_int8 yy_state_t;

/* State numbers in computations.  */
typedef int yy_state_fast_t;

#ifndef YY_
# if defined YYENABLE_NLS && YYENABLE_NLS
#  if ENABLE_NLS
#   include <libintl.h> /* INFRINGES ON USER NAME SPACE */
#   define YY_(Msgid) dgettext ("bison-runtime", Msgid)
#  endif
# endif
# ifndef YY_
#  define YY_(Msgid) Msgid
# endif
#endif


#ifndef YY_ATTRIBUTE_PURE
# if defined __GNUC__ && 2 < __GNUC__ + (96 <= __GNUC_MINOR__)
#  define YY_ATTRIBUTE_PURE __attribute__ ((__pure__))
# else
#  define YY_ATTRIBUTE_PURE
# endif
#endif

#ifndef YY_ATTRIBUTE_UNUSED
# if defined __GNUC__ && 2 < __GNUC__ + (7 <= __GNUC_MINOR__)
#  define YY_ATTRIBUTE_UNUSED __attribute__ ((__unused__))
# else
#  define YY_ATTRIBUTE_UNUSED
# endif
#endif

/* Suppress unused-variable warnings by "using" E.  */
#if ! defined lint || defined __GNUC__
# define YY_USE(E) ((void) (E))
#else
# define YY_USE(E) /* empty */
#endif

/* Suppress an incorrect diagnostic about yylval being uninitialized.  */
#if defined __GNUC__ && ! defined __ICC && 406 <= __GNUC__ * 100 + __GNUC_MINOR__
# if __GNUC__ * 100 + __GNUC_MINOR__ < 407
#  define YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN                           \
    _Pragma ("GCC diagnostic push")                                     \
    _Pragma ("GCC diagnostic ignored \"-Wuninitialized\"")
# else
#  define YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN                           \
    _Pragma ("GCC diagnostic push")                                     \
    _Pragma ("GCC diagnostic ignored \"-Wuninitialized\"")              \
    _Pragma ("GCC diagnostic ignored \"-Wmaybe-uninitialized\"")
# endif
# define YY_IGNORE_MAYBE_UNINITIALIZED_END      \
    _Pragma ("GCC diagnostic pop")
#else
# define YY_INITIAL_VALUE(Value) Value
#endif
#ifndef YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN
# define YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN
# define YY_IGNORE_MAYBE_UNINITIALIZED_END
#endif
#ifndef YY_INITIAL_VALUE
# define YY_INITIAL_VALUE(Value) /* Nothing. */
#endif

#if defined __cplusplus && defined __GNUC__ && ! defined __ICC && 6 <= __GNUC__
# define YY_IGNORE_USELESS_CAST_BEGIN                          \
    _Pragma ("GCC diagnostic push")                            \
    _Pragma ("GCC diagnostic ignored \"-Wuseless-cast\"")
# define YY_IGNORE_USELESS_CAST_END            \
    _Pragma ("GCC diagnostic pop")
#endif
#ifndef YY_IGNORE_USELESS_CAST_BEGIN
# define YY_IGNORE_USELESS_CAST_BEGIN
# define YY_IGNORE_USELESS_CAST_END
#endif


#define YY_ASSERT(E) ((void) (0 && (E)))

#if !defined yyoverflow

/* The parser invokes alloca or malloc; define the necessary symbols.  */

# ifdef YYSTACK_USE_ALLOCA
#  if YYSTACK_USE_ALLOCA
#   ifdef __GNUC__
#    define YYSTACK_ALLOC __builtin_alloca
#   elif defined __BUILTIN_VA_ARG_INCR
#    include <alloca.h> /* INFRINGES ON USER NAME SPACE */
#   elif defined _AIX
#    define YYSTACK_ALLOC __alloca
#   elif defined _MSC_VER
#    include <malloc.h> /* INFRINGES ON USER NAME SPACE */
#    define alloca _alloca
#   else
#    define YYSTACK_ALLOC alloca
#    if ! defined _ALLOCA_H && ! defined EXIT_SUCCESS
#     include <stdlib.h> /* INFRINGES ON USER NAME SPACE */
      /* Use EXIT_SUCCESS as a witness for stdlib.h.  */
#     ifndef EXIT_SUCCESS
#      define EXIT_SUCCESS 0
#     endif
#    endif
#   endif
#  endif
# endif

# ifdef YYSTACK_ALLOC
   /* Pacify GCC's 'empty if-body' warning.  */
#  define YYSTACK_FREE(Ptr) do { /* empty */; } while (0)
#  ifndef YYSTACK_ALLOC_MAXIMUM
    /* The OS might guarantee only one guard page at the bottom of the stack,
       and a page size can be as small as 4096 bytes.  So we cannot safely
       invoke alloca (N) if N exceeds 4096.  Use a slightly smaller number
       to allow for a few compiler-allocated temporary stack slots.  */
#   define YYSTACK_ALLOC_MAXIMUM 4032 /* reasonable circa 2006 */
#  endif
# else
#  define YYSTACK_ALLOC YYMALLOC
#  define YYSTACK_FREE YYFREE
#  ifndef YYSTACK_ALLOC_MAXIMUM
#   define YYSTACK_ALLOC_MAXIMUM YYSIZE_MAXIMUM
#  endif
#  if (defined __cplusplus && ! defined EXIT_SUCCESS \
       && ! ((defined YYMALLOC || defined malloc) \
             && (defined YYFREE || defined free)))
#   include <stdlib.h> /* INFRINGES ON USER NAME SPACE */
#   ifndef EXIT_SUCCESS
#    define EXIT_SUCCESS 0
#   endif
#  endif
#  ifndef YYMALLOC
#   define YYMALLOC malloc
#   if ! defined malloc && ! defined EXIT_SUCCESS
void *malloc (YYSIZE_T); /* INFRINGES ON USER NAME SPACE */
#   endif
#  endif
#  ifndef YYFREE
#   define YYFREE free
#   if ! defined free && ! defined EXIT_SUCCESS
void free (void *); /* INFRINGES ON USER NAME SPACE */
#   endif
#  endif
# endif
#endif /* !defined yyoverflow */

#if (! defined yyoverflow \
     && (! defined __cplusplus \
         || (defined YYSTYPE_IS_TRIVIAL && YYSTYPE_IS_TRIVIAL)))

/* A type that is properly aligned for any stack member.  */
union yyalloc
{
  yy_state_t yyss_alloc;
  YYSTYPE yyvs_alloc;
};

/* The size of the maximum gap between one aligned stack and the next.  */
# define YYSTACK_GAP_MAXIMUM (YYSIZEOF (union yyalloc) - 1)

/* The size of an array large to enough to hold all stacks, each with
   N elements.  */
# define YYSTACK_BYTES(N) \
     ((N) * (YYSIZEOF (yy_state_t) + YYSIZEOF (YYSTYPE)) \
      + YYSTACK_GAP_MAXIMUM)

# define YYCOPY_NEEDED 1

/* Relocate STACK from its old location to the new one.  The
   local variables YYSIZE and YYSTACKSIZE give the old and new number of
   elements in the stack, and YYPTR gives the new location of the
   stack.  Advance YYPTR to a properly aligned location for the next
   stack.  */
# define YYSTACK_RELOCATE(Stack_alloc, Stack)                           \
    do                                                                  \
      {                                                                 \
        YYPTRDIFF_T yynewbytes;                                         \
        YYCOPY (&yyptr->Stack_alloc, Stack, yysize);                    \
        Stack = &yyptr->Stack_alloc;                                    \
        yynewbytes = yystacksize * YYSIZEOF (*Stack) + YYSTACK_GAP_MAXIMUM; \
        yyptr += yynewbytes / YYSIZEOF (*yyptr);                        \
      }                                                                 \
    while (0)

#endif

#if defined YYCOPY_NEEDED && YYCOPY_NEEDED
/* Copy COUNT objects from SRC to DST.  The source and destination do
   not overlap.  */
# ifndef YYCOPY
#  if defined __GNUC__ && 1 < __GNUC__
#   define YYCOPY(Dst, Src, Count) \
      __builtin_memcpy (Dst, Src, YY_CAST (YYSIZE_T, (Count)) * sizeof (*(Src)))
#  else
#   define YYCOPY(Dst, Src, Count)              \
      do                                        \
        {                                       \
          YYPTRDIFF_T yyi;                      \
          for (yyi = 0; yyi < (Count); yyi++)   \
            (Dst)[yyi] = (Src)[yyi];            \
        }                                       \
      while (0)
#  endif
# endif
#endif /* !YYCOPY_NEEDED */

/* YYFINAL -- State number of the termination state.  */
#define YYFINAL  10
/* YYLAST -- Last index in YYTABLE.  */
#define YYLAST   153

/* YYNTOKENS -- Number of terminals.  */
#define YYNTOKENS  58
/* YYNNTS -- Number of nonterminals.  */
#define YYNNTS  16
/* YYNRULES -- Number of rules.  */
#define YYNRULES  77
/* YYNSTATES -- Number of states.  */
#define YYNSTATES  90

/* YYMAXUTOK -- Last valid token kind.  */
#define YYMAXUTOK   312


/* YYTRANSLATE(TOKEN-NUM) -- Symbol number corresponding to TOKEN-NUM
   as returned by yylex, with out-of-bounds checking.  */
#define YYTRANSLATE(YYX)                                \
  (0 <= (YYX) && (YYX) <= YYMAXUTOK                     \
   ? YY_CAST (yysymbol_kind_t, yytranslate[YYX])        \
   : YYSYMBOL_YYUNDEF)

/* YYTRANSLATE[TOKEN-NUM] -- Symbol number corresponding to TOKEN-NUM
   as returned by yylex.  */
static const yytype_int8 yytranslate[] =
{
       0,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     1,     2,     3,     4,
       5,     6,     7,     8,     9,    10,    11,    12,    13,    14,
      15,    16,    17,    18,    19,    20,    21,    22,    23,    24,
      25,    26,    27,    28,    29,    30,    31,    32,    33,    34,
      35,    36,    37,    38,    39,    40,    41,    42,    43,    44,
      45,    46,    47,    48,    49,    50,    51,    52,    53,    54,
      55,    56,    57
};

#if YYDEBUG
/* YYRLINE[YYN] -- Source line where rule number YYN was defined.  */
static const yytype_int16 yyrline[] =
{
       0,   270,   270,   271,   274,   284,   285,   296,   299,   300,
     304,   310,   319,   327,   337,   338,   341,   353,   356,   362,
     376,   380,   387,   394,   401,   408,   413,   441,   442,   445,
     446,   447,   448,   452,   477,   478,   479,   480,   481,   482,
     483,   484,   485,   486,   487,   488,   489,   490,   491,   492,
     493,   494,   495,   496,   497,   498,   499,   500,   501,   502,
     503,   504,   505,   506,   507,   508,   509,   510,   511,   512,
     513,   514,   515,   516,   517,   518,   519,   520
};
#endif

/** Accessing symbol of state STATE.  */
#define YY_ACCESSING_SYMBOL(State) YY_CAST (yysymbol_kind_t, yystos[State])

#if YYDEBUG || 0
/* The user-facing name of the symbol whose (internal) number is
   YYSYMBOL.  No bounds checking.  */
static const char *yysymbol_name (yysymbol_kind_t yysymbol) YY_ATTRIBUTE_UNUSED;

/* YYTNAME[SYMBOL-NUM] -- String name of the symbol SYMBOL-NUM.
   First, the terminals, then, starting at YYNTOKENS, nonterminals.  */
static const char *const yytname[] =
{
  "\"end of file\"", "error", "\"invalid token\"", "EE", "DECIMAL", "INT",
  "SPC", "COLON", "Uh", "Umin", "Um", "Ug", "Us", "UA", "UK", "Umol",
  "Ucd", "UHz", "UN", "UPa", "UJ", "UW", "UC", "UVA", "Uvar", "UV", "Uohm",
  "US", "UF", "UT", "UWb", "UH", "Ulm", "Ulx", "UBq", "UGy", "USv", "Urad",
  "Usr", "PUIS", "PP", "POINT", "BARRE", "Uda", "Uma", "Usa", "Utr",
  "Urpm", "Uangs", "Ubarn", "Uare", "Ul", "Ut", "Ubar", "UeV", "Uuam",
  "Signif", "PlusminPC", "$accept", "but", "valeur_mixte", "style",
  "valeur", "sans_unite", "spc", "unite", "suiv_unit", "point",
  "prim_unit1", "prim_unit", "puissance01", "decimal", "prefixe",
  "base_unite", YY_NULLPTR
};

static const char *
yysymbol_name (yysymbol_kind_t yysymbol)
{
  return yytname[yysymbol];
}
#endif

#define YYPACT_NINF (-71)

#define yypact_value_is_default(Yyn) \
  ((Yyn) == YYPACT_NINF)

#define YYTABLE_NINF (-12)

#define yytable_value_is_error(Yyn) \
  0

/* YYPACT[STATE-NUM] -- Index in YYTABLE of the portion describing
   STATE-NUM.  */
static const yytype_int8 yypact[] =
{
       9,     4,     8,    17,   -71,     2,   -71,     0,    13,    16,
     -71,   -71,    50,     9,   -71,   -71,    50,   -71,   -71,    98,
     -71,    98,   -71,   -71,   -71,   -71,   -71,   -71,   -71,   -71,
     -71,   -71,   -71,   -71,   -71,   -71,   -71,   -71,   -71,   -71,
      98,   -71,   -71,   -71,   -71,   -71,   -71,   -71,   -71,   -71,
     -71,   -71,   -71,   -71,   -71,   -71,   -71,   -71,   -71,   -71,
     -71,   -71,   -71,   -71,   -71,   -26,   -16,   -71,    98,   -71,
     -71,    18,   -37,   -71,   -71,   -71,   -71,   -71,   -71,   -71,
      50,   -71,    50,   -71,   -71,   -71,   -71,   -71,   -71,   -71
};

/* YYDEFACT[STATE-NUM] -- Default reduction number in state STATE-NUM.
   Performed when YYTABLE does not specify something else to do.  Zero
   means the default is an error.  */
static const yytype_int8 yydefact[] =
{
       0,    30,    29,     0,     2,    14,     3,    14,     0,     0,
       1,    15,     0,     0,    12,    13,     0,    31,    32,    34,
      35,    36,    37,    38,    39,    40,    41,    42,    43,    44,
      45,    46,    48,    51,    49,    50,    52,    53,    54,    55,
      47,    56,    57,    58,    59,    60,    61,    62,    63,    64,
      33,    65,    66,    67,    68,    69,    70,    71,    72,    73,
      74,    75,    76,    77,     6,     7,    27,    17,     0,    25,
       4,    14,     8,    34,    36,    47,    23,    21,    22,    20,
       0,    16,     0,    28,    26,    24,     9,    10,    19,    18
};

/* YYPGOTO[NTERM-NUM].  */
static const yytype_int8 yypgoto[] =
{
     -71,   -71,    12,   -71,   -71,   -71,    21,    11,   -71,   -71,
     -71,   -70,   -71,    15,   -71,   -18
};

/* YYDEFGOTO[NTERM-NUM].  */
static const yytype_int8 yydefgoto[] =
{
       0,     3,     4,    64,     5,     6,    16,    65,    81,    82,
      66,    67,    84,     7,    68,    69
};

/* YYTABLE[YYPACT[STATE-NUM]] -- What to do in state STATE-NUM.  If
   positive, shift that token.  If negative, reduce the rule whose
   number is the opposite.  If YYTABLE_NINF, syntax error.  */
static const yytype_int8 yytable[] =
{
     -11,    76,    -5,    77,    79,    80,    11,     8,    11,    12,
      88,     9,    89,     1,     2,    79,    80,    10,    17,    86,
      87,    18,    78,    83,    11,    70,    13,    72,    71,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
      85,     0,     0,     0,     0,     0,    14,    15,    19,    20,
      21,    22,    23,    24,    25,    26,    27,    28,    29,    30,
      31,    32,    33,    34,    35,    36,    37,    38,    39,    40,
      41,    42,    43,    44,    45,    46,    47,    48,    49,     0,
      50,     0,     0,    51,    52,    53,    54,    55,    56,    57,
      58,    59,    60,    61,    62,    63,    73,    20,    74,    22,
      23,    24,    25,    26,    27,    28,    29,    30,    31,    32,
      33,    34,    35,    36,    37,    38,    39,    75,    41,    42,
      43,    44,    45,    46,    47,    48,    49,     0,     0,     0,
       0,    51,    52,    53,    54,    55,    56,    57,    58,    59,
      60,    61,    62,    63
};

static const yytype_int8 yycheck[] =
{
       0,    19,     0,    21,    41,    42,     6,     3,     6,     7,
      80,     3,    82,     4,     5,    41,    42,     0,     5,    56,
      57,     5,    40,    39,     6,    13,     5,    16,    13,    -1,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,
      68,    -1,    -1,    -1,    -1,    -1,    56,    57,     8,     9,
      10,    11,    12,    13,    14,    15,    16,    17,    18,    19,
      20,    21,    22,    23,    24,    25,    26,    27,    28,    29,
      30,    31,    32,    33,    34,    35,    36,    37,    38,    -1,
      40,    -1,    -1,    43,    44,    45,    46,    47,    48,    49,
      50,    51,    52,    53,    54,    55,     8,     9,    10,    11,
      12,    13,    14,    15,    16,    17,    18,    19,    20,    21,
      22,    23,    24,    25,    26,    27,    28,    29,    30,    31,
      32,    33,    34,    35,    36,    37,    38,    -1,    -1,    -1,
      -1,    43,    44,    45,    46,    47,    48,    49,    50,    51,
      52,    53,    54,    55
};

/* YYSTOS[STATE-NUM] -- The symbol kind of the accessing symbol of
   state STATE-NUM.  */
static const yytype_int8 yystos[] =
{
       0,     4,     5,    59,    60,    62,    63,    71,     3,     3,
       0,     6,     7,    64,    56,    57,    64,     5,     5,     8,
       9,    10,    11,    12,    13,    14,    15,    16,    17,    18,
      19,    20,    21,    22,    23,    24,    25,    26,    27,    28,
      29,    30,    31,    32,    33,    34,    35,    36,    37,    38,
      40,    43,    44,    45,    46,    47,    48,    49,    50,    51,
      52,    53,    54,    55,    61,    65,    68,    69,    72,    73,
      60,    71,    65,     8,    10,    29,    73,    73,    73,    41,
      42,    66,    67,    39,    70,    73,    56,    57,    69,    69
};

/* YYR1[RULE-NUM] -- Symbol kind of the left-hand side of rule RULE-NUM.  */
static const yytype_int8 yyr1[] =
{
       0,    58,    59,    59,    60,    60,    60,    61,    62,    62,
      62,    63,    63,    63,    64,    64,    65,    65,    66,    66,
      67,    68,    68,    68,    68,    68,    69,    70,    70,    71,
      71,    71,    71,    72,    73,    73,    73,    73,    73,    73,
      73,    73,    73,    73,    73,    73,    73,    73,    73,    73,
      73,    73,    73,    73,    73,    73,    73,    73,    73,    73,
      73,    73,    73,    73,    73,    73,    73,    73,    73,    73,
      73,    73,    73,    73,    73,    73,    73,    73
};

/* YYR2[RULE-NUM] -- Number of symbols on the right-hand side of rule RULE-NUM.  */
static const yytype_int8 yyr2[] =
{
       0,     2,     1,     1,     3,     1,     3,     1,     3,     4,
       4,     1,     2,     2,     0,     1,     2,     1,     2,     2,
       1,     2,     2,     2,     2,     1,     2,     0,     1,     1,
       1,     3,     3,     1,     1,     1,     1,     1,     1,     1,
       1,     1,     1,     1,     1,     1,     1,     1,     1,     1,
       1,     1,     1,     1,     1,     1,     1,     1,     1,     1,
       1,     1,     1,     1,     1,     1,     1,     1,     1,     1,
       1,     1,     1,     1,     1,     1,     1,     1
};


enum { YYENOMEM = -2 };

#define yyerrok         (yyerrstatus = 0)
#define yyclearin       (yychar = YYEMPTY)

#define YYACCEPT        goto yyacceptlab
#define YYABORT         goto yyabortlab
#define YYERROR         goto yyerrorlab
#define YYNOMEM         goto yyexhaustedlab


#define YYRECOVERING()  (!!yyerrstatus)

#define YYBACKUP(Token, Value)                                    \
  do                                                              \
    if (yychar == YYEMPTY)                                        \
      {                                                           \
        yychar = (Token);                                         \
        yylval = (Value);                                         \
        YYPOPSTACK (yylen);                                       \
        yystate = *yyssp;                                         \
        goto yybackup;                                            \
      }                                                           \
    else                                                          \
      {                                                           \
        yyerror (YY_("syntax error: cannot back up")); \
        YYERROR;                                                  \
      }                                                           \
  while (0)

/* Backward compatibility with an undocumented macro.
   Use YYerror or YYUNDEF. */
#define YYERRCODE YYUNDEF


/* Enable debugging if requested.  */
#if YYDEBUG

# ifndef YYFPRINTF
#  include <stdio.h> /* INFRINGES ON USER NAME SPACE */
#  define YYFPRINTF fprintf
# endif

# define YYDPRINTF(Args)                        \
do {                                            \
  if (yydebug)                                  \
    YYFPRINTF Args;                             \
} while (0)




# define YY_SYMBOL_PRINT(Title, Kind, Value, Location)                    \
do {                                                                      \
  if (yydebug)                                                            \
    {                                                                     \
      YYFPRINTF (stderr, "%s ", Title);                                   \
      yy_symbol_print (stderr,                                            \
                  Kind, Value); \
      YYFPRINTF (stderr, "\n");                                           \
    }                                                                     \
} while (0)


/*-----------------------------------.
| Print this symbol's value on YYO.  |
`-----------------------------------*/

static void
yy_symbol_value_print (FILE *yyo,
                       yysymbol_kind_t yykind, YYSTYPE const * const yyvaluep)
{
  FILE *yyoutput = yyo;
  YY_USE (yyoutput);
  if (!yyvaluep)
    return;
  YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN
  YY_USE (yykind);
  YY_IGNORE_MAYBE_UNINITIALIZED_END
}


/*---------------------------.
| Print this symbol on YYO.  |
`---------------------------*/

static void
yy_symbol_print (FILE *yyo,
                 yysymbol_kind_t yykind, YYSTYPE const * const yyvaluep)
{
  YYFPRINTF (yyo, "%s %s (",
             yykind < YYNTOKENS ? "token" : "nterm", yysymbol_name (yykind));

  yy_symbol_value_print (yyo, yykind, yyvaluep);
  YYFPRINTF (yyo, ")");
}

/*------------------------------------------------------------------.
| yy_stack_print -- Print the state stack from its BOTTOM up to its |
| TOP (included).                                                   |
`------------------------------------------------------------------*/

static void
yy_stack_print (yy_state_t *yybottom, yy_state_t *yytop)
{
  YYFPRINTF (stderr, "Stack now");
  for (; yybottom <= yytop; yybottom++)
    {
      int yybot = *yybottom;
      YYFPRINTF (stderr, " %d", yybot);
    }
  YYFPRINTF (stderr, "\n");
}

# define YY_STACK_PRINT(Bottom, Top)                            \
do {                                                            \
  if (yydebug)                                                  \
    yy_stack_print ((Bottom), (Top));                           \
} while (0)


/*------------------------------------------------.
| Report that the YYRULE is going to be reduced.  |
`------------------------------------------------*/

static void
yy_reduce_print (yy_state_t *yyssp, YYSTYPE *yyvsp,
                 int yyrule)
{
  int yylno = yyrline[yyrule];
  int yynrhs = yyr2[yyrule];
  int yyi;
  YYFPRINTF (stderr, "Reducing stack by rule %d (line %d):\n",
             yyrule - 1, yylno);
  /* The symbols being reduced.  */
  for (yyi = 0; yyi < yynrhs; yyi++)
    {
      YYFPRINTF (stderr, "   $%d = ", yyi + 1);
      yy_symbol_print (stderr,
                       YY_ACCESSING_SYMBOL (+yyssp[yyi + 1 - yynrhs]),
                       &yyvsp[(yyi + 1) - (yynrhs)]);
      YYFPRINTF (stderr, "\n");
    }
}

# define YY_REDUCE_PRINT(Rule)          \
do {                                    \
  if (yydebug)                          \
    yy_reduce_print (yyssp, yyvsp, Rule); \
} while (0)

/* Nonzero means print parse trace.  It is left uninitialized so that
   multiple parsers can coexist.  */
int yydebug;
#else /* !YYDEBUG */
# define YYDPRINTF(Args) ((void) 0)
# define YY_SYMBOL_PRINT(Title, Kind, Value, Location)
# define YY_STACK_PRINT(Bottom, Top)
# define YY_REDUCE_PRINT(Rule)
#endif /* !YYDEBUG */


/* YYINITDEPTH -- initial size of the parser's stacks.  */
#ifndef YYINITDEPTH
# define YYINITDEPTH 200
#endif

/* YYMAXDEPTH -- maximum size the stacks can grow to (effective only
   if the built-in stack extension method is used).

   Do not make this value too large; the results are undefined if
   YYSTACK_ALLOC_MAXIMUM < YYSTACK_BYTES (YYMAXDEPTH)
   evaluated with infinite-precision integer arithmetic.  */

#ifndef YYMAXDEPTH
# define YYMAXDEPTH 10000
#endif






/*-----------------------------------------------.
| Release the memory associated to this symbol.  |
`-----------------------------------------------*/

static void
yydestruct (const char *yymsg,
            yysymbol_kind_t yykind, YYSTYPE *yyvaluep)
{
  YY_USE (yyvaluep);
  if (!yymsg)
    yymsg = "Deleting";
  YY_SYMBOL_PRINT (yymsg, yykind, yyvaluep, yylocationp);

  YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN
  YY_USE (yykind);
  YY_IGNORE_MAYBE_UNINITIALIZED_END
}


/* Lookahead token kind.  */
int yychar;

/* The semantic value of the lookahead symbol.  */
YYSTYPE yylval;
/* Number of syntax errors so far.  */
int yynerrs;




/*----------.
| yyparse.  |
`----------*/

int
yyparse (void)
{
    yy_state_fast_t yystate = 0;
    /* Number of tokens to shift before error messages enabled.  */
    int yyerrstatus = 0;

    /* Refer to the stacks through separate pointers, to allow yyoverflow
       to reallocate them elsewhere.  */

    /* Their size.  */
    YYPTRDIFF_T yystacksize = YYINITDEPTH;

    /* The state stack: array, bottom, top.  */
    yy_state_t yyssa[YYINITDEPTH];
    yy_state_t *yyss = yyssa;
    yy_state_t *yyssp = yyss;

    /* The semantic value stack: array, bottom, top.  */
    YYSTYPE yyvsa[YYINITDEPTH];
    YYSTYPE *yyvs = yyvsa;
    YYSTYPE *yyvsp = yyvs;

  int yyn;
  /* The return value of yyparse.  */
  int yyresult;
  /* Lookahead symbol kind.  */
  yysymbol_kind_t yytoken = YYSYMBOL_YYEMPTY;
  /* The variables used to return semantic value and location from the
     action routines.  */
  YYSTYPE yyval;



#define YYPOPSTACK(N)   (yyvsp -= (N), yyssp -= (N))

  /* The number of symbols on the RHS of the reduced rule.
     Keep to zero when no symbol should be popped.  */
  int yylen = 0;

  YYDPRINTF ((stderr, "Starting parse\n"));

  yychar = YYEMPTY; /* Cause a token to be read.  */

  goto yysetstate;


/*------------------------------------------------------------.
| yynewstate -- push a new state, which is found in yystate.  |
`------------------------------------------------------------*/
yynewstate:
  /* In all cases, when you get here, the value and location stacks
     have just been pushed.  So pushing a state here evens the stacks.  */
  yyssp++;


/*--------------------------------------------------------------------.
| yysetstate -- set current state (the top of the stack) to yystate.  |
`--------------------------------------------------------------------*/
yysetstate:
  YYDPRINTF ((stderr, "Entering state %d\n", yystate));
  YY_ASSERT (0 <= yystate && yystate < YYNSTATES);
  YY_IGNORE_USELESS_CAST_BEGIN
  *yyssp = YY_CAST (yy_state_t, yystate);
  YY_IGNORE_USELESS_CAST_END
  YY_STACK_PRINT (yyss, yyssp);

  if (yyss + yystacksize - 1 <= yyssp)
#if !defined yyoverflow && !defined YYSTACK_RELOCATE
    YYNOMEM;
#else
    {
      /* Get the current used size of the three stacks, in elements.  */
      YYPTRDIFF_T yysize = yyssp - yyss + 1;

# if defined yyoverflow
      {
        /* Give user a chance to reallocate the stack.  Use copies of
           these so that the &'s don't force the real ones into
           memory.  */
        yy_state_t *yyss1 = yyss;
        YYSTYPE *yyvs1 = yyvs;

        /* Each stack pointer address is followed by the size of the
           data in use in that stack, in bytes.  This used to be a
           conditional around just the two extra args, but that might
           be undefined if yyoverflow is a macro.  */
        yyoverflow (YY_("memory exhausted"),
                    &yyss1, yysize * YYSIZEOF (*yyssp),
                    &yyvs1, yysize * YYSIZEOF (*yyvsp),
                    &yystacksize);
        yyss = yyss1;
        yyvs = yyvs1;
      }
# else /* defined YYSTACK_RELOCATE */
      /* Extend the stack our own way.  */
      if (YYMAXDEPTH <= yystacksize)
        YYNOMEM;
      yystacksize *= 2;
      if (YYMAXDEPTH < yystacksize)
        yystacksize = YYMAXDEPTH;

      {
        yy_state_t *yyss1 = yyss;
        union yyalloc *yyptr =
          YY_CAST (union yyalloc *,
                   YYSTACK_ALLOC (YY_CAST (YYSIZE_T, YYSTACK_BYTES (yystacksize))));
        if (! yyptr)
          YYNOMEM;
        YYSTACK_RELOCATE (yyss_alloc, yyss);
        YYSTACK_RELOCATE (yyvs_alloc, yyvs);
#  undef YYSTACK_RELOCATE
        if (yyss1 != yyssa)
          YYSTACK_FREE (yyss1);
      }
# endif

      yyssp = yyss + yysize - 1;
      yyvsp = yyvs + yysize - 1;

      YY_IGNORE_USELESS_CAST_BEGIN
      YYDPRINTF ((stderr, "Stack size increased to %ld\n",
                  YY_CAST (long, yystacksize)));
      YY_IGNORE_USELESS_CAST_END

      if (yyss + yystacksize - 1 <= yyssp)
        YYABORT;
    }
#endif /* !defined yyoverflow && !defined YYSTACK_RELOCATE */


  if (yystate == YYFINAL)
    YYACCEPT;

  goto yybackup;


/*-----------.
| yybackup.  |
`-----------*/
yybackup:
  /* Do appropriate processing given the current state.  Read a
     lookahead token if we need one and don't already have one.  */

  /* First try to decide what to do without reference to lookahead token.  */
  yyn = yypact[yystate];
  if (yypact_value_is_default (yyn))
    goto yydefault;

  /* Not known => get a lookahead token if don't already have one.  */

  /* YYCHAR is either empty, or end-of-input, or a valid lookahead.  */
  if (yychar == YYEMPTY)
    {
      YYDPRINTF ((stderr, "Reading a token\n"));
      yychar = yylex ();
    }

  if (yychar <= YYEOF)
    {
      yychar = YYEOF;
      yytoken = YYSYMBOL_YYEOF;
      YYDPRINTF ((stderr, "Now at end of input.\n"));
    }
  else if (yychar == YYerror)
    {
      /* The scanner already issued an error message, process directly
         to error recovery.  But do not keep the error token as
         lookahead, it is too special and may lead us to an endless
         loop in error recovery. */
      yychar = YYUNDEF;
      yytoken = YYSYMBOL_YYerror;
      goto yyerrlab1;
    }
  else
    {
      yytoken = YYTRANSLATE (yychar);
      YY_SYMBOL_PRINT ("Next token is", yytoken, &yylval, &yylloc);
    }

  /* If the proper action on seeing token YYTOKEN is to reduce or to
     detect an error, take that action.  */
  yyn += yytoken;
  if (yyn < 0 || YYLAST < yyn || yycheck[yyn] != yytoken)
    goto yydefault;
  yyn = yytable[yyn];
  if (yyn <= 0)
    {
      if (yytable_value_is_error (yyn))
        goto yyerrlab;
      yyn = -yyn;
      goto yyreduce;
    }

  /* Count tokens shifted since error; after three, turn off error
     status.  */
  if (yyerrstatus)
    yyerrstatus--;

  /* Shift the lookahead token.  */
  YY_SYMBOL_PRINT ("Shifting", yytoken, &yylval, &yylloc);
  yystate = yyn;
  YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN
  *++yyvsp = yylval;
  YY_IGNORE_MAYBE_UNINITIALIZED_END

  /* Discard the shifted token.  */
  yychar = YYEMPTY;
  goto yynewstate;


/*-----------------------------------------------------------.
| yydefault -- do the default action for the current state.  |
`-----------------------------------------------------------*/
yydefault:
  yyn = yydefact[yystate];
  if (yyn == 0)
    goto yyerrlab;
  goto yyreduce;


/*-----------------------------.
| yyreduce -- do a reduction.  |
`-----------------------------*/
yyreduce:
  /* yyn is the number of a rule to reduce with.  */
  yylen = yyr2[yyn];

  /* If YYLEN is nonzero, implement the default value of the action:
     '$$ = $1'.

     Otherwise, the following line sets YYVAL to garbage.
     This behavior is undocumented and Bison
     users should not rely upon it.  Assigning to YYVAL
     unconditionally makes the parser a bit smaller, and it avoids a
     GCC warning that YYVAL may be used uninitialized.  */
  yyval = yyvsp[1-yylen];


  YY_REDUCE_PRINT (yyn);
  switch (yyn)
    {
  case 2: /* but: valeur_mixte  */
#line 270 "unites.y"
                   {result = yyvsp[0];}
#line 1507 "unitesparser.cc"
    break;

  case 3: /* but: sans_unite  */
#line 271 "unites.y"
             {result = yyvsp[0];}
#line 1513 "unitesparser.cc"
    break;

  case 4: /* valeur_mixte: valeur spc valeur_mixte  */
#line 274 "unites.y"
                                       {
  int i;
  for(i=0; i < BU_LAST; i++){
    if (yyvsp[-2].base[i] != yyvsp[0].base[i]) yyerror ("not homogeneous units");
  }
  if (yyvsp[-2].multip <= yyvsp[0].maxmultip) yyerror ("incorrect multiple units ordering");
  yyval.val=yyvsp[-2].val*yyvsp[-2].multip+yyvsp[0].val*yyvsp[0].multip;
  yyval.multip=1; yyval.maxmultip = yyvsp[-2].multip;
  yyval.wanted_unit="";
}
#line 1528 "unitesparser.cc"
    break;

  case 5: /* valeur_mixte: valeur  */
#line 284 "unites.y"
         {yyval=yyvsp[0]; yyval.maxmultip=yyvsp[0].multip;yyval.wanted_unit="";}
#line 1534 "unitesparser.cc"
    break;

  case 6: /* valeur_mixte: valeur COLON style  */
#line 285 "unites.y"
                     {
  int i;
  yyval=yyvsp[-2]; yyval.maxmultip=yyvsp[-2].multip;
  for(i=0; i < BU_LAST; i++){
    if (yyvsp[-2].base[i] != yyvsp[0].base[i]) yyerror ("wanted unit not homogeneous");
  }  
  yyval.wanted_multip=yyvsp[0].multip;
  yyval.wanted_unit=yyvsp[0].s;
}
#line 1548 "unitesparser.cc"
    break;

  case 7: /* style: unite  */
#line 296 "unites.y"
              {yyval=yyvsp[0];}
#line 1554 "unitesparser.cc"
    break;

  case 8: /* valeur: decimal spc unite  */
#line 299 "unites.y"
                           {yyval=yyvsp[0]; yyval.val=val_decimal; yyval.signif=0; yyval.pcent=0; yyval.v=yyvsp[-2].v;}
#line 1560 "unitesparser.cc"
    break;

  case 9: /* valeur: decimal spc unite Signif  */
#line 300 "unites.y"
                           {
  yyval=yyvsp[-1]; yyval.val=val_decimal; 
  yyval.signif=val_int; yyval.pcent=0;
}
#line 1569 "unitesparser.cc"
    break;

  case 10: /* valeur: decimal spc unite PlusminPC  */
#line 304 "unites.y"
                              {
  yyval=yyvsp[-1]; yyval.val=val_decimal; 
  yyval.pcent=val_int; yyval.signif=0;
}
#line 1578 "unitesparser.cc"
    break;

  case 11: /* sans_unite: decimal  */
#line 310 "unites.y"
                    {
  int i;
  yyval=yyvsp[0];
  yyval.val=val_decimal; 
  for (i=0; i < BU_LAST; i++){yyval.base[i]=unites[TUnull].base[i];} 
  yyval.multip=1.0; 
  yyval.signif=0; yyval.pcent=0;
  yyval.wanted_unit="";
}
#line 1592 "unitesparser.cc"
    break;

  case 12: /* sans_unite: decimal Signif  */
#line 319 "unites.y"
                 {
  int i;
  yyval=yyvsp[-1];
  yyval.val=val_decimal; 
  for (i=0; i < BU_LAST; i++){yyval.base[i]=unites[TUnull].base[i];} 
  yyval.multip=1.0; 
  yyval.signif=val_int; yyval.pcent=0;
}
#line 1605 "unitesparser.cc"
    break;

  case 13: /* sans_unite: decimal PlusminPC  */
#line 327 "unites.y"
                    {
  int i;
  yyval=yyvsp[-1];
  yyval.val=val_decimal; 
  for (i=0; i < BU_LAST; i++){yyval.base[i]=unites[TUnull].base[i];} 
  yyval.multip=1.0; 
  yyval.signif=0; yyval.pcent=val_int;
}
#line 1618 "unitesparser.cc"
    break;

  case 16: /* unite: unite suiv_unit  */
#line 341 "unites.y"
                       {
  int index;
  yyval.unite = TU_LAST; /* unknown unit (not given) */
  strncpy(buffer,yyvsp[-1].s,MAXBUF); 
  strncat(buffer,yyvsp[0].s,MAXBUF-strlen(yyvsp[-1].s)); 
  free(yyvsp[-1].s); free(yyvsp[0].s);
  yyval.s=strdup(buffer);
  for(index=0; index< BU_LAST; index++){
    yyval.base[index] = yyvsp[-1].base[index]+yyvsp[0].base[index] ; 
  }
  yyval.multip = yyvsp[-1].multip*yyvsp[0].multip;
}
#line 1635 "unitesparser.cc"
    break;

  case 17: /* unite: prim_unit  */
#line 353 "unites.y"
            { yyval=yyvsp[0]; }
#line 1641 "unitesparser.cc"
    break;

  case 18: /* suiv_unit: point prim_unit  */
#line 356 "unites.y"
                           {
  yyval=yyvsp[0]; strncpy(buffer,".",MAXBUF); 
  strncat(buffer,yyvsp[0].s,MAXBUF-1); 
  free(yyvsp[0].s);
  yyval.s=strdup(buffer);
}
#line 1652 "unitesparser.cc"
    break;

  case 19: /* suiv_unit: BARRE prim_unit  */
#line 362 "unites.y"
                 {
  int index;
  yyval=yyvsp[0]; 
  yyval.multip = 1/ yyval.multip;
  strncpy(buffer,"/",MAXBUF); 
  strncat(buffer,yyvsp[0].s,MAXBUF-1); 
  free(yyvsp[0].s);
  yyval.s=strdup(buffer);
  for(index=0; index< BU_LAST; index++){
    yyval.base[index] *= -1; 
  }
}
#line 1669 "unitesparser.cc"
    break;

  case 21: /* prim_unit1: Um base_unite  */
#line 380 "unites.y"
              {
  yyval=yyvsp[0];
  strncpy(buffer,"m",MAXBUF); 
  strncat(buffer,yyvsp[0].s,MAXBUF-1); 
  free(yyvsp[0].s);
  yyval.s = strdup(buffer); yyval.multip*=1e-3; 
}
#line 1681 "unitesparser.cc"
    break;

  case 22: /* prim_unit1: UT base_unite  */
#line 387 "unites.y"
                {
  yyval=yyvsp[0];
  strncpy(buffer,"T",MAXBUF); 
  strncat(buffer,yyvsp[0].s,MAXBUF-1); 
  free(yyvsp[0].s);
  yyval.s = strdup(buffer); yyval.multip*=1e12;
}
#line 1693 "unitesparser.cc"
    break;

  case 23: /* prim_unit1: Uh base_unite  */
#line 394 "unites.y"
                {
  yyval=yyvsp[0];
  strncpy(buffer,"h",MAXBUF); 
  strncat(buffer,yyvsp[0].s,MAXBUF-1); 
  free(yyvsp[0].s);
  yyval.s = strdup(buffer); yyval.multip*=1e2;
}
#line 1705 "unitesparser.cc"
    break;

  case 24: /* prim_unit1: prefixe base_unite  */
#line 401 "unites.y"
                      {
  yyval=yyvsp[0];
  strncpy(buffer, yyvsp[-1].s,MAXBUF); 
  strncat(buffer, yyvsp[0].s, MAXBUF-strlen(yyvsp[-1].s));
  free(yyvsp[-1].s); free(yyvsp[0].s);yyval.s=strdup(buffer); 
  yyval.multip*=yyvsp[-1].multip;
  }
#line 1717 "unitesparser.cc"
    break;

  case 25: /* prim_unit1: base_unite  */
#line 408 "unites.y"
             {
  yyval=yyvsp[0];
}
#line 1725 "unitesparser.cc"
    break;

  case 26: /* prim_unit: prim_unit1 puissance01  */
#line 413 "unites.y"
                                   {
  int index;
  double r;

  yyval.i=yyvsp[0].i;
  strncpy(buffer, yyvsp[-1].s,MAXBUF);
  if (yyvsp[0].i!=1){
    strncat(buffer, "^%d",MAXBUF-strlen(yyvsp[-1].s)); 
    sprintf(buffer2, buffer, yyvsp[0].i);
  }
  else strncpy(buffer2,buffer,MAXBUF);
  yyval.s=strdup(buffer2); free(yyvsp[-1].s);
  for(index=0; index< BU_LAST; index++){
    yyval.base[index] = unites[yyvsp[-1].unite].base[index]*yyvsp[0].i;
  }
  if (yyvsp[0].i>0){
    for(index=0, r=1; index<yyvsp[0].i ; index++){
      r = r*yyval.multip;
    }
  } else {
    for(index=0, r=1; index>yyvsp[0].i ; index--){
      r = r* (1/yyval.multip);
    }
  }
  yyval.multip=r;
}
#line 1756 "unitesparser.cc"
    break;

  case 27: /* puissance01: %empty  */
#line 441 "unites.y"
                            {yyval.i=1;}
#line 1762 "unitesparser.cc"
    break;

  case 28: /* puissance01: PUIS  */
#line 442 "unites.y"
       {yyval.i = val_int;}
#line 1768 "unitesparser.cc"
    break;

  case 29: /* decimal: INT  */
#line 445 "unites.y"
              {yyval.val=val_decimal;}
#line 1774 "unitesparser.cc"
    break;

  case 30: /* decimal: DECIMAL  */
#line 446 "unites.y"
          {yyval.val=val_decimal;}
#line 1780 "unitesparser.cc"
    break;

  case 31: /* decimal: DECIMAL EE INT  */
#line 447 "unites.y"
                 {val_decimal=Decimal(yyvsp[-2].v); int e = atoi(yyvsp[0].v); val_decimal.multiplyByTen(e); yyval.val=val_decimal;}
#line 1786 "unitesparser.cc"
    break;

  case 32: /* decimal: INT EE INT  */
#line 448 "unites.y"
             {val_decimal=atoi(yyvsp[-2].v); int e = atoi(yyvsp[0].v); val_decimal.multiplyByTen(e); yyval.val=val_decimal;}
#line 1792 "unitesparser.cc"
    break;

  case 33: /* prefixe: PP  */
#line 452 "unites.y"
   {yyval.multip=1.0; char c=yyval.s[0]; 
 switch (c){
 case 'y' : yyval.multip = 1e-24; break;
 case 'z' : yyval.multip = 1e-21; break;
 case 'a' : yyval.multip = 1e-18; break;
 case 'f' : yyval.multip = 1e-15; break;
 case 'p' : yyval.multip = 1e-12; break;
 case 'n' : yyval.multip = 1e-9; break;
 case 'µ' : yyval.multip = 1e-6; break;
 case 'c' : yyval.multip = 1e-2; break;
 case 'd' : if (!strcmp (yyval.s,"da") ) yyval.multip = 10.0;
    else yyval.multip = 0.1; break;
 case 'h' : yyval.multip = 1e2; break;
 case 'k' : yyval.multip = 1e3; break;
 case 'M' : yyval.multip = 1e6; break;
 case 'G' : yyval.multip = 1e9; break;
 case 'P' : yyval.multip = 1e15; break;
 case 'E' : yyval.multip = 1e18; break;
 case 'Z' : yyval.multip = 1e21; break;
 case 'Y': yyval.multip = 1e24; break;
 }
}
#line 1819 "unitesparser.cc"
    break;

  case 34: /* base_unite: Uh  */
#line 477 "unites.y"
   {yyval.unite=TUh; yyval.s = strdup("h"); yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1825 "unitesparser.cc"
    break;

  case 35: /* base_unite: Umin  */
#line 478 "unites.y"
       {yyval.unite=TUmin;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1831 "unitesparser.cc"
    break;

  case 36: /* base_unite: Um  */
#line 479 "unites.y"
     {yyval.unite=TUm; yyval.s = strdup("m"); yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1837 "unitesparser.cc"
    break;

  case 37: /* base_unite: Ug  */
#line 480 "unites.y"
     {yyval.unite=TUg;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1843 "unitesparser.cc"
    break;

  case 38: /* base_unite: Us  */
#line 481 "unites.y"
     {yyval.unite=TUs;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1849 "unitesparser.cc"
    break;

  case 39: /* base_unite: UA  */
#line 482 "unites.y"
     { yyval.unite = TUA;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1855 "unitesparser.cc"
    break;

  case 40: /* base_unite: UK  */
#line 483 "unites.y"
     { yyval.unite = TUK;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1861 "unitesparser.cc"
    break;

  case 41: /* base_unite: Umol  */
#line 484 "unites.y"
       { yyval.unite = TUmol;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1867 "unitesparser.cc"
    break;

  case 42: /* base_unite: Ucd  */
#line 485 "unites.y"
      { yyval.unite = TUcd;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1873 "unitesparser.cc"
    break;

  case 43: /* base_unite: UHz  */
#line 486 "unites.y"
      { yyval.unite = TUHz;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1879 "unitesparser.cc"
    break;

  case 44: /* base_unite: UN  */
#line 487 "unites.y"
     { yyval.unite = TUN;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1885 "unitesparser.cc"
    break;

  case 45: /* base_unite: UPa  */
#line 488 "unites.y"
      { yyval.unite = TUPa;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1891 "unitesparser.cc"
    break;

  case 46: /* base_unite: UJ  */
#line 489 "unites.y"
     { yyval.unite = TUJ;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1897 "unitesparser.cc"
    break;

  case 47: /* base_unite: UT  */
#line 490 "unites.y"
     { yyval.unite = TUT; yyval.s = strdup("T"); yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1903 "unitesparser.cc"
    break;

  case 48: /* base_unite: UW  */
#line 491 "unites.y"
     { yyval.unite = TUW;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1909 "unitesparser.cc"
    break;

  case 49: /* base_unite: UVA  */
#line 492 "unites.y"
     { yyval.unite = TUVA;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1915 "unitesparser.cc"
    break;

  case 50: /* base_unite: Uvar  */
#line 493 "unites.y"
      { yyval.unite = TUvar;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1921 "unitesparser.cc"
    break;

  case 51: /* base_unite: UC  */
#line 494 "unites.y"
     { yyval.unite = TUC;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1927 "unitesparser.cc"
    break;

  case 52: /* base_unite: UV  */
#line 495 "unites.y"
     { yyval.unite = TUV;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1933 "unitesparser.cc"
    break;

  case 53: /* base_unite: Uohm  */
#line 496 "unites.y"
       { yyval.unite = TUohm;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1939 "unitesparser.cc"
    break;

  case 54: /* base_unite: US  */
#line 497 "unites.y"
     { yyval.unite = TUS;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1945 "unitesparser.cc"
    break;

  case 55: /* base_unite: UF  */
#line 498 "unites.y"
     { yyval.unite = TUF;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1951 "unitesparser.cc"
    break;

  case 56: /* base_unite: UWb  */
#line 499 "unites.y"
      { yyval.unite = TUWb;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1957 "unitesparser.cc"
    break;

  case 57: /* base_unite: UH  */
#line 500 "unites.y"
     { yyval.unite = TUH;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1963 "unitesparser.cc"
    break;

  case 58: /* base_unite: Ulm  */
#line 501 "unites.y"
      { yyval.unite = TUlm;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1969 "unitesparser.cc"
    break;

  case 59: /* base_unite: Ulx  */
#line 502 "unites.y"
      { yyval.unite = TUlx;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1975 "unitesparser.cc"
    break;

  case 60: /* base_unite: UBq  */
#line 503 "unites.y"
      { yyval.unite = TUBq;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1981 "unitesparser.cc"
    break;

  case 61: /* base_unite: UGy  */
#line 504 "unites.y"
      { yyval.unite = TUGy;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1987 "unitesparser.cc"
    break;

  case 62: /* base_unite: USv  */
#line 505 "unites.y"
      { yyval.unite = TUSv;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1993 "unitesparser.cc"
    break;

  case 63: /* base_unite: Urad  */
#line 506 "unites.y"
       { yyval.unite = TUrad;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 1999 "unitesparser.cc"
    break;

  case 64: /* base_unite: Usr  */
#line 507 "unites.y"
      { yyval.unite = TUsr;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2005 "unitesparser.cc"
    break;

  case 65: /* base_unite: Uda  */
#line 508 "unites.y"
      { yyval.unite = TUda;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2011 "unitesparser.cc"
    break;

  case 66: /* base_unite: Uma  */
#line 509 "unites.y"
      { yyval.unite = TUma;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2017 "unitesparser.cc"
    break;

  case 67: /* base_unite: Usa  */
#line 510 "unites.y"
      { yyval.unite = TUsa;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2023 "unitesparser.cc"
    break;

  case 68: /* base_unite: Utr  */
#line 511 "unites.y"
      { yyval.unite = TUtr;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2029 "unitesparser.cc"
    break;

  case 69: /* base_unite: Urpm  */
#line 512 "unites.y"
       { yyval.unite = TUrpm;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2035 "unitesparser.cc"
    break;

  case 70: /* base_unite: Uangs  */
#line 513 "unites.y"
        { yyval.unite = TUangs;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2041 "unitesparser.cc"
    break;

  case 71: /* base_unite: Ubarn  */
#line 514 "unites.y"
        { yyval.unite = TUbarn;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2047 "unitesparser.cc"
    break;

  case 72: /* base_unite: Uare  */
#line 515 "unites.y"
       { yyval.unite = TUare;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2053 "unitesparser.cc"
    break;

  case 73: /* base_unite: Ul  */
#line 516 "unites.y"
     { yyval.unite = TUl;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2059 "unitesparser.cc"
    break;

  case 74: /* base_unite: Ut  */
#line 517 "unites.y"
     { yyval.unite = TUt;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2065 "unitesparser.cc"
    break;

  case 75: /* base_unite: Ubar  */
#line 518 "unites.y"
       { yyval.unite = TUbar;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2071 "unitesparser.cc"
    break;

  case 76: /* base_unite: UeV  */
#line 519 "unites.y"
      { yyval.unite = TUeV;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2077 "unitesparser.cc"
    break;

  case 77: /* base_unite: Uuam  */
#line 520 "unites.y"
       { yyval.unite = TUuam;  yyval.multip=unites[yyval.unite].multiplicateur;}
#line 2083 "unitesparser.cc"
    break;


#line 2087 "unitesparser.cc"

      default: break;
    }
  /* User semantic actions sometimes alter yychar, and that requires
     that yytoken be updated with the new translation.  We take the
     approach of translating immediately before every use of yytoken.
     One alternative is translating here after every semantic action,
     but that translation would be missed if the semantic action invokes
     YYABORT, YYACCEPT, or YYERROR immediately after altering yychar or
     if it invokes YYBACKUP.  In the case of YYABORT or YYACCEPT, an
     incorrect destructor might then be invoked immediately.  In the
     case of YYERROR or YYBACKUP, subsequent parser actions might lead
     to an incorrect destructor call or verbose syntax error message
     before the lookahead is translated.  */
  YY_SYMBOL_PRINT ("-> $$ =", YY_CAST (yysymbol_kind_t, yyr1[yyn]), &yyval, &yyloc);

  YYPOPSTACK (yylen);
  yylen = 0;

  *++yyvsp = yyval;

  /* Now 'shift' the result of the reduction.  Determine what state
     that goes to, based on the state we popped back to and the rule
     number reduced by.  */
  {
    const int yylhs = yyr1[yyn] - YYNTOKENS;
    const int yyi = yypgoto[yylhs] + *yyssp;
    yystate = (0 <= yyi && yyi <= YYLAST && yycheck[yyi] == *yyssp
               ? yytable[yyi]
               : yydefgoto[yylhs]);
  }

  goto yynewstate;


/*--------------------------------------.
| yyerrlab -- here on detecting error.  |
`--------------------------------------*/
yyerrlab:
  /* Make sure we have latest lookahead translation.  See comments at
     user semantic actions for why this is necessary.  */
  yytoken = yychar == YYEMPTY ? YYSYMBOL_YYEMPTY : YYTRANSLATE (yychar);
  /* If not already recovering from an error, report this error.  */
  if (!yyerrstatus)
    {
      ++yynerrs;
      yyerror (YY_("syntax error"));
    }

  if (yyerrstatus == 3)
    {
      /* If just tried and failed to reuse lookahead token after an
         error, discard it.  */

      if (yychar <= YYEOF)
        {
          /* Return failure if at end of input.  */
          if (yychar == YYEOF)
            YYABORT;
        }
      else
        {
          yydestruct ("Error: discarding",
                      yytoken, &yylval);
          yychar = YYEMPTY;
        }
    }

  /* Else will try to reuse lookahead token after shifting the error
     token.  */
  goto yyerrlab1;


/*---------------------------------------------------.
| yyerrorlab -- error raised explicitly by YYERROR.  |
`---------------------------------------------------*/
yyerrorlab:
  /* Pacify compilers when the user code never invokes YYERROR and the
     label yyerrorlab therefore never appears in user code.  */
  if (0)
    YYERROR;
  ++yynerrs;

  /* Do not reclaim the symbols of the rule whose action triggered
     this YYERROR.  */
  YYPOPSTACK (yylen);
  yylen = 0;
  YY_STACK_PRINT (yyss, yyssp);
  yystate = *yyssp;
  goto yyerrlab1;


/*-------------------------------------------------------------.
| yyerrlab1 -- common code for both syntax error and YYERROR.  |
`-------------------------------------------------------------*/
yyerrlab1:
  yyerrstatus = 3;      /* Each real token shifted decrements this.  */

  /* Pop stack until we find a state that shifts the error token.  */
  for (;;)
    {
      yyn = yypact[yystate];
      if (!yypact_value_is_default (yyn))
        {
          yyn += YYSYMBOL_YYerror;
          if (0 <= yyn && yyn <= YYLAST && yycheck[yyn] == YYSYMBOL_YYerror)
            {
              yyn = yytable[yyn];
              if (0 < yyn)
                break;
            }
        }

      /* Pop the current state because it cannot handle the error token.  */
      if (yyssp == yyss)
        YYABORT;


      yydestruct ("Error: popping",
                  YY_ACCESSING_SYMBOL (yystate), yyvsp);
      YYPOPSTACK (1);
      yystate = *yyssp;
      YY_STACK_PRINT (yyss, yyssp);
    }

  YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN
  *++yyvsp = yylval;
  YY_IGNORE_MAYBE_UNINITIALIZED_END


  /* Shift the error token.  */
  YY_SYMBOL_PRINT ("Shifting", YY_ACCESSING_SYMBOL (yyn), yyvsp, yylsp);

  yystate = yyn;
  goto yynewstate;


/*-------------------------------------.
| yyacceptlab -- YYACCEPT comes here.  |
`-------------------------------------*/
yyacceptlab:
  yyresult = 0;
  goto yyreturnlab;


/*-----------------------------------.
| yyabortlab -- YYABORT comes here.  |
`-----------------------------------*/
yyabortlab:
  yyresult = 1;
  goto yyreturnlab;


/*-----------------------------------------------------------.
| yyexhaustedlab -- YYNOMEM (memory exhaustion) comes here.  |
`-----------------------------------------------------------*/
yyexhaustedlab:
  yyerror (YY_("memory exhausted"));
  yyresult = 2;
  goto yyreturnlab;


/*----------------------------------------------------------.
| yyreturnlab -- parsing is finished, clean up and return.  |
`----------------------------------------------------------*/
yyreturnlab:
  if (yychar != YYEMPTY)
    {
      /* Make sure we have latest lookahead translation.  See comments at
         user semantic actions for why this is necessary.  */
      yytoken = YYTRANSLATE (yychar);
      yydestruct ("Cleanup: discarding lookahead",
                  yytoken, &yylval);
    }
  /* Do not reclaim the symbols of the rule whose action triggered
     this YYABORT or YYACCEPT.  */
  YYPOPSTACK (yylen);
  YY_STACK_PRINT (yyss, yyssp);
  while (yyssp != yyss)
    {
      yydestruct ("Cleanup: popping",
                  YY_ACCESSING_SYMBOL (+*yyssp), yyvsp);
      YYPOPSTACK (1);
    }
#ifndef yyoverflow
  if (yyss != yyssa)
    YYSTACK_FREE (yyss);
#endif

  return yyresult;
}

#line 525 "unites.y"


#include "uniteslex.cc"
#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>

#ifdef RECODE_SUPPORT
  #include <recode.h>
#endif

#include <regex.h>

const char *program_name;
int isUTF8;

/* the program is below */

typedef enum {option_default, option_s, option_o, option_l} optiontype;

yyFlexLexer lexer;
yyFlexLexer * thelexer = &lexer;

int yylex(){
  return thelexer->yylex();
}


/**
 * this function is called when an error is detected. It will print a usable
 * hint about the detected error.
 * @param msg the error message.
 **/
inline int yyerror(const char * msg){
  printf("ERROR at %ld : %s\n", pos, msg);
  exit(1);
}

/**
 * this function can be used to debug new features. It outputs verbose
 * data describing the parsed expression. Messages are in French, with
 * Latin-1 encoding.
 **/
void test_verbeux(){
  int i;
  yyparse();
  if (result.s) {
    if (result.unite == TU_LAST){
      cout << result.s << " " << result.multip*result.val << " SI (équation aux dimensions : ";
      for (i=0; i<BU_LAST; i++){
	printf("%3d", result.base[i]);
      }
      printf(")\n");
    }
    else {
      if (result.i!=1) 
	cout <<  result.s << " (" << result.multip*result.val 
		  << " " << unites[result.unite].nom << ")^{" << result.i 
		  << "}\n";
      else 
	cout << result.s << " " << result.multip*result.val 
		  << " " << unites[result.unite].nom << "\n";
    }
  }
  else fprintf(stderr, "problème : result.s = null\n");
}

/**
 * this function is used to output a normalized string describing the
 * parsed data.
 **
 * here is the format of the output:
 * double int int int int int int int
 * which mean respectively ...
 **
 * value
 * power of the length unit (m)
 * power of the mass unit (kg)
 * power of the time unit (s)
 * power of the current unit (A)
 * power of the temperature unit (K)
 * power of the matter quantity unit (mol)
 * power of the light intensity (cd)
 * number of significative numbers
 * tolerance (as a percentage)
 **/
void sortie_normalisee(){
  int i,s=0,pc=0;

  yyparse();
  // the result will be displaied as a decimal number rather as a fraction
  cout << result.multip*result.val;
  if (count_signif){ // take significative numbers in account
    if (!result.signif) {
      s=significative(result.v);
    } else {
      s=result.signif;
    }
  }
  pc=result.pcent;
  for (i=0; i<BU_LAST; i++){
    printf(" %3d", result.base[i]);
  }
  printf("    %d    %d\n",s,pc);
}

/**
 * displays the unit and eventually the tolerance string
 * @param option may be "option_l" to enforce LaTeX encoding
 * @param unit the name of the unit
 * @param tolerance a percentage of tolerance. If it is non-zero, an
 * additional mention will be displayed to express a tolerance.
 **/
void printUnit(optiontype option, string unit, int tolerance){
  char * indexohm;
  char buffer[128];
  char *codedunit;

#ifdef RECODE_SUPPORT
  if(isUTF8) {
    RECODE_OUTER outer = recode_new_outer (true);
    RECODE_REQUEST request = recode_new_request (outer);
    recode_scan_request (request, "latin1..utf8"); 
    codedunit=strdup(recode_string(request,unit.c_str()));
  } else {
    codedunit=strdup(unit.c_str());
  }
#else
  codedunit=strdup(unit.c_str());
#endif

  if (option==option_l){
    strncpy(buffer, codedunit,sizeof(buffer));
    indexohm=strstr(buffer,"ohm");
    if (indexohm){
      strncpy(indexohm, "\\Omega", sizeof(buffer)-strlen("\\Omega")+strlen("ohm"));
    }
    printf(" %s",buffer);
  } else {
    printf(" %s",codedunit);
  }
  if (tolerance){
    if (option==option_l){
      printf(" \\pm %d\\,\\%%",tolerance);
    } else{
      printf(" +-%d%%",tolerance);
    }
  }
  printf("\n");
  free(codedunit);
}

Decimal my_rounded(Decimal r);
/**
 * Uses the rounding method which are taught to students: if the
 * decimal value is 0.5 or more, rounds away from zero; else
 * rounds towards zero
 * @param r the value to round
 * @return the rounded value
 **/
Decimal my_rounded(Decimal r){
  const char * s=r.c_str();
  const char * cur = strchr(s,'.');
  if (cur==NULL) return Decimal(s);
  char trunc[100];
  int l=cur-s; if (l>99) l=99;
  strncpy(trunc, s, l);
  cur++;
  if (*cur=='\0' || *cur-'5' <0) return Decimal(s);
  else { // the mantissa begins by 5, 6, 7, 8 or 9
    if (Decimal(0.0) <= r) return Decimal(s)+Decimal(1.0);
    else return Decimal(s)+Decimal(-1.0);
  }
}

Decimal my_rounded_signif(Decimal r, int s);
/**
 * rounds a number to keep "s" significant numbers.
 * if s == the number of digits before the decimal dot, this function
 * returns the same value as my_rounded(r)
 * @param r the value to round
 * @param s the number of significant digits
 * @return the rounded value
 **/
Decimal my_rounded_signif(Decimal r, int s){
  Decimal result=r;
  result.keepSignificant(s);
  return result;
}

/**
 * displays a value
 * @param option may be "option_l" to enforce LaTeX encoding
 * @param result the value issued by the parser
 * @param s a number to shift the decimal point. s>0 shifts the decimal
 * point to the right; s <0 shifts the decimal point to the left.
 **/
void printValue(optiontype option, yystype result, int s){
  char val[128],exp[128], *i, *j, *indexE;
  char buf[128];
  regex_t regex;
  regmatch_t matches[3];
  int l;
  int vallen;

  Decimal value=result.multip*result.val;
  if (value==0.0){
    printf("0");
    if (s>1){
      printf(".");
      for (int i=1; i<s; i++){
	printf("0");
      }
    }
    return;
  }
  value=my_rounded_signif(value, s);
  if (s<=1){
    snprintf(buf,sizeof(buf),"%1.0e", value.get_double() );
  } else {
    snprintf(buf,sizeof(buf),"%1.*e", s-1,value.get_double() );
  }
  // simplifications
  regcomp(&regex, "^(.*)(e[+-][0-9]+)$", REG_EXTENDED);
  regexec(&regex, buf, 3, matches,0);
  if (strcmp(buf+matches[2].rm_so,"e+00")==0) {
    // removing e+00
    *(buf+matches[2].rm_so)=0;
  }
  l=strlen(buf);
  if (*(buf+matches[2].rm_so+1)=='+'){
    j=buf+matches[2].rm_so+2;
    while (*j=='0') j++;
    for(i=buf+matches[2].rm_so+1; j<=buf+l; i++,j++){
      // erasing +0* after e
      *i=*j;
    }
  }
  if (*(buf+matches[2].rm_so+1)=='-'){
    j=buf+matches[2].rm_so+2;
    while (*j=='0') j++;
    for(i=buf+matches[2].rm_so+2; j<=buf+l; i++,j++){
      // erasing 0* after e-
      *i=*j;
    }
  }
  if (option==option_l){
    indexE=strstr(buf,"e");
    if (indexE){
      vallen=indexE-buf;
      strncpy(val,buf,vallen);
      val[vallen]=0;
      strncpy(exp,indexE+1,sizeof(exp));
      printf("%s\\cdot 10^{%s}\\,",val,exp);
    } else{
      printf("%s\\,",buf);
    }
  } else {
    printf("%s",buf);
  }
}

/**
 * parses the input and displays parsed data as a text
 * @param option may be "option_l" to enforce LaTeX enconding
 **
 * the output is formated as follows: <value unit>
 * where value is a number expressing the desired value, taking in account
 * the desired significant digits, and unit is a SI unit or some custom unit,
 * optionnally followed by "+- pcent %", pcent being the tolerance.
 **/
void sortie_texte(optiontype option){
  int i,j,
    s=0, pc=0,
    notfirst=0,
    trouve=0,
    nb_pref=sizeof(pref_units)/sizeof(pref_units[0]);

  yyparse();
  if (!result.signif) {
    // the number of significant digits must be computed from the given value
    s=significative(result.v);
  } else {
    // the number of significant digits has been declared
    s=result.signif;
  }
  pc=result.pcent;
  // rounds the value taking in account the number of significant digits
  if (result.wanted_unit.length()>0){
    result.multip /= result.wanted_multip;
  }else{ // set the multiplier to 1 if the input unit has been declared
    if (result.s && strlen(result.s)>0){
      result.multip = 1;
    }
  }
  // print the value
  printValue(option, result, s);
  // if a custom unit is wanted, use it
  if (result.wanted_unit.length()>0){
    printUnit(option, result.wanted_unit, pc);
    return;
  }
  // else print the given unit if it is declared
  if (result.s && strlen(result.s)>0){
    printUnit(option, result.s, pc);
    return;
  }
  // else search a preferred unit
  for (i=0; i<nb_pref; i++){
    trouve=(result.base[0]==pref_units[i].base[0]);
    for (j=1; j<BU_LAST; j++){
      trouve &= (result.base[j]==pref_units[i].base[j]);
    }
    if (trouve){
      printUnit(option, pref_units[i].sym, pc);
      return;
    }
  }
  // test whether there will be a visible unit
  int visible_unit=0;
  for (i=0; i<BU_LAST; i++){
    if (result.base[i]!=0) visible_unit=1;
  }
  if (result.wanted_unit.length()>0) visible_unit=1;
  if(visible_unit!=0){ // display a unit only if it has some sense!
    for (i=0; i<BU_LAST; i++){
      if (result.base[i]!=0){
	if (notfirst) printf("."); else printf(" ");
	printf("%s",unit_names[i]);
	notfirst=1;
	if (result.base[i]!=1){
	  if (option==option_l){
	    printf("^{%d}",result.base[i]);
	  } else {
	    printf("^%d",result.base[i]);
	  }
	}
      }
    }
    printUnit(option, "", pc);
  }
}

/**
 * main function
 * @param argc the number of arguments of the program's call
 * @param argv the vector of arguments
 * @return the exit code of the program
 **/
int main(int argc, char * argv[]){
  const char * optstr = "osl";
  char * envoption=getenv("units_option");
  // environmental option take precedence on command-line options

  optiontype option=option_default;
  
  int ch;
  while (-1 != (ch=getopt(argc,argv,optstr))){
    switch(ch){
    case 's': 
      option=option_s;
      break;
    case 'o':
      option=option_o;
      break;
    case 'l':
      option=option_l;
      break;
    default: 
      break;
    }
  }
  // environmental option take precedence on command-line options
  if (envoption && strncmp(envoption, "s", 2)==0) option=option_s;
  if (envoption && strncmp(envoption, "o", 2)==0) option=option_o;
  if (envoption && strncmp(envoption, "l", 2)==0) option=option_l;
#ifdef RECODE_SUPPORT
  // check whether we are in a UTF8 environment
  char *lc_all=getenv("LC_ALL");
  isUTF8 = (lc_all!= NULL && strstr(lc_all,"UTF-8"));
#endif
  program_name = argv[0];


switch(option){
  case option_s: 
    count_signif=1;
    sortie_normalisee();
    return 0;
    break;
  case option_o:
  case option_l:
    sortie_texte(option);
    return 0;
    break;
  default: 
    break;
  }
  // disabled; use only for debug purpose
  /*test_verbeux();*/
  sortie_normalisee();
  return 0;
}
