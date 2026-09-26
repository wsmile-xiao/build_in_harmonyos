
#line 1 "bfpp.rl"
// bfpp.rl written by Boris 'billiob' Faure billiob<att>gmail<dott>com

/************************* Required for every parser *************************/
#ifndef OHCOUNT_BFPP_PARSER_H
#define OHCOUNT_BFPP_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *BFPP_LANG = LANG_BFPP;

// the languages entities
const char *bfpp_entities[] = {
  "space", "comment", "operator", "include"
};

// constants associated with the entities
enum {
  BFPP_SPACE = 0, BFPP_COMMENT, BFPP_OPERATOR, BFPP_INCLUDE
};

/*****************************************************************************/


#line 28 "bfpp.h"
static const char _bfpp_actions[] = {
	0, 1, 0, 1, 4, 1, 5, 1, 
	11, 1, 12, 1, 13, 1, 16, 1, 
	19, 1, 20, 1, 21, 1, 22, 1, 
	23, 1, 27, 1, 28, 1, 29, 2, 
	1, 7, 2, 3, 2, 2, 5, 15, 
	2, 7, 18, 2, 8, 11, 2, 10, 
	11, 2, 14, 7, 3, 3, 2, 0, 
	3, 3, 2, 16, 3, 14, 11, 26, 
	4, 0, 6, 17, 7, 4, 14, 9, 
	24, 11, 4, 14, 10, 25, 11
};

static const char _bfpp_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 1, 2, 2, 2, 2, 2, 2, 
	2, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 4, 4, 4, 
	4
};

static const char _bfpp_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 1, 0, 0, 0, 0, 0, 0, 
	1, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 1, 0, 0, 0, 
	0
};

static const short _bfpp_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _bfpp_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _bfpp_key_offsets[] = {
	0, 0, 1, 2, 3, 4, 5, 6, 
	7, 18, 29, 30, 31, 45, 45, 48, 
	52, 59, 60, 63, 64, 65, 66, 67, 
	68, 69, 70, 71, 72, 100, 102, 105, 
	106
};

static const short _bfpp_trans_keys[] = {
	110, 99, 108, 117, 100, 101, 40, 9, 
	10, 12, 32, 41, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 41, 269, 
	525, 0, 11, 14, 255, 10, 10, 32, 
	35, 37, 61, 64, 91, 9, 13, 43, 
	46, 58, 62, 93, 94, 32, 9, 13, 
	10, 92, 12, 13, 92, 269, 525, 0, 
	12, 14, 255, 10, 92, 12, 13, 105, 
	110, 99, 108, 117, 100, 101, 40, 41, 
	9, 10, 12, 32, 33, 35, 37, 61, 
	64, 91, 269, 525, 0, 8, 14, 42, 
	43, 46, 47, 57, 58, 62, 63, 92, 
	93, 94, 95, 255, 9, 32, 10, 12, 
	13, 105, 10, 0
};

static const char _bfpp_single_lengths[] = {
	0, 1, 1, 1, 1, 1, 1, 1, 
	7, 7, 1, 1, 6, 0, 1, 2, 
	3, 1, 1, 1, 1, 1, 1, 1, 
	1, 1, 1, 1, 12, 2, 1, 1, 
	1
};

static const char _bfpp_range_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	2, 2, 0, 0, 4, 0, 1, 1, 
	2, 0, 1, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 8, 0, 1, 0, 
	0
};

static const char _bfpp_index_offsets[] = {
	0, 0, 2, 4, 6, 8, 10, 12, 
	14, 24, 34, 36, 38, 49, 50, 53, 
	57, 63, 65, 68, 70, 72, 74, 76, 
	78, 80, 82, 84, 86, 107, 110, 113, 
	115
};

static const char _bfpp_indicies[] = {
	1, 0, 2, 0, 3, 0, 4, 0, 
	5, 0, 6, 0, 7, 0, 8, 9, 
	9, 8, 10, 11, 9, 7, 7, 0, 
	13, 14, 14, 13, 15, 16, 14, 12, 
	12, 0, 9, 0, 17, 18, 20, 21, 
	21, 22, 23, 21, 20, 21, 21, 21, 
	19, 19, 20, 20, 19, 19, 27, 19, 
	22, 27, 28, 29, 22, 22, 26, 22, 
	19, 27, 19, 22, 30, 19, 31, 19, 
	32, 19, 33, 19, 34, 19, 35, 19, 
	36, 19, 37, 19, 38, 37, 40, 17, 
	17, 40, 41, 41, 41, 42, 43, 41, 
	44, 45, 39, 39, 41, 39, 41, 39, 
	41, 39, 18, 40, 40, 46, 47, 47, 
	48, 50, 49, 17, 51, 0
};

static const char _bfpp_trans_targs[] = {
	28, 2, 3, 4, 5, 6, 7, 8, 
	8, 9, 28, 10, 8, 8, 9, 28, 
	10, 28, 0, 13, 14, 13, 15, 19, 
	12, 12, 12, 16, 17, 18, 20, 21, 
	22, 23, 24, 25, 26, 27, 13, 28, 
	29, 28, 30, 31, 11, 32, 28, 28, 
	30, 28, 1, 28
};

static const char _bfpp_trans_actions[] = {
	23, 0, 0, 0, 0, 0, 0, 1, 
	0, 0, 13, 0, 52, 34, 34, 56, 
	34, 37, 0, 60, 43, 69, 7, 46, 
	29, 25, 27, 7, 7, 7, 46, 46, 
	46, 46, 46, 46, 46, 46, 74, 40, 
	3, 64, 31, 49, 5, 5, 15, 19, 
	0, 21, 0, 17
};

static const char _bfpp_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 9, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 9, 0, 0, 0, 
	0
};

static const char _bfpp_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 11, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 11, 0, 0, 0, 
	0
};

static const char _bfpp_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 1, 
	1, 1, 1, 0, 0, 25, 26, 27, 
	27, 27, 27, 27, 27, 27, 27, 27, 
	27, 27, 27, 27, 0, 47, 48, 50, 
	52
};

static const int bfpp_start = 12;
static const int bfpp_first_final = 12;
static const int bfpp_error = 0;

static const int bfpp_en_bfpp_line = 28;
static const int bfpp_en_bfpp_entity = 12;


#line 93 "bfpp.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Brainfuck++ code.
 *
 * @param *buffer The string to parse.
 * @param length The length of the string to parse.
 * @param count Integer flag specifying whether or not to count lines. If yes,
 *   uses the Ragel machine optimized for counting. Otherwise uses the Ragel
 *   machine optimized for returning entity positions.
 * @param *callback Callback function. If count is set, callback is called for
 *   every line of code, comment, or blank with 'lcode', 'lcomment', and
 *   'lblank' respectively. Otherwise callback is called for each entity found.
 */
void parse_bfpp(char *buffer, int length, int count,
             void (*callback) (const char *lang, const char *entity, int s,
                               int e, void *udata),
             void *userdata
  ) {
  init

  
#line 210 "bfpp.h"
	{
	cs = bfpp_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 116 "bfpp.rl"
  cs = (count) ? bfpp_en_bfpp_line : bfpp_en_bfpp_entity;
  
#line 221 "bfpp.h"
	{
	int _klen;
	unsigned int _trans;
	short _widec;
	const char *_acts;
	unsigned int _nacts;
	const short *_keys;

	if ( p == pe )
		goto _test_eof;
	if ( cs == 0 )
		goto _out;
_resume:
	_acts = _bfpp_actions + _bfpp_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 13:
#line 1 "NONE"
	{ts = p;}
	break;
#line 243 "bfpp.h"
		}
	}

	_widec = (*p);
	_klen = _bfpp_cond_lengths[cs];
	_keys = _bfpp_cond_keys + (_bfpp_cond_offsets[cs]*2);
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				switch ( _bfpp_cond_spaces[_bfpp_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _bfpp_trans_keys + _bfpp_key_offsets[cs];
	_trans = _bfpp_index_offsets[cs];

	_klen = _bfpp_single_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + _klen - 1;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + ((_upper-_lower) >> 1);
			if ( _widec < *_mid )
				_upper = _mid - 1;
			else if ( _widec > *_mid )
				_lower = _mid + 1;
			else {
				_trans += (unsigned int)(_mid - _keys);
				goto _match;
			}
		}
		_keys += _klen;
		_trans += _klen;
	}

	_klen = _bfpp_range_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				_trans += (unsigned int)((_mid - _keys)>>1);
				goto _match;
			}
		}
		_trans += _klen;
	}

_match:
	_trans = _bfpp_indicies[_trans];
_eof_trans:
	cs = _bfpp_trans_targs[_trans];

	if ( _bfpp_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _bfpp_actions + _bfpp_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 53 "common.rl"
	{
  if (!line_contains_code && !line_start) line_start = ts;
  line_contains_code = 1;
}
	break;
	case 1:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 2:
#line 31 "bfpp.rl"
	{
    switch(entity) {
    case BFPP_SPACE:
      ls
      break;
    case BFPP_OPERATOR:
    case BFPP_INCLUDE:
      code
      break;
    case BFPP_COMMENT:
      comment
      break;
    case INTERNAL_NL:
      std_internal_newline(BFPP_LANG)
      break;
    case NEWLINE:
      std_newline(BFPP_LANG)
    }
  }
	break;
	case 3:
#line 56 "bfpp.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 64 "bfpp.rl"
	{ entity = BFPP_SPACE;    }
	break;
	case 5:
#line 65 "bfpp.rl"
	{ entity = NEWLINE;       }
	break;
	case 6:
#line 68 "bfpp.rl"
	{ entity = BFPP_OPERATOR; }
	break;
	case 7:
#line 69 "bfpp.rl"
	{ entity = BFPP_COMMENT;  }
	break;
	case 8:
#line 88 "bfpp.rl"
	{ entity = BFPP_SPACE;    }
	break;
	case 9:
#line 89 "bfpp.rl"
	{ entity = BFPP_OPERATOR; }
	break;
	case 10:
#line 90 "bfpp.rl"
	{ entity = BFPP_INCLUDE;  }
	break;
	case 11:
#line 91 "bfpp.rl"
	{ entity = BFPP_COMMENT;  }
	break;
	case 14:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 15:
#line 31 "bfpp.rl"
	{te = p+1;{
    switch(entity) {
    case BFPP_SPACE:
      ls
      break;
    case BFPP_OPERATOR:
    case BFPP_INCLUDE:
      code
      break;
    case BFPP_COMMENT:
      comment
      break;
    case INTERNAL_NL:
      std_internal_newline(BFPP_LANG)
      break;
    case NEWLINE:
      std_newline(BFPP_LANG)
    }
  }}
	break;
	case 16:
#line 67 "bfpp.rl"
	{te = p+1;}
	break;
	case 17:
#line 31 "bfpp.rl"
	{te = p+1;{
    switch(entity) {
    case BFPP_SPACE:
      ls
      break;
    case BFPP_OPERATOR:
    case BFPP_INCLUDE:
      code
      break;
    case BFPP_COMMENT:
      comment
      break;
    case INTERNAL_NL:
      std_internal_newline(BFPP_LANG)
      break;
    case NEWLINE:
      std_newline(BFPP_LANG)
    }
  }}
	break;
	case 18:
#line 31 "bfpp.rl"
	{te = p+1;{
    switch(entity) {
    case BFPP_SPACE:
      ls
      break;
    case BFPP_OPERATOR:
    case BFPP_INCLUDE:
      code
      break;
    case BFPP_COMMENT:
      comment
      break;
    case INTERNAL_NL:
      std_internal_newline(BFPP_LANG)
      break;
    case NEWLINE:
      std_newline(BFPP_LANG)
    }
  }}
	break;
	case 19:
#line 31 "bfpp.rl"
	{te = p;p--;{
    switch(entity) {
    case BFPP_SPACE:
      ls
      break;
    case BFPP_OPERATOR:
    case BFPP_INCLUDE:
      code
      break;
    case BFPP_COMMENT:
      comment
      break;
    case INTERNAL_NL:
      std_internal_newline(BFPP_LANG)
      break;
    case NEWLINE:
      std_newline(BFPP_LANG)
    }
  }}
	break;
	case 20:
#line 31 "bfpp.rl"
	{te = p;p--;{
    switch(entity) {
    case BFPP_SPACE:
      ls
      break;
    case BFPP_OPERATOR:
    case BFPP_INCLUDE:
      code
      break;
    case BFPP_COMMENT:
      comment
      break;
    case INTERNAL_NL:
      std_internal_newline(BFPP_LANG)
      break;
    case NEWLINE:
      std_newline(BFPP_LANG)
    }
  }}
	break;
	case 21:
#line 66 "bfpp.rl"
	{te = p;p--;}
	break;
	case 22:
#line 31 "bfpp.rl"
	{te = p;p--;{
    switch(entity) {
    case BFPP_SPACE:
      ls
      break;
    case BFPP_OPERATOR:
    case BFPP_INCLUDE:
      code
      break;
    case BFPP_COMMENT:
      comment
      break;
    case INTERNAL_NL:
      std_internal_newline(BFPP_LANG)
      break;
    case NEWLINE:
      std_newline(BFPP_LANG)
    }
  }}
	break;
	case 23:
#line 31 "bfpp.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case BFPP_SPACE:
      ls
      break;
    case BFPP_OPERATOR:
    case BFPP_INCLUDE:
      code
      break;
    case BFPP_COMMENT:
      comment
      break;
    case INTERNAL_NL:
      std_internal_newline(BFPP_LANG)
      break;
    case NEWLINE:
      std_newline(BFPP_LANG)
    }
  }}
	break;
	case 24:
#line 74 "bfpp.rl"
	{act = 8;}
	break;
	case 25:
#line 74 "bfpp.rl"
	{act = 9;}
	break;
	case 26:
#line 74 "bfpp.rl"
	{act = 10;}
	break;
	case 27:
#line 74 "bfpp.rl"
	{te = p;p--;{
    callback(BFPP_LANG, bfpp_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 28:
#line 74 "bfpp.rl"
	{te = p;p--;{
    callback(BFPP_LANG, bfpp_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 29:
#line 1 "NONE"
	{	switch( act ) {
	case 8:
	{{p = ((te))-1;}
    callback(BFPP_LANG, bfpp_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	case 9:
	{{p = ((te))-1;}
    callback(BFPP_LANG, bfpp_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	case 10:
	{{p = ((te))-1;}
    callback(BFPP_LANG, bfpp_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	}
	}
	break;
#line 625 "bfpp.h"
		}
	}

_again:
	_acts = _bfpp_actions + _bfpp_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 638 "bfpp.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _bfpp_eof_trans[cs] > 0 ) {
		_trans = _bfpp_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 118 "bfpp.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(BFPP_LANG) }
}

#endif

/*****************************************************************************/

