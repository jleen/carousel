import re
import shutil

from pathlib import Path


VIEW = (700, 500)
PREVIEW = (200, 200)
DIR = (100, 100)

source_root = Path('/mnt/c/Mirror/Gallery')
target_root = Path('/home/jleen/gallery')

def main():
    copy_css()
    traverse_dir(source_root)

def traverse_dir(s_dir):
    create_target_dir(s_dir)

    s_photos = [p for p in s_dir.iterdir() if p.is_file() and p.suffix == '.jpeg' and not p.name.startswith('.')]
    preview_sizes = {}
    for i, s_photo in enumerate(sorted(s_photos)):
        preview_sizes[s_photo] = traverse_photo(
            s_photo,
            s_prev = s_photos[i-1] if i > 0 else None,
            s_next = s_photos[i+1] if i < len(s_photos)-1 else None)

    s_preview = s_dir / '.preview.jpeg'
    if s_preview.exists():
        preview_size = resize(s_preview, t_dirdir(s_dir) / '.preview.jpeg', DIR)
    else:
        preview_size = None

    subdir_sizes = {}
    for s_subdir in [p for p in s_dir.iterdir() if p.is_dir()]:
        subdir_sizes[s_subdir] = traverse_dir(s_subdir)

    render_dir_page(s_dir, preview_sizes, subdir_sizes)
    return preview_size
    
def create_target_dir(s_dir):
    t_dirdir(s_dir).mkdir(exist_ok=True)

def create_photo_dir(s_photo):
    t_photodir(s_photo).mkdir(exist_ok=True)

def traverse_photo(s_photo, s_prev, s_next):
    create_photo_dir(s_photo)
    preview_size = render_preview(s_photo)
    view_size = render_view(s_photo)
    render_photo(s_photo)

    render_photo_page(s_photo, view_size, s_prev, s_next)
    return preview_size

def render_photo(s_photo):
    t = t_photo(s_photo, '')
    maybe_copy(s_photo, t)

def render_preview(s_photo):
    t = t_photo(s_photo, '_preview')
    return resize(s_photo, t, PREVIEW)

def render_view(s_photo):
    t = t_photo(s_photo, '_view')
    return resize(s_photo, t, VIEW)

def render_photo_page(s_photo, view_size, s_prev, s_next):
    t_photo_page = t_photopage(s_photo)
    if is_stale(s_photo, t_photo_page):
        # TODO
        print(f'* {t_photo_page}')
    else:
        print(f'  {t_photo_page}')

def render_dir_page(s_dir, preview_sizes, subdir_sizes):
    t_dir_page = t_dirpage(s_dir)
    if is_stale(s_dir, t_dir_page):
        # TODO
        print(f'* {t_dir_page}')
    else:
        print(f'  {t_dir_page}')

def is_stale(s, t):
    if s.is_dir():  # BUGBUG: Recursive containment?
        mtime = max([p.stat().st_mtime for p in s.iterdir()])
    else:
        mtime = s.stat().st_mtime
    return not t.exists() or t.stat().st_mtime < mtime

def copy_css():
    maybe_copy(Path('carousel.css'), target_root / 'carousel.css')

def maybe_copy(s, t):
    if is_stale(s, t):
        # TODO: shutil.copy(s, t)
        print(f'* {t}')
    else:
        print(f'  {t}')

def resize(s, t, bounds):
    if is_stale(s, t):
        size = bounds  # TODO
        print(f'* {t}')
    else:
        size = bounds  # TODO
        print(f'  {t}')
    return size

def scaled_size(ss, tt):
    (sw, sh) = ss
    (tw, th) = tt
    ww = sw / tw
    hh = sh / th
    # Explicitly return at least one target dimension (prioritizing height)
    # to avoid embarrassing floating point off-by-one.
    if (hh >= ww):
        return (int(sw / hh), th)
    else:
        return (tw, int(sh / ww))

def target(s):
    rel = s.relative_to(source_root)
    return target_root / Path(*[targetize(p) for p in rel.parts])

def targetize(part):
    return re.sub(r'^\d\d_', '', part)

def t_dirdir(s):
    return target(s)

def t_dirpage(s):
    return t_dirdir(s) / 'index.html'

def t_photodir(s):
    return target(s.parent / s.stem)

def t_photopage(s):
    return t_photodir(s) / 'index.html'

def t_photo(s, suffix):
    t_dir = t_photodir(s)
    name = jpeg_name(t_dir)
    return t_dir / f'{name}{suffix}.jpeg'

def jpeg_name(t_dir):
    if is_boring(t_dir.name):
        rel_parts = t_dir.relative_to(target_root).parts
        year = rel_parts[0]
        top = rel_parts[1]
        rest = rel_parts[2:-1]
        return '_'.join([top, year] + list(rest) + [t_dir.name])
    else:
        return t_dir.name

def is_boring(name):
    if re.match(r'^\d\d\d\d$', name):
        return False  # Years are not boring.
    else:
        return re.match(r'^\d*$', name)  # Other numbers are boring.

if __name__ == '__main__':
    main()
