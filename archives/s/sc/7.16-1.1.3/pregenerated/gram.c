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
#line 17 "gram.y"

#include <stdlib.h>
#include <limits.h>

#ifdef USELOCALE
#include <locale.h>
#endif

#ifndef MSDOS
#include <unistd.h>
#endif

#include "compat.h"
#include "sc.h"

#define ENULL (struct enode *)0

#line 89 "y.tab.c"

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

/* Use api.header.include to #include this header
   instead of duplicating it here.  */
#ifndef YY_YY_Y_TAB_H_INCLUDED
# define YY_YY_Y_TAB_H_INCLUDED
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
    STRING = 258,                  /* STRING  */
    NUMBER = 259,                  /* NUMBER  */
    FNUMBER = 260,                 /* FNUMBER  */
    RANGE = 261,                   /* RANGE  */
    VAR = 262,                     /* VAR  */
    WORD = 263,                    /* WORD  */
    PLUGIN = 264,                  /* PLUGIN  */
    COL = 265,                     /* COL  */
    S_SHOW = 266,                  /* S_SHOW  */
    S_HIDE = 267,                  /* S_HIDE  */
    S_INSERTCOL = 268,             /* S_INSERTCOL  */
    S_OPENCOL = 269,               /* S_OPENCOL  */
    S_DELETECOL = 270,             /* S_DELETECOL  */
    S_YANKCOL = 271,               /* S_YANKCOL  */
    S_GETFORMAT = 272,             /* S_GETFORMAT  */
    S_FORMAT = 273,                /* S_FORMAT  */
    S_FMT = 274,                   /* S_FMT  */
    S_LET = 275,                   /* S_LET  */
    S_LABEL = 276,                 /* S_LABEL  */
    S_LEFTSTRING = 277,            /* S_LEFTSTRING  */
    S_RIGHTSTRING = 278,           /* S_RIGHTSTRING  */
    S_LEFTJUSTIFY = 279,           /* S_LEFTJUSTIFY  */
    S_RIGHTJUSTIFY = 280,          /* S_RIGHTJUSTIFY  */
    S_CENTER = 281,                /* S_CENTER  */
    S_COLOR = 282,                 /* S_COLOR  */
    S_ADDNOTE = 283,               /* S_ADDNOTE  */
    S_DELNOTE = 284,               /* S_DELNOTE  */
    S_GET = 285,                   /* S_GET  */
    S_PUT = 286,                   /* S_PUT  */
    S_MERGE = 287,                 /* S_MERGE  */
    S_WRITE = 288,                 /* S_WRITE  */
    S_TBL = 289,                   /* S_TBL  */
    S_COPY = 290,                  /* S_COPY  */
    S_MOVE = 291,                  /* S_MOVE  */
    S_ERASE = 292,                 /* S_ERASE  */
    S_YANK = 293,                  /* S_YANK  */
    S_FILL = 294,                  /* S_FILL  */
    S_SORT = 295,                  /* S_SORT  */
    S_LOCK = 296,                  /* S_LOCK  */
    S_UNLOCK = 297,                /* S_UNLOCK  */
    S_GOTO = 298,                  /* S_GOTO  */
    S_DEFINE = 299,                /* S_DEFINE  */
    S_UNDEFINE = 300,              /* S_UNDEFINE  */
    S_ABBREV = 301,                /* S_ABBREV  */
    S_UNABBREV = 302,              /* S_UNABBREV  */
    S_FRAME = 303,                 /* S_FRAME  */
    S_FRAMETOP = 304,              /* S_FRAMETOP  */
    S_FRAMEBOTTOM = 305,           /* S_FRAMEBOTTOM  */
    S_FRAMELEFT = 306,             /* S_FRAMELEFT  */
    S_FRAMERIGHT = 307,            /* S_FRAMERIGHT  */
    S_UNFRAME = 308,               /* S_UNFRAME  */
    S_VALUE = 309,                 /* S_VALUE  */
    S_MDIR = 310,                  /* S_MDIR  */
    S_AUTORUN = 311,               /* S_AUTORUN  */
    S_FKEY = 312,                  /* S_FKEY  */
    S_HISTFILE = 313,              /* S_HISTFILE  */
    S_SCEXT = 314,                 /* S_SCEXT  */
    S_ASCEXT = 315,                /* S_ASCEXT  */
    S_TBL0EXT = 316,               /* S_TBL0EXT  */
    S_TBLEXT = 317,                /* S_TBLEXT  */
    S_LATEXEXT = 318,              /* S_LATEXEXT  */
    S_SLATEXEXT = 319,             /* S_SLATEXEXT  */
    S_TEXEXT = 320,                /* S_TEXEXT  */
    S_SET = 321,                   /* S_SET  */
    S_UP = 322,                    /* S_UP  */
    S_DOWN = 323,                  /* S_DOWN  */
    S_LEFT = 324,                  /* S_LEFT  */
    S_RIGHT = 325,                 /* S_RIGHT  */
    S_ENDUP = 326,                 /* S_ENDUP  */
    S_ENDDOWN = 327,               /* S_ENDDOWN  */
    S_ENDLEFT = 328,               /* S_ENDLEFT  */
    S_ENDRIGHT = 329,              /* S_ENDRIGHT  */
    S_SELECT = 330,                /* S_SELECT  */
    S_INSERTROW = 331,             /* S_INSERTROW  */
    S_OPENROW = 332,               /* S_OPENROW  */
    S_DELETEROW = 333,             /* S_DELETEROW  */
    S_YANKROW = 334,               /* S_YANKROW  */
    S_PULL = 335,                  /* S_PULL  */
    S_PULLMERGE = 336,             /* S_PULLMERGE  */
    S_PULLROWS = 337,              /* S_PULLROWS  */
    S_PULLCOLS = 338,              /* S_PULLCOLS  */
    S_PULLXCHG = 339,              /* S_PULLXCHG  */
    S_PULLTP = 340,                /* S_PULLTP  */
    S_PULLFMT = 341,               /* S_PULLFMT  */
    S_PULLCOPY = 342,              /* S_PULLCOPY  */
    S_WHEREAMI = 343,              /* S_WHEREAMI  */
    S_GETNUM = 344,                /* S_GETNUM  */
    S_FGETNUM = 345,               /* S_FGETNUM  */
    S_GETSTRING = 346,             /* S_GETSTRING  */
    S_GETEXP = 347,                /* S_GETEXP  */
    S_GETFMT = 348,                /* S_GETFMT  */
    S_GETFRAME = 349,              /* S_GETFRAME  */
    S_GETRANGE = 350,              /* S_GETRANGE  */
    S_EVAL = 351,                  /* S_EVAL  */
    S_SEVAL = 352,                 /* S_SEVAL  */
    S_QUERY = 353,                 /* S_QUERY  */
    S_GETKEY = 354,                /* S_GETKEY  */
    S_ERROR = 355,                 /* S_ERROR  */
    S_RECALC = 356,                /* S_RECALC  */
    S_REDRAW = 357,                /* S_REDRAW  */
    S_QUIT = 358,                  /* S_QUIT  */
    S_STATUS = 359,                /* S_STATUS  */
    S_RUN = 360,                   /* S_RUN  */
    S_PLUGIN = 361,                /* S_PLUGIN  */
    S_PLUGOUT = 362,               /* S_PLUGOUT  */
    K_ERROR = 363,                 /* K_ERROR  */
    K_INVALID = 364,               /* K_INVALID  */
    K_FIXED = 365,                 /* K_FIXED  */
    K_SUM = 366,                   /* K_SUM  */
    K_PROD = 367,                  /* K_PROD  */
    K_AVG = 368,                   /* K_AVG  */
    K_STDDEV = 369,                /* K_STDDEV  */
    K_COUNT = 370,                 /* K_COUNT  */
    K_ROWS = 371,                  /* K_ROWS  */
    K_COLS = 372,                  /* K_COLS  */
    K_ABS = 373,                   /* K_ABS  */
    K_ACOS = 374,                  /* K_ACOS  */
    K_ASIN = 375,                  /* K_ASIN  */
    K_ATAN = 376,                  /* K_ATAN  */
    K_ATAN2 = 377,                 /* K_ATAN2  */
    K_CEIL = 378,                  /* K_CEIL  */
    K_COS = 379,                   /* K_COS  */
    K_EXP = 380,                   /* K_EXP  */
    K_FABS = 381,                  /* K_FABS  */
    K_FLOOR = 382,                 /* K_FLOOR  */
    K_HYPOT = 383,                 /* K_HYPOT  */
    K_LN = 384,                    /* K_LN  */
    K_LOG = 385,                   /* K_LOG  */
    K_PI = 386,                    /* K_PI  */
    K_POW = 387,                   /* K_POW  */
    K_SIN = 388,                   /* K_SIN  */
    K_SQRT = 389,                  /* K_SQRT  */
    K_TAN = 390,                   /* K_TAN  */
    K_DTR = 391,                   /* K_DTR  */
    K_RTD = 392,                   /* K_RTD  */
    K_MAX = 393,                   /* K_MAX  */
    K_MIN = 394,                   /* K_MIN  */
    K_RND = 395,                   /* K_RND  */
    K_ROUND = 396,                 /* K_ROUND  */
    K_IF = 397,                    /* K_IF  */
    K_PV = 398,                    /* K_PV  */
    K_FV = 399,                    /* K_FV  */
    K_PMT = 400,                   /* K_PMT  */
    K_HOUR = 401,                  /* K_HOUR  */
    K_MINUTE = 402,                /* K_MINUTE  */
    K_SECOND = 403,                /* K_SECOND  */
    K_MONTH = 404,                 /* K_MONTH  */
    K_DAY = 405,                   /* K_DAY  */
    K_YEAR = 406,                  /* K_YEAR  */
    K_NOW = 407,                   /* K_NOW  */
    K_DATE = 408,                  /* K_DATE  */
    K_DTS = 409,                   /* K_DTS  */
    K_TTS = 410,                   /* K_TTS  */
    K_FMT = 411,                   /* K_FMT  */
    K_SUBSTR = 412,                /* K_SUBSTR  */
    K_UPPER = 413,                 /* K_UPPER  */
    K_LOWER = 414,                 /* K_LOWER  */
    K_CAPITAL = 415,               /* K_CAPITAL  */
    K_STON = 416,                  /* K_STON  */
    K_EQS = 417,                   /* K_EQS  */
    K_EXT = 418,                   /* K_EXT  */
    K_NVAL = 419,                  /* K_NVAL  */
    K_SVAL = 420,                  /* K_SVAL  */
    K_LOOKUP = 421,                /* K_LOOKUP  */
    K_HLOOKUP = 422,               /* K_HLOOKUP  */
    K_VLOOKUP = 423,               /* K_VLOOKUP  */
    K_INDEX = 424,                 /* K_INDEX  */
    K_STINDEX = 425,               /* K_STINDEX  */
    K_AUTO = 426,                  /* K_AUTO  */
    K_AUTOCALC = 427,              /* K_AUTOCALC  */
    K_AUTOINSERT = 428,            /* K_AUTOINSERT  */
    K_AUTOWRAP = 429,              /* K_AUTOWRAP  */
    K_CSLOP = 430,                 /* K_CSLOP  */
    K_BYROWS = 431,                /* K_BYROWS  */
    K_BYCOLS = 432,                /* K_BYCOLS  */
    K_OPTIMIZE = 433,              /* K_OPTIMIZE  */
    K_ITERATIONS = 434,            /* K_ITERATIONS  */
    K_NUMERIC = 435,               /* K_NUMERIC  */
    K_PRESCALE = 436,              /* K_PRESCALE  */
    K_EXTFUN = 437,                /* K_EXTFUN  */
    K_CELLCUR = 438,               /* K_CELLCUR  */
    K_TOPROW = 439,                /* K_TOPROW  */
    K_COLOR = 440,                 /* K_COLOR  */
    K_COLORNEG = 441,              /* K_COLORNEG  */
    K_COLORERR = 442,              /* K_COLORERR  */
    K_BRAILLE = 443,               /* K_BRAILLE  */
    K_BACKUP = 444,                /* K_BACKUP  */
    K_MOUSE = 445,                 /* K_MOUSE  */
    K_BLACK = 446,                 /* K_BLACK  */
    K_RED = 447,                   /* K_RED  */
    K_GREEN = 448,                 /* K_GREEN  */
    K_YELLOW = 449,                /* K_YELLOW  */
    K_BLUE = 450,                  /* K_BLUE  */
    K_MAGENTA = 451,               /* K_MAGENTA  */
    K_CYAN = 452,                  /* K_CYAN  */
    K_WHITE = 453,                 /* K_WHITE  */
    K_TBLSTYLE = 454,              /* K_TBLSTYLE  */
    K_TBL = 455,                   /* K_TBL  */
    K_LATEX = 456,                 /* K_LATEX  */
    K_SLATEX = 457,                /* K_SLATEX  */
    K_TEX = 458,                   /* K_TEX  */
    K_FRAME = 459,                 /* K_FRAME  */
    K_RNDTOEVEN = 460,             /* K_RNDTOEVEN  */
    K_FILENAME = 461,              /* K_FILENAME  */
    K_MYROW = 462,                 /* K_MYROW  */
    K_MYCOL = 463,                 /* K_MYCOL  */
    K_LASTROW = 464,               /* K_LASTROW  */
    K_LASTCOL = 465,               /* K_LASTCOL  */
    K_COLTOA = 466,                /* K_COLTOA  */
    K_CRACTION = 467,              /* K_CRACTION  */
    K_CRROW = 468,                 /* K_CRROW  */
    K_CRCOL = 469,                 /* K_CRCOL  */
    K_ROWLIMIT = 470,              /* K_ROWLIMIT  */
    K_COLLIMIT = 471,              /* K_COLLIMIT  */
    K_PAGESIZE = 472,              /* K_PAGESIZE  */
    K_NUMITER = 473,               /* K_NUMITER  */
    K_ERR = 474,                   /* K_ERR  */
    K_SCRC = 475,                  /* K_SCRC  */
    K_LOCALE = 476                 /* K_LOCALE  */
  };
  typedef enum yytokentype yytoken_kind_t;
#endif
/* Token kinds.  */
#define YYEMPTY -2
#define YYEOF 0
#define YYerror 256
#define YYUNDEF 257
#define STRING 258
#define NUMBER 259
#define FNUMBER 260
#define RANGE 261
#define VAR 262
#define WORD 263
#define PLUGIN 264
#define COL 265
#define S_SHOW 266
#define S_HIDE 267
#define S_INSERTCOL 268
#define S_OPENCOL 269
#define S_DELETECOL 270
#define S_YANKCOL 271
#define S_GETFORMAT 272
#define S_FORMAT 273
#define S_FMT 274
#define S_LET 275
#define S_LABEL 276
#define S_LEFTSTRING 277
#define S_RIGHTSTRING 278
#define S_LEFTJUSTIFY 279
#define S_RIGHTJUSTIFY 280
#define S_CENTER 281
#define S_COLOR 282
#define S_ADDNOTE 283
#define S_DELNOTE 284
#define S_GET 285
#define S_PUT 286
#define S_MERGE 287
#define S_WRITE 288
#define S_TBL 289
#define S_COPY 290
#define S_MOVE 291
#define S_ERASE 292
#define S_YANK 293
#define S_FILL 294
#define S_SORT 295
#define S_LOCK 296
#define S_UNLOCK 297
#define S_GOTO 298
#define S_DEFINE 299
#define S_UNDEFINE 300
#define S_ABBREV 301
#define S_UNABBREV 302
#define S_FRAME 303
#define S_FRAMETOP 304
#define S_FRAMEBOTTOM 305
#define S_FRAMELEFT 306
#define S_FRAMERIGHT 307
#define S_UNFRAME 308
#define S_VALUE 309
#define S_MDIR 310
#define S_AUTORUN 311
#define S_FKEY 312
#define S_HISTFILE 313
#define S_SCEXT 314
#define S_ASCEXT 315
#define S_TBL0EXT 316
#define S_TBLEXT 317
#define S_LATEXEXT 318
#define S_SLATEXEXT 319
#define S_TEXEXT 320
#define S_SET 321
#define S_UP 322
#define S_DOWN 323
#define S_LEFT 324
#define S_RIGHT 325
#define S_ENDUP 326
#define S_ENDDOWN 327
#define S_ENDLEFT 328
#define S_ENDRIGHT 329
#define S_SELECT 330
#define S_INSERTROW 331
#define S_OPENROW 332
#define S_DELETEROW 333
#define S_YANKROW 334
#define S_PULL 335
#define S_PULLMERGE 336
#define S_PULLROWS 337
#define S_PULLCOLS 338
#define S_PULLXCHG 339
#define S_PULLTP 340
#define S_PULLFMT 341
#define S_PULLCOPY 342
#define S_WHEREAMI 343
#define S_GETNUM 344
#define S_FGETNUM 345
#define S_GETSTRING 346
#define S_GETEXP 347
#define S_GETFMT 348
#define S_GETFRAME 349
#define S_GETRANGE 350
#define S_EVAL 351
#define S_SEVAL 352
#define S_QUERY 353
#define S_GETKEY 354
#define S_ERROR 355
#define S_RECALC 356
#define S_REDRAW 357
#define S_QUIT 358
#define S_STATUS 359
#define S_RUN 360
#define S_PLUGIN 361
#define S_PLUGOUT 362
#define K_ERROR 363
#define K_INVALID 364
#define K_FIXED 365
#define K_SUM 366
#define K_PROD 367
#define K_AVG 368
#define K_STDDEV 369
#define K_COUNT 370
#define K_ROWS 371
#define K_COLS 372
#define K_ABS 373
#define K_ACOS 374
#define K_ASIN 375
#define K_ATAN 376
#define K_ATAN2 377
#define K_CEIL 378
#define K_COS 379
#define K_EXP 380
#define K_FABS 381
#define K_FLOOR 382
#define K_HYPOT 383
#define K_LN 384
#define K_LOG 385
#define K_PI 386
#define K_POW 387
#define K_SIN 388
#define K_SQRT 389
#define K_TAN 390
#define K_DTR 391
#define K_RTD 392
#define K_MAX 393
#define K_MIN 394
#define K_RND 395
#define K_ROUND 396
#define K_IF 397
#define K_PV 398
#define K_FV 399
#define K_PMT 400
#define K_HOUR 401
#define K_MINUTE 402
#define K_SECOND 403
#define K_MONTH 404
#define K_DAY 405
#define K_YEAR 406
#define K_NOW 407
#define K_DATE 408
#define K_DTS 409
#define K_TTS 410
#define K_FMT 411
#define K_SUBSTR 412
#define K_UPPER 413
#define K_LOWER 414
#define K_CAPITAL 415
#define K_STON 416
#define K_EQS 417
#define K_EXT 418
#define K_NVAL 419
#define K_SVAL 420
#define K_LOOKUP 421
#define K_HLOOKUP 422
#define K_VLOOKUP 423
#define K_INDEX 424
#define K_STINDEX 425
#define K_AUTO 426
#define K_AUTOCALC 427
#define K_AUTOINSERT 428
#define K_AUTOWRAP 429
#define K_CSLOP 430
#define K_BYROWS 431
#define K_BYCOLS 432
#define K_OPTIMIZE 433
#define K_ITERATIONS 434
#define K_NUMERIC 435
#define K_PRESCALE 436
#define K_EXTFUN 437
#define K_CELLCUR 438
#define K_TOPROW 439
#define K_COLOR 440
#define K_COLORNEG 441
#define K_COLORERR 442
#define K_BRAILLE 443
#define K_BACKUP 444
#define K_MOUSE 445
#define K_BLACK 446
#define K_RED 447
#define K_GREEN 448
#define K_YELLOW 449
#define K_BLUE 450
#define K_MAGENTA 451
#define K_CYAN 452
#define K_WHITE 453
#define K_TBLSTYLE 454
#define K_TBL 455
#define K_LATEX 456
#define K_SLATEX 457
#define K_TEX 458
#define K_FRAME 459
#define K_RNDTOEVEN 460
#define K_FILENAME 461
#define K_MYROW 462
#define K_MYCOL 463
#define K_LASTROW 464
#define K_LASTCOL 465
#define K_COLTOA 466
#define K_CRACTION 467
#define K_CRROW 468
#define K_CRCOL 469
#define K_ROWLIMIT 470
#define K_COLLIMIT 471
#define K_PAGESIZE 472
#define K_NUMITER 473
#define K_ERR 474
#define K_SCRC 475
#define K_LOCALE 476

/* Value type.  */
#if ! defined YYSTYPE && ! defined YYSTYPE_IS_DECLARED
union YYSTYPE
{
#line 35 "gram.y"

    int ival;
    double fval;
    struct ent_ptr ent;
    struct enode *enode;
    char *sval;
    struct range_s rval;

#line 593 "y.tab.c"

};
typedef union YYSTYPE YYSTYPE;
# define YYSTYPE_IS_TRIVIAL 1
# define YYSTYPE_IS_DECLARED 1
#endif


extern YYSTYPE yylval;


int yyparse (void);


#endif /* !YY_YY_Y_TAB_H_INCLUDED  */
/* Symbol kind.  */
enum yysymbol_kind_t
{
  YYSYMBOL_YYEMPTY = -2,
  YYSYMBOL_YYEOF = 0,                      /* "end of file"  */
  YYSYMBOL_YYerror = 1,                    /* error  */
  YYSYMBOL_YYUNDEF = 2,                    /* "invalid token"  */
  YYSYMBOL_STRING = 3,                     /* STRING  */
  YYSYMBOL_NUMBER = 4,                     /* NUMBER  */
  YYSYMBOL_FNUMBER = 5,                    /* FNUMBER  */
  YYSYMBOL_RANGE = 6,                      /* RANGE  */
  YYSYMBOL_VAR = 7,                        /* VAR  */
  YYSYMBOL_WORD = 8,                       /* WORD  */
  YYSYMBOL_PLUGIN = 9,                     /* PLUGIN  */
  YYSYMBOL_COL = 10,                       /* COL  */
  YYSYMBOL_S_SHOW = 11,                    /* S_SHOW  */
  YYSYMBOL_S_HIDE = 12,                    /* S_HIDE  */
  YYSYMBOL_S_INSERTCOL = 13,               /* S_INSERTCOL  */
  YYSYMBOL_S_OPENCOL = 14,                 /* S_OPENCOL  */
  YYSYMBOL_S_DELETECOL = 15,               /* S_DELETECOL  */
  YYSYMBOL_S_YANKCOL = 16,                 /* S_YANKCOL  */
  YYSYMBOL_S_GETFORMAT = 17,               /* S_GETFORMAT  */
  YYSYMBOL_S_FORMAT = 18,                  /* S_FORMAT  */
  YYSYMBOL_S_FMT = 19,                     /* S_FMT  */
  YYSYMBOL_S_LET = 20,                     /* S_LET  */
  YYSYMBOL_S_LABEL = 21,                   /* S_LABEL  */
  YYSYMBOL_S_LEFTSTRING = 22,              /* S_LEFTSTRING  */
  YYSYMBOL_S_RIGHTSTRING = 23,             /* S_RIGHTSTRING  */
  YYSYMBOL_S_LEFTJUSTIFY = 24,             /* S_LEFTJUSTIFY  */
  YYSYMBOL_S_RIGHTJUSTIFY = 25,            /* S_RIGHTJUSTIFY  */
  YYSYMBOL_S_CENTER = 26,                  /* S_CENTER  */
  YYSYMBOL_S_COLOR = 27,                   /* S_COLOR  */
  YYSYMBOL_S_ADDNOTE = 28,                 /* S_ADDNOTE  */
  YYSYMBOL_S_DELNOTE = 29,                 /* S_DELNOTE  */
  YYSYMBOL_S_GET = 30,                     /* S_GET  */
  YYSYMBOL_S_PUT = 31,                     /* S_PUT  */
  YYSYMBOL_S_MERGE = 32,                   /* S_MERGE  */
  YYSYMBOL_S_WRITE = 33,                   /* S_WRITE  */
  YYSYMBOL_S_TBL = 34,                     /* S_TBL  */
  YYSYMBOL_S_COPY = 35,                    /* S_COPY  */
  YYSYMBOL_S_MOVE = 36,                    /* S_MOVE  */
  YYSYMBOL_S_ERASE = 37,                   /* S_ERASE  */
  YYSYMBOL_S_YANK = 38,                    /* S_YANK  */
  YYSYMBOL_S_FILL = 39,                    /* S_FILL  */
  YYSYMBOL_S_SORT = 40,                    /* S_SORT  */
  YYSYMBOL_S_LOCK = 41,                    /* S_LOCK  */
  YYSYMBOL_S_UNLOCK = 42,                  /* S_UNLOCK  */
  YYSYMBOL_S_GOTO = 43,                    /* S_GOTO  */
  YYSYMBOL_S_DEFINE = 44,                  /* S_DEFINE  */
  YYSYMBOL_S_UNDEFINE = 45,                /* S_UNDEFINE  */
  YYSYMBOL_S_ABBREV = 46,                  /* S_ABBREV  */
  YYSYMBOL_S_UNABBREV = 47,                /* S_UNABBREV  */
  YYSYMBOL_S_FRAME = 48,                   /* S_FRAME  */
  YYSYMBOL_S_FRAMETOP = 49,                /* S_FRAMETOP  */
  YYSYMBOL_S_FRAMEBOTTOM = 50,             /* S_FRAMEBOTTOM  */
  YYSYMBOL_S_FRAMELEFT = 51,               /* S_FRAMELEFT  */
  YYSYMBOL_S_FRAMERIGHT = 52,              /* S_FRAMERIGHT  */
  YYSYMBOL_S_UNFRAME = 53,                 /* S_UNFRAME  */
  YYSYMBOL_S_VALUE = 54,                   /* S_VALUE  */
  YYSYMBOL_S_MDIR = 55,                    /* S_MDIR  */
  YYSYMBOL_S_AUTORUN = 56,                 /* S_AUTORUN  */
  YYSYMBOL_S_FKEY = 57,                    /* S_FKEY  */
  YYSYMBOL_S_HISTFILE = 58,                /* S_HISTFILE  */
  YYSYMBOL_S_SCEXT = 59,                   /* S_SCEXT  */
  YYSYMBOL_S_ASCEXT = 60,                  /* S_ASCEXT  */
  YYSYMBOL_S_TBL0EXT = 61,                 /* S_TBL0EXT  */
  YYSYMBOL_S_TBLEXT = 62,                  /* S_TBLEXT  */
  YYSYMBOL_S_LATEXEXT = 63,                /* S_LATEXEXT  */
  YYSYMBOL_S_SLATEXEXT = 64,               /* S_SLATEXEXT  */
  YYSYMBOL_S_TEXEXT = 65,                  /* S_TEXEXT  */
  YYSYMBOL_S_SET = 66,                     /* S_SET  */
  YYSYMBOL_S_UP = 67,                      /* S_UP  */
  YYSYMBOL_S_DOWN = 68,                    /* S_DOWN  */
  YYSYMBOL_S_LEFT = 69,                    /* S_LEFT  */
  YYSYMBOL_S_RIGHT = 70,                   /* S_RIGHT  */
  YYSYMBOL_S_ENDUP = 71,                   /* S_ENDUP  */
  YYSYMBOL_S_ENDDOWN = 72,                 /* S_ENDDOWN  */
  YYSYMBOL_S_ENDLEFT = 73,                 /* S_ENDLEFT  */
  YYSYMBOL_S_ENDRIGHT = 74,                /* S_ENDRIGHT  */
  YYSYMBOL_S_SELECT = 75,                  /* S_SELECT  */
  YYSYMBOL_S_INSERTROW = 76,               /* S_INSERTROW  */
  YYSYMBOL_S_OPENROW = 77,                 /* S_OPENROW  */
  YYSYMBOL_S_DELETEROW = 78,               /* S_DELETEROW  */
  YYSYMBOL_S_YANKROW = 79,                 /* S_YANKROW  */
  YYSYMBOL_S_PULL = 80,                    /* S_PULL  */
  YYSYMBOL_S_PULLMERGE = 81,               /* S_PULLMERGE  */
  YYSYMBOL_S_PULLROWS = 82,                /* S_PULLROWS  */
  YYSYMBOL_S_PULLCOLS = 83,                /* S_PULLCOLS  */
  YYSYMBOL_S_PULLXCHG = 84,                /* S_PULLXCHG  */
  YYSYMBOL_S_PULLTP = 85,                  /* S_PULLTP  */
  YYSYMBOL_S_PULLFMT = 86,                 /* S_PULLFMT  */
  YYSYMBOL_S_PULLCOPY = 87,                /* S_PULLCOPY  */
  YYSYMBOL_S_WHEREAMI = 88,                /* S_WHEREAMI  */
  YYSYMBOL_S_GETNUM = 89,                  /* S_GETNUM  */
  YYSYMBOL_S_FGETNUM = 90,                 /* S_FGETNUM  */
  YYSYMBOL_S_GETSTRING = 91,               /* S_GETSTRING  */
  YYSYMBOL_S_GETEXP = 92,                  /* S_GETEXP  */
  YYSYMBOL_S_GETFMT = 93,                  /* S_GETFMT  */
  YYSYMBOL_S_GETFRAME = 94,                /* S_GETFRAME  */
  YYSYMBOL_S_GETRANGE = 95,                /* S_GETRANGE  */
  YYSYMBOL_S_EVAL = 96,                    /* S_EVAL  */
  YYSYMBOL_S_SEVAL = 97,                   /* S_SEVAL  */
  YYSYMBOL_S_QUERY = 98,                   /* S_QUERY  */
  YYSYMBOL_S_GETKEY = 99,                  /* S_GETKEY  */
  YYSYMBOL_S_ERROR = 100,                  /* S_ERROR  */
  YYSYMBOL_S_RECALC = 101,                 /* S_RECALC  */
  YYSYMBOL_S_REDRAW = 102,                 /* S_REDRAW  */
  YYSYMBOL_S_QUIT = 103,                   /* S_QUIT  */
  YYSYMBOL_S_STATUS = 104,                 /* S_STATUS  */
  YYSYMBOL_S_RUN = 105,                    /* S_RUN  */
  YYSYMBOL_S_PLUGIN = 106,                 /* S_PLUGIN  */
  YYSYMBOL_S_PLUGOUT = 107,                /* S_PLUGOUT  */
  YYSYMBOL_K_ERROR = 108,                  /* K_ERROR  */
  YYSYMBOL_K_INVALID = 109,                /* K_INVALID  */
  YYSYMBOL_K_FIXED = 110,                  /* K_FIXED  */
  YYSYMBOL_K_SUM = 111,                    /* K_SUM  */
  YYSYMBOL_K_PROD = 112,                   /* K_PROD  */
  YYSYMBOL_K_AVG = 113,                    /* K_AVG  */
  YYSYMBOL_K_STDDEV = 114,                 /* K_STDDEV  */
  YYSYMBOL_K_COUNT = 115,                  /* K_COUNT  */
  YYSYMBOL_K_ROWS = 116,                   /* K_ROWS  */
  YYSYMBOL_K_COLS = 117,                   /* K_COLS  */
  YYSYMBOL_K_ABS = 118,                    /* K_ABS  */
  YYSYMBOL_K_ACOS = 119,                   /* K_ACOS  */
  YYSYMBOL_K_ASIN = 120,                   /* K_ASIN  */
  YYSYMBOL_K_ATAN = 121,                   /* K_ATAN  */
  YYSYMBOL_K_ATAN2 = 122,                  /* K_ATAN2  */
  YYSYMBOL_K_CEIL = 123,                   /* K_CEIL  */
  YYSYMBOL_K_COS = 124,                    /* K_COS  */
  YYSYMBOL_K_EXP = 125,                    /* K_EXP  */
  YYSYMBOL_K_FABS = 126,                   /* K_FABS  */
  YYSYMBOL_K_FLOOR = 127,                  /* K_FLOOR  */
  YYSYMBOL_K_HYPOT = 128,                  /* K_HYPOT  */
  YYSYMBOL_K_LN = 129,                     /* K_LN  */
  YYSYMBOL_K_LOG = 130,                    /* K_LOG  */
  YYSYMBOL_K_PI = 131,                     /* K_PI  */
  YYSYMBOL_K_POW = 132,                    /* K_POW  */
  YYSYMBOL_K_SIN = 133,                    /* K_SIN  */
  YYSYMBOL_K_SQRT = 134,                   /* K_SQRT  */
  YYSYMBOL_K_TAN = 135,                    /* K_TAN  */
  YYSYMBOL_K_DTR = 136,                    /* K_DTR  */
  YYSYMBOL_K_RTD = 137,                    /* K_RTD  */
  YYSYMBOL_K_MAX = 138,                    /* K_MAX  */
  YYSYMBOL_K_MIN = 139,                    /* K_MIN  */
  YYSYMBOL_K_RND = 140,                    /* K_RND  */
  YYSYMBOL_K_ROUND = 141,                  /* K_ROUND  */
  YYSYMBOL_K_IF = 142,                     /* K_IF  */
  YYSYMBOL_K_PV = 143,                     /* K_PV  */
  YYSYMBOL_K_FV = 144,                     /* K_FV  */
  YYSYMBOL_K_PMT = 145,                    /* K_PMT  */
  YYSYMBOL_K_HOUR = 146,                   /* K_HOUR  */
  YYSYMBOL_K_MINUTE = 147,                 /* K_MINUTE  */
  YYSYMBOL_K_SECOND = 148,                 /* K_SECOND  */
  YYSYMBOL_K_MONTH = 149,                  /* K_MONTH  */
  YYSYMBOL_K_DAY = 150,                    /* K_DAY  */
  YYSYMBOL_K_YEAR = 151,                   /* K_YEAR  */
  YYSYMBOL_K_NOW = 152,                    /* K_NOW  */
  YYSYMBOL_K_DATE = 153,                   /* K_DATE  */
  YYSYMBOL_K_DTS = 154,                    /* K_DTS  */
  YYSYMBOL_K_TTS = 155,                    /* K_TTS  */
  YYSYMBOL_K_FMT = 156,                    /* K_FMT  */
  YYSYMBOL_K_SUBSTR = 157,                 /* K_SUBSTR  */
  YYSYMBOL_K_UPPER = 158,                  /* K_UPPER  */
  YYSYMBOL_K_LOWER = 159,                  /* K_LOWER  */
  YYSYMBOL_K_CAPITAL = 160,                /* K_CAPITAL  */
  YYSYMBOL_K_STON = 161,                   /* K_STON  */
  YYSYMBOL_K_EQS = 162,                    /* K_EQS  */
  YYSYMBOL_K_EXT = 163,                    /* K_EXT  */
  YYSYMBOL_K_NVAL = 164,                   /* K_NVAL  */
  YYSYMBOL_K_SVAL = 165,                   /* K_SVAL  */
  YYSYMBOL_K_LOOKUP = 166,                 /* K_LOOKUP  */
  YYSYMBOL_K_HLOOKUP = 167,                /* K_HLOOKUP  */
  YYSYMBOL_K_VLOOKUP = 168,                /* K_VLOOKUP  */
  YYSYMBOL_K_INDEX = 169,                  /* K_INDEX  */
  YYSYMBOL_K_STINDEX = 170,                /* K_STINDEX  */
  YYSYMBOL_K_AUTO = 171,                   /* K_AUTO  */
  YYSYMBOL_K_AUTOCALC = 172,               /* K_AUTOCALC  */
  YYSYMBOL_K_AUTOINSERT = 173,             /* K_AUTOINSERT  */
  YYSYMBOL_K_AUTOWRAP = 174,               /* K_AUTOWRAP  */
  YYSYMBOL_K_CSLOP = 175,                  /* K_CSLOP  */
  YYSYMBOL_K_BYROWS = 176,                 /* K_BYROWS  */
  YYSYMBOL_K_BYCOLS = 177,                 /* K_BYCOLS  */
  YYSYMBOL_K_OPTIMIZE = 178,               /* K_OPTIMIZE  */
  YYSYMBOL_K_ITERATIONS = 179,             /* K_ITERATIONS  */
  YYSYMBOL_K_NUMERIC = 180,                /* K_NUMERIC  */
  YYSYMBOL_K_PRESCALE = 181,               /* K_PRESCALE  */
  YYSYMBOL_K_EXTFUN = 182,                 /* K_EXTFUN  */
  YYSYMBOL_K_CELLCUR = 183,                /* K_CELLCUR  */
  YYSYMBOL_K_TOPROW = 184,                 /* K_TOPROW  */
  YYSYMBOL_K_COLOR = 185,                  /* K_COLOR  */
  YYSYMBOL_K_COLORNEG = 186,               /* K_COLORNEG  */
  YYSYMBOL_K_COLORERR = 187,               /* K_COLORERR  */
  YYSYMBOL_K_BRAILLE = 188,                /* K_BRAILLE  */
  YYSYMBOL_K_BACKUP = 189,                 /* K_BACKUP  */
  YYSYMBOL_K_MOUSE = 190,                  /* K_MOUSE  */
  YYSYMBOL_K_BLACK = 191,                  /* K_BLACK  */
  YYSYMBOL_K_RED = 192,                    /* K_RED  */
  YYSYMBOL_K_GREEN = 193,                  /* K_GREEN  */
  YYSYMBOL_K_YELLOW = 194,                 /* K_YELLOW  */
  YYSYMBOL_K_BLUE = 195,                   /* K_BLUE  */
  YYSYMBOL_K_MAGENTA = 196,                /* K_MAGENTA  */
  YYSYMBOL_K_CYAN = 197,                   /* K_CYAN  */
  YYSYMBOL_K_WHITE = 198,                  /* K_WHITE  */
  YYSYMBOL_K_TBLSTYLE = 199,               /* K_TBLSTYLE  */
  YYSYMBOL_K_TBL = 200,                    /* K_TBL  */
  YYSYMBOL_K_LATEX = 201,                  /* K_LATEX  */
  YYSYMBOL_K_SLATEX = 202,                 /* K_SLATEX  */
  YYSYMBOL_K_TEX = 203,                    /* K_TEX  */
  YYSYMBOL_K_FRAME = 204,                  /* K_FRAME  */
  YYSYMBOL_K_RNDTOEVEN = 205,              /* K_RNDTOEVEN  */
  YYSYMBOL_K_FILENAME = 206,               /* K_FILENAME  */
  YYSYMBOL_K_MYROW = 207,                  /* K_MYROW  */
  YYSYMBOL_K_MYCOL = 208,                  /* K_MYCOL  */
  YYSYMBOL_K_LASTROW = 209,                /* K_LASTROW  */
  YYSYMBOL_K_LASTCOL = 210,                /* K_LASTCOL  */
  YYSYMBOL_K_COLTOA = 211,                 /* K_COLTOA  */
  YYSYMBOL_K_CRACTION = 212,               /* K_CRACTION  */
  YYSYMBOL_K_CRROW = 213,                  /* K_CRROW  */
  YYSYMBOL_K_CRCOL = 214,                  /* K_CRCOL  */
  YYSYMBOL_K_ROWLIMIT = 215,               /* K_ROWLIMIT  */
  YYSYMBOL_K_COLLIMIT = 216,               /* K_COLLIMIT  */
  YYSYMBOL_K_PAGESIZE = 217,               /* K_PAGESIZE  */
  YYSYMBOL_K_NUMITER = 218,                /* K_NUMITER  */
  YYSYMBOL_K_ERR = 219,                    /* K_ERR  */
  YYSYMBOL_K_SCRC = 220,                   /* K_SCRC  */
  YYSYMBOL_K_LOCALE = 221,                 /* K_LOCALE  */
  YYSYMBOL_222_ = 222,                     /* ';'  */
  YYSYMBOL_223_ = 223,                     /* '?'  */
  YYSYMBOL_224_ = 224,                     /* ':'  */
  YYSYMBOL_225_ = 225,                     /* '|'  */
  YYSYMBOL_226_ = 226,                     /* '&'  */
  YYSYMBOL_227_ = 227,                     /* '<'  */
  YYSYMBOL_228_ = 228,                     /* '='  */
  YYSYMBOL_229_ = 229,                     /* '>'  */
  YYSYMBOL_230_ = 230,                     /* '!'  */
  YYSYMBOL_231_ = 231,                     /* '+'  */
  YYSYMBOL_232_ = 232,                     /* '-'  */
  YYSYMBOL_233_ = 233,                     /* '#'  */
  YYSYMBOL_234_ = 234,                     /* '*'  */
  YYSYMBOL_235_ = 235,                     /* '/'  */
  YYSYMBOL_236_ = 236,                     /* '%'  */
  YYSYMBOL_237_ = 237,                     /* '^'  */
  YYSYMBOL_238_ = 238,                     /* '@'  */
  YYSYMBOL_239_ = 239,                     /* '('  */
  YYSYMBOL_240_ = 240,                     /* ')'  */
  YYSYMBOL_241_ = 241,                     /* ','  */
  YYSYMBOL_242_ = 242,                     /* '.'  */
  YYSYMBOL_243_ = 243,                     /* '~'  */
  YYSYMBOL_244_ = 244,                     /* '$'  */
  YYSYMBOL_YYACCEPT = 245,                 /* $accept  */
  YYSYMBOL_command = 246,                  /* command  */
  YYSYMBOL_term = 247,                     /* term  */
  YYSYMBOL_e = 248,                        /* e  */
  YYSYMBOL_expr_list = 249,                /* expr_list  */
  YYSYMBOL_range = 250,                    /* range  */
  YYSYMBOL_var = 251,                      /* var  */
  YYSYMBOL_var_or_range = 252,             /* var_or_range  */
  YYSYMBOL_num = 253,                      /* num  */
  YYSYMBOL_strarg = 254,                   /* strarg  */
  YYSYMBOL_setlist = 255,                  /* setlist  */
  YYSYMBOL_setitem = 256,                  /* setitem  */
  YYSYMBOL_errlist = 257                   /* errlist  */
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
typedef yytype_int16 yy_state_t;

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
#define YYFINAL  242
/* YYLAST -- Last index in YYTABLE.  */
#define YYLAST   2888

/* YYNTOKENS -- Number of terminals.  */
#define YYNTOKENS  245
/* YYNNTS -- Number of nonterminals.  */
#define YYNNTS  13
/* YYNRULES -- Number of rules.  */
#define YYNRULES  431
/* YYNSTATES -- Number of states.  */
#define YYNSTATES  899

/* YYMAXUTOK -- Last valid token kind.  */
#define YYMAXUTOK   476


/* YYTRANSLATE(TOKEN-NUM) -- Symbol number corresponding to TOKEN-NUM
   as returned by yylex, with out-of-bounds checking.  */
#define YYTRANSLATE(YYX)                                \
  (0 <= (YYX) && (YYX) <= YYMAXUTOK                     \
   ? YY_CAST (yysymbol_kind_t, yytranslate[YYX])        \
   : YYSYMBOL_YYUNDEF)

/* YYTRANSLATE[TOKEN-NUM] -- Symbol number corresponding to TOKEN-NUM
   as returned by yylex.  */
static const yytype_uint8 yytranslate[] =
{
       0,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,   230,     2,   233,   244,   236,   226,     2,
     239,   240,   234,   231,   241,   232,   242,   235,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,   224,   222,
     227,   228,   229,   223,   238,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,   237,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,   225,     2,   243,     2,     2,     2,
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
      55,    56,    57,    58,    59,    60,    61,    62,    63,    64,
      65,    66,    67,    68,    69,    70,    71,    72,    73,    74,
      75,    76,    77,    78,    79,    80,    81,    82,    83,    84,
      85,    86,    87,    88,    89,    90,    91,    92,    93,    94,
      95,    96,    97,    98,    99,   100,   101,   102,   103,   104,
     105,   106,   107,   108,   109,   110,   111,   112,   113,   114,
     115,   116,   117,   118,   119,   120,   121,   122,   123,   124,
     125,   126,   127,   128,   129,   130,   131,   132,   133,   134,
     135,   136,   137,   138,   139,   140,   141,   142,   143,   144,
     145,   146,   147,   148,   149,   150,   151,   152,   153,   154,
     155,   156,   157,   158,   159,   160,   161,   162,   163,   164,
     165,   166,   167,   168,   169,   170,   171,   172,   173,   174,
     175,   176,   177,   178,   179,   180,   181,   182,   183,   184,
     185,   186,   187,   188,   189,   190,   191,   192,   193,   194,
     195,   196,   197,   198,   199,   200,   201,   202,   203,   204,
     205,   206,   207,   208,   209,   210,   211,   212,   213,   214,
     215,   216,   217,   218,   219,   220,   221
};

#if YYDEBUG
/* YYRLINE[YYN] -- Source line where rule number YYN was defined.  */
static const yytype_int16 yyrline[] =
{
       0,   293,   293,   295,   308,   310,   312,   314,   317,   321,
     324,   328,   331,   335,   350,   359,   360,   366,   368,   370,
     372,   374,   387,   394,   400,   404,   409,   421,   422,   424,
     425,   427,   428,   430,   432,   433,   438,   440,   444,   449,
     453,   456,   458,   460,   464,   466,   469,   471,   473,   477,
     479,   480,   482,   502,   503,   516,   517,   531,   540,   542,
     545,   547,   549,   551,   552,   554,   555,   557,   561,   563,
     565,   566,   568,   570,   572,   574,   576,   578,   582,   585,
     589,   591,   592,   596,   600,   604,   606,   608,   610,   611,
     613,   623,   624,   625,   626,   627,   628,   629,   632,   649,
     664,   667,   674,   677,   684,   687,   694,   697,   704,   706,
     713,   717,   718,   720,   721,   722,   723,   724,   725,   726,
     727,   728,   729,   730,   731,   732,   733,   744,   745,   746,
     747,   748,   749,   750,   751,   752,   764,   765,   770,   784,
     796,   801,   802,   815,   827,   828,   833,   845,   857,   862,
     863,   874,   875,   876,   877,   878,   879,   880,   881,   882,
     884,   892,   900,   904,   909,   911,   913,   917,   922,   924,
     926,   931,   936,   938,   940,   944,   949,   951,   953,   954,
     956,   957,   958,   962,   967,   969,   971,   972,   973,   974,
     976,   978,   980,   983,   984,   985,   987,   988,   990,   991,
     992,   993,   994,   995,   996,  1000,  1008,  1009,  1019,  1021,
    1023,  1028,  1029,  1031,  1032,  1033,  1035,  1038,  1041,  1044,
    1047,  1050,  1053,  1056,  1059,  1062,  1065,  1068,  1071,  1073,
    1076,  1079,  1081,  1083,  1085,  1086,  1087,  1088,  1089,  1090,
    1091,  1092,  1093,  1094,  1095,  1096,  1097,  1098,  1099,  1100,
    1101,  1102,  1103,  1104,  1105,  1106,  1108,  1109,  1110,  1112,
    1113,  1114,  1115,  1116,  1117,  1118,  1119,  1121,  1125,  1127,
    1128,  1129,  1130,  1131,  1132,  1133,  1134,  1135,  1137,  1139,
    1142,  1144,  1146,  1149,  1152,  1155,  1158,  1160,  1162,  1165,
    1166,  1167,  1168,  1170,  1171,  1172,  1173,  1174,  1175,  1176,
    1177,  1178,  1179,  1180,  1181,  1182,  1183,  1184,  1185,  1186,
    1187,  1188,  1189,  1190,  1191,  1192,  1193,  1194,  1195,  1199,
    1200,  1201,  1202,  1203,  1204,  1205,  1206,  1207,  1208,  1209,
    1210,  1211,  1212,  1213,  1214,  1215,  1216,  1217,  1220,  1221,
    1224,  1225,  1228,  1229,  1231,  1233,  1235,  1238,  1239,  1242,
    1243,  1244,  1245,  1248,  1249,  1263,  1264,  1268,  1269,  1270,
    1271,  1272,  1273,  1274,  1275,  1276,  1277,  1278,  1279,  1280,
    1281,  1282,  1283,  1284,  1285,  1286,  1287,  1288,  1289,  1290,
    1291,  1292,  1293,  1294,  1295,  1296,  1297,  1298,  1299,  1300,
    1301,  1302,  1303,  1310,  1316,  1322,  1323,  1324,  1325,  1326,
    1327,  1328,  1329,  1330,  1331,  1332,  1333,  1334,  1335,  1336,
    1337,  1338,  1339,  1340,  1341,  1342,  1343,  1344,  1345,  1346,
    1347,  1348,  1349,  1350,  1351,  1352,  1372,  1377,  1385,  1389,
    1391,  1395
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
  "\"end of file\"", "error", "\"invalid token\"", "STRING", "NUMBER",
  "FNUMBER", "RANGE", "VAR", "WORD", "PLUGIN", "COL", "S_SHOW", "S_HIDE",
  "S_INSERTCOL", "S_OPENCOL", "S_DELETECOL", "S_YANKCOL", "S_GETFORMAT",
  "S_FORMAT", "S_FMT", "S_LET", "S_LABEL", "S_LEFTSTRING", "S_RIGHTSTRING",
  "S_LEFTJUSTIFY", "S_RIGHTJUSTIFY", "S_CENTER", "S_COLOR", "S_ADDNOTE",
  "S_DELNOTE", "S_GET", "S_PUT", "S_MERGE", "S_WRITE", "S_TBL", "S_COPY",
  "S_MOVE", "S_ERASE", "S_YANK", "S_FILL", "S_SORT", "S_LOCK", "S_UNLOCK",
  "S_GOTO", "S_DEFINE", "S_UNDEFINE", "S_ABBREV", "S_UNABBREV", "S_FRAME",
  "S_FRAMETOP", "S_FRAMEBOTTOM", "S_FRAMELEFT", "S_FRAMERIGHT",
  "S_UNFRAME", "S_VALUE", "S_MDIR", "S_AUTORUN", "S_FKEY", "S_HISTFILE",
  "S_SCEXT", "S_ASCEXT", "S_TBL0EXT", "S_TBLEXT", "S_LATEXEXT",
  "S_SLATEXEXT", "S_TEXEXT", "S_SET", "S_UP", "S_DOWN", "S_LEFT",
  "S_RIGHT", "S_ENDUP", "S_ENDDOWN", "S_ENDLEFT", "S_ENDRIGHT", "S_SELECT",
  "S_INSERTROW", "S_OPENROW", "S_DELETEROW", "S_YANKROW", "S_PULL",
  "S_PULLMERGE", "S_PULLROWS", "S_PULLCOLS", "S_PULLXCHG", "S_PULLTP",
  "S_PULLFMT", "S_PULLCOPY", "S_WHEREAMI", "S_GETNUM", "S_FGETNUM",
  "S_GETSTRING", "S_GETEXP", "S_GETFMT", "S_GETFRAME", "S_GETRANGE",
  "S_EVAL", "S_SEVAL", "S_QUERY", "S_GETKEY", "S_ERROR", "S_RECALC",
  "S_REDRAW", "S_QUIT", "S_STATUS", "S_RUN", "S_PLUGIN", "S_PLUGOUT",
  "K_ERROR", "K_INVALID", "K_FIXED", "K_SUM", "K_PROD", "K_AVG",
  "K_STDDEV", "K_COUNT", "K_ROWS", "K_COLS", "K_ABS", "K_ACOS", "K_ASIN",
  "K_ATAN", "K_ATAN2", "K_CEIL", "K_COS", "K_EXP", "K_FABS", "K_FLOOR",
  "K_HYPOT", "K_LN", "K_LOG", "K_PI", "K_POW", "K_SIN", "K_SQRT", "K_TAN",
  "K_DTR", "K_RTD", "K_MAX", "K_MIN", "K_RND", "K_ROUND", "K_IF", "K_PV",
  "K_FV", "K_PMT", "K_HOUR", "K_MINUTE", "K_SECOND", "K_MONTH", "K_DAY",
  "K_YEAR", "K_NOW", "K_DATE", "K_DTS", "K_TTS", "K_FMT", "K_SUBSTR",
  "K_UPPER", "K_LOWER", "K_CAPITAL", "K_STON", "K_EQS", "K_EXT", "K_NVAL",
  "K_SVAL", "K_LOOKUP", "K_HLOOKUP", "K_VLOOKUP", "K_INDEX", "K_STINDEX",
  "K_AUTO", "K_AUTOCALC", "K_AUTOINSERT", "K_AUTOWRAP", "K_CSLOP",
  "K_BYROWS", "K_BYCOLS", "K_OPTIMIZE", "K_ITERATIONS", "K_NUMERIC",
  "K_PRESCALE", "K_EXTFUN", "K_CELLCUR", "K_TOPROW", "K_COLOR",
  "K_COLORNEG", "K_COLORERR", "K_BRAILLE", "K_BACKUP", "K_MOUSE",
  "K_BLACK", "K_RED", "K_GREEN", "K_YELLOW", "K_BLUE", "K_MAGENTA",
  "K_CYAN", "K_WHITE", "K_TBLSTYLE", "K_TBL", "K_LATEX", "K_SLATEX",
  "K_TEX", "K_FRAME", "K_RNDTOEVEN", "K_FILENAME", "K_MYROW", "K_MYCOL",
  "K_LASTROW", "K_LASTCOL", "K_COLTOA", "K_CRACTION", "K_CRROW", "K_CRCOL",
  "K_ROWLIMIT", "K_COLLIMIT", "K_PAGESIZE", "K_NUMITER", "K_ERR", "K_SCRC",
  "K_LOCALE", "';'", "'?'", "':'", "'|'", "'&'", "'<'", "'='", "'>'",
  "'!'", "'+'", "'-'", "'#'", "'*'", "'/'", "'%'", "'^'", "'@'", "'('",
  "')'", "','", "'.'", "'~'", "'$'", "$accept", "command", "term", "e",
  "expr_list", "range", "var", "var_or_range", "num", "strarg", "setlist",
  "setitem", "errlist", YY_NULLPTR
};

static const char *
yysymbol_name (yysymbol_kind_t yysymbol)
{
  return yytname[yysymbol];
}
#endif

#define YYPACT_NINF (-167)

#define yypact_value_is_default(Yyn) \
  ((Yyn) == YYPACT_NINF)

#define YYTABLE_NINF (-349)

#define yytable_value_is_error(Yyn) \
  ((Yyn) == YYTABLE_NINF)

/* YYPACT[STATE-NUM] -- Index in YYTABLE of the portion describing
   STATE-NUM.  */
static const yytype_int16 yypact[] =
{
    1117,  -167,  -167,    67,   102,  -164,  -153,    40,   134,    -5,
     105,   130,   130,   130,   130,   130,   130,   130,   130,   120,
     135,   135,   115,   125,   115,   107,   115,   130,   135,   130,
     130,   130,   130,   130,   130,    97,   115,   130,   108,   113,
     130,   149,   180,   194,   206,   130,   130,   115,   115,   104,
     115,   115,   115,   115,   115,   115,   115,   115,  -167,   117,
     119,   129,   142,  -167,  -167,  -167,  -167,   126,  -115,   -76,
       6,     7,  -167,  -167,  -167,  -167,  -167,  -167,  -167,   130,
     -65,    81,   304,   360,   366,   380,   -62,   166,   288,   288,
      59,  -167,   168,  -167,  -167,  -167,   -53,   170,   178,   179,
     183,   -36,   -35,   -33,   -27,   198,   199,    -9,   213,  -167,
       2,   215,     0,   228,     5,    65,  -167,  -167,     3,   224,
    -167,    11,   233,    16,    17,    18,    23,  -167,  -167,  -167,
      24,   249,    11,   130,  -167,  -167,  -167,  -167,   130,    19,
      21,    11,   130,  -167,  -167,  -167,   130,   130,   130,   130,
    -167,  -167,    35,   115,  -167,  -167,   130,  -167,  -167,  -167,
     130,   130,    35,    35,   254,   255,   130,   130,  -167,   130,
    -167,  -167,  -167,   130,  -167,   256,  -167,   260,  -167,   261,
    -167,   265,  -167,  -167,  -167,  -167,    43,  -167,  -167,  -167,
    -167,  -167,  -167,  -167,  -167,  1054,  -167,  -167,  -167,  -167,
    -167,   266,   271,    58,   279,    66,   290,  -167,   292,   298,
      78,   300,    80,   305,    90,   317,    98,   318,    99,   322,
     106,  -167,    85,  -167,  -167,   288,   288,   288,   729,   332,
     288,  -167,   511,  -167,  1086,    60,   328,  -167,   330,  -167,
     112,   143,  -167,   358,   353,   371,   367,  -167,  -167,   370,
    -167,   374,  -167,   377,  -167,   382,   384,   379,  -167,   387,
       4,   135,  -167,   288,   288,   288,   288,   288,  -167,  -167,
    -167,   130,   130,  -167,  -167,  -167,  -167,  -167,    35,  -167,
    -167,  -167,  -167,  -167,  -167,   130,   130,  -167,  -167,  -167,
      11,  -167,  -167,  -167,  -167,  -167,   115,  -167,  -167,  -167,
    -167,  -167,  -167,  -167,  -167,   167,  -167,  -167,  -167,  -167,
    -167,  -167,  -167,  -167,  -167,  -167,  -167,   171,  -167,   172,
     173,   174,   176,  -167,  -167,   888,  1105,  -167,  -167,  -167,
     390,  -167,   394,  -167,  -167,  -167,   402,  -167,   403,  -167,
     406,  -167,   407,  -167,   408,  -167,   409,   410,  -167,  -167,
    -167,   288,   177,   186,   190,   191,   192,   200,   201,   202,
     207,   210,   267,   269,   270,   274,   277,   284,   285,   286,
     289,   291,  -167,   301,   302,   306,   307,   308,   310,   311,
     313,   314,   315,   316,   319,   326,   327,   329,   333,   334,
     335,   338,   354,  -167,   355,   359,   363,   368,   369,   372,
     375,   376,   378,   381,   386,   388,   389,   392,   396,   398,
     400,   401,  -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,
     404,  -167,  -167,  -167,  -167,   405,  -167,  -167,   839,  1649,
    -167,   193,   288,   288,   288,   288,    -1,   288,   189,   187,
     288,   288,   288,   288,   288,   288,   288,   197,   433,  -167,
    -167,   442,   501,  -167,  -167,  -167,  -167,  -167,  -167,  -167,
    -167,   506,   539,  -167,  -167,   540,  -167,  1086,  1086,  1086,
    1086,  1086,  -167,  -167,  -167,  -167,  -167,  -167,   552,   116,
     553,   557,   563,   565,  -167,  -167,  -167,  -167,  -167,  -167,
    -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,
    -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,
    -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,
    -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,
     263,  -167,   130,   130,   130,   130,   130,   130,   130,   288,
     288,   288,   288,   288,   288,   288,   288,   288,   288,   288,
     288,   288,   288,   288,   288,   288,   288,   288,    69,    69,
     288,   288,   288,   288,   288,   288,   288,   288,   288,   288,
     288,   288,   288,   288,   288,   288,   288,   288,   288,   288,
     288,   288,   288,   288,   288,    69,    69,    69,    69,    69,
     288,   288,   204,  -167,   588,  1086,  2628,  2640,   599,   288,
     288,  2651,  2651,   288,  2651,   288,   -13,   -13,   -13,   416,
     416,   416,  -167,   602,  -167,  -167,  -167,  -167,   605,  -167,
    -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,
    -167,   609,   385,   383,   413,   393,   415,   417,   418,   420,
     422,   421,   424,   426,  1665,  1681,  1697,  1713,   494,  1729,
    1745,  1761,  1777,  1793,  1122,  1809,  1825,  1139,  1841,  1857,
    1873,  1889,  1905,  1156,   432,   -60,   427,  1173,   434,   436,
    1921,  1190,  1207,  1224,  1241,  1258,  1937,  1953,  1969,  1985,
    2001,  2017,   574,  1275,  1292,  1309,  1326,  2033,  2049,  2065,
    2081,  1343,  1360,  1377,  1394,  1411,   437,    11,  1428,   438,
    1445,   444,  1462,   445,  1479,   446,  2097,  2113,   288,  -167,
     288,  2651,  2651,  2651,  2651,  -167,   612,  -167,   288,  -167,
     288,  -167,   288,  -167,   288,  -167,   288,  -167,  -167,  -167,
    -167,  -167,  -167,  -167,   288,  -167,  -167,  -167,  -167,  -167,
     288,  -167,  -167,   288,  -167,  -167,  -167,  -167,  -167,   288,
     288,  -167,   288,   288,  -167,  -167,   288,   288,   288,   288,
     288,  -167,  -167,  -167,  -167,  -167,  -167,  -167,   288,   288,
     288,   288,   288,  -167,  -167,  -167,  -167,   288,   288,   288,
     288,   130,   288,   130,   288,   130,   288,   130,   288,   130,
     288,  -167,  -167,  -167,   854,  -167,  2129,  2145,  2161,  2177,
    2193,  2209,  2225,  2241,  1086,   -89,  2257,   -75,  2273,  2289,
    1496,  1513,  1530,  1547,  2305,  1564,  1581,  2321,  1598,  2337,
    2353,  2369,  2385,   448,  2401,   452,  1615,   454,  1632,   457,
     678,   461,  1102,  -167,  -167,  -167,  -167,  -167,  -167,  -167,
    -167,  -167,   288,  -167,  -167,  -167,  -167,   288,   288,   288,
     288,  -167,   288,   288,  -167,   288,  -167,  -167,  -167,  -167,
    -167,  -167,   288,   288,   288,   288,  -167,  -167,   288,  -167,
    -167,   288,  1086,  2417,  2433,  2449,  2465,  2481,  2497,  2513,
    2529,  2545,  2561,  2577,  2593,  2609,  -167,  -167,  -167,  -167,
    -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167,  -167
};

/* YYDEFACT[STATE-NUM] -- Default reduction number in state STATE-NUM.
   Performed when YYTABLE does not specify something else to do.  Zero
   means the default is an error.  */
static const yytype_int16 yydefact[] =
{
       0,   212,   210,     0,    52,   131,   133,   139,   147,   180,
       0,     0,     0,     0,     0,     0,     8,    10,    12,     0,
       0,    16,     0,    42,     0,    47,     0,    57,     0,    62,
      64,     0,    69,    73,    75,    88,     0,     0,    95,     0,
      99,     0,     0,     0,     0,   109,    66,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,   355,   114,
     116,   118,   120,   122,   123,   124,   125,     0,   127,   129,
     135,   143,   151,   152,   153,   154,   155,   156,   157,   158,
     160,   164,   168,   172,   176,   184,   186,     0,     0,     0,
     198,   200,     0,   204,   205,   206,   202,     0,     0,     0,
       0,     0,     0,    55,    53,     0,     0,   140,     0,   148,
       0,     0,   178,     0,     0,     0,   341,   346,     0,     0,
     347,   348,     0,     0,     0,     0,     0,     7,     9,    11,
       0,     0,     0,    13,    15,   353,   354,    22,     0,    41,
      37,   354,    36,    23,    46,    45,    44,    49,    58,    60,
      63,    65,     0,    70,    74,    76,    85,   349,   350,    89,
     429,   431,     0,     0,     0,     0,    78,    80,    81,    90,
      93,    94,    96,    98,   101,     0,   103,     0,   105,     0,
     107,     0,   108,    67,    24,    25,     0,    28,    27,    29,
      30,    31,    32,    33,    34,   113,   115,   117,   119,   121,
     126,     0,     0,   137,     0,   145,     0,   159,     0,     0,
     162,     0,   166,     0,   170,     0,   174,     0,   182,     0,
     188,   299,   296,   297,   310,     0,     0,     0,     0,     0,
       0,   325,   190,   213,   193,   196,     0,   201,     0,   207,
       0,     0,     1,     0,     0,     0,     0,   132,   134,     0,
     141,     0,   149,     0,   181,     0,     0,     0,   342,     0,
       0,     0,    72,     3,     0,     0,     0,   110,   112,    14,
      40,     0,     0,    35,    43,    48,    59,    61,     0,    71,
      82,   428,   430,   352,   351,    86,    87,    77,    79,    91,
      92,    97,   100,   102,   104,   106,     0,   357,   358,   383,
     386,   389,   364,   363,   365,     0,   368,   371,   374,   377,
     380,   392,   395,   398,   401,   404,   407,     0,   417,     0,
       0,     0,     0,   424,   425,     0,     0,   356,   128,   130,
       0,   136,     0,   144,   161,   165,     0,   169,     0,   173,
       0,   177,     0,   185,     0,   187,     0,     0,   301,   294,
     295,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,   298,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,   265,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,   311,   312,   313,   314,   315,   316,   317,   318,
       0,   303,   304,   305,   306,     0,   308,   309,     0,     0,
     300,   191,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,   194,     0,   199,
     203,     0,     0,    51,    50,    56,    54,   142,   150,   179,
      21,    20,     0,   344,   343,     0,   340,     2,     4,     5,
       6,   111,    39,    38,    68,    83,    84,    26,     0,     0,
       0,     0,     0,     0,   361,   362,   385,   388,   391,   367,
     370,   373,   376,   379,   382,   393,   396,   399,   402,   405,
     408,   418,   426,   359,   360,   384,   387,   390,   366,   369,
     372,   375,   378,   381,   394,   397,   400,   403,   406,   409,
     419,   427,   138,   146,   163,   167,   171,   175,   183,   189,
       0,   214,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,   293,     0,   327,     0,   332,   331,     0,
       0,   328,   329,     0,   330,     0,   319,   320,   337,   321,
     322,   323,   324,     0,   197,   208,   209,    18,     0,   345,
     410,   411,   412,   413,   414,   415,   416,   420,   421,   422,
     423,     0,   347,     0,   347,     0,   347,     0,   347,     0,
     347,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,   347,   213,     0,     0,   347,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,   213,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,   192,
       0,   333,   335,   336,   334,   195,    19,   267,     0,   216,
       0,   218,     0,   220,     0,   222,     0,   224,   232,   233,
     234,   235,   236,   237,     0,   239,   240,   241,   242,   243,
       0,   245,   246,     0,   248,   249,   250,   251,   252,     0,
       0,   226,     0,     0,   229,   253,     0,     0,     0,     0,
       0,   259,   260,   261,   262,   263,   264,   271,     0,     0,
       0,     0,     0,   274,   275,   276,   269,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,   302,   307,   215,   326,    17,     0,     0,     0,     0,
       0,     0,     0,     0,   338,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,   217,   219,   221,   223,   225,   238,   244,
     247,   228,     0,   227,   231,   230,   254,     0,     0,     0,
       0,   272,     0,     0,   273,     0,   270,   289,   290,   291,
     281,   280,     0,     0,     0,     0,   278,   277,     0,   287,
     286,     0,   339,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,   255,   256,   257,   258,
     266,   268,   292,   283,   282,   285,   284,   279,   288
};

/* YYPGOTO[NTERM-NUM].  */
static const yytype_int16 yypgoto[] =
{
    -167,  -167,  -166,   -88,  -134,   236,     1,   566,    87,    42,
    -167,  -167,  -167
};

/* YYDEFGOTO[NTERM-NUM].  */
static const yytype_int16 yydefgoto[] =
{
       0,   100,   231,   804,   805,   120,   233,   122,   167,   137,
     195,   327,   168
};

/* YYTABLE[YYPACT[STATE-NUM]] -- What to do in state STATE-NUM.  If
   positive, shift that token.  If negative, reduce the rule whose
   number is the opposite.  If YYTABLE_NINF, syntax error.  */
static const yytype_int16 yytable[] =
{
     232,   234,   221,   222,   223,   112,   117,   258,   464,   118,
     203,   205,   121,   121,   121,   121,   121,   121,   121,   121,
     132,   133,   134,   136,   141,   136,   141,   136,   132,   149,
     121,   121,   121,   132,   121,   121,   121,   136,   121,   157,
     158,   132,   132,   132,   132,   132,   132,   121,   136,   136,
     107,   136,   136,   136,   136,   136,   136,   136,   136,   348,
     349,   350,   235,   447,   430,   142,   143,   146,   147,   256,
     105,   101,   221,   222,   223,   116,   117,   102,   169,   118,
     121,   106,   121,   121,   121,   121,   121,   116,   117,   184,
     185,   118,   187,   188,   189,   190,   191,   192,   193,   194,
     156,   157,   158,   116,   117,   159,   103,   118,   186,   114,
     135,   171,   104,   116,   117,   115,   172,   118,   135,   201,
     621,   196,   117,   197,   130,   118,   116,   117,   135,   200,
     118,   116,   117,   198,   121,   118,   116,   117,   109,   121,
     118,   429,   117,   132,   110,   118,   199,   132,   132,   121,
     121,   841,   842,   174,   136,   116,   117,   132,   202,   118,
     208,   132,   132,   219,   261,   844,   842,   121,   132,   220,
     290,   237,   238,   239,   132,   467,   468,   469,   470,   471,
    -348,   240,   241,   242,   176,   531,   116,   117,   243,   244,
     118,   245,   221,   222,   223,   279,   117,   246,   178,   118,
     116,   117,   247,   248,   118,   160,   161,   221,   222,   223,
     180,   117,   116,   117,   118,   249,   118,   250,   224,   252,
     113,   443,   444,   445,   446,   253,   251,   599,   600,   225,
     226,   227,   254,   255,   260,   261,   262,   228,   229,   278,
     204,   206,   230,   119,   263,   264,   265,   259,   465,   283,
     284,   266,   267,   268,   271,   131,   272,   285,   286,   140,
     292,   145,   466,   148,   293,   294,   162,   163,   153,   295,
     328,   296,   121,   121,   108,   329,   173,   175,   177,   179,
     181,   182,   330,   331,   236,   448,   132,   132,   224,   257,
     332,   221,   222,   223,   333,   117,   334,   136,   118,   225,
     226,   227,   335,   336,   337,   338,   209,   228,   229,   339,
     116,   117,   230,   119,   118,   340,   622,   623,   624,   625,
     626,   341,   343,   342,   344,   119,   345,   347,   162,   163,
     164,   346,   449,   165,   450,   221,   222,   223,   477,   117,
     451,   119,   118,   144,   595,   596,   597,   598,   601,   602,
     604,   119,   606,   607,   608,   609,   610,   611,   612,   119,
     138,   139,   453,   454,   119,   474,   116,   117,   111,   119,
     118,   452,   116,   117,   119,   455,   118,   456,   273,   119,
     457,   459,   274,   275,   458,   460,   116,   117,   461,   462,
     118,   463,   280,   119,   522,   478,   281,   282,   523,   479,
     480,   481,   482,   288,   483,   289,   524,   525,   224,   291,
     526,   527,   528,   529,   530,   605,   532,   603,   594,   225,
     226,   227,   613,   224,   119,   533,   531,   228,   229,   534,
     535,   536,   230,   119,   225,   226,   227,   614,   119,   537,
     538,   539,   228,   229,   708,   615,   540,   230,   119,   541,
     119,   644,   645,   646,   647,   648,   649,   650,   651,   652,
     653,   654,   655,   656,   657,   658,   659,   660,   661,   662,
     663,   667,   670,   671,   672,   673,   674,   675,   676,   677,
     678,   679,   680,   681,   682,   683,   684,   685,   686,   687,
     688,   689,   690,   691,   692,   693,   694,   695,   698,   700,
     702,   704,   706,   707,   616,   631,   542,   224,   543,   544,
     617,   711,   712,   545,   431,   713,   546,   714,   225,   226,
     227,   475,   476,   547,   548,   549,   228,   229,   550,   211,
     551,   230,   119,   121,   121,   121,   121,   121,   121,   121,
     552,   553,   793,   618,   619,   554,   555,   556,   119,   557,
     558,   224,   559,   560,   561,   562,   620,   627,   563,   665,
     665,   628,   225,   226,   227,   564,   565,   629,   566,   630,
     428,   229,   567,   568,   569,   230,   119,   570,   123,   124,
     125,   126,   127,   128,   129,   213,   697,   697,   697,   697,
     697,   215,   709,   571,   572,   150,   151,   152,   573,   154,
     155,   166,   574,   170,   119,   217,   715,   575,   576,   716,
     119,   577,   183,   717,   578,   579,   795,   580,   807,     0,
     581,     0,   794,   719,   119,   582,   718,   583,   584,     0,
     796,   585,   797,   721,   798,   586,   799,   587,   800,   588,
     589,     0,     0,   590,   591,   207,   801,   210,   212,   214,
     216,   218,   802,   446,   720,   803,   722,   723,     0,   724,
     725,   727,   806,   726,   728,   808,   729,   751,   809,   810,
     811,   812,   813,   750,     0,   753,   754,     0,   782,   784,
     814,   815,   816,   817,   818,   786,   788,   790,   860,   819,
     820,   821,   822,   862,   824,   864,   826,   866,   828,   269,
     830,   869,   832,     0,   270,     0,     0,     0,     0,     0,
       0,     0,     0,     0,   276,   277,   432,   433,     0,   434,
     435,   436,   437,   438,   439,   440,   441,   442,   443,   444,
     445,   446,   287,   432,   433,   734,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,     0,
       0,     0,     0,     0,   872,     0,     0,     0,     0,   873,
     874,   875,   876,     0,   877,   878,     0,   879,   632,   634,
     636,   638,   640,     0,   880,   881,   882,   883,     0,     0,
     884,     0,   132,   885,   132,     0,   132,     0,   132,     0,
     132,     0,     0,     0,   664,   668,   432,   433,     0,   434,
     435,   436,   437,   438,   439,   440,   441,   442,   443,   444,
     445,   446,     0,     0,   767,   768,     0,     0,     0,     0,
       0,   696,   699,   701,   703,   705,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,   472,   473,   351,
     352,   353,   354,   355,   356,   357,   358,   359,   360,   361,
     362,   363,   364,   365,   366,   367,   368,   369,   370,   371,
     372,   373,   374,   375,   376,   377,   378,   379,   380,   381,
     382,   383,   384,   385,   386,   387,   388,   389,   390,   391,
     392,   393,   394,   395,   396,   397,   398,   399,   400,   401,
     402,   403,   404,   405,   406,   407,   408,   409,   410,   411,
     432,   433,     0,   434,   435,   436,   437,   438,   439,   440,
     441,   442,   443,   444,   445,   446,     0,     0,   867,   868,
     412,   413,   414,   415,   416,   417,   418,   419,     0,     0,
       0,     0,     0,     0,     0,   420,   421,   422,   423,   424,
     425,     0,     0,     0,     0,     0,     0,   426,   427,   592,
     352,   353,   354,   355,   356,   357,   358,   359,   360,   361,
     362,   363,   364,   365,   366,   367,   368,   369,   370,   371,
     372,   373,   374,   375,   376,   377,   378,   379,   380,   381,
     382,   383,   384,   385,   386,   387,   388,   389,   390,   391,
     392,   393,   394,   395,   396,   397,   398,   399,   400,   401,
     402,   403,   404,   405,   406,   407,   408,   409,   410,   411,
       0,     0,     0,     0,     0,     0,     0,   823,     0,   825,
       0,   827,     0,   829,     0,   831,     0,     0,     0,     0,
     412,   413,   414,   415,   416,   417,   418,   419,     0,     0,
       0,     0,     0,     0,     0,   420,   421,   422,   423,   424,
     425,     0,     0,     0,     0,     0,     0,   426,   427,   484,
     485,   486,   487,   488,     0,     0,   489,     0,   490,   491,
     492,   493,   494,   495,   496,   497,   498,   499,   500,   434,
     435,   436,   437,   438,   439,   440,   441,   442,   443,   444,
     445,   446,     0,   501,     0,     0,     0,     0,   633,   635,
     637,   639,   641,   642,   643,     0,     0,     0,     0,   502,
       0,     0,     0,     0,     0,     0,     0,  -211,     1,     0,
       0,     0,     0,     0,   666,   669,     2,     0,     3,     4,
       5,     6,     7,     8,     9,    10,    11,    12,    13,    14,
      15,    16,    17,    18,    19,    20,    21,    22,    23,    24,
      25,    26,    27,    28,    29,    30,    31,    32,    33,    34,
      35,    36,    37,    38,    39,    40,    41,    42,    43,    44,
      45,    46,    47,    48,    49,    50,    51,    52,    53,    54,
      55,    56,    57,    58,    59,    60,    61,    62,    63,    64,
      65,    66,    67,    68,    69,    70,    71,    72,    73,    74,
      75,    76,    77,    78,    79,    80,    81,    82,    83,    84,
      85,    86,    87,    88,    89,    90,    91,    92,    93,    94,
      95,    96,    97,    98,    99,   297,   298,   299,   300,   301,
     302,   303,   304,   305,   306,   307,   308,   309,   310,   311,
     312,   313,   314,   315,   316,     0,     0,     0,     0,     0,
       0,     0,     0,   317,     0,     0,     0,     0,     0,   318,
       0,     0,     0,     0,     0,     0,   319,     0,     0,   320,
     321,   322,     0,     0,   323,   324,   503,   504,   505,   506,
     507,     0,     0,   508,   325,   509,   510,   511,   512,   513,
     514,   515,   516,   517,   518,   519,     0,   326,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,   432,   433,
     520,   434,   435,   436,   437,   438,   439,   440,   441,   442,
     443,   444,   445,   446,   432,   433,   521,   434,   435,   436,
     437,   438,   439,   440,   441,   442,   443,   444,   445,   446,
       0,     0,   870,   871,   432,   433,     0,   434,   435,   436,
     437,   438,   439,   440,   441,   442,   443,   444,   445,   446,
       0,   432,   433,   740,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,     0,   432,   433,
     743,   434,   435,   436,   437,   438,   439,   440,   441,   442,
     443,   444,   445,   446,     0,   432,   433,   749,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,     0,   432,   433,   752,   434,   435,   436,   437,   438,
     439,   440,   441,   442,   443,   444,   445,   446,     0,   432,
     433,   756,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,     0,   432,   433,   757,   434,
     435,   436,   437,   438,   439,   440,   441,   442,   443,   444,
     445,   446,     0,   432,   433,   758,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,     0,
     432,   433,   759,   434,   435,   436,   437,   438,   439,   440,
     441,   442,   443,   444,   445,   446,     0,   432,   433,   760,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,     0,   432,   433,   769,   434,   435,   436,
     437,   438,   439,   440,   441,   442,   443,   444,   445,   446,
       0,   432,   433,   770,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,     0,   432,   433,
     771,   434,   435,   436,   437,   438,   439,   440,   441,   442,
     443,   444,   445,   446,     0,   432,   433,   772,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,     0,   432,   433,   777,   434,   435,   436,   437,   438,
     439,   440,   441,   442,   443,   444,   445,   446,     0,   432,
     433,   778,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,     0,   432,   433,   779,   434,
     435,   436,   437,   438,   439,   440,   441,   442,   443,   444,
     445,   446,     0,   432,   433,   780,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,     0,
     432,   433,   781,   434,   435,   436,   437,   438,   439,   440,
     441,   442,   443,   444,   445,   446,     0,   432,   433,   783,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,     0,   432,   433,   785,   434,   435,   436,
     437,   438,   439,   440,   441,   442,   443,   444,   445,   446,
       0,   432,   433,   787,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,     0,   432,   433,
     789,   434,   435,   436,   437,   438,   439,   440,   441,   442,
     443,   444,   445,   446,     0,   432,   433,   847,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,     0,   432,   433,   848,   434,   435,   436,   437,   438,
     439,   440,   441,   442,   443,   444,   445,   446,     0,   432,
     433,   849,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,     0,   432,   433,   850,   434,
     435,   436,   437,   438,   439,   440,   441,   442,   443,   444,
     445,   446,     0,   432,   433,   852,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,     0,
     432,   433,   853,   434,   435,   436,   437,   438,   439,   440,
     441,   442,   443,   444,   445,   446,     0,   432,   433,   855,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,     0,   432,   433,   863,   434,   435,   436,
     437,   438,   439,   440,   441,   442,   443,   444,   445,   446,
       0,   432,   433,   865,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,   432,   433,   593,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,   432,   433,   730,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,   432,
     433,   731,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,   432,   433,   732,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,   432,   433,   733,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,   432,   433,   735,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,   432,   433,   736,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,   432,
     433,   737,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,   432,   433,   738,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,   432,   433,   739,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,   432,   433,   741,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,   432,   433,   742,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,   432,
     433,   744,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,   432,   433,   745,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,   432,   433,   746,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,   432,   433,   747,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,   432,   433,   748,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,   432,
     433,   755,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,   432,   433,   761,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,   432,   433,   762,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,   432,   433,   763,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,   432,   433,   764,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,   432,
     433,   765,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,   432,   433,   766,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,   432,   433,   773,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,   432,   433,   774,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,   432,   433,   775,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,   432,
     433,   776,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,   432,   433,   791,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,   432,   433,   792,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,   432,   433,   833,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,   432,   433,   834,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,   432,
     433,   835,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,   432,   433,   836,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,   432,   433,   837,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,   432,   433,   838,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,   432,   433,   839,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,   432,
     433,   840,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,   432,   433,   843,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,   432,   433,   845,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,   432,   433,   846,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,   432,   433,   851,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,   432,
     433,   854,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,   432,   433,   856,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,   432,   433,   857,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,   432,   433,   858,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,   432,   433,   859,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,   432,
     433,   861,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,   432,   433,   886,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,   432,   433,   887,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,   432,   433,   888,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,   432,   433,   889,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,   432,
     433,   890,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,   432,   433,   891,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,   432,   433,   892,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,   432,   433,   893,
     434,   435,   436,   437,   438,   439,   440,   441,   442,   443,
     444,   445,   446,   432,   433,   894,   434,   435,   436,   437,
     438,   439,   440,   441,   442,   443,   444,   445,   446,   432,
     433,   895,   434,   435,   436,   437,   438,   439,   440,   441,
     442,   443,   444,   445,   446,   432,   433,   896,   434,   435,
     436,   437,   438,   439,   440,   441,   442,   443,   444,   445,
     446,   432,   433,   897,   434,   435,   436,   437,   438,   439,
     440,   441,   442,   443,   444,   445,   446,     0,     0,   898,
     432,   433,   710,   434,   435,   436,   437,   438,   439,   440,
     441,   442,   443,   444,   445,   446,   435,   436,   437,   438,
     439,   440,   441,   442,   443,   444,   445,   446,  -349,  -349,
    -349,  -349,   440,   441,   442,   443,   444,   445,   446
};

static const yytype_int16 yycheck[] =
{
      88,    89,     3,     4,     5,    10,     7,     4,     4,    10,
       4,     4,    11,    12,    13,    14,    15,    16,    17,    18,
      19,    20,    21,    22,    23,    24,    25,    26,    27,    28,
      29,    30,    31,    32,    33,    34,    35,    36,    37,     4,
       5,    40,    41,    42,    43,    44,    45,    46,    47,    48,
      10,    50,    51,    52,    53,    54,    55,    56,    57,   225,
     226,   227,     3,     3,   230,    23,    24,    25,    26,     4,
     234,     4,     3,     4,     5,     6,     7,    10,    36,    10,
      79,   234,    81,    82,    83,    84,    85,     6,     7,    47,
      48,    10,    50,    51,    52,    53,    54,    55,    56,    57,
       3,     4,     5,     6,     7,     8,     4,    10,     4,     4,
       3,     3,    10,     6,     7,    10,     3,    10,     3,   234,
       4,     4,     7,     4,     4,    10,     6,     7,     3,     3,
      10,     6,     7,     4,   133,    10,     6,     7,     4,   138,
      10,   229,     7,   142,    10,    10,     4,   146,   147,   148,
     149,   240,   241,     4,   153,     6,     7,   156,   234,    10,
     225,   160,   161,   225,   224,   240,   241,   166,   167,     3,
     169,     3,   225,     3,   173,   263,   264,   265,   266,   267,
     240,     3,     3,     0,     4,   351,     6,     7,   224,   224,
      10,   224,     3,     4,     5,   153,     7,   224,     4,    10,
       6,     7,     4,     4,    10,   108,   109,     3,     4,     5,
       4,     7,     6,     7,    10,   224,    10,     4,   219,     4,
     225,   234,   235,   236,   237,   225,   224,   228,   229,   230,
     231,   232,     4,   228,    10,   224,     3,   238,   239,   152,
     234,   234,   243,   244,   228,   228,   228,   244,   244,   162,
     163,   228,   228,     4,   235,    19,   235,     3,     3,    23,
       4,    25,   261,    27,     4,     4,   231,   232,    32,     4,
       4,   228,   271,   272,   234,     4,    40,    41,    42,    43,
      44,    45,   224,     4,   225,   225,   285,   286,   219,   224,
     224,     3,     4,     5,     4,     7,     4,   296,    10,   230,
     231,   232,     4,   225,     4,   225,   225,   238,   239,     4,
       6,     7,   243,   244,    10,   225,   200,   201,   202,   203,
     204,     4,     4,   225,   225,   244,     4,   242,   231,   232,
     233,   225,     4,   236,     4,     3,     4,     5,   296,     7,
     228,   244,    10,   236,   432,   433,   434,   435,   436,   437,
     438,   244,   440,   441,   442,   443,   444,   445,   446,   244,
     235,   236,     4,    10,   244,   278,     6,     7,   234,   244,
      10,   228,     6,     7,   244,     4,    10,    10,   142,   244,
      10,     4,   146,   147,    10,     3,     6,     7,     4,    10,
      10,     4,   156,   244,     4,   228,   160,   161,     4,   228,
     228,   228,   228,   167,   228,   169,     4,     4,   219,   173,
       4,     4,     4,     4,     4,   228,   239,   228,   225,   230,
     231,   232,   225,   219,   244,   239,   592,   238,   239,   239,
     239,   239,   243,   244,   230,   231,   232,     4,   244,   239,
     239,   239,   238,   239,   240,     3,   239,   243,   244,   239,
     244,   539,   540,   541,   542,   543,   544,   545,   546,   547,
     548,   549,   550,   551,   552,   553,   554,   555,   556,   557,
     558,   559,   560,   561,   562,   563,   564,   565,   566,   567,
     568,   569,   570,   571,   572,   573,   574,   575,   576,   577,
     578,   579,   580,   581,   582,   583,   584,   585,   586,   587,
     588,   589,   590,   591,     3,   242,   239,   219,   239,   239,
       4,   599,   600,   239,     3,   603,   239,   605,   230,   231,
     232,   285,   286,   239,   239,   239,   238,   239,   239,   225,
     239,   243,   244,   532,   533,   534,   535,   536,   537,   538,
     239,   239,   708,     4,     4,   239,   239,   239,   244,   239,
     239,   219,   239,   239,   239,   239,     4,     4,   239,   558,
     559,     4,   230,   231,   232,   239,   239,     4,   239,     4,
     238,   239,   239,   239,   239,   243,   244,   239,    12,    13,
      14,    15,    16,    17,    18,   225,   585,   586,   587,   588,
     589,   225,     4,   239,   239,    29,    30,    31,   239,    33,
      34,    35,   239,    37,   244,   225,     4,   239,   239,     4,
     244,   239,    46,     4,   239,   239,     4,   239,   752,    -1,
     239,    -1,   710,   240,   244,   239,   241,   239,   239,    -1,
     718,   239,   720,   240,   722,   239,   724,   239,   726,   239,
     239,    -1,    -1,   239,   239,    79,   734,    81,    82,    83,
      84,    85,   740,   237,   241,   743,   241,   240,    -1,   241,
     240,   240,   750,   241,   240,   753,   240,   240,   756,   757,
     758,   759,   760,   241,    -1,   241,   240,    -1,   241,   241,
     768,   769,   770,   771,   772,   241,   241,   241,   240,   777,
     778,   779,   780,   241,   782,   241,   784,   240,   786,   133,
     788,   240,   790,    -1,   138,    -1,    -1,    -1,    -1,    -1,
      -1,    -1,    -1,    -1,   148,   149,   222,   223,    -1,   225,
     226,   227,   228,   229,   230,   231,   232,   233,   234,   235,
     236,   237,   166,   222,   223,   241,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,    -1,
      -1,    -1,    -1,    -1,   842,    -1,    -1,    -1,    -1,   847,
     848,   849,   850,    -1,   852,   853,    -1,   855,   532,   533,
     534,   535,   536,    -1,   862,   863,   864,   865,    -1,    -1,
     868,    -1,   781,   871,   783,    -1,   785,    -1,   787,    -1,
     789,    -1,    -1,    -1,   558,   559,   222,   223,    -1,   225,
     226,   227,   228,   229,   230,   231,   232,   233,   234,   235,
     236,   237,    -1,    -1,   240,   241,    -1,    -1,    -1,    -1,
      -1,   585,   586,   587,   588,   589,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,   271,   272,   110,
     111,   112,   113,   114,   115,   116,   117,   118,   119,   120,
     121,   122,   123,   124,   125,   126,   127,   128,   129,   130,
     131,   132,   133,   134,   135,   136,   137,   138,   139,   140,
     141,   142,   143,   144,   145,   146,   147,   148,   149,   150,
     151,   152,   153,   154,   155,   156,   157,   158,   159,   160,
     161,   162,   163,   164,   165,   166,   167,   168,   169,   170,
     222,   223,    -1,   225,   226,   227,   228,   229,   230,   231,
     232,   233,   234,   235,   236,   237,    -1,    -1,   240,   241,
     191,   192,   193,   194,   195,   196,   197,   198,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,   206,   207,   208,   209,   210,
     211,    -1,    -1,    -1,    -1,    -1,    -1,   218,   219,   110,
     111,   112,   113,   114,   115,   116,   117,   118,   119,   120,
     121,   122,   123,   124,   125,   126,   127,   128,   129,   130,
     131,   132,   133,   134,   135,   136,   137,   138,   139,   140,
     141,   142,   143,   144,   145,   146,   147,   148,   149,   150,
     151,   152,   153,   154,   155,   156,   157,   158,   159,   160,
     161,   162,   163,   164,   165,   166,   167,   168,   169,   170,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,   781,    -1,   783,
      -1,   785,    -1,   787,    -1,   789,    -1,    -1,    -1,    -1,
     191,   192,   193,   194,   195,   196,   197,   198,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,   206,   207,   208,   209,   210,
     211,    -1,    -1,    -1,    -1,    -1,    -1,   218,   219,   171,
     172,   173,   174,   175,    -1,    -1,   178,    -1,   180,   181,
     182,   183,   184,   185,   186,   187,   188,   189,   190,   225,
     226,   227,   228,   229,   230,   231,   232,   233,   234,   235,
     236,   237,    -1,   205,    -1,    -1,    -1,    -1,   532,   533,
     534,   535,   536,   537,   538,    -1,    -1,    -1,    -1,   221,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,     0,     1,    -1,
      -1,    -1,    -1,    -1,   558,   559,     9,    -1,    11,    12,
      13,    14,    15,    16,    17,    18,    19,    20,    21,    22,
      23,    24,    25,    26,    27,    28,    29,    30,    31,    32,
      33,    34,    35,    36,    37,    38,    39,    40,    41,    42,
      43,    44,    45,    46,    47,    48,    49,    50,    51,    52,
      53,    54,    55,    56,    57,    58,    59,    60,    61,    62,
      63,    64,    65,    66,    67,    68,    69,    70,    71,    72,
      73,    74,    75,    76,    77,    78,    79,    80,    81,    82,
      83,    84,    85,    86,    87,    88,    89,    90,    91,    92,
      93,    94,    95,    96,    97,    98,    99,   100,   101,   102,
     103,   104,   105,   106,   107,   171,   172,   173,   174,   175,
     176,   177,   178,   179,   180,   181,   182,   183,   184,   185,
     186,   187,   188,   189,   190,    -1,    -1,    -1,    -1,    -1,
      -1,    -1,    -1,   199,    -1,    -1,    -1,    -1,    -1,   205,
      -1,    -1,    -1,    -1,    -1,    -1,   212,    -1,    -1,   215,
     216,   217,    -1,    -1,   220,   221,   171,   172,   173,   174,
     175,    -1,    -1,   178,   230,   180,   181,   182,   183,   184,
     185,   186,   187,   188,   189,   190,    -1,   243,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,   222,   223,
     205,   225,   226,   227,   228,   229,   230,   231,   232,   233,
     234,   235,   236,   237,   222,   223,   221,   225,   226,   227,
     228,   229,   230,   231,   232,   233,   234,   235,   236,   237,
      -1,    -1,   240,   241,   222,   223,    -1,   225,   226,   227,
     228,   229,   230,   231,   232,   233,   234,   235,   236,   237,
      -1,   222,   223,   241,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,    -1,   222,   223,
     241,   225,   226,   227,   228,   229,   230,   231,   232,   233,
     234,   235,   236,   237,    -1,   222,   223,   241,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,    -1,   222,   223,   241,   225,   226,   227,   228,   229,
     230,   231,   232,   233,   234,   235,   236,   237,    -1,   222,
     223,   241,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,    -1,   222,   223,   241,   225,
     226,   227,   228,   229,   230,   231,   232,   233,   234,   235,
     236,   237,    -1,   222,   223,   241,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,    -1,
     222,   223,   241,   225,   226,   227,   228,   229,   230,   231,
     232,   233,   234,   235,   236,   237,    -1,   222,   223,   241,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,    -1,   222,   223,   241,   225,   226,   227,
     228,   229,   230,   231,   232,   233,   234,   235,   236,   237,
      -1,   222,   223,   241,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,    -1,   222,   223,
     241,   225,   226,   227,   228,   229,   230,   231,   232,   233,
     234,   235,   236,   237,    -1,   222,   223,   241,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,    -1,   222,   223,   241,   225,   226,   227,   228,   229,
     230,   231,   232,   233,   234,   235,   236,   237,    -1,   222,
     223,   241,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,    -1,   222,   223,   241,   225,
     226,   227,   228,   229,   230,   231,   232,   233,   234,   235,
     236,   237,    -1,   222,   223,   241,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,    -1,
     222,   223,   241,   225,   226,   227,   228,   229,   230,   231,
     232,   233,   234,   235,   236,   237,    -1,   222,   223,   241,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,    -1,   222,   223,   241,   225,   226,   227,
     228,   229,   230,   231,   232,   233,   234,   235,   236,   237,
      -1,   222,   223,   241,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,    -1,   222,   223,
     241,   225,   226,   227,   228,   229,   230,   231,   232,   233,
     234,   235,   236,   237,    -1,   222,   223,   241,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,    -1,   222,   223,   241,   225,   226,   227,   228,   229,
     230,   231,   232,   233,   234,   235,   236,   237,    -1,   222,
     223,   241,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,    -1,   222,   223,   241,   225,
     226,   227,   228,   229,   230,   231,   232,   233,   234,   235,
     236,   237,    -1,   222,   223,   241,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,    -1,
     222,   223,   241,   225,   226,   227,   228,   229,   230,   231,
     232,   233,   234,   235,   236,   237,    -1,   222,   223,   241,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,    -1,   222,   223,   241,   225,   226,   227,
     228,   229,   230,   231,   232,   233,   234,   235,   236,   237,
      -1,   222,   223,   241,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,   222,   223,   240,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,   222,   223,   240,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,   222,
     223,   240,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,   222,   223,   240,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,   222,   223,   240,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,   222,   223,   240,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,   222,   223,   240,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,   222,
     223,   240,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,   222,   223,   240,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,   222,   223,   240,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,   222,   223,   240,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,   222,   223,   240,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,   222,
     223,   240,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,   222,   223,   240,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,   222,   223,   240,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,   222,   223,   240,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,   222,   223,   240,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,   222,
     223,   240,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,   222,   223,   240,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,   222,   223,   240,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,   222,   223,   240,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,   222,   223,   240,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,   222,
     223,   240,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,   222,   223,   240,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,   222,   223,   240,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,   222,   223,   240,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,   222,   223,   240,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,   222,
     223,   240,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,   222,   223,   240,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,   222,   223,   240,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,   222,   223,   240,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,   222,   223,   240,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,   222,
     223,   240,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,   222,   223,   240,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,   222,   223,   240,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,   222,   223,   240,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,   222,   223,   240,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,   222,
     223,   240,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,   222,   223,   240,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,   222,   223,   240,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,   222,   223,   240,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,   222,   223,   240,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,   222,
     223,   240,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,   222,   223,   240,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,   222,   223,   240,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,   222,   223,   240,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,   222,   223,   240,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,   222,
     223,   240,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,   222,   223,   240,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,   222,   223,   240,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,   222,   223,   240,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,   222,   223,   240,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,   222,
     223,   240,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,   222,   223,   240,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,   222,   223,   240,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,   222,   223,   240,
     225,   226,   227,   228,   229,   230,   231,   232,   233,   234,
     235,   236,   237,   222,   223,   240,   225,   226,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237,   222,
     223,   240,   225,   226,   227,   228,   229,   230,   231,   232,
     233,   234,   235,   236,   237,   222,   223,   240,   225,   226,
     227,   228,   229,   230,   231,   232,   233,   234,   235,   236,
     237,   222,   223,   240,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,    -1,    -1,   240,
     222,   223,   224,   225,   226,   227,   228,   229,   230,   231,
     232,   233,   234,   235,   236,   237,   226,   227,   228,   229,
     230,   231,   232,   233,   234,   235,   236,   237,   227,   228,
     229,   230,   231,   232,   233,   234,   235,   236,   237
};

/* YYSTOS[STATE-NUM] -- The symbol kind of the accessing symbol of
   state STATE-NUM.  */
static const yytype_int16 yystos[] =
{
       0,     1,     9,    11,    12,    13,    14,    15,    16,    17,
      18,    19,    20,    21,    22,    23,    24,    25,    26,    27,
      28,    29,    30,    31,    32,    33,    34,    35,    36,    37,
      38,    39,    40,    41,    42,    43,    44,    45,    46,    47,
      48,    49,    50,    51,    52,    53,    54,    55,    56,    57,
      58,    59,    60,    61,    62,    63,    64,    65,    66,    67,
      68,    69,    70,    71,    72,    73,    74,    75,    76,    77,
      78,    79,    80,    81,    82,    83,    84,    85,    86,    87,
      88,    89,    90,    91,    92,    93,    94,    95,    96,    97,
      98,    99,   100,   101,   102,   103,   104,   105,   106,   107,
     246,     4,    10,     4,    10,   234,   234,    10,   234,     4,
      10,   234,    10,   225,     4,    10,     6,     7,    10,   244,
     250,   251,   252,   252,   252,   252,   252,   252,   252,   252,
       4,   250,   251,   251,   251,     3,   251,   254,   235,   236,
     250,   251,   254,   254,   236,   250,   254,   254,   250,   251,
     252,   252,   252,   250,   252,   252,     3,     4,     5,     8,
     108,   109,   231,   232,   233,   236,   252,   253,   257,   254,
     252,     3,     3,   250,     4,   250,     4,   250,     4,   250,
       4,   250,   250,   252,   254,   254,     4,   254,   254,   254,
     254,   254,   254,   254,   254,   255,     4,     4,     4,     4,
       3,   234,   234,     4,   234,     4,   234,   252,   225,   225,
     252,   225,   252,   225,   252,   225,   252,   225,   252,   225,
       3,     3,     4,     5,   219,   230,   231,   232,   238,   239,
     243,   247,   248,   251,   248,     3,   225,     3,   225,     3,
       3,     3,     0,   224,   224,   224,   224,     4,     4,   224,
       4,   224,     4,   225,     4,   228,     4,   224,     4,   244,
      10,   224,     3,   228,   228,   228,   228,   228,     4,   252,
     252,   235,   235,   250,   250,   250,   252,   252,   253,   254,
     250,   250,   250,   253,   253,     3,     3,   252,   250,   250,
     251,   250,     4,     4,     4,     4,   228,   171,   172,   173,
     174,   175,   176,   177,   178,   179,   180,   181,   182,   183,
     184,   185,   186,   187,   188,   189,   190,   199,   205,   212,
     215,   216,   217,   220,   221,   230,   243,   256,     4,     4,
     224,     4,   224,     4,     4,     4,   225,     4,   225,     4,
     225,     4,   225,     4,   225,     4,   225,   242,   247,   247,
     247,   110,   111,   112,   113,   114,   115,   116,   117,   118,
     119,   120,   121,   122,   123,   124,   125,   126,   127,   128,
     129,   130,   131,   132,   133,   134,   135,   136,   137,   138,
     139,   140,   141,   142,   143,   144,   145,   146,   147,   148,
     149,   150,   151,   152,   153,   154,   155,   156,   157,   158,
     159,   160,   161,   162,   163,   164,   165,   166,   167,   168,
     169,   170,   191,   192,   193,   194,   195,   196,   197,   198,
     206,   207,   208,   209,   210,   211,   218,   219,   238,   248,
     247,     3,   222,   223,   225,   226,   227,   228,   229,   230,
     231,   232,   233,   234,   235,   236,   237,     3,   225,     4,
       4,   228,   228,     4,    10,     4,    10,    10,    10,     4,
       3,     4,    10,     4,     4,   244,   251,   248,   248,   248,
     248,   248,   252,   252,   253,   250,   250,   254,   228,   228,
     228,   228,   228,   228,   171,   172,   173,   174,   175,   178,
     180,   181,   182,   183,   184,   185,   186,   187,   188,   189,
     190,   205,   221,   171,   172,   173,   174,   175,   178,   180,
     181,   182,   183,   184,   185,   186,   187,   188,   189,   190,
     205,   221,     4,     4,     4,     4,     4,     4,     4,     4,
       4,   247,   239,   239,   239,   239,   239,   239,   239,   239,
     239,   239,   239,   239,   239,   239,   239,   239,   239,   239,
     239,   239,   239,   239,   239,   239,   239,   239,   239,   239,
     239,   239,   239,   239,   239,   239,   239,   239,   239,   239,
     239,   239,   239,   239,   239,   239,   239,   239,   239,   239,
     239,   239,   239,   239,   239,   239,   239,   239,   239,   239,
     239,   239,   110,   240,   225,   248,   248,   248,   248,   228,
     229,   248,   248,   228,   248,   228,   248,   248,   248,   248,
     248,   248,   248,   225,     4,     3,     3,     4,     4,     4,
       4,     4,   200,   201,   202,   203,   204,     4,     4,     4,
       4,   242,   250,   252,   250,   252,   250,   252,   250,   252,
     250,   252,   252,   252,   248,   248,   248,   248,   248,   248,
     248,   248,   248,   248,   248,   248,   248,   248,   248,   248,
     248,   248,   248,   248,   250,   251,   252,   248,   250,   252,
     248,   248,   248,   248,   248,   248,   248,   248,   248,   248,
     248,   248,   248,   248,   248,   248,   248,   248,   248,   248,
     248,   248,   248,   248,   248,   248,   250,   251,   248,   250,
     248,   250,   248,   250,   248,   250,   248,   248,   240,     4,
     224,   248,   248,   248,   248,     4,     4,     4,   241,   240,
     241,   240,   241,   240,   241,   240,   241,   240,   240,   240,
     240,   240,   240,   240,   241,   240,   240,   240,   240,   240,
     241,   240,   240,   241,   240,   240,   240,   240,   240,   241,
     241,   240,   241,   241,   240,   240,   241,   241,   241,   241,
     241,   240,   240,   240,   240,   240,   240,   240,   241,   241,
     241,   241,   241,   240,   240,   240,   240,   241,   241,   241,
     241,   241,   241,   241,   241,   241,   241,   241,   241,   241,
     241,   240,   240,   247,   248,     4,   248,   248,   248,   248,
     248,   248,   248,   248,   248,   249,   248,   249,   248,   248,
     248,   248,   248,   248,   248,   248,   248,   248,   248,   248,
     248,   248,   248,   250,   248,   250,   248,   250,   248,   250,
     248,   250,   248,   240,   240,   240,   240,   240,   240,   240,
     240,   240,   241,   240,   240,   240,   240,   241,   241,   241,
     241,   240,   241,   241,   240,   241,   240,   240,   240,   240,
     240,   240,   241,   241,   241,   241,   240,   240,   241,   240,
     240,   241,   248,   248,   248,   248,   248,   248,   248,   248,
     248,   248,   248,   248,   248,   248,   240,   240,   240,   240,
     240,   240,   240,   240,   240,   240,   240,   240,   240
};

/* YYR1[RULE-NUM] -- Symbol kind of the left-hand side of rule RULE-NUM.  */
static const yytype_int16 yyr1[] =
{
       0,   245,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   246,   246,   246,   246,   246,   246,   246,
     246,   246,   246,   247,   247,   247,   247,   247,   247,   247,
     247,   247,   247,   247,   247,   247,   247,   247,   247,   247,
     247,   247,   247,   247,   247,   247,   247,   247,   247,   247,
     247,   247,   247,   247,   247,   247,   247,   247,   247,   247,
     247,   247,   247,   247,   247,   247,   247,   247,   247,   247,
     247,   247,   247,   247,   247,   247,   247,   247,   247,   247,
     247,   247,   247,   247,   247,   247,   247,   247,   247,   247,
     247,   247,   247,   247,   247,   247,   247,   247,   247,   247,
     247,   247,   247,   247,   247,   247,   247,   247,   247,   247,
     247,   247,   247,   247,   247,   247,   247,   247,   247,   247,
     247,   247,   247,   247,   247,   247,   247,   247,   247,   248,
     248,   248,   248,   248,   248,   248,   248,   248,   248,   248,
     248,   248,   248,   248,   248,   248,   248,   248,   249,   249,
     250,   250,   251,   251,   251,   251,   251,   252,   252,   253,
     253,   253,   253,   254,   254,   255,   255,   256,   256,   256,
     256,   256,   256,   256,   256,   256,   256,   256,   256,   256,
     256,   256,   256,   256,   256,   256,   256,   256,   256,   256,
     256,   256,   256,   256,   256,   256,   256,   256,   256,   256,
     256,   256,   256,   256,   256,   256,   256,   256,   256,   256,
     256,   256,   256,   256,   256,   256,   256,   256,   256,   256,
     256,   256,   256,   256,   256,   256,   256,   256,   256,   256,
     256,   256,   256,   256,   256,   256,   256,   256,   257,   257,
     257,   257
};

/* YYR2[RULE-NUM] -- Number of symbols on the right-hand side of rule RULE-NUM.  */
static const yytype_int8 yyr2[] =
{
       0,     2,     4,     3,     4,     4,     4,     2,     1,     2,
       1,     2,     1,     2,     3,     2,     1,     7,     5,     6,
       4,     4,     2,     2,     2,     2,     4,     2,     2,     2,
       2,     2,     2,     2,     2,     3,     2,     2,     4,     4,
       3,     2,     1,     3,     2,     2,     2,     1,     3,     2,
       4,     4,     1,     2,     4,     2,     4,     1,     2,     3,
       2,     3,     1,     2,     1,     2,     1,     2,     4,     1,
       2,     3,     3,     1,     2,     1,     2,     3,     2,     3,
       2,     2,     3,     4,     4,     2,     3,     3,     1,     2,
       2,     3,     3,     2,     2,     1,     2,     3,     2,     1,
       3,     2,     3,     2,     3,     2,     3,     2,     2,     1,
       3,     4,     3,     2,     1,     2,     1,     2,     1,     2,
       1,     2,     1,     1,     1,     1,     2,     1,     3,     1,
       3,     1,     3,     1,     3,     1,     3,     2,     4,     1,
       2,     3,     4,     1,     3,     2,     4,     1,     2,     3,
       4,     1,     1,     1,     1,     1,     1,     1,     1,     2,
       1,     3,     2,     4,     1,     3,     2,     4,     1,     3,
       2,     4,     1,     3,     2,     4,     1,     3,     2,     4,
       1,     3,     2,     4,     1,     3,     1,     3,     2,     4,
       2,     3,     5,     2,     3,     5,     2,     4,     1,     3,
       1,     2,     1,     3,     1,     1,     1,     2,     4,     4,
       1,     0,     1,     1,     3,     5,     5,     7,     5,     7,
       5,     7,     5,     7,     5,     7,     5,     7,     7,     5,
       7,     7,     5,     5,     5,     5,     5,     5,     7,     5,
       5,     5,     5,     5,     7,     5,     5,     7,     5,     5,
       5,     5,     5,     5,     7,     9,     9,     9,     9,     5,
       5,     5,     5,     5,     5,     2,     9,     5,     9,     5,
       7,     5,     7,     7,     5,     5,     5,     7,     7,     9,
       7,     7,     9,     9,     9,     9,     7,     7,     9,     7,
       7,     7,     9,     3,     2,     2,     1,     1,     2,     1,
       2,     2,     5,     2,     2,     2,     2,     5,     2,     2,
       1,     2,     2,     2,     2,     2,     2,     2,     2,     3,
       3,     3,     3,     3,     3,     1,     5,     3,     3,     3,
       3,     3,     3,     4,     4,     4,     4,     3,     1,     3,
       3,     1,     2,     3,     3,     4,     1,     1,     1,     1,
       1,     2,     2,     1,     1,     0,     2,     1,     1,     2,
       2,     2,     2,     1,     1,     1,     2,     2,     1,     2,
       2,     1,     2,     2,     1,     2,     2,     1,     2,     2,
       1,     2,     2,     1,     2,     2,     1,     2,     2,     1,
       2,     2,     1,     2,     2,     1,     2,     2,     1,     2,
       2,     1,     2,     2,     1,     2,     2,     1,     2,     2,
       3,     3,     3,     3,     3,     3,     3,     1,     2,     2,
       3,     3,     3,     3,     1,     1,     2,     2,     2,     1,
       2,     1
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
  case 2: /* command: S_LET var_or_range '=' e  */
#line 294 "gram.y"
                                { let((yyvsp[-2].rval).left.vp, (yyvsp[0].enode)); }
#line 2851 "y.tab.c"
    break;

  case 3: /* command: S_LET var_or_range '='  */
#line 296 "gram.y"
                                { (yyvsp[-1].rval).left.vp->v = (double) 0.0;
				  if ((yyvsp[-1].rval).left.vp->expr &&
					!((yyvsp[-1].rval).left.vp->flags & IS_STREXPR)) {
				    efree((yyvsp[-1].rval).left.vp->expr);
				    (yyvsp[-1].rval).left.vp->expr = NULL;
				  }
				  (yyvsp[-1].rval).left.vp->cellerror = CELLOK;
				  (yyvsp[-1].rval).left.vp->flags &= ~IS_VALID;
				  (yyvsp[-1].rval).left.vp->flags |= IS_CHANGED;
				  changed++;
				  FullUpdate++;
				  modflg++; }
#line 2868 "y.tab.c"
    break;

  case 4: /* command: S_LABEL var_or_range '=' e  */
#line 309 "gram.y"
                                { slet((yyvsp[-2].rval).left.vp, (yyvsp[0].enode), 0); }
#line 2874 "y.tab.c"
    break;

  case 5: /* command: S_LEFTSTRING var_or_range '=' e  */
#line 311 "gram.y"
                                { slet((yyvsp[-2].rval).left.vp, (yyvsp[0].enode), -1); }
#line 2880 "y.tab.c"
    break;

  case 6: /* command: S_RIGHTSTRING var_or_range '=' e  */
#line 313 "gram.y"
                                { slet((yyvsp[-2].rval).left.vp, (yyvsp[0].enode), 1); }
#line 2886 "y.tab.c"
    break;

  case 7: /* command: S_LEFTJUSTIFY var_or_range  */
#line 315 "gram.y"
                                { ljustify((yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col,
				    (yyvsp[0].rval).right.vp->row, (yyvsp[0].rval).right.vp->col); }
#line 2893 "y.tab.c"
    break;

  case 8: /* command: S_LEFTJUSTIFY  */
#line 318 "gram.y"
                                { if (showrange)
				    ljustify(showsr, showsc, currow, curcol);
				}
#line 2901 "y.tab.c"
    break;

  case 9: /* command: S_RIGHTJUSTIFY var_or_range  */
#line 322 "gram.y"
                                { rjustify((yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col,
				    (yyvsp[0].rval).right.vp->row, (yyvsp[0].rval).right.vp->col); }
#line 2908 "y.tab.c"
    break;

  case 10: /* command: S_RIGHTJUSTIFY  */
#line 325 "gram.y"
                                { if (showrange)
				    rjustify(showsr, showsc, currow, curcol);
				}
#line 2916 "y.tab.c"
    break;

  case 11: /* command: S_CENTER var_or_range  */
#line 329 "gram.y"
                                { center((yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col,
				    (yyvsp[0].rval).right.vp->row, (yyvsp[0].rval).right.vp->col); }
#line 2923 "y.tab.c"
    break;

  case 12: /* command: S_CENTER  */
#line 332 "gram.y"
                                { if (showrange)
				    center(showsr, showsc, currow, curcol);
				}
#line 2931 "y.tab.c"
    break;

  case 13: /* command: S_ADDNOTE var  */
#line 335 "gram.y"
                                { if (showrange) {
				    (yyvsp[0].ent).vp->nrow=currow<showsr?currow:showsr;
				    (yyvsp[0].ent).vp->ncol=curcol<showsc?curcol:showsc;
				    (yyvsp[0].ent).vp->nlastrow=currow<showsr?showsr:currow;
				    (yyvsp[0].ent).vp->nlastcol=curcol<showsc?showsc:curcol;
				  } else {
				    (yyvsp[0].ent).vp->nrow=currow;
				    (yyvsp[0].ent).vp->ncol=curcol;
				    (yyvsp[0].ent).vp->nlastrow=currow;
				    (yyvsp[0].ent).vp->nlastcol=curcol;
				  }
				  (yyvsp[0].ent).vp->flags |= IS_CHANGED;
				  FullUpdate++;
				  modflg++;
				}
#line 2951 "y.tab.c"
    break;

  case 14: /* command: S_ADDNOTE var var_or_range  */
#line 351 "gram.y"
                                { (yyvsp[-1].ent).vp->nrow = (yyvsp[0].rval).left.vp->row;
				  (yyvsp[-1].ent).vp->ncol = (yyvsp[0].rval).left.vp->col;
				  (yyvsp[-1].ent).vp->nlastrow = (yyvsp[0].rval).right.vp->row;
				  (yyvsp[-1].ent).vp->nlastcol = (yyvsp[0].rval).right.vp->col;
				  (yyvsp[-1].ent).vp->flags |= IS_CHANGED;
				  FullUpdate++;
				  modflg++;
				}
#line 2964 "y.tab.c"
    break;

  case 15: /* command: S_DELNOTE var  */
#line 359 "gram.y"
                                { (yyvsp[0].ent).vp->nrow = (yyvsp[0].ent).vp->ncol = -1; }
#line 2970 "y.tab.c"
    break;

  case 16: /* command: S_DELNOTE  */
#line 360 "gram.y"
                                { struct ent *p;
				  p = lookat(currow, curcol);
				  p->nrow = p->ncol = -1;
				  p->flags |= IS_CHANGED;
				  modflg++;
				}
#line 2981 "y.tab.c"
    break;

  case 17: /* command: S_FORMAT COL ':' COL NUMBER NUMBER NUMBER  */
#line 367 "gram.y"
                                { doformat((yyvsp[-5].ival),(yyvsp[-3].ival),(yyvsp[-2].ival),(yyvsp[-1].ival),(yyvsp[0].ival)); }
#line 2987 "y.tab.c"
    break;

  case 18: /* command: S_FORMAT COL NUMBER NUMBER NUMBER  */
#line 369 "gram.y"
                                { doformat((yyvsp[-3].ival),(yyvsp[-3].ival),(yyvsp[-2].ival),(yyvsp[-1].ival),(yyvsp[0].ival)); }
#line 2993 "y.tab.c"
    break;

  case 19: /* command: S_FORMAT COL ':' COL NUMBER NUMBER  */
#line 371 "gram.y"
                                { doformat((yyvsp[-4].ival),(yyvsp[-2].ival),(yyvsp[-1].ival),(yyvsp[0].ival), REFMTFIX); }
#line 2999 "y.tab.c"
    break;

  case 20: /* command: S_FORMAT COL NUMBER NUMBER  */
#line 373 "gram.y"
                                { doformat((yyvsp[-2].ival),(yyvsp[-2].ival),(yyvsp[-1].ival),(yyvsp[0].ival), REFMTFIX); }
#line 3005 "y.tab.c"
    break;

  case 21: /* command: S_FORMAT NUMBER '=' STRING  */
#line 375 "gram.y"
                                { if ((yyvsp[-2].ival) >= 0 && (yyvsp[-2].ival) < 10) {
				    if (colformat[(yyvsp[-2].ival)])
					scxfree(colformat[(yyvsp[-2].ival)]);
				    if (strlen((yyvsp[0].sval)))
					colformat[(yyvsp[-2].ival)] = (yyvsp[0].sval);
				    else
					colformat[(yyvsp[-2].ival)] = NULL;
				    FullUpdate++;
				    modflg++;
				  } else
				    error("Invalid format number");
				}
#line 3022 "y.tab.c"
    break;

  case 22: /* command: S_GET strarg  */
#line 387 "gram.y"
                                {  /* This tmp hack is because readfile
				    * recurses back through yyparse. */
				    char *tmp;
				    tmp = (yyvsp[0].sval);
				    readfile(tmp, 1);
				    scxfree(tmp);
				}
#line 3034 "y.tab.c"
    break;

  case 23: /* command: S_MERGE strarg  */
#line 394 "gram.y"
                                {
				    char *tmp;
				    tmp = (yyvsp[0].sval);
				    readfile(tmp, 0);
				    scxfree(tmp);
				}
#line 3045 "y.tab.c"
    break;

  case 24: /* command: S_MDIR strarg  */
#line 400 "gram.y"
                                { if (mdir) scxfree(mdir);
				  if (strlen((yyvsp[0].sval)))
				    mdir = (yyvsp[0].sval);
				  modflg++; }
#line 3054 "y.tab.c"
    break;

  case 25: /* command: S_AUTORUN strarg  */
#line 405 "gram.y"
                                { if (autorun) scxfree(autorun);
				  if (strlen((yyvsp[0].sval)))
				    autorun = (yyvsp[0].sval);
				  modflg++; }
#line 3063 "y.tab.c"
    break;

  case 26: /* command: S_FKEY NUMBER '=' strarg  */
#line 410 "gram.y"
                                { if ((yyvsp[-2].ival) > 0 && (yyvsp[-2].ival) <= FKEYS) {
				    if (fkey[(yyvsp[-2].ival) - 1]) {
					scxfree(fkey[(yyvsp[-2].ival) - 1]);
					fkey[(yyvsp[-2].ival) - 1] = NULL;
				    }
				    if (strlen((yyvsp[0].sval)))
					fkey[(yyvsp[-2].ival) - 1] = (yyvsp[0].sval);
				    modflg++;
				  } else
				    error("Invalid function key");
				}
#line 3079 "y.tab.c"
    break;

  case 27: /* command: S_SCEXT strarg  */
#line 421 "gram.y"
                                { if (scext) scxfree(scext); scext = (yyvsp[0].sval); }
#line 3085 "y.tab.c"
    break;

  case 28: /* command: S_HISTFILE strarg  */
#line 422 "gram.y"
                                  { strlcpy(histfile, (yyvsp[0].sval), sizeof histfile);
				    scxfree((yyvsp[0].sval)); }
#line 3092 "y.tab.c"
    break;

  case 29: /* command: S_ASCEXT strarg  */
#line 424 "gram.y"
                                { if (ascext) scxfree(ascext); ascext = (yyvsp[0].sval); }
#line 3098 "y.tab.c"
    break;

  case 30: /* command: S_TBL0EXT strarg  */
#line 426 "gram.y"
                                { if (tbl0ext) scxfree(tbl0ext); tbl0ext = (yyvsp[0].sval); }
#line 3104 "y.tab.c"
    break;

  case 31: /* command: S_TBLEXT strarg  */
#line 427 "gram.y"
                                { if (tblext) scxfree(tblext); tblext = (yyvsp[0].sval); }
#line 3110 "y.tab.c"
    break;

  case 32: /* command: S_LATEXEXT strarg  */
#line 428 "gram.y"
                                        { if (latexext) scxfree(latexext);
					    latexext = (yyvsp[0].sval); }
#line 3117 "y.tab.c"
    break;

  case 33: /* command: S_SLATEXEXT strarg  */
#line 430 "gram.y"
                                        { if (slatexext) scxfree(slatexext);
					    slatexext = (yyvsp[0].sval); }
#line 3124 "y.tab.c"
    break;

  case 34: /* command: S_TEXEXT strarg  */
#line 432 "gram.y"
                                { if (texext) scxfree(texext); texext = (yyvsp[0].sval); }
#line 3130 "y.tab.c"
    break;

  case 35: /* command: S_PUT strarg range  */
#line 434 "gram.y"
                                { (void) writefile((yyvsp[-1].sval), ((yyvsp[0].rval).left.vp)->row, 
					((yyvsp[0].rval).left.vp)->col, ((yyvsp[0].rval).right.vp)->row,
					((yyvsp[0].rval).right.vp)->col);
					    scxfree((yyvsp[-1].sval)); }
#line 3139 "y.tab.c"
    break;

  case 36: /* command: S_PUT strarg  */
#line 438 "gram.y"
                                { (void) writefile((yyvsp[0].sval), 0, 0, maxrow, maxcol);
					    scxfree((yyvsp[0].sval)); }
#line 3146 "y.tab.c"
    break;

  case 37: /* command: S_PUT range  */
#line 440 "gram.y"
                                        { (void) write_cells(stdout,
					  (yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col,
					  (yyvsp[0].rval).right.vp->row, (yyvsp[0].rval).right.vp->col,
					  (yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col); }
#line 3155 "y.tab.c"
    break;

  case 38: /* command: S_PUT range '/' var_or_range  */
#line 445 "gram.y"
                                        { (void) write_cells(stdout,
					  (yyvsp[-2].rval).left.vp->row, (yyvsp[-2].rval).left.vp->col,
					  (yyvsp[-2].rval).right.vp->row, (yyvsp[-2].rval).right.vp->col,
					  (yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col); }
#line 3164 "y.tab.c"
    break;

  case 39: /* command: S_PUT '%' '/' var_or_range  */
#line 450 "gram.y"
                                        { (void) write_cells(stdout, 0, 0,
					  maxrow, maxcol,
					  (yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col); }
#line 3172 "y.tab.c"
    break;

  case 40: /* command: S_PUT '/' var_or_range  */
#line 453 "gram.y"
                                        { (void) write_cells(stdout,
					  showsr, showsc, currow, curcol,
					  (yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col); }
#line 3180 "y.tab.c"
    break;

  case 41: /* command: S_PUT '%'  */
#line 456 "gram.y"
                                { (void) write_cells(stdout, 0, 0,
					    maxrow, maxcol, 0, 0); }
#line 3187 "y.tab.c"
    break;

  case 42: /* command: S_PUT  */
#line 458 "gram.y"
                                { (void) write_cells(stdout, 0, 0,
					    maxrow, maxcol, 0, 0); }
#line 3194 "y.tab.c"
    break;

  case 43: /* command: S_WRITE strarg range  */
#line 460 "gram.y"
                                     { (void) printfile((yyvsp[-1].sval), ((yyvsp[0].rval).left.vp)->row, 
					((yyvsp[0].rval).left.vp)->col, ((yyvsp[0].rval).right.vp)->row,
					((yyvsp[0].rval).right.vp)->col);
					    scxfree((yyvsp[-1].sval)); }
#line 3203 "y.tab.c"
    break;

  case 44: /* command: S_WRITE strarg  */
#line 464 "gram.y"
                                { (void) printfile((yyvsp[0].sval), 0, 0, maxrow, maxcol);
					    scxfree((yyvsp[0].sval)); }
#line 3210 "y.tab.c"
    break;

  case 45: /* command: S_WRITE range  */
#line 466 "gram.y"
                                        { (void) printfile(NULL,
					  (yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col,
					  (yyvsp[0].rval).right.vp->row, (yyvsp[0].rval).right.vp->col); }
#line 3218 "y.tab.c"
    break;

  case 46: /* command: S_WRITE '%'  */
#line 469 "gram.y"
                                { (void) printfile(NULL, 0, 0,
					    maxrow, maxcol); }
#line 3225 "y.tab.c"
    break;

  case 47: /* command: S_WRITE  */
#line 471 "gram.y"
                                { (void) printfile(NULL, 0, 0,
					    maxrow, maxcol); }
#line 3232 "y.tab.c"
    break;

  case 48: /* command: S_TBL strarg range  */
#line 473 "gram.y"
                                   { (void) tblprintfile((yyvsp[-1].sval), ((yyvsp[0].rval).left.vp)->row, 
					((yyvsp[0].rval).left.vp)->col, ((yyvsp[0].rval).right.vp)->row,
					((yyvsp[0].rval).right.vp)->col);
					    scxfree((yyvsp[-1].sval)); }
#line 3241 "y.tab.c"
    break;

  case 49: /* command: S_TBL strarg  */
#line 477 "gram.y"
                                { (void)tblprintfile((yyvsp[0].sval), 0, 0, maxrow, maxcol);
					    scxfree((yyvsp[0].sval)); }
#line 3248 "y.tab.c"
    break;

  case 50: /* command: S_SHOW COL ':' COL  */
#line 479 "gram.y"
                                        { showcol((yyvsp[-2].ival), (yyvsp[0].ival)); }
#line 3254 "y.tab.c"
    break;

  case 51: /* command: S_SHOW NUMBER ':' NUMBER  */
#line 481 "gram.y"
                                        { showrow((yyvsp[-2].ival), (yyvsp[0].ival)); }
#line 3260 "y.tab.c"
    break;

  case 52: /* command: S_HIDE  */
#line 482 "gram.y"
                                        { int a;
	    				  if (showrange == SHOWROWS) {
					    if (showsr < currow) {
						int r = currow;
						currow = showsr;
						showsr = r;
					    }
					    a = showsr - currow + 1;
					    hiderow(a);
					  } else if (showrange == SHOWCOLS) {
					    if (showsc < curcol) {
						int c = curcol;
						curcol = showsc;
						showsc = c;
					    }
					    a = showsc - curcol + 1;
					    hidecol(a);
					  } else
					    a = 1;
					}
#line 3285 "y.tab.c"
    break;

  case 53: /* command: S_HIDE COL  */
#line 502 "gram.y"
                                        { hide_col((yyvsp[0].ival)); }
#line 3291 "y.tab.c"
    break;

  case 54: /* command: S_HIDE COL ':' COL  */
#line 503 "gram.y"
                                        { int c = curcol, a;
					  if ((yyvsp[-2].ival) < (yyvsp[0].ival)) {
					    curcol = (yyvsp[-2].ival);
					    a = (yyvsp[0].ival) - (yyvsp[-2].ival) + 1;
					  } else {
					      curcol = (yyvsp[0].ival);
					      a = (yyvsp[-2].ival) - (yyvsp[0].ival) + 1;
					  }
					  hidecol(a);
					  curcol = c < curcol ? c :
					      c < curcol + a ? curcol :
					      c - a;
					}
#line 3309 "y.tab.c"
    break;

  case 55: /* command: S_HIDE NUMBER  */
#line 516 "gram.y"
                                        { hide_row((yyvsp[0].ival)); }
#line 3315 "y.tab.c"
    break;

  case 56: /* command: S_HIDE NUMBER ':' NUMBER  */
#line 518 "gram.y"
                                        { int r = currow, a;
					  if ((yyvsp[-2].ival) < (yyvsp[0].ival)) {
					    currow = (yyvsp[-2].ival);
					    a = (yyvsp[0].ival) - (yyvsp[-2].ival) + 1;
					  } else {
					      currow = (yyvsp[0].ival);
					      a = (yyvsp[-2].ival) - (yyvsp[0].ival) + 1;
					  }
					  hiderow(a);
					  currow = r < currow ? r :
					      r < currow + a ? currow :
					      r - a;
					}
#line 3333 "y.tab.c"
    break;

  case 57: /* command: S_COPY  */
#line 531 "gram.y"
                                        { if (showrange) {
					    showrange = 0;
					    copy(lookat(showsr, showsc),
					    lookat(currow, curcol),
					    NULL, NULL);
					  } else
					    copy(lookat(currow, curcol),
					    lookat(currow, curcol),
					    NULL, NULL); }
#line 3347 "y.tab.c"
    break;

  case 58: /* command: S_COPY range  */
#line 540 "gram.y"
                                        { copy((yyvsp[0].rval).left.vp, (yyvsp[0].rval).right.vp,
					    NULL, NULL); }
#line 3354 "y.tab.c"
    break;

  case 59: /* command: S_COPY range var_or_range  */
#line 543 "gram.y"
                                        { copy((yyvsp[-1].rval).left.vp, (yyvsp[-1].rval).right.vp,
					    (yyvsp[0].rval).left.vp, (yyvsp[0].rval).right.vp); }
#line 3361 "y.tab.c"
    break;

  case 60: /* command: S_MOVE var  */
#line 545 "gram.y"
                                        { mover((yyvsp[0].ent).vp, lookat(showsr, showsc),
					    lookat(currow, curcol)); }
#line 3368 "y.tab.c"
    break;

  case 61: /* command: S_MOVE var var_or_range  */
#line 547 "gram.y"
                                        { mover((yyvsp[-1].ent).vp, (yyvsp[0].rval).left.vp,
					    (yyvsp[0].rval).right.vp); }
#line 3375 "y.tab.c"
    break;

  case 62: /* command: S_ERASE  */
#line 549 "gram.y"
                                        { eraser(lookat(showsr, showsc),
					    lookat(currow, curcol)); }
#line 3382 "y.tab.c"
    break;

  case 63: /* command: S_ERASE var_or_range  */
#line 551 "gram.y"
                                        { eraser((yyvsp[0].rval).left.vp, (yyvsp[0].rval).right.vp); }
#line 3388 "y.tab.c"
    break;

  case 64: /* command: S_YANK  */
#line 552 "gram.y"
                                        { yankr(lookat(showsr, showsc),
					    lookat(currow, curcol)); }
#line 3395 "y.tab.c"
    break;

  case 65: /* command: S_YANK var_or_range  */
#line 554 "gram.y"
                                        { yankr((yyvsp[0].rval).left.vp, (yyvsp[0].rval).right.vp); }
#line 3401 "y.tab.c"
    break;

  case 66: /* command: S_VALUE  */
#line 555 "gram.y"
                              { valueize_area(showsr, showsc, currow, curcol);
					    modflg++; }
#line 3408 "y.tab.c"
    break;

  case 67: /* command: S_VALUE var_or_range  */
#line 557 "gram.y"
                                        { valueize_area(((yyvsp[0].rval).left.vp)->row,
					    ((yyvsp[0].rval).left.vp)->col,
					    ((yyvsp[0].rval).right.vp)->row,
					    ((yyvsp[0].rval).right.vp)->col); modflg++; }
#line 3417 "y.tab.c"
    break;

  case 68: /* command: S_FILL var_or_range num num  */
#line 562 "gram.y"
                                { fill((yyvsp[-2].rval).left.vp, (yyvsp[-2].rval).right.vp, (yyvsp[-1].fval), (yyvsp[0].fval)); }
#line 3423 "y.tab.c"
    break;

  case 69: /* command: S_SORT  */
#line 563 "gram.y"
                                { sortrange(lookat(showsr, showsc),
				  lookat(currow, curcol), NULL); }
#line 3430 "y.tab.c"
    break;

  case 70: /* command: S_SORT range  */
#line 565 "gram.y"
                                { sortrange((yyvsp[0].rval).left.vp, (yyvsp[0].rval).right.vp, NULL); }
#line 3436 "y.tab.c"
    break;

  case 71: /* command: S_SORT range strarg  */
#line 567 "gram.y"
                                { sortrange((yyvsp[-1].rval).left.vp, (yyvsp[-1].rval).right.vp, (yyvsp[0].sval)); }
#line 3442 "y.tab.c"
    break;

  case 72: /* command: S_FMT var_or_range STRING  */
#line 569 "gram.y"
                                { format_cell((yyvsp[-1].rval).left.vp, (yyvsp[-1].rval).right.vp, (yyvsp[0].sval)); }
#line 3448 "y.tab.c"
    break;

  case 73: /* command: S_LOCK  */
#line 570 "gram.y"
                                { lock_cells(lookat(showsr, showsc),
				    lookat(currow, curcol)); }
#line 3455 "y.tab.c"
    break;

  case 74: /* command: S_LOCK var_or_range  */
#line 573 "gram.y"
                                { lock_cells((yyvsp[0].rval).left.vp, (yyvsp[0].rval).right.vp); }
#line 3461 "y.tab.c"
    break;

  case 75: /* command: S_UNLOCK  */
#line 574 "gram.y"
                                        { unlock_cells(lookat(showsr, showsc),
					    lookat(currow, curcol)); }
#line 3468 "y.tab.c"
    break;

  case 76: /* command: S_UNLOCK var_or_range  */
#line 577 "gram.y"
                                { unlock_cells((yyvsp[0].rval).left.vp, (yyvsp[0].rval).right.vp); }
#line 3474 "y.tab.c"
    break;

  case 77: /* command: S_GOTO var_or_range var_or_range  */
#line 579 "gram.y"
                                { moveto((yyvsp[-1].rval).left.vp->row, (yyvsp[-1].rval).left.vp->col,
					    (yyvsp[-1].rval).right.vp->row, (yyvsp[-1].rval).right.vp->col,
					    (yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col); }
#line 3482 "y.tab.c"
    break;

  case 78: /* command: S_GOTO var_or_range  */
#line 582 "gram.y"
                                    { moveto((yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col,
					    (yyvsp[0].rval).right.vp->row, (yyvsp[0].rval).right.vp->col,
					    -1, -1); }
#line 3490 "y.tab.c"
    break;

  case 79: /* command: S_GOTO num range  */
#line 585 "gram.y"
                                        { num_search((yyvsp[-1].fval),
					  (yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col,
					  (yyvsp[0].rval).right.vp->row,
					  (yyvsp[0].rval).right.vp->col, 0); }
#line 3499 "y.tab.c"
    break;

  case 80: /* command: S_GOTO num  */
#line 589 "gram.y"
                                        { num_search((yyvsp[0].fval), 0, 0,
					  maxrow, maxcol, 0); }
#line 3506 "y.tab.c"
    break;

  case 82: /* command: S_GOTO STRING range  */
#line 592 "gram.y"
                                        { str_search((yyvsp[-1].sval),
					  (yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col,
					  (yyvsp[0].rval).right.vp->row,
					  (yyvsp[0].rval).right.vp->col, 0); }
#line 3515 "y.tab.c"
    break;

  case 83: /* command: S_GOTO '#' STRING range  */
#line 596 "gram.y"
                                        { str_search((yyvsp[-1].sval),
					  (yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col,
					  (yyvsp[0].rval).right.vp->row,
					  (yyvsp[0].rval).right.vp->col, 1); }
#line 3524 "y.tab.c"
    break;

  case 84: /* command: S_GOTO '%' STRING range  */
#line 600 "gram.y"
                                        { str_search((yyvsp[-1].sval),
					  (yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col,
					  (yyvsp[0].rval).right.vp->row,
					  (yyvsp[0].rval).right.vp->col, 2); }
#line 3533 "y.tab.c"
    break;

  case 85: /* command: S_GOTO STRING  */
#line 604 "gram.y"
                                        { str_search((yyvsp[0].sval), 0, 0,
					  maxrow, maxcol, 0); }
#line 3540 "y.tab.c"
    break;

  case 86: /* command: S_GOTO '#' STRING  */
#line 606 "gram.y"
                                        { str_search((yyvsp[0].sval), 0, 0,
					  maxrow, maxcol, 1); }
#line 3547 "y.tab.c"
    break;

  case 87: /* command: S_GOTO '%' STRING  */
#line 608 "gram.y"
                                        { str_search((yyvsp[0].sval), 0, 0,
					  maxrow, maxcol, 2); }
#line 3554 "y.tab.c"
    break;

  case 88: /* command: S_GOTO  */
#line 610 "gram.y"
                                        { go_last(); }
#line 3560 "y.tab.c"
    break;

  case 89: /* command: S_GOTO WORD  */
#line 611 "gram.y"
                                        { /* don't repeat last goto on
						"unintelligible word" */ ; }
#line 3567 "y.tab.c"
    break;

  case 90: /* command: S_DEFINE strarg  */
#line 613 "gram.y"
                                        { struct ent_ptr arg1, arg2;
					  arg1.vp = lookat(showsr, showsc);
					  arg1.vf = 0;
					  arg2.vp = lookat(currow, curcol);
					  arg2.vf = 0;
                                          if (arg1.vp == arg2.vp || !showrange)
                                             add_range((yyvsp[0].sval), arg2, arg2, 0);
                                          else
                                             add_range((yyvsp[0].sval), arg1, arg2, 1); }
#line 3581 "y.tab.c"
    break;

  case 91: /* command: S_DEFINE strarg range  */
#line 623 "gram.y"
                                        { add_range((yyvsp[-1].sval), (yyvsp[0].rval).left, (yyvsp[0].rval).right, 1); }
#line 3587 "y.tab.c"
    break;

  case 92: /* command: S_DEFINE strarg var  */
#line 624 "gram.y"
                                        { add_range((yyvsp[-1].sval), (yyvsp[0].ent), (yyvsp[0].ent), 0); }
#line 3593 "y.tab.c"
    break;

  case 93: /* command: S_UNDEFINE var_or_range  */
#line 625 "gram.y"
                                        { del_range((yyvsp[0].rval).left.vp, (yyvsp[0].rval).right.vp); }
#line 3599 "y.tab.c"
    break;

  case 94: /* command: S_ABBREV STRING  */
#line 626 "gram.y"
                                        { add_abbr((yyvsp[0].sval)); }
#line 3605 "y.tab.c"
    break;

  case 95: /* command: S_ABBREV  */
#line 627 "gram.y"
                                        { add_abbr(NULL); }
#line 3611 "y.tab.c"
    break;

  case 96: /* command: S_UNABBREV STRING  */
#line 628 "gram.y"
                                        { del_abbr((yyvsp[0].sval)); }
#line 3617 "y.tab.c"
    break;

  case 97: /* command: S_FRAME range range  */
#line 629 "gram.y"
                                        { add_frange((yyvsp[-1].rval).left.vp, (yyvsp[-1].rval).right.vp,
						(yyvsp[0].rval).left.vp, (yyvsp[0].rval).right.vp,
						0, 0, 0, 0); }
#line 3625 "y.tab.c"
    break;

  case 98: /* command: S_FRAME range  */
#line 632 "gram.y"
                                        { if (showrange) {
					    showrange = 0;
					    add_frange((yyvsp[0].rval).left.vp, (yyvsp[0].rval).right.vp,
						lookat(showsr, showsc),
						lookat(currow, curcol),
						0, 0, 0, 0);
					  } else {
					    struct frange *cfr;
					    cfr = find_frange(currow, curcol);
					    if (cfr) {
						add_frange(cfr->or_left,
						    cfr->or_right,
						    (yyvsp[0].rval).left.vp, (yyvsp[0].rval).right.vp,
						    0, 0, 0, 0);
					    }
					  }
					}
#line 3647 "y.tab.c"
    break;

  case 99: /* command: S_FRAME  */
#line 649 "gram.y"
                                        { struct frange *cfr;
					  /* cfr points to current frange */
					  cfr = find_frange(currow, curcol);
					  if (showrange && cfr) {
					    showrange = 0;
					    add_frange(cfr->or_left,
						cfr->or_right,
						lookat(showsr, showsc),
						lookat(currow, curcol),
						0, 0, 0, 0);
					  } else {
					    error("Need both outer and inner"
						    " ranges to create frame");
					  }
					}
#line 3667 "y.tab.c"
    break;

  case 100: /* command: S_FRAMETOP range NUMBER  */
#line 665 "gram.y"
                                        { add_frange((yyvsp[-1].rval).left.vp, (yyvsp[-1].rval).right.vp,
						NULL, NULL, (yyvsp[0].ival), -1, -1, -1); }
#line 3674 "y.tab.c"
    break;

  case 101: /* command: S_FRAMETOP NUMBER  */
#line 667 "gram.y"
                                        { struct frange *cfr;
					  /* cfr points to current frange */
					  cfr = find_frange(currow, curcol);
					  if (cfr)
					    add_frange(cfr->or_left,
						cfr->or_right,
						NULL, NULL, (yyvsp[0].ival), -1, -1, -1); }
#line 3686 "y.tab.c"
    break;

  case 102: /* command: S_FRAMEBOTTOM range NUMBER  */
#line 675 "gram.y"
                                        { add_frange((yyvsp[-1].rval).left.vp, (yyvsp[-1].rval).right.vp,
						NULL, NULL, -1, (yyvsp[0].ival), -1, -1); }
#line 3693 "y.tab.c"
    break;

  case 103: /* command: S_FRAMEBOTTOM NUMBER  */
#line 677 "gram.y"
                                        { struct frange *cfr;
					  /* cfr points to current frange */
					  cfr = find_frange(currow, curcol);
					  if (cfr)
					    add_frange(cfr->or_left,
						cfr->or_right,
						NULL, NULL, -1, (yyvsp[0].ival), -1, -1); }
#line 3705 "y.tab.c"
    break;

  case 104: /* command: S_FRAMELEFT range NUMBER  */
#line 685 "gram.y"
                                        { add_frange((yyvsp[-1].rval).left.vp, (yyvsp[-1].rval).right.vp,
						NULL, NULL, -1, -1, (yyvsp[0].ival), -1); }
#line 3712 "y.tab.c"
    break;

  case 105: /* command: S_FRAMELEFT NUMBER  */
#line 687 "gram.y"
                                        { struct frange *cfr;
					  /* cfr points to current frange */
					  cfr = find_frange(currow, curcol);
					  if (cfr)
					    add_frange(cfr->or_left,
						cfr->or_right,
						NULL, NULL, -1, -1, (yyvsp[0].ival), -1); }
#line 3724 "y.tab.c"
    break;

  case 106: /* command: S_FRAMERIGHT range NUMBER  */
#line 695 "gram.y"
                                        { add_frange((yyvsp[-1].rval).left.vp, (yyvsp[-1].rval).right.vp,
						NULL, NULL, -1, -1, -1, (yyvsp[0].ival)); }
#line 3731 "y.tab.c"
    break;

  case 107: /* command: S_FRAMERIGHT NUMBER  */
#line 697 "gram.y"
                                        { struct frange *cfr;
					  /* cfr points to current frange */
					  cfr = find_frange(currow, curcol);
					  if (cfr)
					    add_frange(cfr->or_left,
						cfr->or_right,
						NULL, NULL, -1, -1, -1, (yyvsp[0].ival)); }
#line 3743 "y.tab.c"
    break;

  case 108: /* command: S_UNFRAME range  */
#line 704 "gram.y"
                                        { add_frange((yyvsp[0].rval).left.vp, (yyvsp[0].rval).right.vp,
						NULL, NULL, 0, 0, 0, 0); }
#line 3750 "y.tab.c"
    break;

  case 109: /* command: S_UNFRAME  */
#line 706 "gram.y"
                                        { struct frange *cfr;
					  /* cfr points to current frange */
					  cfr = find_frange(currow, curcol);
					  if (cfr)
					    add_frange(cfr->or_left,
						cfr->or_right,
						NULL, NULL, 0, 0, 0, 0); }
#line 3762 "y.tab.c"
    break;

  case 110: /* command: S_COLOR NUMBER '='  */
#line 713 "gram.y"
                                        { if ((yyvsp[-1].ival) > 0 && (yyvsp[-1].ival) < 9)
					    initcolor((yyvsp[-1].ival));
					  else
					    error("Invalid color number"); }
#line 3771 "y.tab.c"
    break;

  case 111: /* command: S_COLOR NUMBER '=' e  */
#line 717 "gram.y"
                                        { change_color((yyvsp[-2].ival), (yyvsp[0].enode)); }
#line 3777 "y.tab.c"
    break;

  case 112: /* command: S_COLOR range NUMBER  */
#line 718 "gram.y"
                                        { add_crange((yyvsp[-1].rval).left.vp, (yyvsp[-1].rval).right.vp,
						(yyvsp[0].ival)); }
#line 3784 "y.tab.c"
    break;

  case 113: /* command: S_SET setlist  */
#line 720 "gram.y"
                                        { modflg++; }
#line 3790 "y.tab.c"
    break;

  case 114: /* command: S_UP  */
#line 721 "gram.y"
                                        { backrow( 1); }
#line 3796 "y.tab.c"
    break;

  case 115: /* command: S_UP NUMBER  */
#line 722 "gram.y"
                                        { backrow((yyvsp[0].ival)); }
#line 3802 "y.tab.c"
    break;

  case 116: /* command: S_DOWN  */
#line 723 "gram.y"
                                        { forwrow( 1); }
#line 3808 "y.tab.c"
    break;

  case 117: /* command: S_DOWN NUMBER  */
#line 724 "gram.y"
                                        { forwrow((yyvsp[0].ival)); }
#line 3814 "y.tab.c"
    break;

  case 118: /* command: S_LEFT  */
#line 725 "gram.y"
                                        { backcol( 1); }
#line 3820 "y.tab.c"
    break;

  case 119: /* command: S_LEFT NUMBER  */
#line 726 "gram.y"
                                        { backcol((yyvsp[0].ival)); }
#line 3826 "y.tab.c"
    break;

  case 120: /* command: S_RIGHT  */
#line 727 "gram.y"
                                        { forwcol( 1); }
#line 3832 "y.tab.c"
    break;

  case 121: /* command: S_RIGHT NUMBER  */
#line 728 "gram.y"
                                        { forwcol((yyvsp[0].ival)); }
#line 3838 "y.tab.c"
    break;

  case 122: /* command: S_ENDUP  */
#line 729 "gram.y"
                                        { doend(-1, 0); }
#line 3844 "y.tab.c"
    break;

  case 123: /* command: S_ENDDOWN  */
#line 730 "gram.y"
                                        { doend( 1, 0); }
#line 3850 "y.tab.c"
    break;

  case 124: /* command: S_ENDLEFT  */
#line 731 "gram.y"
                                        { doend( 0,-1); }
#line 3856 "y.tab.c"
    break;

  case 125: /* command: S_ENDRIGHT  */
#line 732 "gram.y"
                                        { doend( 0, 1); }
#line 3862 "y.tab.c"
    break;

  case 126: /* command: S_SELECT STRING  */
#line 733 "gram.y"
                                        { int c;
					  if ((c = *(yyvsp[0].sval)) >= '0' && c <= '9') {
					    qbuf = c - '0' + (DELBUFSIZE - 10);
					  } else if (c >= 'a' && c <= 'z') {
					    qbuf = c - 'a' + (DELBUFSIZE - 36);
					  } else if (c == '"') {
					    qbuf = 0;
					  } else
					    error("Invalid buffer");
					  scxfree((yyvsp[0].sval));
					}
#line 3878 "y.tab.c"
    break;

  case 127: /* command: S_INSERTROW  */
#line 744 "gram.y"
                                        { insertrow( 1, 0); }
#line 3884 "y.tab.c"
    break;

  case 128: /* command: S_INSERTROW '*' NUMBER  */
#line 745 "gram.y"
                                        { insertrow((yyvsp[0].ival), 0); }
#line 3890 "y.tab.c"
    break;

  case 129: /* command: S_OPENROW  */
#line 746 "gram.y"
                                        { insertrow( 1, 1); }
#line 3896 "y.tab.c"
    break;

  case 130: /* command: S_OPENROW '*' NUMBER  */
#line 747 "gram.y"
                                        { insertrow((yyvsp[0].ival), 1); }
#line 3902 "y.tab.c"
    break;

  case 131: /* command: S_INSERTCOL  */
#line 748 "gram.y"
                                        { insertcol( 1, 0); }
#line 3908 "y.tab.c"
    break;

  case 132: /* command: S_INSERTCOL '*' NUMBER  */
#line 749 "gram.y"
                                        { insertcol((yyvsp[0].ival), 0); }
#line 3914 "y.tab.c"
    break;

  case 133: /* command: S_OPENCOL  */
#line 750 "gram.y"
                                        { insertcol( 1, 1); }
#line 3920 "y.tab.c"
    break;

  case 134: /* command: S_OPENCOL '*' NUMBER  */
#line 751 "gram.y"
                                        { insertcol((yyvsp[0].ival), 1); }
#line 3926 "y.tab.c"
    break;

  case 135: /* command: S_DELETEROW  */
#line 752 "gram.y"
                                        { int a;
	    				  if (showrange == SHOWROWS) {
					    if (showsr < currow) {
						int r = currow;
						currow = showsr;
						showsr = r;
					    }
					    a = showsr - currow + 1;
					  } else
					    a = 1;
					  deleterow(a);
					}
#line 3943 "y.tab.c"
    break;

  case 136: /* command: S_DELETEROW '*' NUMBER  */
#line 764 "gram.y"
                                        { deleterow((yyvsp[0].ival)); }
#line 3949 "y.tab.c"
    break;

  case 137: /* command: S_DELETEROW NUMBER  */
#line 765 "gram.y"
                                        { int r = currow;
					  currow = (yyvsp[0].ival);
					  deleterow(1);
					  currow = r <= currow ? r : r - 1;
					}
#line 3959 "y.tab.c"
    break;

  case 138: /* command: S_DELETEROW NUMBER ':' NUMBER  */
#line 771 "gram.y"
                                        { int r = currow, a;
					  if ((yyvsp[-2].ival) < (yyvsp[0].ival)) {
					    currow = (yyvsp[-2].ival);
					    a = (yyvsp[0].ival) - (yyvsp[-2].ival) + 1;
					  } else {
					      currow = (yyvsp[0].ival);
					      a = (yyvsp[-2].ival) - (yyvsp[0].ival) + 1;
					  }
					  deleterow(a);
					  currow = r < currow ? r :
					      r < currow + a ? currow :
					      r - a;
					}
#line 3977 "y.tab.c"
    break;

  case 139: /* command: S_DELETECOL  */
#line 784 "gram.y"
                                        { int a;
	    				  if (showrange == SHOWCOLS) {
					    if (showsc < curcol) {
						int c = curcol;
						curcol = showsc;
						showsc = c;
					    }
					    a = showsc - curcol + 1;
					  } else
					    a = 1;
					  closecol(a);
					}
#line 3994 "y.tab.c"
    break;

  case 140: /* command: S_DELETECOL COL  */
#line 796 "gram.y"
                                        { int r = curcol;
					  curcol = (yyvsp[0].ival);
					  closecol(1);
					  curcol = r <= curcol ? r : r - 1;
					}
#line 4004 "y.tab.c"
    break;

  case 141: /* command: S_DELETECOL '*' NUMBER  */
#line 801 "gram.y"
                                        { closecol((yyvsp[0].ival)); }
#line 4010 "y.tab.c"
    break;

  case 142: /* command: S_DELETECOL COL ':' COL  */
#line 802 "gram.y"
                                        { int c = curcol, a;
					  if ((yyvsp[-2].ival) < (yyvsp[0].ival)) {
					    curcol = (yyvsp[-2].ival);
					    a = (yyvsp[0].ival) - (yyvsp[-2].ival) + 1;
					  } else {
					      curcol = (yyvsp[0].ival);
					      a = (yyvsp[-2].ival) - (yyvsp[0].ival) + 1;
					  }
					  closecol(a);
					  curcol = c < curcol ? c :
					      c < curcol + a ? curcol :
					      c - a;
					}
#line 4028 "y.tab.c"
    break;

  case 143: /* command: S_YANKROW  */
#line 815 "gram.y"
                                        { int r = currow, a;
	    				  if (showrange == SHOWROWS) {
					    if (showsr < currow) {
						currow = showsr;
						showsr = r;
					    }
					    a = showsr - currow + 1;
					  } else
					    a = 1;
					  yankrow(a);
					  currow = r;
					}
#line 4045 "y.tab.c"
    break;

  case 144: /* command: S_YANKROW '*' NUMBER  */
#line 827 "gram.y"
                                        { yankrow((yyvsp[0].ival)); }
#line 4051 "y.tab.c"
    break;

  case 145: /* command: S_YANKROW NUMBER  */
#line 828 "gram.y"
                                        { int r = currow;
					  currow = (yyvsp[0].ival);
					  yankrow(1);
					  currow = r;
					}
#line 4061 "y.tab.c"
    break;

  case 146: /* command: S_YANKROW NUMBER ':' NUMBER  */
#line 834 "gram.y"
                                        { int r = currow, a;
					  if ((yyvsp[-2].ival) < (yyvsp[0].ival)) {
					    currow = (yyvsp[-2].ival);
					    a = (yyvsp[0].ival) - (yyvsp[-2].ival) + 1;
					  } else {
					      currow = (yyvsp[0].ival);
					      a = (yyvsp[-2].ival) - (yyvsp[0].ival) + 1;
					  }
					  yankrow(a);
					  currow = r;
					}
#line 4077 "y.tab.c"
    break;

  case 147: /* command: S_YANKCOL  */
#line 845 "gram.y"
                                        { int c = curcol, a;
	    				  if (showrange == SHOWCOLS) {
					    if (showsc < curcol) {
						curcol = showsc;
						showsc = c;
					    }
					    a = showsc - curcol + 1;
					  } else
					    a = 1;
					  yankcol(a);
					  curcol = c;
					}
#line 4094 "y.tab.c"
    break;

  case 148: /* command: S_YANKCOL NUMBER  */
#line 857 "gram.y"
                                        { int c = curcol;
					  curcol = (yyvsp[0].ival);
					  yankcol(1);
					  curcol = c;
					}
#line 4104 "y.tab.c"
    break;

  case 149: /* command: S_YANKCOL '*' NUMBER  */
#line 862 "gram.y"
                                        { yankcol((yyvsp[0].ival)); }
#line 4110 "y.tab.c"
    break;

  case 150: /* command: S_YANKCOL COL ':' COL  */
#line 863 "gram.y"
                                        { int c = curcol, a;
					  if ((yyvsp[-2].ival) < (yyvsp[0].ival)) {
					    curcol = (yyvsp[-2].ival);
					    a = (yyvsp[0].ival) - (yyvsp[-2].ival) + 1;
					  } else {
					      curcol = (yyvsp[0].ival);
					      a = (yyvsp[-2].ival) - (yyvsp[0].ival) + 1;
					  }
					  yankcol(a);
					  curcol = c;
					}
#line 4126 "y.tab.c"
    break;

  case 151: /* command: S_PULL  */
#line 874 "gram.y"
                                        { pullcells('p'); }
#line 4132 "y.tab.c"
    break;

  case 152: /* command: S_PULLMERGE  */
#line 875 "gram.y"
                                        { pullcells('m'); }
#line 4138 "y.tab.c"
    break;

  case 153: /* command: S_PULLROWS  */
#line 876 "gram.y"
                                        { pullcells('r'); }
#line 4144 "y.tab.c"
    break;

  case 154: /* command: S_PULLCOLS  */
#line 877 "gram.y"
                                        { pullcells('c'); }
#line 4150 "y.tab.c"
    break;

  case 155: /* command: S_PULLXCHG  */
#line 878 "gram.y"
                                        { pullcells('x'); }
#line 4156 "y.tab.c"
    break;

  case 156: /* command: S_PULLTP  */
#line 879 "gram.y"
                                        { pullcells('t'); }
#line 4162 "y.tab.c"
    break;

  case 157: /* command: S_PULLFMT  */
#line 880 "gram.y"
                                        { pullcells('f'); }
#line 4168 "y.tab.c"
    break;

  case 158: /* command: S_PULLCOPY  */
#line 881 "gram.y"
                                        { copy(NULL, NULL, NULL, NULL); }
#line 4174 "y.tab.c"
    break;

  case 159: /* command: S_PULLCOPY var_or_range  */
#line 882 "gram.y"
                                        { copy((yyvsp[0].rval).left.vp, (yyvsp[0].rval).right.vp,
					     NULL, (struct ent *)1); }
#line 4181 "y.tab.c"
    break;

  case 160: /* command: S_WHEREAMI  */
#line 884 "gram.y"
                                        { size_t l;
					  snprintf(line, sizeof line, "%s%d ",
					     coltoa(curcol), currow);
					  l = strlen(line);
					  snprintf(line + l, sizeof(line) - l,
					     "%s%d\n", coltoa(stcol), strow);
					  write(macrofd, line, strlen(line));
					  line[0] = '\0'; }
#line 4194 "y.tab.c"
    break;

  case 161: /* command: S_WHEREAMI '|' NUMBER  */
#line 892 "gram.y"
                                        { size_t l;
					  snprintf(line, sizeof line, "%s%d ",
					     coltoa(curcol), currow);
					  l = strlen(line);
					  snprintf(line + l, sizeof(line) - l,
					     "%s%d\n", coltoa(stcol), strow);
					  write((yyvsp[0].ival), line, strlen(line));
					  line[0] = '\0'; }
#line 4207 "y.tab.c"
    break;

  case 162: /* command: S_GETNUM var_or_range  */
#line 900 "gram.y"
                                        { getnum((yyvsp[0].rval).left.vp->row,
						(yyvsp[0].rval).left.vp->col,
						(yyvsp[0].rval).right.vp->row,
						(yyvsp[0].rval).right.vp->col, macrofd); }
#line 4216 "y.tab.c"
    break;

  case 163: /* command: S_GETNUM var_or_range '|' NUMBER  */
#line 905 "gram.y"
                                        { getnum((yyvsp[-2].rval).left.vp->row,
						(yyvsp[-2].rval).left.vp->col,
						(yyvsp[-2].rval).right.vp->row,
						(yyvsp[-2].rval).right.vp->col, (yyvsp[0].ival)); }
#line 4225 "y.tab.c"
    break;

  case 164: /* command: S_GETNUM  */
#line 909 "gram.y"
                                        { getnum(currow, curcol,
						currow, curcol, macrofd); }
#line 4232 "y.tab.c"
    break;

  case 165: /* command: S_GETNUM '|' NUMBER  */
#line 911 "gram.y"
                                        { getnum(currow, curcol,
						currow, curcol, (yyvsp[0].ival)); }
#line 4239 "y.tab.c"
    break;

  case 166: /* command: S_FGETNUM var_or_range  */
#line 913 "gram.y"
                                        { fgetnum((yyvsp[0].rval).left.vp->row,
						(yyvsp[0].rval).left.vp->col,
						(yyvsp[0].rval).right.vp->row,
						(yyvsp[0].rval).right.vp->col, macrofd); }
#line 4248 "y.tab.c"
    break;

  case 167: /* command: S_FGETNUM var_or_range '|' NUMBER  */
#line 918 "gram.y"
                                        { fgetnum((yyvsp[-2].rval).left.vp->row,
						(yyvsp[-2].rval).left.vp->col,
						(yyvsp[-2].rval).right.vp->row,
						(yyvsp[-2].rval).right.vp->col, (yyvsp[0].ival)); }
#line 4257 "y.tab.c"
    break;

  case 168: /* command: S_FGETNUM  */
#line 922 "gram.y"
                                        { fgetnum(currow, curcol,
						currow, curcol, macrofd); }
#line 4264 "y.tab.c"
    break;

  case 169: /* command: S_FGETNUM '|' NUMBER  */
#line 924 "gram.y"
                                        { fgetnum(currow, curcol,
						currow, curcol, (yyvsp[0].ival)); }
#line 4271 "y.tab.c"
    break;

  case 170: /* command: S_GETSTRING var_or_range  */
#line 927 "gram.y"
                                        { getstring((yyvsp[0].rval).left.vp->row,
						(yyvsp[0].rval).left.vp->col,
						(yyvsp[0].rval).right.vp->row,
						(yyvsp[0].rval).right.vp->col, macrofd); }
#line 4280 "y.tab.c"
    break;

  case 171: /* command: S_GETSTRING var_or_range '|' NUMBER  */
#line 932 "gram.y"
                                        { getstring((yyvsp[-2].rval).left.vp->row,
						(yyvsp[-2].rval).left.vp->col,
						(yyvsp[-2].rval).right.vp->row,
						(yyvsp[-2].rval).right.vp->col, (yyvsp[0].ival)); }
#line 4289 "y.tab.c"
    break;

  case 172: /* command: S_GETSTRING  */
#line 936 "gram.y"
                                        { getstring(currow, curcol,
						currow, curcol, macrofd); }
#line 4296 "y.tab.c"
    break;

  case 173: /* command: S_GETSTRING '|' NUMBER  */
#line 938 "gram.y"
                                        { getstring(currow, curcol,
						currow, curcol, (yyvsp[0].ival)); }
#line 4303 "y.tab.c"
    break;

  case 174: /* command: S_GETEXP var_or_range  */
#line 940 "gram.y"
                                        { getexp((yyvsp[0].rval).left.vp->row,
						(yyvsp[0].rval).left.vp->col,
						(yyvsp[0].rval).right.vp->row,
						(yyvsp[0].rval).right.vp->col, macrofd); }
#line 4312 "y.tab.c"
    break;

  case 175: /* command: S_GETEXP var_or_range '|' NUMBER  */
#line 945 "gram.y"
                                        { getexp((yyvsp[-2].rval).left.vp->row,
						(yyvsp[-2].rval).left.vp->col,
						(yyvsp[-2].rval).right.vp->row,
						(yyvsp[-2].rval).right.vp->col, (yyvsp[0].ival)); }
#line 4321 "y.tab.c"
    break;

  case 176: /* command: S_GETEXP  */
#line 949 "gram.y"
                                        { getexp(currow, curcol,
						currow, curcol, macrofd); }
#line 4328 "y.tab.c"
    break;

  case 177: /* command: S_GETEXP '|' NUMBER  */
#line 951 "gram.y"
                                        { getexp(currow, curcol,
						currow, curcol, (yyvsp[0].ival)); }
#line 4335 "y.tab.c"
    break;

  case 178: /* command: S_GETFORMAT COL  */
#line 953 "gram.y"
                                        { getformat((yyvsp[0].ival), macrofd); }
#line 4341 "y.tab.c"
    break;

  case 179: /* command: S_GETFORMAT COL '|' NUMBER  */
#line 955 "gram.y"
                                        { getformat((yyvsp[-2].ival), (yyvsp[0].ival)); }
#line 4347 "y.tab.c"
    break;

  case 180: /* command: S_GETFORMAT  */
#line 956 "gram.y"
                                        { getformat(curcol, macrofd); }
#line 4353 "y.tab.c"
    break;

  case 181: /* command: S_GETFORMAT '|' NUMBER  */
#line 957 "gram.y"
                                        { getformat(curcol, (yyvsp[0].ival)); }
#line 4359 "y.tab.c"
    break;

  case 182: /* command: S_GETFMT var_or_range  */
#line 958 "gram.y"
                                        { getfmt((yyvsp[0].rval).left.vp->row,
						(yyvsp[0].rval).left.vp->col,
						(yyvsp[0].rval).right.vp->row,
						(yyvsp[0].rval).right.vp->col, macrofd); }
#line 4368 "y.tab.c"
    break;

  case 183: /* command: S_GETFMT var_or_range '|' NUMBER  */
#line 963 "gram.y"
                                        { getfmt((yyvsp[-2].rval).left.vp->row,
						(yyvsp[-2].rval).left.vp->col,
						(yyvsp[-2].rval).right.vp->row,
						(yyvsp[-2].rval).right.vp->col, (yyvsp[0].ival)); }
#line 4377 "y.tab.c"
    break;

  case 184: /* command: S_GETFMT  */
#line 967 "gram.y"
                                        { getfmt(currow, curcol,
						currow, curcol, macrofd); }
#line 4384 "y.tab.c"
    break;

  case 185: /* command: S_GETFMT '|' NUMBER  */
#line 969 "gram.y"
                                        { getfmt(currow, curcol,
						currow, curcol, (yyvsp[0].ival)); }
#line 4391 "y.tab.c"
    break;

  case 186: /* command: S_GETFRAME  */
#line 971 "gram.y"
                                        { getframe(macrofd); }
#line 4397 "y.tab.c"
    break;

  case 187: /* command: S_GETFRAME '|' NUMBER  */
#line 972 "gram.y"
                                        { getframe((yyvsp[0].ival)); }
#line 4403 "y.tab.c"
    break;

  case 188: /* command: S_GETRANGE STRING  */
#line 973 "gram.y"
                                        { getrange((yyvsp[0].sval), macrofd); }
#line 4409 "y.tab.c"
    break;

  case 189: /* command: S_GETRANGE STRING '|' NUMBER  */
#line 975 "gram.y"
                                        { getrange((yyvsp[-2].sval), (yyvsp[0].ival)); }
#line 4415 "y.tab.c"
    break;

  case 190: /* command: S_EVAL e  */
#line 976 "gram.y"
                                        { doeval((yyvsp[0].enode), NULL, currow, curcol,
						macrofd); }
#line 4422 "y.tab.c"
    break;

  case 191: /* command: S_EVAL e STRING  */
#line 978 "gram.y"
                                        { doeval((yyvsp[-1].enode), (yyvsp[0].sval), currow, curcol,
						macrofd); }
#line 4429 "y.tab.c"
    break;

  case 192: /* command: S_EVAL e STRING '|' NUMBER  */
#line 981 "gram.y"
                                        { doeval((yyvsp[-3].enode), (yyvsp[-2].sval), currow, curcol,
						(yyvsp[0].ival)); }
#line 4436 "y.tab.c"
    break;

  case 193: /* command: S_SEVAL e  */
#line 983 "gram.y"
                                        { doseval((yyvsp[0].enode), currow, curcol, macrofd); }
#line 4442 "y.tab.c"
    break;

  case 194: /* command: S_QUERY STRING STRING  */
#line 984 "gram.y"
                                        { doquery((yyvsp[-1].sval), (yyvsp[0].sval), macrofd); }
#line 4448 "y.tab.c"
    break;

  case 195: /* command: S_QUERY STRING STRING '|' NUMBER  */
#line 986 "gram.y"
                                        { doquery((yyvsp[-3].sval), (yyvsp[-2].sval), (yyvsp[0].ival)); }
#line 4454 "y.tab.c"
    break;

  case 196: /* command: S_QUERY STRING  */
#line 987 "gram.y"
                                        { doquery((yyvsp[0].sval), NULL, macrofd); }
#line 4460 "y.tab.c"
    break;

  case 197: /* command: S_QUERY STRING '|' NUMBER  */
#line 989 "gram.y"
                                        { doquery((yyvsp[-2].sval), NULL, (yyvsp[0].ival)); }
#line 4466 "y.tab.c"
    break;

  case 198: /* command: S_QUERY  */
#line 990 "gram.y"
                                        { doquery(NULL, NULL, macrofd); }
#line 4472 "y.tab.c"
    break;

  case 199: /* command: S_QUERY '|' NUMBER  */
#line 991 "gram.y"
                                        { doquery(NULL, NULL, (yyvsp[0].ival)); }
#line 4478 "y.tab.c"
    break;

  case 200: /* command: S_GETKEY  */
#line 992 "gram.y"
                                        { dogetkey(); }
#line 4484 "y.tab.c"
    break;

  case 201: /* command: S_ERROR STRING  */
#line 993 "gram.y"
                                        { error("%s", (yyvsp[0].sval)); }
#line 4490 "y.tab.c"
    break;

  case 202: /* command: S_STATUS  */
#line 994 "gram.y"
                                                { dostat(macrofd); }
#line 4496 "y.tab.c"
    break;

  case 203: /* command: S_STATUS '|' NUMBER  */
#line 995 "gram.y"
                                        { dostat((yyvsp[0].ival)); }
#line 4502 "y.tab.c"
    break;

  case 204: /* command: S_RECALC  */
#line 996 "gram.y"
                                        { EvalAll();
					  update(1);
					  changed = 0;
					}
#line 4511 "y.tab.c"
    break;

  case 205: /* command: S_REDRAW  */
#line 1000 "gram.y"
                                        { if (usecurses) {
					    clearok(stdscr, TRUE);
					    linelim = -1;
					    update(1);
					    refresh();
					    changed = 0;
					  }
					}
#line 4524 "y.tab.c"
    break;

  case 206: /* command: S_QUIT  */
#line 1008 "gram.y"
                                        { stopdisp(); exit(0); }
#line 4530 "y.tab.c"
    break;

  case 207: /* command: S_RUN STRING  */
#line 1009 "gram.y"
                                        { deraw(1);
					  system((yyvsp[0].sval));
					  if (*((yyvsp[0].sval) + strlen((yyvsp[0].sval)) - 1) != '&') {
					    printf("Press any key to continue ");
					    fflush(stdout);
					    cbreak();
					    nmgetch();
					  }
					  goraw();
					  scxfree((yyvsp[0].sval)); }
#line 4545 "y.tab.c"
    break;

  case 208: /* command: S_PLUGIN STRING '=' STRING  */
#line 1020 "gram.y"
                                        { addplugin((yyvsp[-2].sval), (yyvsp[0].sval), 'r'); }
#line 4551 "y.tab.c"
    break;

  case 209: /* command: S_PLUGOUT STRING '=' STRING  */
#line 1022 "gram.y"
                                        { addplugin((yyvsp[-2].sval), (yyvsp[0].sval), 'w'); }
#line 4557 "y.tab.c"
    break;

  case 210: /* command: PLUGIN  */
#line 1023 "gram.y"
                                        { *line = '|';
					  snprintf(line + 1, sizeof(line) - 1,
					      "%s", (yyvsp[0].sval));
					  readfile(line, 0);
					  scxfree((yyvsp[0].sval)); }
#line 4567 "y.tab.c"
    break;

  case 213: /* term: var  */
#line 1031 "gram.y"
                                        { (yyval.enode) = new_var(O_VAR, (yyvsp[0].ent)); }
#line 4573 "y.tab.c"
    break;

  case 214: /* term: '@' K_FIXED term  */
#line 1032 "gram.y"
                                        { (yyval.enode) = new('f', (yyvsp[0].enode), ENULL); }
#line 4579 "y.tab.c"
    break;

  case 215: /* term: '(' '@' K_FIXED ')' term  */
#line 1034 "gram.y"
                                        { (yyval.enode) = new('F', (yyvsp[0].enode), ENULL); }
#line 4585 "y.tab.c"
    break;

  case 216: /* term: '@' K_SUM '(' var_or_range ')'  */
#line 1036 "gram.y"
                                { (yyval.enode) = new(SUM,
					new_range(REDUCE | SUM, (yyvsp[-1].rval)), ENULL); }
#line 4592 "y.tab.c"
    break;

  case 217: /* term: '@' K_SUM '(' range ',' e ')'  */
#line 1039 "gram.y"
                                { (yyval.enode) = new(SUM,
					new_range(REDUCE | SUM, (yyvsp[-3].rval)), (yyvsp[-1].enode)); }
#line 4599 "y.tab.c"
    break;

  case 218: /* term: '@' K_PROD '(' var_or_range ')'  */
#line 1042 "gram.y"
                                { (yyval.enode) = new(PROD,
					new_range(REDUCE | PROD, (yyvsp[-1].rval)), ENULL); }
#line 4606 "y.tab.c"
    break;

  case 219: /* term: '@' K_PROD '(' range ',' e ')'  */
#line 1045 "gram.y"
                                { (yyval.enode) = new(PROD,
					new_range(REDUCE | PROD, (yyvsp[-3].rval)), (yyvsp[-1].enode)); }
#line 4613 "y.tab.c"
    break;

  case 220: /* term: '@' K_AVG '(' var_or_range ')'  */
#line 1048 "gram.y"
                                { (yyval.enode) = new(AVG,
					new_range(REDUCE | AVG, (yyvsp[-1].rval)), ENULL); }
#line 4620 "y.tab.c"
    break;

  case 221: /* term: '@' K_AVG '(' range ',' e ')'  */
#line 1051 "gram.y"
                                { (yyval.enode) = new(AVG,
					new_range(REDUCE | AVG, (yyvsp[-3].rval)), (yyvsp[-1].enode)); }
#line 4627 "y.tab.c"
    break;

  case 222: /* term: '@' K_STDDEV '(' var_or_range ')'  */
#line 1054 "gram.y"
                                { (yyval.enode) = new(STDDEV,
					new_range(REDUCE | STDDEV, (yyvsp[-1].rval)), ENULL); }
#line 4634 "y.tab.c"
    break;

  case 223: /* term: '@' K_STDDEV '(' range ',' e ')'  */
#line 1057 "gram.y"
                                { (yyval.enode) = new(STDDEV,
					new_range(REDUCE | STDDEV, (yyvsp[-3].rval)), (yyvsp[-1].enode)); }
#line 4641 "y.tab.c"
    break;

  case 224: /* term: '@' K_COUNT '(' var_or_range ')'  */
#line 1060 "gram.y"
                                { (yyval.enode) = new(COUNT,
					new_range(REDUCE | COUNT, (yyvsp[-1].rval)), ENULL); }
#line 4648 "y.tab.c"
    break;

  case 225: /* term: '@' K_COUNT '(' range ',' e ')'  */
#line 1063 "gram.y"
                                { (yyval.enode) = new(COUNT,
					new_range(REDUCE | COUNT, (yyvsp[-3].rval)), (yyvsp[-1].enode)); }
#line 4655 "y.tab.c"
    break;

  case 226: /* term: '@' K_MAX '(' var_or_range ')'  */
#line 1066 "gram.y"
                                { (yyval.enode) = new(MAX,
					new_range(REDUCE | MAX, (yyvsp[-1].rval)), ENULL); }
#line 4662 "y.tab.c"
    break;

  case 227: /* term: '@' K_MAX '(' range ',' e ')'  */
#line 1069 "gram.y"
                                { (yyval.enode) = new(MAX,
					new_range(REDUCE | MAX, (yyvsp[-3].rval)), (yyvsp[-1].enode)); }
#line 4669 "y.tab.c"
    break;

  case 228: /* term: '@' K_MAX '(' e ',' expr_list ')'  */
#line 1072 "gram.y"
                                { (yyval.enode) = new(LMAX, (yyvsp[-1].enode), (yyvsp[-3].enode)); }
#line 4675 "y.tab.c"
    break;

  case 229: /* term: '@' K_MIN '(' var_or_range ')'  */
#line 1074 "gram.y"
                                { (yyval.enode) = new(MIN,
					new_range(REDUCE | MIN, (yyvsp[-1].rval)), ENULL); }
#line 4682 "y.tab.c"
    break;

  case 230: /* term: '@' K_MIN '(' range ',' e ')'  */
#line 1077 "gram.y"
                                { (yyval.enode) = new(MIN,
					new_range(REDUCE | MIN, (yyvsp[-3].rval)), (yyvsp[-1].enode)); }
#line 4689 "y.tab.c"
    break;

  case 231: /* term: '@' K_MIN '(' e ',' expr_list ')'  */
#line 1080 "gram.y"
                                { (yyval.enode) = new(LMIN, (yyvsp[-1].enode), (yyvsp[-3].enode)); }
#line 4695 "y.tab.c"
    break;

  case 232: /* term: '@' K_ROWS '(' var_or_range ')'  */
#line 1082 "gram.y"
                                { (yyval.enode) = new_range(REDUCE | 'R', (yyvsp[-1].rval)); }
#line 4701 "y.tab.c"
    break;

  case 233: /* term: '@' K_COLS '(' var_or_range ')'  */
#line 1084 "gram.y"
                                { (yyval.enode) = new_range(REDUCE | 'C', (yyvsp[-1].rval)); }
#line 4707 "y.tab.c"
    break;

  case 234: /* term: '@' K_ABS '(' e ')'  */
#line 1085 "gram.y"
                                        { (yyval.enode) = new(ABS, (yyvsp[-1].enode), ENULL); }
#line 4713 "y.tab.c"
    break;

  case 235: /* term: '@' K_ACOS '(' e ')'  */
#line 1086 "gram.y"
                                        { (yyval.enode) = new(ACOS, (yyvsp[-1].enode), ENULL); }
#line 4719 "y.tab.c"
    break;

  case 236: /* term: '@' K_ASIN '(' e ')'  */
#line 1087 "gram.y"
                                        { (yyval.enode) = new(ASIN, (yyvsp[-1].enode), ENULL); }
#line 4725 "y.tab.c"
    break;

  case 237: /* term: '@' K_ATAN '(' e ')'  */
#line 1088 "gram.y"
                                        { (yyval.enode) = new(ATAN, (yyvsp[-1].enode), ENULL); }
#line 4731 "y.tab.c"
    break;

  case 238: /* term: '@' K_ATAN2 '(' e ',' e ')'  */
#line 1089 "gram.y"
                                        { (yyval.enode) = new(ATAN2, (yyvsp[-3].enode), (yyvsp[-1].enode)); }
#line 4737 "y.tab.c"
    break;

  case 239: /* term: '@' K_CEIL '(' e ')'  */
#line 1090 "gram.y"
                                        { (yyval.enode) = new(CEIL, (yyvsp[-1].enode), ENULL); }
#line 4743 "y.tab.c"
    break;

  case 240: /* term: '@' K_COS '(' e ')'  */
#line 1091 "gram.y"
                                        { (yyval.enode) = new(COS, (yyvsp[-1].enode), ENULL); }
#line 4749 "y.tab.c"
    break;

  case 241: /* term: '@' K_EXP '(' e ')'  */
#line 1092 "gram.y"
                                        { (yyval.enode) = new(EXP, (yyvsp[-1].enode), ENULL); }
#line 4755 "y.tab.c"
    break;

  case 242: /* term: '@' K_FABS '(' e ')'  */
#line 1093 "gram.y"
                                        { (yyval.enode) = new(FABS, (yyvsp[-1].enode), ENULL); }
#line 4761 "y.tab.c"
    break;

  case 243: /* term: '@' K_FLOOR '(' e ')'  */
#line 1094 "gram.y"
                                        { (yyval.enode) = new(FLOOR, (yyvsp[-1].enode), ENULL); }
#line 4767 "y.tab.c"
    break;

  case 244: /* term: '@' K_HYPOT '(' e ',' e ')'  */
#line 1095 "gram.y"
                                        { (yyval.enode) = new(HYPOT, (yyvsp[-3].enode), (yyvsp[-1].enode)); }
#line 4773 "y.tab.c"
    break;

  case 245: /* term: '@' K_LN '(' e ')'  */
#line 1096 "gram.y"
                                        { (yyval.enode) = new(LOG, (yyvsp[-1].enode), ENULL); }
#line 4779 "y.tab.c"
    break;

  case 246: /* term: '@' K_LOG '(' e ')'  */
#line 1097 "gram.y"
                                        { (yyval.enode) = new(LOG10, (yyvsp[-1].enode), ENULL); }
#line 4785 "y.tab.c"
    break;

  case 247: /* term: '@' K_POW '(' e ',' e ')'  */
#line 1098 "gram.y"
                                        { (yyval.enode) = new(POW, (yyvsp[-3].enode), (yyvsp[-1].enode)); }
#line 4791 "y.tab.c"
    break;

  case 248: /* term: '@' K_SIN '(' e ')'  */
#line 1099 "gram.y"
                                        { (yyval.enode) = new(SIN, (yyvsp[-1].enode), ENULL); }
#line 4797 "y.tab.c"
    break;

  case 249: /* term: '@' K_SQRT '(' e ')'  */
#line 1100 "gram.y"
                                        { (yyval.enode) = new(SQRT, (yyvsp[-1].enode), ENULL); }
#line 4803 "y.tab.c"
    break;

  case 250: /* term: '@' K_TAN '(' e ')'  */
#line 1101 "gram.y"
                                        { (yyval.enode) = new(TAN, (yyvsp[-1].enode), ENULL); }
#line 4809 "y.tab.c"
    break;

  case 251: /* term: '@' K_DTR '(' e ')'  */
#line 1102 "gram.y"
                                        { (yyval.enode) = new(DTR, (yyvsp[-1].enode), ENULL); }
#line 4815 "y.tab.c"
    break;

  case 252: /* term: '@' K_RTD '(' e ')'  */
#line 1103 "gram.y"
                                        { (yyval.enode) = new(RTD, (yyvsp[-1].enode), ENULL); }
#line 4821 "y.tab.c"
    break;

  case 253: /* term: '@' K_RND '(' e ')'  */
#line 1104 "gram.y"
                                        { (yyval.enode) = new(RND, (yyvsp[-1].enode), ENULL); }
#line 4827 "y.tab.c"
    break;

  case 254: /* term: '@' K_ROUND '(' e ',' e ')'  */
#line 1105 "gram.y"
                                        { (yyval.enode) = new(ROUND, (yyvsp[-3].enode), (yyvsp[-1].enode)); }
#line 4833 "y.tab.c"
    break;

  case 255: /* term: '@' K_IF '(' e ',' e ',' e ')'  */
#line 1106 "gram.y"
                                          { (yyval.enode) = new(IF,  (yyvsp[-5].enode),new(',',(yyvsp[-3].enode),(yyvsp[-1].enode))); }
#line 4839 "y.tab.c"
    break;

  case 256: /* term: '@' K_PV '(' e ',' e ',' e ')'  */
#line 1108 "gram.y"
                                          { (yyval.enode) = new(PV,  (yyvsp[-5].enode),new(':',(yyvsp[-3].enode),(yyvsp[-1].enode))); }
#line 4845 "y.tab.c"
    break;

  case 257: /* term: '@' K_FV '(' e ',' e ',' e ')'  */
#line 1109 "gram.y"
                                          { (yyval.enode) = new(FV,  (yyvsp[-5].enode),new(':',(yyvsp[-3].enode),(yyvsp[-1].enode))); }
#line 4851 "y.tab.c"
    break;

  case 258: /* term: '@' K_PMT '(' e ',' e ',' e ')'  */
#line 1110 "gram.y"
                                          { (yyval.enode) = new(PMT, (yyvsp[-5].enode),new(':',(yyvsp[-3].enode),(yyvsp[-1].enode))); }
#line 4857 "y.tab.c"
    break;

  case 259: /* term: '@' K_HOUR '(' e ')'  */
#line 1112 "gram.y"
                                        { (yyval.enode) = new(HOUR, (yyvsp[-1].enode), ENULL); }
#line 4863 "y.tab.c"
    break;

  case 260: /* term: '@' K_MINUTE '(' e ')'  */
#line 1113 "gram.y"
                                        { (yyval.enode) = new(MINUTE, (yyvsp[-1].enode), ENULL); }
#line 4869 "y.tab.c"
    break;

  case 261: /* term: '@' K_SECOND '(' e ')'  */
#line 1114 "gram.y"
                                        { (yyval.enode) = new(SECOND, (yyvsp[-1].enode), ENULL); }
#line 4875 "y.tab.c"
    break;

  case 262: /* term: '@' K_MONTH '(' e ')'  */
#line 1115 "gram.y"
                                        { (yyval.enode) = new(MONTH, (yyvsp[-1].enode), ENULL); }
#line 4881 "y.tab.c"
    break;

  case 263: /* term: '@' K_DAY '(' e ')'  */
#line 1116 "gram.y"
                                        { (yyval.enode) = new(DAY, (yyvsp[-1].enode), ENULL); }
#line 4887 "y.tab.c"
    break;

  case 264: /* term: '@' K_YEAR '(' e ')'  */
#line 1117 "gram.y"
                                        { (yyval.enode) = new(YEAR, (yyvsp[-1].enode), ENULL); }
#line 4893 "y.tab.c"
    break;

  case 265: /* term: '@' K_NOW  */
#line 1118 "gram.y"
                                        { (yyval.enode) = new(NOW, ENULL, ENULL);}
#line 4899 "y.tab.c"
    break;

  case 266: /* term: '@' K_DTS '(' e ',' e ',' e ')'  */
#line 1120 "gram.y"
                                        { (yyval.enode) = new(DTS, (yyvsp[-5].enode), new(',', (yyvsp[-3].enode), (yyvsp[-1].enode)));}
#line 4905 "y.tab.c"
    break;

  case 267: /* term: NUMBER '.' NUMBER '.' NUMBER  */
#line 1121 "gram.y"
                                        { (yyval.enode) = new(DTS,
				new_const(O_CONST, (double) (yyvsp[-4].ival)),
				new(',', new_const(O_CONST, (double) (yyvsp[-2].ival)),
				new_const(O_CONST, (double) (yyvsp[0].ival))));}
#line 4914 "y.tab.c"
    break;

  case 268: /* term: '@' K_TTS '(' e ',' e ',' e ')'  */
#line 1126 "gram.y"
                                        { (yyval.enode) = new(TTS, (yyvsp[-5].enode), new(',', (yyvsp[-3].enode), (yyvsp[-1].enode)));}
#line 4920 "y.tab.c"
    break;

  case 269: /* term: '@' K_STON '(' e ')'  */
#line 1127 "gram.y"
                                        { (yyval.enode) = new(STON, (yyvsp[-1].enode), ENULL); }
#line 4926 "y.tab.c"
    break;

  case 270: /* term: '@' K_EQS '(' e ',' e ')'  */
#line 1128 "gram.y"
                                        { (yyval.enode) = new(EQS, (yyvsp[-3].enode), (yyvsp[-1].enode)); }
#line 4932 "y.tab.c"
    break;

  case 271: /* term: '@' K_DATE '(' e ')'  */
#line 1129 "gram.y"
                                        { (yyval.enode) = new(DATE, (yyvsp[-1].enode), ENULL); }
#line 4938 "y.tab.c"
    break;

  case 272: /* term: '@' K_DATE '(' e ',' e ')'  */
#line 1130 "gram.y"
                                        { (yyval.enode) = new(DATE, (yyvsp[-3].enode), (yyvsp[-1].enode)); }
#line 4944 "y.tab.c"
    break;

  case 273: /* term: '@' K_FMT '(' e ',' e ')'  */
#line 1131 "gram.y"
                                        { (yyval.enode) = new(FMT, (yyvsp[-3].enode), (yyvsp[-1].enode)); }
#line 4950 "y.tab.c"
    break;

  case 274: /* term: '@' K_UPPER '(' e ')'  */
#line 1132 "gram.y"
                                        { (yyval.enode) = new(UPPER, (yyvsp[-1].enode), ENULL); }
#line 4956 "y.tab.c"
    break;

  case 275: /* term: '@' K_LOWER '(' e ')'  */
#line 1133 "gram.y"
                                        { (yyval.enode) = new(LOWER, (yyvsp[-1].enode), ENULL); }
#line 4962 "y.tab.c"
    break;

  case 276: /* term: '@' K_CAPITAL '(' e ')'  */
#line 1134 "gram.y"
                                        { (yyval.enode) = new(CAPITAL, (yyvsp[-1].enode), ENULL); }
#line 4968 "y.tab.c"
    break;

  case 277: /* term: '@' K_INDEX '(' range ',' e ')'  */
#line 1136 "gram.y"
                 { (yyval.enode) = new(INDEX, new_range(REDUCE | INDEX, (yyvsp[-3].rval)), (yyvsp[-1].enode)); }
#line 4974 "y.tab.c"
    break;

  case 278: /* term: '@' K_INDEX '(' e ',' range ')'  */
#line 1138 "gram.y"
                 { (yyval.enode) = new(INDEX, new_range(REDUCE | INDEX, (yyvsp[-1].rval)), (yyvsp[-3].enode)); }
#line 4980 "y.tab.c"
    break;

  case 279: /* term: '@' K_INDEX '(' range ',' e ',' e ')'  */
#line 1140 "gram.y"
                 { (yyval.enode) = new(INDEX, new_range(REDUCE | INDEX, (yyvsp[-5].rval)),
		    new(',', (yyvsp[-3].enode), (yyvsp[-1].enode))); }
#line 4987 "y.tab.c"
    break;

  case 280: /* term: '@' K_LOOKUP '(' range ',' e ')'  */
#line 1143 "gram.y"
                 { (yyval.enode) = new(LOOKUP, new_range(REDUCE | LOOKUP, (yyvsp[-3].rval)), (yyvsp[-1].enode)); }
#line 4993 "y.tab.c"
    break;

  case 281: /* term: '@' K_LOOKUP '(' e ',' range ')'  */
#line 1145 "gram.y"
                 { (yyval.enode) = new(LOOKUP, new_range(REDUCE | LOOKUP, (yyvsp[-1].rval)), (yyvsp[-3].enode)); }
#line 4999 "y.tab.c"
    break;

  case 282: /* term: '@' K_HLOOKUP '(' range ',' e ',' e ')'  */
#line 1147 "gram.y"
                 { (yyval.enode) = new(HLOOKUP, new_range(REDUCE | HLOOKUP, (yyvsp[-5].rval)),
		    new(',', (yyvsp[-3].enode), (yyvsp[-1].enode))); }
#line 5006 "y.tab.c"
    break;

  case 283: /* term: '@' K_HLOOKUP '(' e ',' range ',' e ')'  */
#line 1150 "gram.y"
                 { (yyval.enode) = new(HLOOKUP, new_range(REDUCE | HLOOKUP, (yyvsp[-3].rval)),
		    new(',', (yyvsp[-5].enode), (yyvsp[-1].enode))); }
#line 5013 "y.tab.c"
    break;

  case 284: /* term: '@' K_VLOOKUP '(' range ',' e ',' e ')'  */
#line 1153 "gram.y"
                 { (yyval.enode) = new(VLOOKUP, new_range(REDUCE | VLOOKUP, (yyvsp[-5].rval)),
		    new(',', (yyvsp[-3].enode), (yyvsp[-1].enode))); }
#line 5020 "y.tab.c"
    break;

  case 285: /* term: '@' K_VLOOKUP '(' e ',' range ',' e ')'  */
#line 1156 "gram.y"
                 { (yyval.enode) = new(VLOOKUP, new_range(REDUCE | VLOOKUP, (yyvsp[-3].rval)),
		    new(',', (yyvsp[-5].enode), (yyvsp[-1].enode))); }
#line 5027 "y.tab.c"
    break;

  case 286: /* term: '@' K_STINDEX '(' range ',' e ')'  */
#line 1159 "gram.y"
                 { (yyval.enode) = new(STINDEX, new_range(REDUCE | STINDEX, (yyvsp[-3].rval)), (yyvsp[-1].enode)); }
#line 5033 "y.tab.c"
    break;

  case 287: /* term: '@' K_STINDEX '(' e ',' range ')'  */
#line 1161 "gram.y"
                 { (yyval.enode) = new(STINDEX, new_range(REDUCE | STINDEX, (yyvsp[-1].rval)), (yyvsp[-3].enode)); }
#line 5039 "y.tab.c"
    break;

  case 288: /* term: '@' K_STINDEX '(' range ',' e ',' e ')'  */
#line 1163 "gram.y"
                 { (yyval.enode) = new(STINDEX, new_range(REDUCE | STINDEX, (yyvsp[-5].rval)),
		    new(',', (yyvsp[-3].enode), (yyvsp[-1].enode))); }
#line 5046 "y.tab.c"
    break;

  case 289: /* term: '@' K_EXT '(' e ',' e ')'  */
#line 1165 "gram.y"
                                        { (yyval.enode) = new(EXT, (yyvsp[-3].enode), (yyvsp[-1].enode)); }
#line 5052 "y.tab.c"
    break;

  case 290: /* term: '@' K_NVAL '(' e ',' e ')'  */
#line 1166 "gram.y"
                                        { (yyval.enode) = new(NVAL, (yyvsp[-3].enode), (yyvsp[-1].enode)); }
#line 5058 "y.tab.c"
    break;

  case 291: /* term: '@' K_SVAL '(' e ',' e ')'  */
#line 1167 "gram.y"
                                        { (yyval.enode) = new(SVAL, (yyvsp[-3].enode), (yyvsp[-1].enode)); }
#line 5064 "y.tab.c"
    break;

  case 292: /* term: '@' K_SUBSTR '(' e ',' e ',' e ')'  */
#line 1169 "gram.y"
                                { (yyval.enode) = new(SUBSTR, (yyvsp[-5].enode), new(',', (yyvsp[-3].enode), (yyvsp[-1].enode))); }
#line 5070 "y.tab.c"
    break;

  case 293: /* term: '(' e ')'  */
#line 1170 "gram.y"
                                { (yyval.enode) = (yyvsp[-1].enode); }
#line 5076 "y.tab.c"
    break;

  case 294: /* term: '+' term  */
#line 1171 "gram.y"
                                { (yyval.enode) = (yyvsp[0].enode); }
#line 5082 "y.tab.c"
    break;

  case 295: /* term: '-' term  */
#line 1172 "gram.y"
                                { (yyval.enode) = new('m', (yyvsp[0].enode), ENULL); }
#line 5088 "y.tab.c"
    break;

  case 296: /* term: NUMBER  */
#line 1173 "gram.y"
                                { (yyval.enode) = new_const(O_CONST, (double) (yyvsp[0].ival)); }
#line 5094 "y.tab.c"
    break;

  case 297: /* term: FNUMBER  */
#line 1174 "gram.y"
                                { (yyval.enode) = new_const(O_CONST, (yyvsp[0].fval)); }
#line 5100 "y.tab.c"
    break;

  case 298: /* term: '@' K_PI  */
#line 1175 "gram.y"
                                { (yyval.enode) = new(PI_, ENULL, ENULL); }
#line 5106 "y.tab.c"
    break;

  case 299: /* term: STRING  */
#line 1176 "gram.y"
                                { (yyval.enode) = new_str((yyvsp[0].sval)); }
#line 5112 "y.tab.c"
    break;

  case 300: /* term: '~' term  */
#line 1177 "gram.y"
                                { (yyval.enode) = new('!', (yyvsp[0].enode), ENULL); }
#line 5118 "y.tab.c"
    break;

  case 301: /* term: '!' term  */
#line 1178 "gram.y"
                                { (yyval.enode) = new('!', (yyvsp[0].enode), ENULL); }
#line 5124 "y.tab.c"
    break;

  case 302: /* term: '@' K_FILENAME '(' e ')'  */
#line 1179 "gram.y"
                                        { (yyval.enode) = new(FILENAME, (yyvsp[-1].enode), ENULL); }
#line 5130 "y.tab.c"
    break;

  case 303: /* term: '@' K_MYROW  */
#line 1180 "gram.y"
                                        { (yyval.enode) = new(MYROW, ENULL, ENULL);}
#line 5136 "y.tab.c"
    break;

  case 304: /* term: '@' K_MYCOL  */
#line 1181 "gram.y"
                                        { (yyval.enode) = new(MYCOL, ENULL, ENULL);}
#line 5142 "y.tab.c"
    break;

  case 305: /* term: '@' K_LASTROW  */
#line 1182 "gram.y"
                                        { (yyval.enode) = new(LASTROW, ENULL, ENULL);}
#line 5148 "y.tab.c"
    break;

  case 306: /* term: '@' K_LASTCOL  */
#line 1183 "gram.y"
                                        { (yyval.enode) = new(LASTCOL, ENULL, ENULL);}
#line 5154 "y.tab.c"
    break;

  case 307: /* term: '@' K_COLTOA '(' e ')'  */
#line 1184 "gram.y"
                                        { (yyval.enode) = new(COLTOA, (yyvsp[-1].enode), ENULL);}
#line 5160 "y.tab.c"
    break;

  case 308: /* term: '@' K_NUMITER  */
#line 1185 "gram.y"
                                        { (yyval.enode) = new(NUMITER, ENULL, ENULL);}
#line 5166 "y.tab.c"
    break;

  case 309: /* term: '@' K_ERR  */
#line 1186 "gram.y"
                                { (yyval.enode) = new(ERR_, ENULL, ENULL); }
#line 5172 "y.tab.c"
    break;

  case 310: /* term: K_ERR  */
#line 1187 "gram.y"
                                { (yyval.enode) = new(ERR_, ENULL, ENULL); }
#line 5178 "y.tab.c"
    break;

  case 311: /* term: '@' K_BLACK  */
#line 1188 "gram.y"
                                { (yyval.enode) = new(BLACK, ENULL, ENULL); }
#line 5184 "y.tab.c"
    break;

  case 312: /* term: '@' K_RED  */
#line 1189 "gram.y"
                                { (yyval.enode) = new(RED, ENULL, ENULL); }
#line 5190 "y.tab.c"
    break;

  case 313: /* term: '@' K_GREEN  */
#line 1190 "gram.y"
                                { (yyval.enode) = new(GREEN, ENULL, ENULL); }
#line 5196 "y.tab.c"
    break;

  case 314: /* term: '@' K_YELLOW  */
#line 1191 "gram.y"
                                { (yyval.enode) = new(YELLOW, ENULL, ENULL); }
#line 5202 "y.tab.c"
    break;

  case 315: /* term: '@' K_BLUE  */
#line 1192 "gram.y"
                                { (yyval.enode) = new(BLUE, ENULL, ENULL); }
#line 5208 "y.tab.c"
    break;

  case 316: /* term: '@' K_MAGENTA  */
#line 1193 "gram.y"
                                { (yyval.enode) = new(MAGENTA, ENULL, ENULL); }
#line 5214 "y.tab.c"
    break;

  case 317: /* term: '@' K_CYAN  */
#line 1194 "gram.y"
                                { (yyval.enode) = new(CYAN, ENULL, ENULL); }
#line 5220 "y.tab.c"
    break;

  case 318: /* term: '@' K_WHITE  */
#line 1195 "gram.y"
                                { (yyval.enode) = new(WHITE, ENULL, ENULL); }
#line 5226 "y.tab.c"
    break;

  case 319: /* e: e '+' e  */
#line 1199 "gram.y"
                                { (yyval.enode) = new('+', (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5232 "y.tab.c"
    break;

  case 320: /* e: e '-' e  */
#line 1200 "gram.y"
                                { (yyval.enode) = new('-', (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5238 "y.tab.c"
    break;

  case 321: /* e: e '*' e  */
#line 1201 "gram.y"
                                { (yyval.enode) = new('*', (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5244 "y.tab.c"
    break;

  case 322: /* e: e '/' e  */
#line 1202 "gram.y"
                                { (yyval.enode) = new('/', (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5250 "y.tab.c"
    break;

  case 323: /* e: e '%' e  */
#line 1203 "gram.y"
                                { (yyval.enode) = new('%', (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5256 "y.tab.c"
    break;

  case 324: /* e: e '^' e  */
#line 1204 "gram.y"
                                { (yyval.enode) = new('^', (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5262 "y.tab.c"
    break;

  case 326: /* e: e '?' e ':' e  */
#line 1206 "gram.y"
                                { (yyval.enode) = new('?', (yyvsp[-4].enode), new(':', (yyvsp[-2].enode), (yyvsp[0].enode))); }
#line 5268 "y.tab.c"
    break;

  case 327: /* e: e ';' e  */
#line 1207 "gram.y"
                                { (yyval.enode) = new(';', (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5274 "y.tab.c"
    break;

  case 328: /* e: e '<' e  */
#line 1208 "gram.y"
                                { (yyval.enode) = new('<', (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5280 "y.tab.c"
    break;

  case 329: /* e: e '=' e  */
#line 1209 "gram.y"
                                { (yyval.enode) = new('=', (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5286 "y.tab.c"
    break;

  case 330: /* e: e '>' e  */
#line 1210 "gram.y"
                                { (yyval.enode) = new('>', (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5292 "y.tab.c"
    break;

  case 331: /* e: e '&' e  */
#line 1211 "gram.y"
                                { (yyval.enode) = new('&', (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5298 "y.tab.c"
    break;

  case 332: /* e: e '|' e  */
#line 1212 "gram.y"
                                { (yyval.enode) = new('|', (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5304 "y.tab.c"
    break;

  case 333: /* e: e '<' '=' e  */
#line 1213 "gram.y"
                                { (yyval.enode) = new('!', new('>', (yyvsp[-3].enode), (yyvsp[0].enode)), ENULL); }
#line 5310 "y.tab.c"
    break;

  case 334: /* e: e '!' '=' e  */
#line 1214 "gram.y"
                                { (yyval.enode) = new('!', new('=', (yyvsp[-3].enode), (yyvsp[0].enode)), ENULL); }
#line 5316 "y.tab.c"
    break;

  case 335: /* e: e '<' '>' e  */
#line 1215 "gram.y"
                                { (yyval.enode) = new('!', new('=', (yyvsp[-3].enode), (yyvsp[0].enode)), ENULL); }
#line 5322 "y.tab.c"
    break;

  case 336: /* e: e '>' '=' e  */
#line 1216 "gram.y"
                                { (yyval.enode) = new('!', new('<', (yyvsp[-3].enode), (yyvsp[0].enode)), ENULL); }
#line 5328 "y.tab.c"
    break;

  case 337: /* e: e '#' e  */
#line 1217 "gram.y"
                                { (yyval.enode) = new('#', (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5334 "y.tab.c"
    break;

  case 338: /* expr_list: e  */
#line 1220 "gram.y"
                                { (yyval.enode) = new(ELIST, ENULL, (yyvsp[0].enode)); }
#line 5340 "y.tab.c"
    break;

  case 339: /* expr_list: expr_list ',' e  */
#line 1221 "gram.y"
                                { (yyval.enode) = new(ELIST, (yyvsp[-2].enode), (yyvsp[0].enode)); }
#line 5346 "y.tab.c"
    break;

  case 340: /* range: var ':' var  */
#line 1224 "gram.y"
                                { (yyval.rval).left = (yyvsp[-2].ent); (yyval.rval).right = (yyvsp[0].ent); }
#line 5352 "y.tab.c"
    break;

  case 341: /* range: RANGE  */
#line 1225 "gram.y"
                                { (yyval.rval) = (yyvsp[0].rval); }
#line 5358 "y.tab.c"
    break;

  case 342: /* var: COL NUMBER  */
#line 1228 "gram.y"
                                { (yyval.ent).vp = lookat((yyvsp[0].ival), (yyvsp[-1].ival)); (yyval.ent).vf = 0; }
#line 5364 "y.tab.c"
    break;

  case 343: /* var: '$' COL NUMBER  */
#line 1229 "gram.y"
                                { (yyval.ent).vp = lookat((yyvsp[0].ival), (yyvsp[-1].ival));
					(yyval.ent).vf = FIX_COL; }
#line 5371 "y.tab.c"
    break;

  case 344: /* var: COL '$' NUMBER  */
#line 1231 "gram.y"
                                { (yyval.ent).vp = lookat((yyvsp[0].ival), (yyvsp[-2].ival));
					(yyval.ent).vf = FIX_ROW; }
#line 5378 "y.tab.c"
    break;

  case 345: /* var: '$' COL '$' NUMBER  */
#line 1233 "gram.y"
                                   { (yyval.ent).vp = lookat((yyvsp[0].ival), (yyvsp[-2].ival));
					(yyval.ent).vf = FIX_ROW | FIX_COL; }
#line 5385 "y.tab.c"
    break;

  case 346: /* var: VAR  */
#line 1235 "gram.y"
                                { (yyval.ent) = (yyvsp[0].rval).left; }
#line 5391 "y.tab.c"
    break;

  case 347: /* var_or_range: range  */
#line 1238 "gram.y"
                                { (yyval.rval) = (yyvsp[0].rval); }
#line 5397 "y.tab.c"
    break;

  case 348: /* var_or_range: var  */
#line 1239 "gram.y"
                                { (yyval.rval).left = (yyvsp[0].ent); (yyval.rval).right = (yyvsp[0].ent); }
#line 5403 "y.tab.c"
    break;

  case 349: /* num: NUMBER  */
#line 1242 "gram.y"
                                { (yyval.fval) = (double) (yyvsp[0].ival); }
#line 5409 "y.tab.c"
    break;

  case 350: /* num: FNUMBER  */
#line 1243 "gram.y"
                                { (yyval.fval) = (yyvsp[0].fval); }
#line 5415 "y.tab.c"
    break;

  case 351: /* num: '-' num  */
#line 1244 "gram.y"
                                { (yyval.fval) = -(yyvsp[0].fval); }
#line 5421 "y.tab.c"
    break;

  case 352: /* num: '+' num  */
#line 1245 "gram.y"
                                { (yyval.fval) = (yyvsp[0].fval); }
#line 5427 "y.tab.c"
    break;

  case 353: /* strarg: STRING  */
#line 1248 "gram.y"
                                { (yyval.sval) = (yyvsp[0].sval); }
#line 5433 "y.tab.c"
    break;

  case 354: /* strarg: var  */
#line 1249 "gram.y"
                                {
				    char *s, *s1;
				    size_t l;
				    s1 = (yyvsp[0].ent).vp->label;
				    if (!s1)
					s1 = "NULL_STRING";
				    l = strlen(s1) + 1;
				    s = scxmalloc(l);
				    strlcpy(s, s1, l);
				    (yyval.sval) = s;
				}
#line 5449 "y.tab.c"
    break;

  case 357: /* setitem: K_AUTO  */
#line 1268 "gram.y"
                                        { setauto(1); }
#line 5455 "y.tab.c"
    break;

  case 358: /* setitem: K_AUTOCALC  */
#line 1269 "gram.y"
                                        { setauto(1); }
#line 5461 "y.tab.c"
    break;

  case 359: /* setitem: '~' K_AUTO  */
#line 1270 "gram.y"
                                        { setauto(0); }
#line 5467 "y.tab.c"
    break;

  case 360: /* setitem: '~' K_AUTOCALC  */
#line 1271 "gram.y"
                                        { setauto(0); }
#line 5473 "y.tab.c"
    break;

  case 361: /* setitem: '!' K_AUTO  */
#line 1272 "gram.y"
                                        { setauto(0); }
#line 5479 "y.tab.c"
    break;

  case 362: /* setitem: '!' K_AUTOCALC  */
#line 1273 "gram.y"
                                        { setauto(0); }
#line 5485 "y.tab.c"
    break;

  case 363: /* setitem: K_BYCOLS  */
#line 1274 "gram.y"
                                        { setorder(BYCOLS); }
#line 5491 "y.tab.c"
    break;

  case 364: /* setitem: K_BYROWS  */
#line 1275 "gram.y"
                                        { setorder(BYROWS); }
#line 5497 "y.tab.c"
    break;

  case 365: /* setitem: K_OPTIMIZE  */
#line 1276 "gram.y"
                                        { optimize = 1; }
#line 5503 "y.tab.c"
    break;

  case 366: /* setitem: '~' K_OPTIMIZE  */
#line 1277 "gram.y"
                                        { optimize = 0; }
#line 5509 "y.tab.c"
    break;

  case 367: /* setitem: '!' K_OPTIMIZE  */
#line 1278 "gram.y"
                                        { optimize = 0; }
#line 5515 "y.tab.c"
    break;

  case 368: /* setitem: K_NUMERIC  */
#line 1279 "gram.y"
                                        { numeric = 1; }
#line 5521 "y.tab.c"
    break;

  case 369: /* setitem: '~' K_NUMERIC  */
#line 1280 "gram.y"
                                        { numeric = 0; }
#line 5527 "y.tab.c"
    break;

  case 370: /* setitem: '!' K_NUMERIC  */
#line 1281 "gram.y"
                                        { numeric = 0; }
#line 5533 "y.tab.c"
    break;

  case 371: /* setitem: K_PRESCALE  */
#line 1282 "gram.y"
                                        { prescale = 0.01; }
#line 5539 "y.tab.c"
    break;

  case 372: /* setitem: '~' K_PRESCALE  */
#line 1283 "gram.y"
                                        { prescale = 1.0; }
#line 5545 "y.tab.c"
    break;

  case 373: /* setitem: '!' K_PRESCALE  */
#line 1284 "gram.y"
                                        { prescale = 1.0; }
#line 5551 "y.tab.c"
    break;

  case 374: /* setitem: K_EXTFUN  */
#line 1285 "gram.y"
                                        { extfunc = 1; }
#line 5557 "y.tab.c"
    break;

  case 375: /* setitem: '~' K_EXTFUN  */
#line 1286 "gram.y"
                                        { extfunc = 0; }
#line 5563 "y.tab.c"
    break;

  case 376: /* setitem: '!' K_EXTFUN  */
#line 1287 "gram.y"
                                        { extfunc = 0; }
#line 5569 "y.tab.c"
    break;

  case 377: /* setitem: K_CELLCUR  */
#line 1288 "gram.y"
                                        { showcell = 1; }
#line 5575 "y.tab.c"
    break;

  case 378: /* setitem: '~' K_CELLCUR  */
#line 1289 "gram.y"
                                        { showcell = 0; }
#line 5581 "y.tab.c"
    break;

  case 379: /* setitem: '!' K_CELLCUR  */
#line 1290 "gram.y"
                                        { showcell = 0; }
#line 5587 "y.tab.c"
    break;

  case 380: /* setitem: K_TOPROW  */
#line 1291 "gram.y"
                                        { showtop = 1; }
#line 5593 "y.tab.c"
    break;

  case 381: /* setitem: '~' K_TOPROW  */
#line 1292 "gram.y"
                                        { showtop = 0; }
#line 5599 "y.tab.c"
    break;

  case 382: /* setitem: '!' K_TOPROW  */
#line 1293 "gram.y"
                                        { showtop = 0; }
#line 5605 "y.tab.c"
    break;

  case 383: /* setitem: K_AUTOINSERT  */
#line 1294 "gram.y"
                                        { autoinsert = 1; }
#line 5611 "y.tab.c"
    break;

  case 384: /* setitem: '~' K_AUTOINSERT  */
#line 1295 "gram.y"
                                        { autoinsert = 0; }
#line 5617 "y.tab.c"
    break;

  case 385: /* setitem: '!' K_AUTOINSERT  */
#line 1296 "gram.y"
                                        { autoinsert = 0; }
#line 5623 "y.tab.c"
    break;

  case 386: /* setitem: K_AUTOWRAP  */
#line 1297 "gram.y"
                                        { autowrap = 1; }
#line 5629 "y.tab.c"
    break;

  case 387: /* setitem: '~' K_AUTOWRAP  */
#line 1298 "gram.y"
                                        { autowrap = 0; }
#line 5635 "y.tab.c"
    break;

  case 388: /* setitem: '!' K_AUTOWRAP  */
#line 1299 "gram.y"
                                        { autowrap = 0; }
#line 5641 "y.tab.c"
    break;

  case 389: /* setitem: K_CSLOP  */
#line 1300 "gram.y"
                                        { cslop = 1; FullUpdate++; }
#line 5647 "y.tab.c"
    break;

  case 390: /* setitem: '~' K_CSLOP  */
#line 1301 "gram.y"
                                        { cslop = 0; FullUpdate++; }
#line 5653 "y.tab.c"
    break;

  case 391: /* setitem: '!' K_CSLOP  */
#line 1302 "gram.y"
                                        { cslop = 0; FullUpdate++; }
#line 5659 "y.tab.c"
    break;

  case 392: /* setitem: K_COLOR  */
#line 1303 "gram.y"
                                        { color = 1;
					  if (usecurses && has_colors()) {
					    color_set(1, NULL);
					    bkgd(COLOR_PAIR(1) | ' ');
					    FullUpdate++;
					  }
					}
#line 5671 "y.tab.c"
    break;

  case 393: /* setitem: '!' K_COLOR  */
#line 1310 "gram.y"
                                        { color = 0;
					  if (usecurses && has_colors()) {
					    color_set(0, NULL);
					    bkgd(COLOR_PAIR(0) | ' ');
					  }
					}
#line 5682 "y.tab.c"
    break;

  case 394: /* setitem: '~' K_COLOR  */
#line 1316 "gram.y"
                                        { color = 0;
					  if (usecurses && has_colors()) {
					    color_set(0, NULL);
					    bkgd(COLOR_PAIR(0) | ' ');
					  }
					}
#line 5693 "y.tab.c"
    break;

  case 395: /* setitem: K_COLORNEG  */
#line 1322 "gram.y"
                                        { colorneg = 1; }
#line 5699 "y.tab.c"
    break;

  case 396: /* setitem: '!' K_COLORNEG  */
#line 1323 "gram.y"
                                        { colorneg = 0; }
#line 5705 "y.tab.c"
    break;

  case 397: /* setitem: '~' K_COLORNEG  */
#line 1324 "gram.y"
                                        { colorneg = 0; }
#line 5711 "y.tab.c"
    break;

  case 398: /* setitem: K_COLORERR  */
#line 1325 "gram.y"
                                        { colorerr = 1; }
#line 5717 "y.tab.c"
    break;

  case 399: /* setitem: '!' K_COLORERR  */
#line 1326 "gram.y"
                                        { colorerr = 0; }
#line 5723 "y.tab.c"
    break;

  case 400: /* setitem: '~' K_COLORERR  */
#line 1327 "gram.y"
                                        { colorerr = 0; }
#line 5729 "y.tab.c"
    break;

  case 401: /* setitem: K_BRAILLE  */
#line 1328 "gram.y"
                                        { braille = 1; }
#line 5735 "y.tab.c"
    break;

  case 402: /* setitem: '!' K_BRAILLE  */
#line 1329 "gram.y"
                                        { braille = 0; }
#line 5741 "y.tab.c"
    break;

  case 403: /* setitem: '~' K_BRAILLE  */
#line 1330 "gram.y"
                                        { braille = 0; }
#line 5747 "y.tab.c"
    break;

  case 404: /* setitem: K_BACKUP  */
#line 1331 "gram.y"
                                        { dobackups = 1; }
#line 5753 "y.tab.c"
    break;

  case 405: /* setitem: '!' K_BACKUP  */
#line 1332 "gram.y"
                                        { dobackups = 0; }
#line 5759 "y.tab.c"
    break;

  case 406: /* setitem: '~' K_BACKUP  */
#line 1333 "gram.y"
                                        { dobackups = 0; }
#line 5765 "y.tab.c"
    break;

  case 407: /* setitem: K_MOUSE  */
#line 1334 "gram.y"
                                        { mouseon(); }
#line 5771 "y.tab.c"
    break;

  case 408: /* setitem: '!' K_MOUSE  */
#line 1335 "gram.y"
                                        { mouseoff(); }
#line 5777 "y.tab.c"
    break;

  case 409: /* setitem: '~' K_MOUSE  */
#line 1336 "gram.y"
                                        { mouseoff(); }
#line 5783 "y.tab.c"
    break;

  case 410: /* setitem: K_ITERATIONS '=' NUMBER  */
#line 1337 "gram.y"
                                        { setiterations((yyvsp[0].ival)); }
#line 5789 "y.tab.c"
    break;

  case 411: /* setitem: K_TBLSTYLE '=' NUMBER  */
#line 1338 "gram.y"
                                        { tbl_style = (yyvsp[0].ival); }
#line 5795 "y.tab.c"
    break;

  case 412: /* setitem: K_TBLSTYLE '=' K_TBL  */
#line 1339 "gram.y"
                                        { tbl_style = TBL; }
#line 5801 "y.tab.c"
    break;

  case 413: /* setitem: K_TBLSTYLE '=' K_LATEX  */
#line 1340 "gram.y"
                                        { tbl_style = LATEX; }
#line 5807 "y.tab.c"
    break;

  case 414: /* setitem: K_TBLSTYLE '=' K_SLATEX  */
#line 1341 "gram.y"
                                        { tbl_style = SLATEX; }
#line 5813 "y.tab.c"
    break;

  case 415: /* setitem: K_TBLSTYLE '=' K_TEX  */
#line 1342 "gram.y"
                                        { tbl_style = TEX; }
#line 5819 "y.tab.c"
    break;

  case 416: /* setitem: K_TBLSTYLE '=' K_FRAME  */
#line 1343 "gram.y"
                                        { tbl_style = FRAME; }
#line 5825 "y.tab.c"
    break;

  case 417: /* setitem: K_RNDTOEVEN  */
#line 1344 "gram.y"
                                        { rndtoeven = 1; FullUpdate++; }
#line 5831 "y.tab.c"
    break;

  case 418: /* setitem: '!' K_RNDTOEVEN  */
#line 1345 "gram.y"
                                        { rndtoeven = 0; FullUpdate++; }
#line 5837 "y.tab.c"
    break;

  case 419: /* setitem: '~' K_RNDTOEVEN  */
#line 1346 "gram.y"
                                        { rndtoeven = 0; FullUpdate++; }
#line 5843 "y.tab.c"
    break;

  case 420: /* setitem: K_CRACTION '=' NUMBER  */
#line 1347 "gram.y"
                                        { craction = (yyvsp[0].ival); }
#line 5849 "y.tab.c"
    break;

  case 421: /* setitem: K_ROWLIMIT '=' NUMBER  */
#line 1348 "gram.y"
                                        { rowlimit = (yyvsp[0].ival); }
#line 5855 "y.tab.c"
    break;

  case 422: /* setitem: K_COLLIMIT '=' NUMBER  */
#line 1349 "gram.y"
                                        { collimit = (yyvsp[0].ival); }
#line 5861 "y.tab.c"
    break;

  case 423: /* setitem: K_PAGESIZE '=' NUMBER  */
#line 1350 "gram.y"
                                        { pagesize = (yyvsp[0].ival); }
#line 5867 "y.tab.c"
    break;

  case 424: /* setitem: K_SCRC  */
#line 1351 "gram.y"
                                        { scrc++; }
#line 5873 "y.tab.c"
    break;

  case 425: /* setitem: K_LOCALE  */
#line 1352 "gram.y"
                                        {
#ifdef USELOCALE
					  struct  lconv *locstruct;
					  char    *loc;

					  loc = setlocale(LC_ALL, "");
					  if (loc != NULL) {
					    locstruct = localeconv();
					    dpoint = (locstruct->decimal_point)[0];
					    thsep = (locstruct->thousands_sep)[0];
					  }
					  else {
					    dpoint = '.';
					    thsep = ',';
					  }
					  FullUpdate++;
#else
					  error("Locale support not available");
#endif
					}
#line 5898 "y.tab.c"
    break;

  case 426: /* setitem: '!' K_LOCALE  */
#line 1372 "gram.y"
                                        {
					  dpoint = '.';
					  thsep = ',';
					  FullUpdate++;
					}
#line 5908 "y.tab.c"
    break;

  case 427: /* setitem: '~' K_LOCALE  */
#line 1377 "gram.y"
                                        {
					  dpoint = '.';
					  thsep = ',';
					  FullUpdate++;
					}
#line 5918 "y.tab.c"
    break;

  case 428: /* errlist: K_ERROR range  */
#line 1385 "gram.y"
                                        { num_search((double)0,
					  (yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col,
					  (yyvsp[0].rval).right.vp->row, (yyvsp[0].rval).right.vp->col,
					  CELLERROR); }
#line 5927 "y.tab.c"
    break;

  case 429: /* errlist: K_ERROR  */
#line 1389 "gram.y"
                                        { num_search((double)0, 0, 0,
					  maxrow, maxcol, CELLERROR); }
#line 5934 "y.tab.c"
    break;

  case 430: /* errlist: K_INVALID range  */
#line 1391 "gram.y"
                                        { num_search((double)0,
					  (yyvsp[0].rval).left.vp->row, (yyvsp[0].rval).left.vp->col,
					  (yyvsp[0].rval).right.vp->row, (yyvsp[0].rval).right.vp->col,
					  CELLINVALID); }
#line 5943 "y.tab.c"
    break;

  case 431: /* errlist: K_INVALID  */
#line 1395 "gram.y"
                                        { num_search((double)0, 0, 0,
					  maxrow, maxcol, CELLINVALID); }
#line 5950 "y.tab.c"
    break;


#line 5954 "y.tab.c"

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

