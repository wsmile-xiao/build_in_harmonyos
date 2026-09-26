
#line 1 "matlab.rl"
// matlab.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_MATLAB_PARSER_H
#define OHCOUNT_MATLAB_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *MATLAB_LANG = LANG_MATLAB;

// the languages entities
const char *matlab_entities[] = {
  "space", "comment", "string", "any",
};

// constants associated with the entities
enum {
  MATLAB_SPACE = 0, MATLAB_COMMENT, MATLAB_STRING, MATLAB_ANY
};

/*****************************************************************************/


#line 28 "matlab.h"
static const char _matlab_actions[] = {
	0, 1, 0, 1, 1, 1, 5, 1, 
	6, 1, 9, 1, 10, 1, 11, 1, 
	12, 1, 14, 1, 15, 1, 18, 1, 
	19, 1, 20, 1, 21, 1, 22, 1, 
	24, 1, 25, 1, 26, 1, 27, 1, 
	28, 2, 3, 1, 2, 4, 2, 2, 
	6, 16, 2, 7, 17, 2, 8, 10, 
	2, 10, 23, 2, 13, 7, 2, 13, 
	10, 3, 4, 2, 0, 3, 13, 0, 
	7
};

static const char _matlab_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 2, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 4, 4, 
	4, 4, 4, 4, 4
};

static const char _matlab_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	1, 1, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 1, 0, 0, 
	0, 0, 0, 0, 0
};

static const short _matlab_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _matlab_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _matlab_key_offsets[] = {
	0, 0, 1, 3, 4, 5, 10, 13, 
	24, 35, 47, 48, 53, 56, 57, 58, 
	59, 64, 67, 68, 71, 72, 86, 88, 
	93, 94, 97, 102, 103
};

static const short _matlab_trans_keys[] = {
	37, 37, 125, 46, 123, 10, 34, 92, 
	12, 13, 10, 12, 13, 9, 10, 12, 
	32, 37, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 37, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 37, 
	125, 269, 525, 0, 11, 14, 255, 10, 
	10, 39, 92, 12, 13, 10, 12, 13, 
	46, 123, 10, 32, 37, 46, 9, 13, 
	32, 9, 13, 123, 10, 12, 13, 46, 
	9, 10, 12, 32, 34, 37, 39, 46, 
	269, 525, 0, 8, 14, 255, 9, 32, 
	10, 34, 92, 12, 13, 123, 10, 12, 
	13, 10, 39, 92, 12, 13, 46, 10, 
	0
};

static const char _matlab_single_lengths[] = {
	0, 1, 2, 1, 1, 3, 1, 7, 
	7, 8, 1, 3, 1, 1, 1, 1, 
	3, 1, 1, 1, 1, 10, 2, 3, 
	1, 1, 3, 1, 1
};

static const char _matlab_range_lengths[] = {
	0, 0, 0, 0, 0, 1, 1, 2, 
	2, 2, 0, 1, 1, 0, 0, 0, 
	1, 1, 0, 1, 0, 2, 0, 1, 
	0, 1, 1, 0, 0
};

static const char _matlab_index_offsets[] = {
	0, 0, 2, 5, 7, 9, 14, 17, 
	27, 37, 48, 50, 55, 58, 60, 62, 
	64, 69, 72, 74, 77, 79, 92, 95, 
	100, 102, 105, 110, 112
};

static const char _matlab_indicies[] = {
	2, 1, 2, 3, 1, 4, 0, 0, 
	5, 6, 8, 9, 6, 7, 6, 6, 
	7, 11, 12, 12, 11, 13, 14, 12, 
	10, 10, 6, 16, 17, 17, 16, 18, 
	19, 17, 15, 15, 6, 11, 12, 12, 
	11, 13, 20, 14, 12, 10, 10, 6, 
	12, 6, 6, 8, 22, 6, 21, 6, 
	6, 21, 23, 6, 6, 24, 25, 26, 
	28, 29, 30, 28, 27, 28, 28, 31, 
	1, 5, 33, 33, 34, 35, 32, 37, 
	25, 25, 37, 38, 39, 40, 41, 42, 
	43, 36, 36, 26, 37, 37, 44, 45, 
	8, 9, 45, 7, 46, 24, 47, 47, 
	48, 45, 8, 22, 45, 21, 49, 45, 
	25, 50, 0
};

static const char _matlab_trans_targs[] = {
	16, 1, 2, 16, 4, 19, 21, 5, 
	21, 6, 7, 7, 8, 9, 10, 7, 
	7, 8, 9, 10, 21, 11, 12, 14, 
	25, 21, 0, 16, 17, 18, 20, 16, 
	16, 16, 19, 3, 21, 22, 23, 24, 
	26, 27, 15, 28, 21, 21, 7, 21, 
	25, 13, 21
};

static const char _matlab_trans_actions[] = {
	39, 11, 11, 56, 11, 53, 29, 0, 
	19, 0, 1, 0, 0, 1, 0, 65, 
	44, 44, 65, 44, 17, 0, 0, 0, 
	41, 47, 0, 31, 9, 62, 62, 33, 
	37, 35, 11, 11, 50, 5, 69, 59, 
	69, 59, 7, 7, 21, 27, 3, 23, 
	0, 0, 25
};

static const char _matlab_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	13, 0, 0, 0, 0, 13, 0, 0, 
	0, 0, 0, 0, 0
};

static const char _matlab_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	15, 0, 0, 0, 0, 15, 0, 0, 
	0, 0, 0, 0, 0
};

static const char _matlab_eof_trans[] = {
	0, 1, 1, 1, 1, 7, 7, 7, 
	7, 7, 7, 7, 7, 7, 7, 0, 
	0, 32, 33, 34, 33, 0, 45, 46, 
	46, 48, 46, 46, 51
};

static const int matlab_start = 16;
static const int matlab_first_final = 16;
static const int matlab_error = 0;

static const int matlab_en_matlab_line = 21;
static const int matlab_en_matlab_entity = 16;


#line 91 "matlab.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with MATLAB code.
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
void parse_matlab(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  init

  
#line 201 "matlab.h"
	{
	cs = matlab_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 114 "matlab.rl"
  cs = (count) ? matlab_en_matlab_line : matlab_en_matlab_entity;
  
#line 212 "matlab.h"
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
	_acts = _matlab_actions + _matlab_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = p;}
	break;
#line 234 "matlab.h"
		}
	}

	_widec = (*p);
	_klen = _matlab_cond_lengths[cs];
	_keys = _matlab_cond_keys + (_matlab_cond_offsets[cs]*2);
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
				switch ( _matlab_cond_spaces[_matlab_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _matlab_trans_keys + _matlab_key_offsets[cs];
	_trans = _matlab_index_offsets[cs];

	_klen = _matlab_single_lengths[cs];
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

	_klen = _matlab_range_lengths[cs];
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
	_trans = _matlab_indicies[_trans];
_eof_trans:
	cs = _matlab_trans_targs[_trans];

	if ( _matlab_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _matlab_actions + _matlab_trans_actions[_trans];
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
#line 31 "matlab.rl"
	{
    switch(entity) {
    case MATLAB_SPACE:
      ls
      break;
    case MATLAB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MATLAB_LANG)
      break;
    case NEWLINE:
      std_newline(MATLAB_LANG)
    }
  }
	break;
	case 3:
#line 48 "matlab.rl"
	{ p--; }
	break;
	case 4:
#line 51 "matlab.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 66 "matlab.rl"
	{ entity = MATLAB_SPACE; }
	break;
	case 6:
#line 69 "matlab.rl"
	{ entity = NEWLINE;      }
	break;
	case 7:
#line 70 "matlab.rl"
	{ entity = MATLAB_ANY;   }
	break;
	case 8:
#line 80 "matlab.rl"
	{ p--; }
	break;
	case 9:
#line 86 "matlab.rl"
	{ entity = MATLAB_SPACE;   }
	break;
	case 10:
#line 87 "matlab.rl"
	{ entity = MATLAB_COMMENT; }
	break;
	case 13:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 14:
#line 67 "matlab.rl"
	{te = p+1;}
	break;
	case 15:
#line 68 "matlab.rl"
	{te = p+1;}
	break;
	case 16:
#line 31 "matlab.rl"
	{te = p+1;{
    switch(entity) {
    case MATLAB_SPACE:
      ls
      break;
    case MATLAB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MATLAB_LANG)
      break;
    case NEWLINE:
      std_newline(MATLAB_LANG)
    }
  }}
	break;
	case 17:
#line 31 "matlab.rl"
	{te = p+1;{
    switch(entity) {
    case MATLAB_SPACE:
      ls
      break;
    case MATLAB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MATLAB_LANG)
      break;
    case NEWLINE:
      std_newline(MATLAB_LANG)
    }
  }}
	break;
	case 18:
#line 31 "matlab.rl"
	{te = p;p--;{
    switch(entity) {
    case MATLAB_SPACE:
      ls
      break;
    case MATLAB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MATLAB_LANG)
      break;
    case NEWLINE:
      std_newline(MATLAB_LANG)
    }
  }}
	break;
	case 19:
#line 67 "matlab.rl"
	{te = p;p--;}
	break;
	case 20:
#line 31 "matlab.rl"
	{te = p;p--;{
    switch(entity) {
    case MATLAB_SPACE:
      ls
      break;
    case MATLAB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MATLAB_LANG)
      break;
    case NEWLINE:
      std_newline(MATLAB_LANG)
    }
  }}
	break;
	case 21:
#line 31 "matlab.rl"
	{te = p;p--;{
    switch(entity) {
    case MATLAB_SPACE:
      ls
      break;
    case MATLAB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MATLAB_LANG)
      break;
    case NEWLINE:
      std_newline(MATLAB_LANG)
    }
  }}
	break;
	case 22:
#line 31 "matlab.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case MATLAB_SPACE:
      ls
      break;
    case MATLAB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MATLAB_LANG)
      break;
    case NEWLINE:
      std_newline(MATLAB_LANG)
    }
  }}
	break;
	case 23:
#line 75 "matlab.rl"
	{te = p+1;{
    callback(MATLAB_LANG, matlab_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 24:
#line 89 "matlab.rl"
	{te = p+1;}
	break;
	case 25:
#line 75 "matlab.rl"
	{te = p;p--;{
    callback(MATLAB_LANG, matlab_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 26:
#line 75 "matlab.rl"
	{te = p;p--;{
    callback(MATLAB_LANG, matlab_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 27:
#line 89 "matlab.rl"
	{te = p;p--;}
	break;
	case 28:
#line 89 "matlab.rl"
	{{p = ((te))-1;}}
	break;
#line 554 "matlab.h"
		}
	}

_again:
	_acts = _matlab_actions + _matlab_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 567 "matlab.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _matlab_eof_trans[cs] > 0 ) {
		_trans = _matlab_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 116 "matlab.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(MATLAB_LANG) }
}

#endif

/*****************************************************************************/
