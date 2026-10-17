
#line 1 "stratego.rl"
/************************* Required for every parser *************************/
#ifndef OHCOUNT_STRATEGO_PARSER_H
#define OHCOUNT_STRATEGO_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *STRATEGO_LANG = LANG_STRATEGO;

// the languages entities
const char *stratego_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  STRATEGO_SPACE = 0, STRATEGO_COMMENT, STRATEGO_STRING, STRATEGO_ANY
};

/*****************************************************************************/


#line 26 "stratego.h"
static const char _stratego_actions[] = {
	0, 1, 0, 1, 1, 1, 6, 1, 
	7, 1, 9, 1, 10, 1, 11, 1, 
	12, 1, 13, 1, 15, 1, 16, 1, 
	19, 1, 20, 1, 21, 1, 22, 1, 
	23, 1, 24, 1, 27, 1, 28, 1, 
	29, 1, 30, 1, 31, 1, 32, 2, 
	0, 16, 2, 3, 2, 2, 4, 2, 
	2, 5, 2, 2, 7, 17, 2, 8, 
	18, 2, 10, 25, 2, 11, 26, 2, 
	14, 1, 2, 14, 8, 2, 14, 10, 
	2, 14, 11, 3, 3, 2, 1, 3, 
	3, 2, 20, 3, 4, 2, 1, 3, 
	5, 2, 0, 3, 5, 2, 16, 3, 
	14, 0, 8, 4, 14, 3, 2, 1
	
};

static const char _stratego_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 1, 1, 1, 1, 1, 1, 
	2, 3, 4, 4, 4, 4, 4, 4, 
	4, 4, 4, 4, 5, 5, 6, 6, 
	6, 6, 6, 6, 7, 7, 7
};

static const char _stratego_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 1, 0, 0, 0, 0, 0, 1, 
	1, 1, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 1, 0, 1, 0, 0, 
	0, 0, 0, 1, 0, 0, 0
};

static const short _stratego_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 0
};

static const char _stratego_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0
};

static const char _stratego_key_offsets[] = {
	0, 0, 2, 2, 3, 4, 5, 7, 
	8, 12, 20, 24, 25, 30, 31, 32, 
	43, 54, 66, 67, 68, 69, 75, 78, 
	80, 82, 84, 88, 95, 98, 111, 113, 
	117, 119, 121, 127, 138, 144, 150
};

static const short _stratego_trans_keys[] = {
	34, 92, 39, 46, 42, 42, 47, 10, 
	9, 32, 34, 92, 10, 12, 269, 525, 
	0, 11, 14, 255, 9, 32, 34, 92, 
	10, 9, 10, 32, 34, 92, 39, 46, 
	9, 10, 12, 32, 42, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 42, 47, 269, 525, 0, 11, 
	14, 255, 10, 10, 10, 32, 34, 39, 
	47, 9, 13, 32, 9, 13, 34, 92, 
	39, 92, 42, 47, 10, 92, 12, 13, 
	92, 269, 525, 0, 12, 14, 255, 92, 
	12, 13, 9, 10, 12, 32, 34, 39, 
	47, 269, 525, 0, 8, 14, 255, 9, 
	32, 9, 32, 34, 92, 39, 92, 42, 
	47, 9, 10, 32, 92, 12, 13, 9, 
	10, 12, 32, 92, 269, 525, 0, 11, 
	14, 255, 9, 10, 32, 92, 12, 13, 
	9, 10, 32, 92, 12, 13, 10, 0
};

static const char _stratego_single_lengths[] = {
	0, 2, 0, 1, 1, 1, 2, 1, 
	4, 4, 4, 1, 5, 1, 1, 7, 
	7, 8, 1, 1, 1, 4, 1, 2, 
	2, 2, 2, 3, 1, 9, 2, 4, 
	2, 2, 4, 7, 4, 4, 1
};

static const char _stratego_range_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 2, 0, 0, 0, 0, 0, 2, 
	2, 2, 0, 0, 0, 1, 1, 0, 
	0, 0, 1, 2, 1, 2, 0, 0, 
	0, 0, 1, 2, 1, 1, 0
};

static const char _stratego_index_offsets[] = {
	0, 0, 3, 4, 6, 8, 10, 13, 
	15, 20, 27, 32, 34, 40, 42, 44, 
	54, 64, 75, 77, 79, 81, 87, 90, 
	93, 96, 99, 103, 109, 112, 124, 127, 
	132, 135, 138, 144, 154, 160, 166
};

static const char _stratego_indicies[] = {
	2, 3, 1, 1, 2, 0, 4, 0, 
	6, 5, 6, 7, 5, 9, 8, 12, 
	12, 13, 14, 11, 15, 15, 16, 17, 
	11, 11, 10, 19, 19, 20, 21, 18, 
	15, 10, 19, 22, 19, 20, 21, 18, 
	23, 10, 24, 10, 26, 27, 27, 26, 
	28, 29, 27, 25, 25, 10, 31, 32, 
	32, 31, 33, 34, 32, 30, 30, 10, 
	26, 27, 27, 26, 28, 35, 29, 27, 
	25, 25, 10, 27, 10, 37, 36, 38, 
	39, 41, 42, 43, 44, 41, 40, 41, 
	41, 45, 2, 3, 1, 46, 47, 4, 
	5, 9, 46, 48, 49, 48, 9, 49, 
	50, 51, 9, 9, 48, 49, 48, 9, 
	53, 38, 38, 53, 54, 55, 56, 57, 
	58, 52, 52, 39, 53, 53, 59, 12, 
	12, 13, 14, 11, 60, 61, 24, 25, 
	62, 60, 64, 63, 64, 65, 63, 62, 
	64, 37, 37, 64, 65, 66, 67, 62, 
	62, 63, 70, 68, 70, 71, 68, 69, 
	70, 37, 70, 71, 68, 69, 38, 72, 
	0
};

static const char _stratego_trans_targs[] = {
	21, 1, 21, 2, 3, 5, 6, 21, 
	21, 26, 29, 8, 8, 29, 9, 10, 
	11, 12, 8, 8, 29, 9, 10, 29, 
	13, 15, 15, 16, 17, 18, 15, 15, 
	16, 17, 18, 29, 29, 36, 29, 0, 
	21, 22, 23, 24, 25, 21, 21, 4, 
	21, 27, 7, 28, 29, 30, 31, 32, 
	33, 20, 38, 29, 29, 14, 34, 29, 
	34, 35, 19, 37, 29, 34, 34, 35, 
	29
};

static const char _stratego_trans_actions[] = {
	45, 13, 68, 13, 13, 11, 11, 65, 
	43, 11, 33, 1, 0, 21, 0, 0, 
	0, 0, 95, 56, 99, 56, 95, 47, 
	0, 3, 0, 0, 3, 0, 91, 53, 
	53, 91, 53, 19, 31, 0, 59, 0, 
	35, 9, 80, 80, 77, 37, 41, 13, 
	39, 77, 11, 11, 62, 5, 103, 74, 
	74, 7, 7, 23, 29, 0, 3, 25, 
	0, 71, 0, 0, 87, 83, 50, 107, 
	27
};

static const char _stratego_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 15, 0, 0, 
	0, 0, 0, 0, 0, 15, 0, 0, 
	0, 0, 0, 0, 0, 0, 0
};

static const char _stratego_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 17, 0, 0, 
	0, 0, 0, 0, 0, 17, 0, 0, 
	0, 0, 0, 0, 0, 0, 0
};

static const char _stratego_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 9, 
	11, 11, 11, 11, 11, 11, 11, 11, 
	11, 11, 11, 37, 0, 0, 46, 47, 
	47, 47, 49, 49, 49, 0, 60, 61, 
	61, 61, 64, 64, 69, 69, 73
};

static const int stratego_start = 21;
static const int stratego_first_final = 21;
static const int stratego_error = 0;

static const int stratego_en_stratego_line = 29;
static const int stratego_en_stratego_entity = 21;


#line 112 "stratego.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Stratego code.
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
void parse_stratego(char *buffer, int length, int count,
                    void (*callback) (const char *lang, const char *entity,
                                      int s, int e, void *udata),
                    void *userdata
  ) {
  init

  
#line 231 "stratego.h"
	{
	cs = stratego_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 135 "stratego.rl"
  cs = (count) ? stratego_en_stratego_line : stratego_en_stratego_entity;
  
#line 242 "stratego.h"
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
	_acts = _stratego_actions + _stratego_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 13:
#line 1 "NONE"
	{ts = p;}
	break;
#line 264 "stratego.h"
		}
	}

	_widec = (*p);
	_klen = _stratego_cond_lengths[cs];
	_keys = _stratego_cond_keys + (_stratego_cond_offsets[cs]*2);
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
				switch ( _stratego_cond_spaces[_stratego_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _stratego_trans_keys + _stratego_key_offsets[cs];
	_trans = _stratego_index_offsets[cs];

	_klen = _stratego_single_lengths[cs];
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

	_klen = _stratego_range_lengths[cs];
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
	_trans = _stratego_indicies[_trans];
_eof_trans:
	cs = _stratego_trans_targs[_trans];

	if ( _stratego_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _stratego_actions + _stratego_trans_actions[_trans];
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
#line 29 "stratego.rl"
	{
    switch(entity) {
    case STRATEGO_SPACE:
      ls
      break;
    case STRATEGO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(STRATEGO_LANG)
      break;
    case NEWLINE:
      std_newline(STRATEGO_LANG)
    }
  }
	break;
	case 3:
#line 47 "stratego.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 56 "stratego.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 67 "stratego.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 86 "stratego.rl"
	{ entity = STRATEGO_SPACE; }
	break;
	case 7:
#line 89 "stratego.rl"
	{ entity = NEWLINE; }
	break;
	case 8:
#line 90 "stratego.rl"
	{ entity = STRATEGO_ANY;   }
	break;
	case 9:
#line 106 "stratego.rl"
	{ entity = STRATEGO_SPACE;   }
	break;
	case 10:
#line 107 "stratego.rl"
	{ entity = STRATEGO_COMMENT; }
	break;
	case 11:
#line 108 "stratego.rl"
	{ entity = STRATEGO_STRING;   }
	break;
	case 14:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 15:
#line 87 "stratego.rl"
	{te = p+1;}
	break;
	case 16:
#line 88 "stratego.rl"
	{te = p+1;}
	break;
	case 17:
#line 29 "stratego.rl"
	{te = p+1;{
    switch(entity) {
    case STRATEGO_SPACE:
      ls
      break;
    case STRATEGO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(STRATEGO_LANG)
      break;
    case NEWLINE:
      std_newline(STRATEGO_LANG)
    }
  }}
	break;
	case 18:
#line 29 "stratego.rl"
	{te = p+1;{
    switch(entity) {
    case STRATEGO_SPACE:
      ls
      break;
    case STRATEGO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(STRATEGO_LANG)
      break;
    case NEWLINE:
      std_newline(STRATEGO_LANG)
    }
  }}
	break;
	case 19:
#line 29 "stratego.rl"
	{te = p;p--;{
    switch(entity) {
    case STRATEGO_SPACE:
      ls
      break;
    case STRATEGO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(STRATEGO_LANG)
      break;
    case NEWLINE:
      std_newline(STRATEGO_LANG)
    }
  }}
	break;
	case 20:
#line 87 "stratego.rl"
	{te = p;p--;}
	break;
	case 21:
#line 29 "stratego.rl"
	{te = p;p--;{
    switch(entity) {
    case STRATEGO_SPACE:
      ls
      break;
    case STRATEGO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(STRATEGO_LANG)
      break;
    case NEWLINE:
      std_newline(STRATEGO_LANG)
    }
  }}
	break;
	case 22:
#line 29 "stratego.rl"
	{te = p;p--;{
    switch(entity) {
    case STRATEGO_SPACE:
      ls
      break;
    case STRATEGO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(STRATEGO_LANG)
      break;
    case NEWLINE:
      std_newline(STRATEGO_LANG)
    }
  }}
	break;
	case 23:
#line 87 "stratego.rl"
	{{p = ((te))-1;}}
	break;
	case 24:
#line 29 "stratego.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case STRATEGO_SPACE:
      ls
      break;
    case STRATEGO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(STRATEGO_LANG)
      break;
    case NEWLINE:
      std_newline(STRATEGO_LANG)
    }
  }}
	break;
	case 25:
#line 95 "stratego.rl"
	{te = p+1;{
    callback(STRATEGO_LANG, stratego_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 26:
#line 95 "stratego.rl"
	{te = p+1;{
    callback(STRATEGO_LANG, stratego_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 27:
#line 110 "stratego.rl"
	{te = p+1;}
	break;
	case 28:
#line 95 "stratego.rl"
	{te = p;p--;{
    callback(STRATEGO_LANG, stratego_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 29:
#line 95 "stratego.rl"
	{te = p;p--;{
    callback(STRATEGO_LANG, stratego_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 30:
#line 110 "stratego.rl"
	{te = p;p--;}
	break;
	case 31:
#line 95 "stratego.rl"
	{{p = ((te))-1;}{
    callback(STRATEGO_LANG, stratego_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 32:
#line 110 "stratego.rl"
	{{p = ((te))-1;}}
	break;
#line 606 "stratego.h"
		}
	}

_again:
	_acts = _stratego_actions + _stratego_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 619 "stratego.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _stratego_eof_trans[cs] > 0 ) {
		_trans = _stratego_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 137 "stratego.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(STRATEGO_LANG) }
}

#endif

/*****************************************************************************/
