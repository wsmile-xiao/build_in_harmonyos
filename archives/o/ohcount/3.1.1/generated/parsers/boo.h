
#line 1 "boo.rl"
// boo.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_BOO_PARSER_H
#define OHCOUNT_BOO_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *BOO_LANG = LANG_BOO;

// the languages entities
const char *boo_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  BOO_SPACE = 0, BOO_COMMENT, BOO_STRING, BOO_ANY
};

/*****************************************************************************/


#line 28 "boo.h"
static const char _boo_actions[] = {
	0, 1, 1, 1, 9, 1, 10, 1, 
	11, 1, 12, 1, 14, 1, 15, 1, 
	16, 1, 17, 1, 23, 1, 24, 1, 
	25, 1, 26, 1, 27, 1, 29, 1, 
	30, 1, 31, 1, 32, 1, 33, 2, 
	0, 20, 2, 1, 13, 2, 1, 19, 
	2, 4, 1, 2, 4, 15, 2, 5, 
	1, 2, 5, 15, 2, 6, 2, 2, 
	7, 2, 2, 8, 9, 2, 12, 21, 
	2, 13, 22, 2, 15, 28, 2, 18, 
	13, 3, 6, 2, 1, 3, 7, 2, 
	1, 3, 18, 3, 13, 3, 18, 3, 
	15
};

static const char _boo_cond_offsets[] = {
	0, 0, 1, 2, 3, 5, 5, 5, 
	5, 6, 7, 8, 9, 9, 9, 9, 
	9, 9, 11, 13, 15, 15, 17, 20, 
	20, 20, 20, 20, 20, 21, 21, 21, 
	21, 21, 21, 21
};

static const char _boo_cond_lengths[] = {
	0, 1, 1, 1, 2, 0, 0, 0, 
	1, 1, 1, 1, 0, 0, 0, 0, 
	0, 2, 2, 2, 0, 2, 3, 0, 
	0, 0, 0, 0, 1, 0, 0, 0, 
	0, 0, 0, 0
};

static const short _boo_cond_keys[] = {
	42, 42, 42, 42, 42, 42, 42, 42, 
	47, 47, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 42, 42, 13, 13, 
	42, 42, 13, 13, 42, 42, 13, 13, 
	42, 42, 13, 13, 42, 42, 47, 47, 
	13, 13, 0
};

static const char _boo_cond_spaces[] = {
	2, 2, 2, 2, 2, 0, 0, 0, 
	0, 0, 1, 0, 1, 0, 1, 0, 
	1, 0, 1, 1, 0, 0
};

static const char _boo_key_offsets[] = {
	0, 0, 7, 14, 21, 31, 36, 39, 
	40, 51, 62, 73, 84, 85, 86, 89, 
	94, 97, 112, 127, 142, 143, 158, 176, 
	177, 182, 185, 188, 190, 204, 206, 207, 
	208, 211, 216, 218
};

static const short _boo_trans_keys[] = {
	47, 1322, 1578, 0, 41, 43, 255, 47, 
	1322, 1578, 0, 41, 43, 255, 47, 1322, 
	1578, 0, 41, 43, 255, 1322, 1327, 1578, 
	1583, 0, 41, 43, 46, 48, 255, 10, 
	34, 92, 12, 13, 10, 12, 13, 34, 
	9, 10, 12, 32, 34, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 34, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 34, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 34, 269, 525, 
	0, 11, 14, 255, 10, 39, 10, 12, 
	13, 10, 47, 92, 12, 13, 10, 12, 
	13, 9, 10, 12, 32, 47, 269, 525, 
	810, 1066, 0, 8, 14, 41, 43, 255, 
	9, 10, 12, 32, 47, 269, 525, 810, 
	1066, 0, 8, 14, 41, 43, 255, 9, 
	10, 12, 32, 47, 269, 525, 810, 1066, 
	0, 8, 14, 41, 43, 255, 10, 9, 
	10, 12, 32, 47, 269, 525, 810, 1066, 
	0, 8, 14, 41, 43, 255, 9, 10, 
	12, 32, 269, 525, 810, 815, 1066, 1071, 
	0, 8, 14, 41, 43, 46, 48, 255, 
	10, 32, 35, 47, 9, 13, 32, 9, 
	13, 10, 12, 13, 42, 47, 9, 10, 
	12, 32, 34, 35, 39, 47, 269, 525, 
	0, 8, 14, 255, 9, 32, 34, 34, 
	10, 12, 13, 10, 39, 92, 12, 13, 
	42, 47, 10, 0
};

static const char _boo_single_lengths[] = {
	0, 3, 3, 3, 4, 3, 1, 1, 
	7, 7, 7, 7, 1, 1, 1, 3, 
	1, 9, 9, 9, 1, 9, 10, 1, 
	3, 1, 1, 2, 10, 2, 1, 1, 
	1, 3, 2, 1
};

static const char _boo_range_lengths[] = {
	0, 2, 2, 2, 3, 1, 1, 0, 
	2, 2, 2, 2, 0, 0, 1, 1, 
	1, 3, 3, 3, 0, 3, 4, 0, 
	1, 1, 1, 0, 2, 0, 0, 0, 
	1, 1, 0, 0
};

static const char _boo_index_offsets[] = {
	0, 0, 6, 12, 18, 26, 31, 34, 
	36, 46, 56, 66, 76, 78, 80, 83, 
	88, 91, 104, 117, 130, 132, 145, 160, 
	162, 167, 170, 173, 176, 189, 192, 194, 
	196, 199, 204, 207
};

static const char _boo_indicies[] = {
	2, 3, 4, 1, 1, 0, 2, 5, 
	6, 1, 1, 0, 7, 3, 4, 1, 
	1, 0, 3, 7, 4, 8, 1, 1, 
	1, 0, 9, 11, 12, 9, 10, 9, 
	9, 10, 14, 13, 15, 16, 16, 15, 
	17, 18, 16, 14, 14, 9, 20, 21, 
	21, 20, 22, 23, 21, 19, 19, 9, 
	15, 16, 16, 15, 24, 18, 16, 14, 
	14, 9, 15, 16, 16, 15, 25, 18, 
	16, 14, 14, 9, 16, 9, 11, 9, 
	9, 9, 26, 9, 11, 28, 9, 27, 
	9, 9, 27, 30, 31, 31, 30, 32, 
	33, 31, 34, 35, 29, 29, 29, 9, 
	37, 38, 38, 37, 39, 40, 38, 41, 
	42, 36, 36, 36, 9, 30, 31, 31, 
	30, 32, 33, 31, 43, 44, 29, 29, 
	29, 9, 31, 9, 30, 31, 31, 30, 
	45, 33, 31, 34, 35, 29, 29, 29, 
	9, 30, 31, 31, 30, 33, 31, 34, 
	45, 35, 46, 29, 29, 29, 29, 9, 
	47, 48, 50, 51, 52, 50, 49, 50, 
	50, 53, 54, 54, 51, 1, 51, 55, 
	57, 47, 47, 57, 58, 59, 60, 61, 
	62, 63, 56, 56, 48, 57, 57, 64, 
	67, 66, 46, 68, 68, 68, 69, 65, 
	65, 70, 65, 26, 29, 72, 71, 47, 
	73, 0
};

static const char _boo_trans_targs[] = {
	24, 1, 2, 3, 4, 3, 4, 2, 
	24, 28, 5, 28, 6, 5, 8, 8, 
	9, 10, 12, 8, 8, 9, 10, 12, 
	11, 31, 13, 15, 16, 17, 17, 18, 
	19, 20, 21, 22, 17, 17, 18, 19, 
	20, 21, 22, 21, 22, 19, 28, 28, 
	0, 24, 25, 26, 27, 24, 24, 24, 
	28, 29, 30, 32, 33, 34, 23, 35, 
	28, 28, 5, 7, 28, 32, 14, 15, 
	32, 28
};

static const char _boo_trans_actions[] = {
	37, 13, 13, 13, 13, 51, 51, 57, 
	75, 27, 0, 39, 0, 66, 1, 0, 
	0, 1, 0, 85, 63, 63, 85, 63, 
	1, 1, 0, 0, 0, 1, 0, 0, 
	1, 0, 1, 1, 81, 60, 60, 81, 
	60, 81, 81, 48, 48, 54, 45, 69, 
	0, 29, 11, 13, 93, 31, 33, 35, 
	72, 7, 78, 42, 78, 89, 9, 9, 
	19, 25, 3, 0, 21, 0, 0, 5, 
	1, 23
};

static const char _boo_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	15, 0, 0, 0, 15, 0, 0, 0, 
	0, 0, 0, 0
};

static const char _boo_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	17, 0, 0, 0, 17, 0, 0, 0, 
	0, 0, 0, 0
};

static const char _boo_eof_trans[] = {
	0, 1, 1, 1, 1, 10, 10, 10, 
	10, 10, 10, 10, 10, 10, 10, 10, 
	10, 10, 10, 10, 10, 10, 10, 0, 
	0, 54, 55, 56, 0, 65, 66, 69, 
	69, 66, 66, 74
};

static const int boo_start = 24;
static const int boo_first_final = 24;
static const int boo_error = 0;

static const int boo_en_boo_line = 28;
static const int boo_en_boo_entity = 24;


#line 111 "boo.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Boo code.
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
void parse_boo(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  int nest_count = 0;

  
#line 253 "boo.h"
	{
	cs = boo_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 136 "boo.rl"
  cs = (count) ? boo_en_boo_line : boo_en_boo_entity;
  
#line 264 "boo.h"
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
	_acts = _boo_actions + _boo_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 17:
#line 1 "NONE"
	{ts = p;}
	break;
#line 286 "boo.h"
		}
	}

	_widec = (*p);
	_klen = _boo_cond_lengths[cs];
	_keys = _boo_cond_keys + (_boo_cond_offsets[cs]*2);
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
				switch ( _boo_cond_spaces[_boo_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
	case 1: {
		_widec = (short)(768 + ((*p) - 0));
		if ( 
#line 63 "boo.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
	case 2: {
		_widec = (short)(1280 + ((*p) - 0));
		if ( 
#line 102 "boo.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _boo_trans_keys + _boo_key_offsets[cs];
	_trans = _boo_index_offsets[cs];

	_klen = _boo_single_lengths[cs];
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

	_klen = _boo_range_lengths[cs];
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
	_trans = _boo_indicies[_trans];
_eof_trans:
	cs = _boo_trans_targs[_trans];

	if ( _boo_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _boo_actions + _boo_trans_actions[_trans];
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
#line 31 "boo.rl"
	{
    switch(entity) {
    case BOO_SPACE:
      ls
      break;
    case BOO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BOO_LANG)
      break;
    case NEWLINE:
      std_newline(BOO_LANG)
    }
  }
	break;
	case 3:
#line 47 "boo.rl"
	{ nest_count = 0; }
	break;
	case 4:
#line 48 "boo.rl"
	{ nest_count++; }
	break;
	case 5:
#line 49 "boo.rl"
	{ nest_count--; }
	break;
	case 6:
#line 54 "boo.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 66 "boo.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 8:
#line 76 "boo.rl"
	{ p--; }
	break;
	case 9:
#line 76 "boo.rl"
	{ p--; }
	break;
	case 10:
#line 78 "boo.rl"
	{ p--; }
	break;
	case 11:
#line 82 "boo.rl"
	{ entity = BOO_SPACE; }
	break;
	case 12:
#line 85 "boo.rl"
	{ entity = NEWLINE;   }
	break;
	case 13:
#line 86 "boo.rl"
	{ entity = BOO_ANY;   }
	break;
	case 14:
#line 106 "boo.rl"
	{ entity = BOO_SPACE;   }
	break;
	case 15:
#line 107 "boo.rl"
	{ entity = BOO_COMMENT; }
	break;
	case 18:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 19:
#line 83 "boo.rl"
	{te = p+1;}
	break;
	case 20:
#line 84 "boo.rl"
	{te = p+1;}
	break;
	case 21:
#line 31 "boo.rl"
	{te = p+1;{
    switch(entity) {
    case BOO_SPACE:
      ls
      break;
    case BOO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BOO_LANG)
      break;
    case NEWLINE:
      std_newline(BOO_LANG)
    }
  }}
	break;
	case 22:
#line 31 "boo.rl"
	{te = p+1;{
    switch(entity) {
    case BOO_SPACE:
      ls
      break;
    case BOO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BOO_LANG)
      break;
    case NEWLINE:
      std_newline(BOO_LANG)
    }
  }}
	break;
	case 23:
#line 31 "boo.rl"
	{te = p;p--;{
    switch(entity) {
    case BOO_SPACE:
      ls
      break;
    case BOO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BOO_LANG)
      break;
    case NEWLINE:
      std_newline(BOO_LANG)
    }
  }}
	break;
	case 24:
#line 83 "boo.rl"
	{te = p;p--;}
	break;
	case 25:
#line 31 "boo.rl"
	{te = p;p--;{
    switch(entity) {
    case BOO_SPACE:
      ls
      break;
    case BOO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BOO_LANG)
      break;
    case NEWLINE:
      std_newline(BOO_LANG)
    }
  }}
	break;
	case 26:
#line 31 "boo.rl"
	{te = p;p--;{
    switch(entity) {
    case BOO_SPACE:
      ls
      break;
    case BOO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BOO_LANG)
      break;
    case NEWLINE:
      std_newline(BOO_LANG)
    }
  }}
	break;
	case 27:
#line 31 "boo.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case BOO_SPACE:
      ls
      break;
    case BOO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(BOO_LANG)
      break;
    case NEWLINE:
      std_newline(BOO_LANG)
    }
  }}
	break;
	case 28:
#line 91 "boo.rl"
	{te = p+1;{
    callback(BOO_LANG, boo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 29:
#line 109 "boo.rl"
	{te = p+1;}
	break;
	case 30:
#line 91 "boo.rl"
	{te = p;p--;{
    callback(BOO_LANG, boo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 31:
#line 91 "boo.rl"
	{te = p;p--;{
    callback(BOO_LANG, boo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 32:
#line 109 "boo.rl"
	{te = p;p--;}
	break;
	case 33:
#line 109 "boo.rl"
	{{p = ((te))-1;}}
	break;
#line 637 "boo.h"
		}
	}

_again:
	_acts = _boo_actions + _boo_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 16:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 650 "boo.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _boo_eof_trans[cs] > 0 ) {
		_trans = _boo_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 138 "boo.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(BOO_LANG) }
}

#endif

/*****************************************************************************/
