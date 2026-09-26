
#line 1 "fortranfixed.rl"
// fortranfixed.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_FORTRANFIXED_PARSER_H
#define OHCOUNT_FORTRANFIXED_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *FORTRANFIXED_LANG = LANG_FORTRANFIXED;

// the languages entities
const char *ffixed_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  FFIXED_SPACE = 0, FFIXED_COMMENT, FFIXED_STRING, FFIXED_ANY
};

/*****************************************************************************/


#line 28 "fortranfixed.h"
static const char _fortranfixed_actions[] = {
	0, 1, 2, 1, 3, 1, 5, 1, 
	6, 1, 7, 1, 8, 1, 14, 1, 
	15, 1, 16, 1, 17, 1, 18, 1, 
	19, 1, 20, 2, 1, 4, 2, 3, 
	12, 2, 4, 13, 2, 9, 10, 4, 
	9, 0, 4, 11
};

static const char _fortranfixed_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 1, 1, 1, 1
};

static const char _fortranfixed_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	0, 0, 0, 0, 0
};

static const short _fortranfixed_cond_keys[] = {
	13, 13, 0
};

static const char _fortranfixed_cond_spaces[] = {
	0, 0
};

static const char _fortranfixed_key_offsets[] = {
	0, 0, 4, 8, 9, 13, 16, 19, 
	32, 34, 38, 42, 45
};

static const short _fortranfixed_trans_keys[] = {
	10, 34, 12, 13, 10, 39, 12, 13, 
	10, 32, 67, 9, 13, 32, 9, 13, 
	10, 12, 13, 9, 10, 12, 32, 34, 
	39, 67, 269, 525, 0, 8, 14, 255, 
	9, 32, 10, 34, 12, 13, 10, 39, 
	12, 13, 10, 12, 13, 10, 0
};

static const char _fortranfixed_single_lengths[] = {
	0, 2, 2, 1, 2, 1, 1, 9, 
	2, 2, 2, 1, 1
};

static const char _fortranfixed_range_lengths[] = {
	0, 1, 1, 0, 1, 1, 1, 2, 
	0, 1, 1, 1, 0
};

static const char _fortranfixed_index_offsets[] = {
	0, 0, 4, 8, 10, 14, 17, 20, 
	32, 35, 39, 43, 46
};

static const char _fortranfixed_indicies[] = {
	0, 2, 0, 1, 0, 4, 0, 3, 
	5, 6, 8, 9, 8, 7, 8, 8, 
	10, 11, 11, 9, 13, 5, 5, 13, 
	14, 15, 16, 17, 18, 12, 12, 6, 
	13, 13, 19, 0, 2, 0, 1, 0, 
	4, 0, 3, 20, 20, 21, 5, 22, 
	0
};

static const char _fortranfixed_trans_targs[] = {
	7, 1, 9, 2, 10, 7, 0, 4, 
	5, 6, 4, 4, 7, 8, 9, 10, 
	11, 3, 12, 7, 7, 11, 7
};

static const char _fortranfixed_trans_actions[] = {
	19, 0, 36, 0, 36, 30, 0, 21, 
	5, 7, 23, 25, 33, 1, 39, 39, 
	27, 3, 3, 13, 15, 0, 17
};

static const char _fortranfixed_to_state_actions[] = {
	0, 0, 0, 0, 9, 0, 0, 9, 
	0, 0, 0, 0, 0
};

static const char _fortranfixed_from_state_actions[] = {
	0, 0, 0, 0, 11, 0, 0, 11, 
	0, 0, 0, 0, 0
};

static const char _fortranfixed_eof_trans[] = {
	0, 1, 1, 0, 0, 11, 12, 0, 
	20, 1, 1, 21, 23
};

static const int fortranfixed_start = 4;
static const int fortranfixed_first_final = 4;
static const int fortranfixed_error = 0;

static const int fortranfixed_en_ffixed_line = 7;
static const int fortranfixed_en_ffixed_entity = 4;


#line 76 "fortranfixed.rl"


/* Parses a string buffer with Fortran Fixedform code.
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
void parse_fortranfixed(char *buffer, int length, int count,
                        void (*callback) (const char *lang, const char *entity,
                                          int s, int e, void *udata),
                        void *userdata
  ) {
  init

  
#line 152 "fortranfixed.h"
	{
	cs = fortranfixed_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 97 "fortranfixed.rl"
  cs = (count) ? fortranfixed_en_ffixed_line : fortranfixed_en_ffixed_entity;
  
#line 163 "fortranfixed.h"
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
	_acts = _fortranfixed_actions + _fortranfixed_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = p;}
	break;
#line 185 "fortranfixed.h"
		}
	}

	_widec = (*p);
	_klen = _fortranfixed_cond_lengths[cs];
	_keys = _fortranfixed_cond_keys + (_fortranfixed_cond_offsets[cs]*2);
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
				switch ( _fortranfixed_cond_spaces[_fortranfixed_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _fortranfixed_trans_keys + _fortranfixed_key_offsets[cs];
	_trans = _fortranfixed_index_offsets[cs];

	_klen = _fortranfixed_single_lengths[cs];
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

	_klen = _fortranfixed_range_lengths[cs];
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
	_trans = _fortranfixed_indicies[_trans];
_eof_trans:
	cs = _fortranfixed_trans_targs[_trans];

	if ( _fortranfixed_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _fortranfixed_actions + _fortranfixed_trans_actions[_trans];
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
#line 54 "fortranfixed.rl"
	{ entity = FFIXED_SPACE; }
	break;
	case 3:
#line 57 "fortranfixed.rl"
	{ entity = NEWLINE;      }
	break;
	case 4:
#line 58 "fortranfixed.rl"
	{ entity = FFIXED_ANY;   }
	break;
	case 5:
#line 71 "fortranfixed.rl"
	{ entity = FFIXED_SPACE;   }
	break;
	case 6:
#line 72 "fortranfixed.rl"
	{ entity = FFIXED_COMMENT; }
	break;
	case 9:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 10:
#line 56 "fortranfixed.rl"
	{act = 3;}
	break;
	case 11:
#line 31 "fortranfixed.rl"
	{act = 5;}
	break;
	case 12:
#line 31 "fortranfixed.rl"
	{te = p+1;{
    switch(entity) {
    case FFIXED_SPACE:
      ls
      break;
    case FFIXED_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTRANFIXED_LANG)
      break;
    case NEWLINE:
      std_newline(FORTRANFIXED_LANG)
    }
  }}
	break;
	case 13:
#line 31 "fortranfixed.rl"
	{te = p+1;{
    switch(entity) {
    case FFIXED_SPACE:
      ls
      break;
    case FFIXED_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTRANFIXED_LANG)
      break;
    case NEWLINE:
      std_newline(FORTRANFIXED_LANG)
    }
  }}
	break;
	case 14:
#line 31 "fortranfixed.rl"
	{te = p;p--;{
    switch(entity) {
    case FFIXED_SPACE:
      ls
      break;
    case FFIXED_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTRANFIXED_LANG)
      break;
    case NEWLINE:
      std_newline(FORTRANFIXED_LANG)
    }
  }}
	break;
	case 15:
#line 55 "fortranfixed.rl"
	{te = p;p--;}
	break;
	case 16:
#line 31 "fortranfixed.rl"
	{te = p;p--;{
    switch(entity) {
    case FFIXED_SPACE:
      ls
      break;
    case FFIXED_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTRANFIXED_LANG)
      break;
    case NEWLINE:
      std_newline(FORTRANFIXED_LANG)
    }
  }}
	break;
	case 17:
#line 1 "NONE"
	{	switch( act ) {
	case 5:
	{{p = ((te))-1;}
    switch(entity) {
    case FFIXED_SPACE:
      ls
      break;
    case FFIXED_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTRANFIXED_LANG)
      break;
    case NEWLINE:
      std_newline(FORTRANFIXED_LANG)
    }
  }
	break;
	default:
	{{p = ((te))-1;}}
	break;
	}
	}
	break;
	case 18:
#line 74 "fortranfixed.rl"
	{te = p+1;}
	break;
	case 19:
#line 63 "fortranfixed.rl"
	{te = p;p--;{
    callback(FORTRANFIXED_LANG, ffixed_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 20:
#line 63 "fortranfixed.rl"
	{te = p;p--;{
    callback(FORTRANFIXED_LANG, ffixed_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
#line 450 "fortranfixed.h"
		}
	}

_again:
	_acts = _fortranfixed_actions + _fortranfixed_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 463 "fortranfixed.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _fortranfixed_eof_trans[cs] > 0 ) {
		_trans = _fortranfixed_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 99 "fortranfixed.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(FORTRANFIXED_LANG) }
}

#endif
