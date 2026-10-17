
#line 1 "tex.rl"
// tex.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_TEX_PARSER_H
#define OHCOUNT_TEX_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *TEX_LANG = LANG_TEX;

// the languages entities
const char *tex_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  TEX_SPACE = 0, TEX_COMMENT, TEX_STRING, TEX_ANY
};

/*****************************************************************************/


#line 28 "tex.h"
static const char _tex_actions[] = {
	0, 1, 1, 1, 2, 1, 4, 1, 
	5, 1, 6, 1, 7, 1, 10, 1, 
	11, 1, 12, 1, 13, 1, 14, 1, 
	15, 2, 0, 3, 2, 2, 8, 2, 
	3, 9
};

static const char _tex_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 1, 1, 
	1
};

static const char _tex_cond_lengths[] = {
	0, 0, 0, 0, 0, 1, 0, 0, 
	0
};

static const short _tex_cond_keys[] = {
	13, 13, 0
};

static const char _tex_cond_spaces[] = {
	0, 0
};

static const char _tex_key_offsets[] = {
	0, 0, 1, 5, 8, 11, 22, 24, 
	27
};

static const short _tex_trans_keys[] = {
	10, 32, 37, 9, 13, 32, 9, 13, 
	10, 12, 13, 9, 10, 12, 32, 37, 
	269, 525, 0, 8, 14, 255, 9, 32, 
	10, 12, 13, 10, 0
};

static const char _tex_single_lengths[] = {
	0, 1, 2, 1, 1, 7, 2, 1, 
	1
};

static const char _tex_range_lengths[] = {
	0, 0, 1, 1, 1, 2, 0, 1, 
	0
};

static const char _tex_index_offsets[] = {
	0, 0, 2, 6, 9, 12, 22, 25, 
	28
};

static const char _tex_trans_targs[] = {
	5, 0, 3, 4, 3, 2, 3, 3, 
	2, 2, 2, 4, 6, 5, 5, 6, 
	7, 1, 8, 5, 5, 0, 6, 6, 
	5, 5, 5, 7, 5, 5, 2, 2, 
	5, 5, 5, 0
};

static const char _tex_trans_actions[] = {
	28, 0, 5, 7, 5, 19, 5, 5, 
	21, 23, 23, 7, 1, 28, 28, 1, 
	25, 3, 3, 31, 31, 0, 1, 1, 
	13, 15, 15, 0, 28, 17, 21, 23, 
	13, 15, 17, 0
};

static const char _tex_to_state_actions[] = {
	0, 0, 9, 0, 0, 9, 0, 0, 
	0
};

static const char _tex_from_state_actions[] = {
	0, 0, 11, 0, 0, 11, 0, 0, 
	0
};

static const char _tex_eof_trans[] = {
	0, 0, 0, 31, 32, 0, 33, 34, 
	35
};

static const int tex_start = 2;
static const int tex_first_final = 2;
static const int tex_error = 0;

static const int tex_en_tex_line = 5;
static const int tex_en_tex_entity = 2;


#line 70 "tex.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Tex markup.
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
void parse_tex(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 145 "tex.h"
	{
	cs = tex_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 93 "tex.rl"
  cs = (count) ? tex_en_tex_line : tex_en_tex_entity;
  
#line 156 "tex.h"
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
	_acts = _tex_actions + _tex_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = p;}
	break;
#line 178 "tex.h"
		}
	}

	_widec = (*p);
	_klen = _tex_cond_lengths[cs];
	_keys = _tex_cond_keys + (_tex_cond_offsets[cs]*2);
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
				switch ( _tex_cond_spaces[_tex_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _tex_trans_keys + _tex_key_offsets[cs];
	_trans = _tex_index_offsets[cs];

	_klen = _tex_single_lengths[cs];
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

	_klen = _tex_range_lengths[cs];
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
	cs = _tex_trans_targs[_trans];

	if ( _tex_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _tex_actions + _tex_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 1:
#line 50 "tex.rl"
	{ entity = TEX_SPACE; }
	break;
	case 2:
#line 52 "tex.rl"
	{ entity = NEWLINE;   }
	break;
	case 3:
#line 53 "tex.rl"
	{ entity = TEX_ANY;   }
	break;
	case 4:
#line 65 "tex.rl"
	{ entity = TEX_SPACE;   }
	break;
	case 5:
#line 66 "tex.rl"
	{ entity = TEX_COMMENT; }
	break;
	case 8:
#line 31 "tex.rl"
	{te = p+1;{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 9:
#line 31 "tex.rl"
	{te = p+1;{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 10:
#line 31 "tex.rl"
	{te = p;p--;{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 11:
#line 51 "tex.rl"
	{te = p;p--;}
	break;
	case 12:
#line 31 "tex.rl"
	{te = p;p--;{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 13:
#line 68 "tex.rl"
	{te = p+1;}
	break;
	case 14:
#line 58 "tex.rl"
	{te = p;p--;{
    callback(TEX_LANG, tex_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 15:
#line 58 "tex.rl"
	{te = p;p--;{
    callback(TEX_LANG, tex_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
#line 395 "tex.h"
		}
	}

_again:
	_acts = _tex_actions + _tex_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 6:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 408 "tex.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _tex_eof_trans[cs] > 0 ) {
		_trans = _tex_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 95 "tex.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(TEX_LANG) }
}

#endif

/*****************************************************************************/
