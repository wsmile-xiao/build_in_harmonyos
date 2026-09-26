
#line 1 "postscript.rl"
/************************* Required for every parser *************************/
#ifndef OHCOUNT_PS_PARSER_H
#define OHCOUNT_PS_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *POSTSCRIPT_LANG = LANG_POSTSCRIPT;

// the languages entities
const char *postscript_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  POSTSCRIPT_SPACE = 0, POSTSCRIPT_COMMENT, POSTSCRIPT_STRING, POSTSCRIPT_ANY
};

/*****************************************************************************/


#line 26 "postscript.h"
static const char _postscript_actions[] = {
	0, 1, 2, 1, 3, 1, 5, 1, 
	6, 1, 7, 1, 8, 1, 14, 1, 
	15, 1, 16, 1, 17, 1, 18, 1, 
	19, 1, 20, 2, 1, 4, 2, 3, 
	12, 2, 4, 13, 2, 9, 10, 4, 
	9, 0, 4, 11
};

static const char _postscript_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	1, 1, 1
};

static const char _postscript_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 1, 0, 
	0, 0, 0
};

static const short _postscript_cond_keys[] = {
	13, 13, 0
};

static const char _postscript_cond_spaces[] = {
	0, 0
};

static const char _postscript_key_offsets[] = {
	0, 0, 4, 5, 9, 12, 15, 27, 
	29, 32, 36
};

static const short _postscript_trans_keys[] = {
	10, 41, 12, 13, 10, 32, 37, 9, 
	13, 32, 9, 13, 10, 12, 13, 9, 
	10, 12, 32, 37, 40, 269, 525, 0, 
	8, 14, 255, 9, 32, 10, 12, 13, 
	10, 41, 12, 13, 10, 0
};

static const char _postscript_single_lengths[] = {
	0, 2, 1, 2, 1, 1, 8, 2, 
	1, 2, 1
};

static const char _postscript_range_lengths[] = {
	0, 1, 0, 1, 1, 1, 2, 0, 
	1, 1, 0
};

static const char _postscript_index_offsets[] = {
	0, 0, 4, 6, 10, 13, 16, 27, 
	30, 33, 37
};

static const char _postscript_trans_targs[] = {
	6, 9, 6, 1, 6, 0, 4, 5, 
	4, 3, 4, 4, 3, 3, 3, 5, 
	7, 6, 6, 7, 8, 9, 2, 10, 
	6, 6, 0, 7, 7, 6, 6, 6, 
	8, 6, 9, 6, 1, 6, 6, 6, 
	3, 3, 6, 6, 6, 6, 0
};

static const char _postscript_trans_actions[] = {
	19, 36, 19, 0, 30, 0, 5, 7, 
	5, 21, 5, 5, 23, 25, 25, 7, 
	1, 30, 30, 1, 27, 39, 3, 3, 
	33, 33, 0, 1, 1, 13, 15, 15, 
	0, 19, 36, 19, 0, 30, 17, 19, 
	23, 25, 13, 15, 19, 17, 0
};

static const char _postscript_to_state_actions[] = {
	0, 0, 0, 9, 0, 0, 9, 0, 
	0, 0, 0
};

static const char _postscript_from_state_actions[] = {
	0, 0, 0, 11, 0, 0, 11, 0, 
	0, 0, 0
};

static const char _postscript_eof_trans[] = {
	0, 45, 0, 0, 41, 42, 0, 43, 
	44, 45, 46
};

static const int postscript_start = 3;
static const int postscript_first_final = 3;
static const int postscript_error = 0;

static const int postscript_en_postscript_line = 6;
static const int postscript_en_postscript_entity = 3;


#line 72 "postscript.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with PostScript code.
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
void parse_postscript(char *buffer, int length, int count,
             void (*callback) (const char *lang, const char *entity, int s,
                               int e, void *udata),
             void *userdata
  ) {
  init

  
#line 147 "postscript.h"
	{
	cs = postscript_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 95 "postscript.rl"
  cs = (count) ? postscript_en_postscript_line : postscript_en_postscript_entity;
  
#line 158 "postscript.h"
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
	_acts = _postscript_actions + _postscript_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = p;}
	break;
#line 180 "postscript.h"
		}
	}

	_widec = (*p);
	_klen = _postscript_cond_lengths[cs];
	_keys = _postscript_cond_keys + (_postscript_cond_offsets[cs]*2);
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
				switch ( _postscript_cond_spaces[_postscript_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _postscript_trans_keys + _postscript_key_offsets[cs];
	_trans = _postscript_index_offsets[cs];

	_klen = _postscript_single_lengths[cs];
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

	_klen = _postscript_range_lengths[cs];
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
_eof_trans:
	cs = _postscript_trans_targs[_trans];

	if ( _postscript_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _postscript_actions + _postscript_trans_actions[_trans];
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
#line 50 "postscript.rl"
	{ entity = POSTSCRIPT_SPACE; }
	break;
	case 3:
#line 53 "postscript.rl"
	{ entity = NEWLINE;         }
	break;
	case 4:
#line 54 "postscript.rl"
	{ entity = POSTSCRIPT_ANY; }
	break;
	case 5:
#line 67 "postscript.rl"
	{ entity = POSTSCRIPT_SPACE; }
	break;
	case 6:
#line 68 "postscript.rl"
	{ entity = POSTSCRIPT_COMMENT; }
	break;
	case 9:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 10:
#line 52 "postscript.rl"
	{act = 3;}
	break;
	case 11:
#line 29 "postscript.rl"
	{act = 5;}
	break;
	case 12:
#line 29 "postscript.rl"
	{te = p+1;{
  switch(entity) {
    case POSTSCRIPT_SPACE:
      ls
      break;
    case POSTSCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(POSTSCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(POSTSCRIPT_LANG)
  }
  }}
	break;
	case 13:
#line 29 "postscript.rl"
	{te = p+1;{
  switch(entity) {
    case POSTSCRIPT_SPACE:
      ls
      break;
    case POSTSCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(POSTSCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(POSTSCRIPT_LANG)
  }
  }}
	break;
	case 14:
#line 29 "postscript.rl"
	{te = p;p--;{
  switch(entity) {
    case POSTSCRIPT_SPACE:
      ls
      break;
    case POSTSCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(POSTSCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(POSTSCRIPT_LANG)
  }
  }}
	break;
	case 15:
#line 51 "postscript.rl"
	{te = p;p--;}
	break;
	case 16:
#line 29 "postscript.rl"
	{te = p;p--;{
  switch(entity) {
    case POSTSCRIPT_SPACE:
      ls
      break;
    case POSTSCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(POSTSCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(POSTSCRIPT_LANG)
  }
  }}
	break;
	case 17:
#line 1 "NONE"
	{	switch( act ) {
	case 5:
	{{p = ((te))-1;}
  switch(entity) {
    case POSTSCRIPT_SPACE:
      ls
      break;
    case POSTSCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(POSTSCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(POSTSCRIPT_LANG)
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
#line 70 "postscript.rl"
	{te = p+1;}
	break;
	case 19:
#line 59 "postscript.rl"
	{te = p;p--;{
    callback(POSTSCRIPT_LANG, postscript_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 20:
#line 59 "postscript.rl"
	{te = p;p--;{
    callback(POSTSCRIPT_LANG, postscript_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
#line 444 "postscript.h"
		}
	}

_again:
	_acts = _postscript_actions + _postscript_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 457 "postscript.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _postscript_eof_trans[cs] > 0 ) {
		_trans = _postscript_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 97 "postscript.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(POSTSCRIPT_LANG) }
}

#endif

/*****************************************************************************/
