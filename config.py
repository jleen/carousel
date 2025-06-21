import re


GALLERY_NAME = 'Hall of Light'

VIEW = (700, 500)
PREVIEW = (200, 200)
DIR = (100, 100)


def jpeg_name(rel_parts):
    if is_boring(rel_parts[-1]):
        year = rel_parts[0]
        if len(rel_parts) > 2:
            top = rel_parts[1]
            preamble = [top, year]
        else:
            preamble = [year]
        rest = rel_parts[2:-1]
        return '_'.join(preamble + list(rest) + [rel_parts[-1]])
    else:
        return rel_parts[-1]

def title(name):
    if len(name) == 0:
        return GALLERY_NAME
    elif re.match(r'\w+_20\d\d_\w*_\d*', name):
        return name.split('_')[-1]
    else:
        # TODO: Well, here we are again.  There are too many kinds of name.
        # URL sanitization probably needs to proceed in two phases
        #        source filename -> neutral name -> target filename
        # But this will do for now.
        return re.sub(r'^\d\d ', '', name.replace('_', ' ').replace("'", '’'))

def caption(name):
    return '' if is_boring(name) else title(name)

def is_boring(name):
    if re.match(r'^\d\d\d\d$', name):
        return False  # Years are not boring.
    else:
        return re.match(r'^\d*$', name)  # Other numbers are boring.

def is_hidden(s_dir):
    return s_dir.name.startswith('_')
