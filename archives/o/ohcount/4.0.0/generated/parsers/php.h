
#line 1 "php.rl"
// php.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_PHP_PARSER_H
#define OHCOUNT_PHP_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *PHP_LANG = LANG_PHP;

// the languages entities
const char *php_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  PHP_SPACE = 0, PHP_COMMENT, PHP_STRING, PHP_ANY
};

/*****************************************************************************/


#line 28 "php.h"
static const char _php_actions[] = {
	0, 1, 2, 1, 3, 1, 8, 1, 
	9, 1, 11, 1, 12, 1, 13, 1, 
	14, 1, 16, 1, 20, 1, 21, 1, 
	22, 1, 23, 1, 24, 1, 26, 1, 
	27, 1, 28, 1, 29, 1, 30, 2, 
	3, 10, 2, 5, 4, 2, 6, 4, 
	2, 7, 4, 2, 9, 18, 2, 10, 
	19, 2, 12, 25, 2, 15, 10, 2, 
	15, 12, 3, 1, 2, 17, 3, 5, 
	4, 3, 3, 6, 4, 2, 3, 7, 
	4, 2, 4, 15, 0, 2, 10, 5, 
	6, 4, 1, 2, 17, 5, 7, 4, 
	1, 2, 17
};

static const char _php_cond_offsets[] = {
	0, 0, 0, 0, 1, 2, 2, 2, 
	3, 4, 4, 4, 5, 6, 7, 7, 
	7, 7, 7, 7, 7, 8, 8, 9, 
	9, 10, 10
};

static const char _php_cond_lengths[] = {
	0, 0, 0, 1, 1, 0, 0, 1, 
	1, 0, 0, 1, 1, 1, 0, 0, 
	0, 0, 0, 0, 1, 0, 1, 0, 
	1, 0, 0
};

static const short _php_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 0
};

static const char _php_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0
};

static const char _php_key_offsets[] = {
	0, 0, 1, 3, 13, 23, 26, 27, 
	37, 47, 50, 51, 62, 73, 85, 86, 
	87, 92, 95, 98, 100, 114, 116, 126, 
	129, 139, 141
};

static const short _php_trans_keys[] = {
	42, 42, 47, 10, 12, 34, 92, 269, 
	525, 0, 11, 14, 255, 10, 12, 34, 
	92, 269, 525, 0, 11, 14, 255, 10, 
	12, 13, 10, 10, 12, 39, 92, 269, 
	525, 0, 11, 14, 255, 10, 12, 39, 
	92, 269, 525, 0, 11, 14, 255, 10, 
	12, 13, 10, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 42, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 42, 47, 269, 
	525, 0, 11, 14, 255, 10, 10, 32, 
	35, 47, 9, 13, 32, 9, 13, 10, 
	12, 13, 42, 47, 9, 10, 12, 32, 
	34, 35, 39, 47, 269, 525, 0, 8, 
	14, 255, 9, 32, 10, 12, 34, 92, 
	269, 525, 0, 11, 14, 255, 10, 12, 
	13, 10, 12, 39, 92, 269, 525, 0, 
	11, 14, 255, 42, 47, 10, 0
};

static const char _php_single_lengths[] = {
	0, 1, 2, 6, 6, 1, 1, 6, 
	6, 1, 1, 7, 7, 8, 1, 1, 
	3, 1, 1, 2, 10, 2, 6, 1, 
	6, 2, 1
};

static const char _php_range_lengths[] = {
	0, 0, 0, 2, 2, 1, 0, 2, 
	2, 1, 0, 2, 2, 2, 0, 0, 
	1, 1, 1, 0, 2, 0, 2, 1, 
	2, 0, 0
};

static const char _php_index_offsets[] = {
	0, 0, 2, 5, 14, 23, 26, 28, 
	37, 46, 49, 51, 61, 71, 82, 84, 
	86, 91, 94, 97, 100, 113, 116, 125, 
	128, 137, 140
};

static const char _php_indicies[] = {
	2, 1, 2, 3, 1, 6, 6, 7, 
	8, 9, 6, 5, 5, 4, 11, 11, 
	12, 13, 14, 11, 10, 10, 4, 4, 
	4, 5, 6, 4, 16, 16, 7, 17, 
	18, 16, 15, 15, 4, 20, 20, 21, 
	22, 23, 20, 19, 19, 4, 4, 4, 
	15, 16, 4, 25, 26, 26, 25, 27, 
	28, 26, 24, 24, 4, 30, 31, 31, 
	30, 32, 33, 31, 29, 29, 4, 25, 
	26, 26, 25, 27, 34, 28, 26, 24, 
	24, 4, 26, 4, 35, 36, 38, 39, 
	40, 38, 37, 38, 38, 41, 42, 42, 
	39, 1, 39, 43, 45, 35, 35, 45, 
	46, 47, 48, 49, 50, 51, 44, 44, 
	36, 45, 45, 52, 6, 6, 7, 8, 
	9, 6, 5, 5, 53, 54, 54, 55, 
	16, 16, 7, 17, 18, 16, 15, 15, 
	53, 24, 56, 53, 35, 57, 0
};

static const char _php_trans_targs[] = {
	16, 1, 2, 16, 20, 3, 4, 20, 
	5, 6, 3, 4, 20, 5, 6, 7, 
	8, 9, 10, 7, 8, 20, 9, 10, 
	11, 11, 12, 13, 14, 11, 11, 12, 
	13, 14, 20, 20, 0, 16, 17, 18, 
	19, 16, 16, 16, 20, 21, 22, 23, 
	24, 25, 15, 26, 20, 20, 20, 23, 
	23, 20
};

static const char _php_trans_actions[] = {
	37, 11, 11, 57, 27, 1, 0, 66, 
	0, 0, 78, 48, 93, 48, 48, 1, 
	0, 0, 0, 74, 45, 87, 45, 45, 
	3, 0, 0, 3, 0, 70, 42, 42, 
	70, 42, 17, 51, 0, 29, 9, 11, 
	63, 31, 33, 35, 54, 5, 82, 39, 
	82, 60, 7, 7, 19, 25, 21, 0, 
	3, 23
};

static const char _php_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	13, 0, 0, 0, 13, 0, 0, 0, 
	0, 0, 0
};

static const char _php_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	15, 0, 0, 0, 15, 0, 0, 0, 
	0, 0, 0
};

static const char _php_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 0, 
	0, 42, 43, 44, 0, 53, 54, 55, 
	54, 54, 58
};

static const int php_start = 16;
static const int php_first_final = 16;
static const int php_error = 0;

static const int php_en_php_line = 20;
static const int php_en_php_entity = 16;


#line 109 "php.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with PHP code (not in HTML).
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
void parse_php(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 215 "php.h"
	{
	cs = php_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 132 "php.rl"
  cs = (count) ? php_en_php_line : php_en_php_entity;
  
#line 226 "php.h"
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
	_acts = _php_actions + _php_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 14:
#line 1 "NONE"
	{ts = p;}
	break;
#line 248 "php.h"
		}
	}

	_widec = (*p);
	_klen = _php_cond_lengths[cs];
	_keys = _php_cond_keys + (_php_cond_offsets[cs]*2);
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
				switch ( _php_cond_spaces[_php_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _php_trans_keys + _php_key_offsets[cs];
	_trans = _php_index_offsets[cs];

	_klen = _php_single_lengths[cs];
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

	_klen = _php_range_lengths[cs];
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
	_trans = _php_indicies[_trans];
_eof_trans:
	cs = _php_trans_targs[_trans];

	if ( _php_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _php_actions + _php_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 30 "common.rl"
	{
  inqueue = 1;
  if (callback_list_head) free_queue(); // free the current queue
  callback_list_head = NULL;
  callback_list_tail = NULL;
  // set backup variables
  last_line_start = line_start;
  last_line_contains_code = line_contains_code;
  last_whole_line_comment = whole_line_comment;
}
	break;
	case 1:
#line 41 "common.rl"
	{
  if (inqueue) {
    Callback *item;
    for (item = callback_list_head; item != NULL; item = item->next)
      callback(item->lang, item->entity, item->s, item->e, item->udata);
    free_queue();
    inqueue = 0;
  }
}
	break;
	case 2:
#line 53 "common.rl"
	{
  if (!line_contains_code && !line_start) line_start = ts;
  line_contains_code = 1;
}
	break;
	case 3:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 4:
#line 31 "php.rl"
	{
    switch(entity) {
    case PHP_SPACE:
      ls
      break;
    case PHP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PHP_LANG)
      break;
    case NEWLINE:
      std_newline(PHP_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(PHP_LANG)
      break;
    }
  }
	break;
	case 5:
#line 54 "php.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 64 "php.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 74 "php.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 8:
#line 86 "php.rl"
	{ entity = PHP_SPACE; }
	break;
	case 9:
#line 89 "php.rl"
	{ entity = NEWLINE;   }
	break;
	case 10:
#line 90 "php.rl"
	{ entity = PHP_ANY;   }
	break;
	case 11:
#line 104 "php.rl"
	{ entity = PHP_SPACE;   }
	break;
	case 12:
#line 105 "php.rl"
	{ entity = PHP_COMMENT; }
	break;
	case 15:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 16:
#line 87 "php.rl"
	{te = p+1;}
	break;
	case 17:
#line 88 "php.rl"
	{te = p+1;}
	break;
	case 18:
#line 31 "php.rl"
	{te = p+1;{
    switch(entity) {
    case PHP_SPACE:
      ls
      break;
    case PHP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PHP_LANG)
      break;
    case NEWLINE:
      std_newline(PHP_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(PHP_LANG)
      break;
    }
  }}
	break;
	case 19:
#line 31 "php.rl"
	{te = p+1;{
    switch(entity) {
    case PHP_SPACE:
      ls
      break;
    case PHP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PHP_LANG)
      break;
    case NEWLINE:
      std_newline(PHP_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(PHP_LANG)
      break;
    }
  }}
	break;
	case 20:
#line 31 "php.rl"
	{te = p;p--;{
    switch(entity) {
    case PHP_SPACE:
      ls
      break;
    case PHP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PHP_LANG)
      break;
    case NEWLINE:
      std_newline(PHP_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(PHP_LANG)
      break;
    }
  }}
	break;
	case 21:
#line 87 "php.rl"
	{te = p;p--;}
	break;
	case 22:
#line 31 "php.rl"
	{te = p;p--;{
    switch(entity) {
    case PHP_SPACE:
      ls
      break;
    case PHP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PHP_LANG)
      break;
    case NEWLINE:
      std_newline(PHP_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(PHP_LANG)
      break;
    }
  }}
	break;
	case 23:
#line 31 "php.rl"
	{te = p;p--;{
    switch(entity) {
    case PHP_SPACE:
      ls
      break;
    case PHP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PHP_LANG)
      break;
    case NEWLINE:
      std_newline(PHP_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(PHP_LANG)
      break;
    }
  }}
	break;
	case 24:
#line 31 "php.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case PHP_SPACE:
      ls
      break;
    case PHP_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PHP_LANG)
      break;
    case NEWLINE:
      std_newline(PHP_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(PHP_LANG)
      break;
    }
  }}
	break;
	case 25:
#line 95 "php.rl"
	{te = p+1;{
    callback(PHP_LANG, php_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 26:
#line 107 "php.rl"
	{te = p+1;}
	break;
	case 27:
#line 95 "php.rl"
	{te = p;p--;{
    callback(PHP_LANG, php_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 28:
#line 95 "php.rl"
	{te = p;p--;{
    callback(PHP_LANG, php_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 29:
#line 107 "php.rl"
	{te = p;p--;}
	break;
	case 30:
#line 107 "php.rl"
	{{p = ((te))-1;}}
	break;
#line 618 "php.h"
		}
	}

_again:
	_acts = _php_actions + _php_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 13:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 631 "php.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _php_eof_trans[cs] > 0 ) {
		_trans = _php_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 134 "php.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(PHP_LANG) }
}

#endif

/*****************************************************************************/
