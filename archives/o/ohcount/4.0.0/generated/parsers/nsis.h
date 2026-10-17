
#line 1 "nsis.rl"
// nsis.rl written by Chris Morgan.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_NSIS_PARSER_H
#define OHCOUNT_NSIS_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *NSIS_LANG = LANG_NSIS;

// the languages entities
const char *nsis_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  NSIS_SPACE = 0, NSIS_COMMENT, NSIS_STRING, NSIS_ANY
};

/*****************************************************************************/


#line 28 "nsis.h"
static const char _nsis_actions[] = {
	0, 1, 1, 1, 4, 1, 5, 1, 
	7, 1, 8, 1, 9, 1, 10, 1, 
	12, 1, 13, 1, 16, 1, 17, 1, 
	18, 1, 19, 1, 20, 1, 22, 1, 
	23, 1, 24, 1, 25, 1, 26, 2, 
	1, 6, 2, 3, 2, 2, 5, 14, 
	2, 6, 15, 2, 8, 21, 2, 11, 
	6, 2, 11, 8, 3, 3, 2, 1, 
	3, 11, 0, 6
};

static const char _nsis_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 2, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 4, 4, 4, 4, 4, 
	4, 4
};

static const char _nsis_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	1, 1, 0, 0, 0, 0, 0, 0, 
	0, 0, 1, 0, 0, 0, 0, 0, 
	0, 0
};

static const short _nsis_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _nsis_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _nsis_key_offsets[] = {
	0, 0, 1, 3, 8, 11, 16, 19, 
	30, 41, 53, 54, 59, 62, 63, 68, 
	71, 74, 76, 92, 94, 99, 102, 107, 
	108, 113
};

static const short _nsis_trans_keys[] = {
	42, 42, 47, 10, 34, 92, 12, 13, 
	10, 12, 13, 10, 39, 92, 12, 13, 
	10, 12, 13, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 42, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 42, 47, 269, 
	525, 0, 11, 14, 255, 10, 10, 92, 
	96, 12, 13, 10, 12, 13, 10, 32, 
	35, 47, 9, 13, 32, 9, 13, 10, 
	12, 13, 42, 47, 9, 10, 12, 32, 
	34, 35, 39, 47, 59, 96, 269, 525, 
	0, 8, 14, 255, 9, 32, 10, 34, 
	92, 12, 13, 10, 12, 13, 10, 39, 
	92, 12, 13, 42, 10, 92, 96, 12, 
	13, 10, 0
};

static const char _nsis_single_lengths[] = {
	0, 1, 2, 3, 1, 3, 1, 7, 
	7, 8, 1, 3, 1, 1, 3, 1, 
	1, 2, 12, 2, 3, 1, 3, 1, 
	3, 1
};

static const char _nsis_range_lengths[] = {
	0, 0, 0, 1, 1, 1, 1, 2, 
	2, 2, 0, 1, 1, 0, 1, 1, 
	1, 0, 2, 0, 1, 1, 1, 0, 
	1, 0
};

static const char _nsis_index_offsets[] = {
	0, 0, 2, 5, 10, 13, 18, 21, 
	31, 41, 52, 54, 59, 62, 64, 69, 
	72, 75, 78, 93, 96, 101, 104, 109, 
	111, 116
};

static const char _nsis_indicies[] = {
	2, 1, 2, 3, 1, 4, 6, 7, 
	4, 5, 4, 4, 5, 4, 6, 9, 
	4, 8, 4, 4, 8, 11, 12, 12, 
	11, 13, 14, 12, 10, 10, 4, 16, 
	17, 17, 16, 18, 19, 17, 15, 15, 
	4, 11, 12, 12, 11, 13, 20, 14, 
	12, 10, 10, 4, 12, 4, 4, 22, 
	6, 4, 21, 4, 4, 21, 23, 24, 
	26, 27, 28, 26, 25, 26, 26, 29, 
	30, 30, 27, 1, 27, 31, 33, 23, 
	23, 33, 34, 35, 36, 37, 35, 38, 
	39, 40, 32, 32, 24, 33, 33, 41, 
	42, 6, 7, 42, 5, 43, 43, 44, 
	42, 6, 9, 42, 8, 10, 42, 42, 
	22, 6, 42, 21, 23, 45, 0
};

static const char _nsis_trans_targs[] = {
	14, 1, 2, 14, 18, 3, 18, 4, 
	5, 6, 7, 7, 8, 9, 10, 7, 
	7, 8, 9, 10, 18, 11, 12, 18, 
	0, 14, 15, 16, 17, 14, 14, 14, 
	18, 19, 20, 21, 22, 23, 24, 13, 
	25, 18, 18, 18, 21, 18
};

static const char _nsis_trans_actions[] = {
	37, 9, 9, 51, 27, 0, 17, 0, 
	0, 0, 1, 0, 0, 1, 0, 60, 
	42, 42, 60, 42, 15, 0, 0, 45, 
	0, 29, 7, 9, 57, 31, 33, 35, 
	48, 3, 64, 39, 64, 54, 64, 5, 
	5, 19, 25, 21, 0, 23
};

static const char _nsis_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 11, 0, 
	0, 0, 11, 0, 0, 0, 0, 0, 
	0, 0
};

static const char _nsis_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 13, 0, 
	0, 0, 13, 0, 0, 0, 0, 0, 
	0, 0
};

static const char _nsis_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 0, 0, 30, 
	31, 32, 0, 42, 43, 44, 43, 43, 
	43, 46
};

static const int nsis_start = 14;
static const int nsis_first_final = 14;
static const int nsis_error = 0;

static const int nsis_en_nsis_line = 18;
static const int nsis_en_nsis_entity = 14;


#line 87 "nsis.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with NSIS code.
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
void parse_nsis(char *buffer, int length, int count,
                void (*callback) (const char *lang, const char *entity, int s,
                                  int e, void *udata),
                void *userdata
  ) {
  init

  
#line 199 "nsis.h"
	{
	cs = nsis_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 110 "nsis.rl"
  cs = (count) ? nsis_en_nsis_line : nsis_en_nsis_entity;
  
#line 210 "nsis.h"
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
	_acts = _nsis_actions + _nsis_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = p;}
	break;
#line 232 "nsis.h"
		}
	}

	_widec = (*p);
	_klen = _nsis_cond_lengths[cs];
	_keys = _nsis_cond_keys + (_nsis_cond_offsets[cs]*2);
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
				switch ( _nsis_cond_spaces[_nsis_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _nsis_trans_keys + _nsis_key_offsets[cs];
	_trans = _nsis_index_offsets[cs];

	_klen = _nsis_single_lengths[cs];
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

	_klen = _nsis_range_lengths[cs];
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
	_trans = _nsis_indicies[_trans];
_eof_trans:
	cs = _nsis_trans_targs[_trans];

	if ( _nsis_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _nsis_actions + _nsis_trans_actions[_trans];
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
#line 31 "nsis.rl"
	{
    switch(entity) {
    case NSIS_SPACE:
      ls
      break;
    case NSIS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NSIS_LANG)
      break;
    case NEWLINE:
      std_newline(NSIS_LANG)
    }
  }
	break;
	case 3:
#line 50 "nsis.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 64 "nsis.rl"
	{ entity = NSIS_SPACE; }
	break;
	case 5:
#line 67 "nsis.rl"
	{ entity = NEWLINE;    }
	break;
	case 6:
#line 68 "nsis.rl"
	{ entity = NSIS_ANY;   }
	break;
	case 7:
#line 82 "nsis.rl"
	{ entity = NSIS_SPACE;   }
	break;
	case 8:
#line 83 "nsis.rl"
	{ entity = NSIS_COMMENT; }
	break;
	case 11:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 12:
#line 65 "nsis.rl"
	{te = p+1;}
	break;
	case 13:
#line 66 "nsis.rl"
	{te = p+1;}
	break;
	case 14:
#line 31 "nsis.rl"
	{te = p+1;{
    switch(entity) {
    case NSIS_SPACE:
      ls
      break;
    case NSIS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NSIS_LANG)
      break;
    case NEWLINE:
      std_newline(NSIS_LANG)
    }
  }}
	break;
	case 15:
#line 31 "nsis.rl"
	{te = p+1;{
    switch(entity) {
    case NSIS_SPACE:
      ls
      break;
    case NSIS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NSIS_LANG)
      break;
    case NEWLINE:
      std_newline(NSIS_LANG)
    }
  }}
	break;
	case 16:
#line 31 "nsis.rl"
	{te = p;p--;{
    switch(entity) {
    case NSIS_SPACE:
      ls
      break;
    case NSIS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NSIS_LANG)
      break;
    case NEWLINE:
      std_newline(NSIS_LANG)
    }
  }}
	break;
	case 17:
#line 65 "nsis.rl"
	{te = p;p--;}
	break;
	case 18:
#line 31 "nsis.rl"
	{te = p;p--;{
    switch(entity) {
    case NSIS_SPACE:
      ls
      break;
    case NSIS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NSIS_LANG)
      break;
    case NEWLINE:
      std_newline(NSIS_LANG)
    }
  }}
	break;
	case 19:
#line 31 "nsis.rl"
	{te = p;p--;{
    switch(entity) {
    case NSIS_SPACE:
      ls
      break;
    case NSIS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NSIS_LANG)
      break;
    case NEWLINE:
      std_newline(NSIS_LANG)
    }
  }}
	break;
	case 20:
#line 31 "nsis.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case NSIS_SPACE:
      ls
      break;
    case NSIS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NSIS_LANG)
      break;
    case NEWLINE:
      std_newline(NSIS_LANG)
    }
  }}
	break;
	case 21:
#line 73 "nsis.rl"
	{te = p+1;{
    callback(NSIS_LANG, nsis_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 22:
#line 85 "nsis.rl"
	{te = p+1;}
	break;
	case 23:
#line 73 "nsis.rl"
	{te = p;p--;{
    callback(NSIS_LANG, nsis_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 73 "nsis.rl"
	{te = p;p--;{
    callback(NSIS_LANG, nsis_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 85 "nsis.rl"
	{te = p;p--;}
	break;
	case 26:
#line 85 "nsis.rl"
	{{p = ((te))-1;}}
	break;
#line 541 "nsis.h"
		}
	}

_again:
	_acts = _nsis_actions + _nsis_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 9:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 554 "nsis.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _nsis_eof_trans[cs] > 0 ) {
		_trans = _nsis_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 112 "nsis.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(NSIS_LANG) }
}

#endif

/*****************************************************************************/
