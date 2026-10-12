/* A Bison parser, made by GNU Bison 3.8.2.  */

/* Bison interface for Yacc-like parsers in C

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

/* DO NOT RELY ON FEATURES THAT ARE NOT DOCUMENTED in the manual,
   especially those whose name start with YY_ or yy_.  They are
   private implementation details that can be changed or removed.  */

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

#line 518 "y.tab.h"

};
typedef union YYSTYPE YYSTYPE;
# define YYSTYPE_IS_TRIVIAL 1
# define YYSTYPE_IS_DECLARED 1
#endif


extern YYSTYPE yylval;


int yyparse (void);


#endif /* !YY_YY_Y_TAB_H_INCLUDED  */
