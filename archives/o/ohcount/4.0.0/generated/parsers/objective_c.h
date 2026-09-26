
#line 1 "objective_c.rl"
// objective_c.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_OBJECTIVE_C_PARSER_H
#define OHCOUNT_OBJECTIVE_C_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *OBJC_LANG = LANG_OBJECTIVE_C;

// the languages entities
const char *objc_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  OBJC_SPACE = 0, OBJC_COMMENT, OBJC_STRING, OBJC_ANY,
};

/*****************************************************************************/


#line 28 "objective_c.h"
static const char _objective_c_actions[] = {
	0, 1, 1, 1, 5, 1, 6, 1, 
	8, 1, 9, 1, 10, 1, 11, 1, 
	13, 1, 14, 1, 17, 1, 18, 1, 
	19, 1, 20, 1, 21, 1, 22, 1, 
	24, 1, 25, 1, 26, 1, 27, 1, 
	28, 1, 29, 2, 3, 2, 2, 4, 
	2, 2, 6, 15, 2, 7, 16, 2, 
	9, 23, 2, 12, 1, 2, 12, 7, 
	2, 12, 9, 3, 3, 2, 1, 3, 
	3, 2, 18, 3, 4, 2, 1, 3, 
	12, 0, 7, 4, 12, 3, 2, 1
	
};

static const char _objective_c_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 1, 2, 3, 3, 3, 3, 3, 
	3, 3, 3, 4, 4, 5, 5, 5, 
	5, 5, 5, 6, 6, 6
};

static const char _objective_c_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 1, 1, 0, 0, 0, 0, 0, 
	0, 0, 1, 0, 1, 0, 0, 0, 
	0, 0, 1, 0, 0, 0
};

static const short _objective_c_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 0
};

static const char _objective_c_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0
};

static const char _objective_c_key_offsets[] = {
	0, 0, 1, 3, 4, 9, 12, 17, 
	20, 31, 42, 54, 55, 56, 57, 61, 
	64, 66, 70, 77, 80, 93, 95, 100, 
	105, 107, 113, 124, 130, 136
};

static const short _objective_c_trans_keys[] = {
	42, 42, 47, 10, 10, 34, 92, 12, 
	13, 10, 12, 13, 10, 39, 92, 12, 
	13, 10, 12, 13, 9, 10, 12, 32, 
	42, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 42, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 42, 47, 
	269, 525, 0, 11, 14, 255, 10, 10, 
	10, 32, 47, 9, 13, 32, 9, 13, 
	42, 47, 10, 92, 12, 13, 92, 269, 
	525, 0, 12, 14, 255, 92, 12, 13, 
	9, 10, 12, 32, 34, 39, 47, 269, 
	525, 0, 8, 14, 255, 9, 32, 10, 
	34, 92, 12, 13, 10, 39, 92, 12, 
	13, 42, 47, 9, 10, 32, 92, 12, 
	13, 9, 10, 12, 32, 92, 269, 525, 
	0, 11, 14, 255, 9, 10, 32, 92, 
	12, 13, 9, 10, 32, 92, 12, 13, 
	10, 0
};

static const char _objective_c_single_lengths[] = {
	0, 1, 2, 1, 3, 1, 3, 1, 
	7, 7, 8, 1, 1, 1, 2, 1, 
	2, 2, 3, 1, 9, 2, 3, 3, 
	2, 4, 7, 4, 4, 1
};

static const char _objective_c_range_lengths[] = {
	0, 0, 0, 0, 1, 1, 1, 1, 
	2, 2, 2, 0, 0, 0, 1, 1, 
	0, 1, 2, 1, 2, 0, 1, 1, 
	0, 1, 2, 1, 1, 0
};

static const char _objective_c_index_offsets[] = {
	0, 0, 2, 5, 7, 12, 15, 20, 
	23, 33, 43, 54, 56, 58, 60, 64, 
	67, 70, 74, 80, 83, 95, 98, 103, 
	108, 111, 117, 127, 133, 139
};

static const char _objective_c_indicies[] = {
	2, 1, 2, 3, 1, 5, 4, 6, 
	8, 9, 6, 7, 6, 6, 7, 6, 
	8, 11, 6, 10, 6, 6, 10, 13, 
	14, 14, 13, 15, 16, 14, 12, 12, 
	6, 18, 19, 19, 18, 20, 21, 19, 
	17, 17, 6, 13, 14, 14, 13, 15, 
	22, 16, 14, 12, 12, 6, 14, 6, 
	24, 23, 25, 26, 28, 29, 28, 27, 
	28, 28, 30, 1, 5, 31, 32, 33, 
	32, 5, 33, 34, 35, 5, 5, 32, 
	33, 32, 5, 37, 25, 25, 37, 38, 
	39, 40, 41, 42, 36, 36, 26, 37, 
	37, 43, 44, 8, 9, 44, 7, 44, 
	8, 11, 44, 10, 12, 45, 44, 47, 
	46, 47, 48, 46, 45, 47, 24, 24, 
	47, 48, 49, 50, 45, 45, 46, 53, 
	51, 53, 54, 51, 52, 53, 24, 53, 
	54, 51, 52, 25, 55, 0
};

static const char _objective_c_trans_targs[] = {
	14, 1, 2, 14, 14, 17, 20, 4, 
	20, 5, 6, 7, 8, 8, 9, 10, 
	11, 8, 8, 9, 10, 11, 20, 20, 
	27, 20, 0, 14, 15, 16, 14, 14, 
	14, 18, 3, 19, 20, 21, 22, 23, 
	24, 13, 29, 20, 20, 25, 20, 25, 
	26, 12, 28, 20, 25, 25, 26, 20
};

static const char _objective_c_trans_actions[] = {
	41, 9, 9, 55, 39, 9, 29, 0, 
	17, 0, 0, 0, 1, 0, 0, 1, 
	0, 75, 46, 46, 75, 46, 15, 27, 
	0, 49, 0, 31, 7, 64, 33, 37, 
	35, 64, 9, 9, 52, 3, 79, 79, 
	61, 5, 5, 19, 25, 1, 21, 0, 
	58, 0, 0, 71, 67, 43, 83, 23
};

static const char _objective_c_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 11, 0, 
	0, 0, 0, 0, 11, 0, 0, 0, 
	0, 0, 0, 0, 0, 0
};

static const char _objective_c_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 13, 0, 
	0, 0, 0, 0, 13, 0, 0, 0, 
	0, 0, 0, 0, 0, 0
};

static const char _objective_c_eof_trans[] = {
	0, 1, 1, 5, 7, 7, 7, 7, 
	7, 7, 7, 7, 24, 0, 0, 31, 
	32, 33, 33, 33, 0, 44, 45, 45, 
	45, 47, 47, 52, 52, 56
};

static const int objective_c_start = 14;
static const int objective_c_first_final = 14;
static const int objective_c_error = 0;

static const int objective_c_en_objc_line = 20;
static const int objective_c_en_objc_entity = 14;


#line 93 "objective_c.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Objective C code.
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
void parse_objective_c(char *buffer, int length, int count,
                       void (*callback) (const char *lang, const char *entity,
                                         int s, int e, void *udata),
                       void *userdata
  ) {
  init

  
#line 210 "objective_c.h"
	{
	cs = objective_c_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 116 "objective_c.rl"
  cs = (count) ? objective_c_en_objc_line : objective_c_en_objc_entity;
  
#line 221 "objective_c.h"
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
	_acts = _objective_c_actions + _objective_c_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = p;}
	break;
#line 243 "objective_c.h"
		}
	}

	_widec = (*p);
	_klen = _objective_c_cond_lengths[cs];
	_keys = _objective_c_cond_keys + (_objective_c_cond_offsets[cs]*2);
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
				switch ( _objective_c_cond_spaces[_objective_c_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _objective_c_trans_keys + _objective_c_key_offsets[cs];
	_trans = _objective_c_index_offsets[cs];

	_klen = _objective_c_single_lengths[cs];
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

	_klen = _objective_c_range_lengths[cs];
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
	_trans = _objective_c_indicies[_trans];
_eof_trans:
	cs = _objective_c_trans_targs[_trans];

	if ( _objective_c_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _objective_c_actions + _objective_c_trans_actions[_trans];
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
#line 31 "objective_c.rl"
	{
    switch(entity) {
    case OBJC_SPACE:
      ls
      break;
    case OBJC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBJC_LANG)
      break;
    case NEWLINE:
      std_newline(OBJC_LANG)
    }
  }
	break;
	case 3:
#line 49 "objective_c.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 57 "objective_c.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 70 "objective_c.rl"
	{ entity = OBJC_SPACE; }
	break;
	case 6:
#line 73 "objective_c.rl"
	{ entity = NEWLINE;    }
	break;
	case 7:
#line 74 "objective_c.rl"
	{ entity = OBJC_ANY;   }
	break;
	case 8:
#line 88 "objective_c.rl"
	{ entity = OBJC_SPACE;   }
	break;
	case 9:
#line 89 "objective_c.rl"
	{ entity = OBJC_COMMENT; }
	break;
	case 12:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 13:
#line 71 "objective_c.rl"
	{te = p+1;}
	break;
	case 14:
#line 72 "objective_c.rl"
	{te = p+1;}
	break;
	case 15:
#line 31 "objective_c.rl"
	{te = p+1;{
    switch(entity) {
    case OBJC_SPACE:
      ls
      break;
    case OBJC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBJC_LANG)
      break;
    case NEWLINE:
      std_newline(OBJC_LANG)
    }
  }}
	break;
	case 16:
#line 31 "objective_c.rl"
	{te = p+1;{
    switch(entity) {
    case OBJC_SPACE:
      ls
      break;
    case OBJC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBJC_LANG)
      break;
    case NEWLINE:
      std_newline(OBJC_LANG)
    }
  }}
	break;
	case 17:
#line 31 "objective_c.rl"
	{te = p;p--;{
    switch(entity) {
    case OBJC_SPACE:
      ls
      break;
    case OBJC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBJC_LANG)
      break;
    case NEWLINE:
      std_newline(OBJC_LANG)
    }
  }}
	break;
	case 18:
#line 71 "objective_c.rl"
	{te = p;p--;}
	break;
	case 19:
#line 31 "objective_c.rl"
	{te = p;p--;{
    switch(entity) {
    case OBJC_SPACE:
      ls
      break;
    case OBJC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBJC_LANG)
      break;
    case NEWLINE:
      std_newline(OBJC_LANG)
    }
  }}
	break;
	case 20:
#line 31 "objective_c.rl"
	{te = p;p--;{
    switch(entity) {
    case OBJC_SPACE:
      ls
      break;
    case OBJC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBJC_LANG)
      break;
    case NEWLINE:
      std_newline(OBJC_LANG)
    }
  }}
	break;
	case 21:
#line 71 "objective_c.rl"
	{{p = ((te))-1;}}
	break;
	case 22:
#line 31 "objective_c.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case OBJC_SPACE:
      ls
      break;
    case OBJC_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBJC_LANG)
      break;
    case NEWLINE:
      std_newline(OBJC_LANG)
    }
  }}
	break;
	case 23:
#line 79 "objective_c.rl"
	{te = p+1;{
    callback(OBJC_LANG, objc_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 91 "objective_c.rl"
	{te = p+1;}
	break;
	case 25:
#line 79 "objective_c.rl"
	{te = p;p--;{
    callback(OBJC_LANG, objc_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 26:
#line 79 "objective_c.rl"
	{te = p;p--;{
    callback(OBJC_LANG, objc_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 27:
#line 91 "objective_c.rl"
	{te = p;p--;}
	break;
	case 28:
#line 79 "objective_c.rl"
	{{p = ((te))-1;}{
    callback(OBJC_LANG, objc_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 29:
#line 91 "objective_c.rl"
	{{p = ((te))-1;}}
	break;
#line 566 "objective_c.h"
		}
	}

_again:
	_acts = _objective_c_actions + _objective_c_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 579 "objective_c.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _objective_c_eof_trans[cs] > 0 ) {
		_trans = _objective_c_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 118 "objective_c.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(OBJC_LANG) }
}

#endif

/*****************************************************************************/
