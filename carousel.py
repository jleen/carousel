import re
import shutil
import sys

from PIL import Image
from pathlib import Path

import appeldryck

import config


source_root = Path(sys.argv[1])
target_root = Path(sys.argv[2])

def main():
    copy_css()
    traverse_dir(source_root)

def iter_photos(s_dir):
    return [p for p in s_dir.iterdir()
            if p.is_file()
            and p.suffix == '.jpeg'
            and not p.name.startswith('.')]

def iter_subdirs(s_dir):
    return [p for p in s_dir.iterdir()
            if p.is_dir()]

def traverse_dir(s_dir):
    create_target_dir(s_dir)

    s_photos = iter_photos(s_dir)
    preview_sizes = {}
    for i, s_photo in enumerate(sorted(s_photos)):
        preview_sizes[s_photo] = traverse_photo(
            s_photo,
            s_prev = s_photos[i-1] if i > 0 else None,
            s_next = s_photos[i+1] if i < len(s_photos)-1 else None)

    s_preview = s_dir / '.preview.jpeg'
    if s_preview.exists():
        preview_size = resize(s_preview, t_dirpreview(s_dir), config.DIR)
    else:
        preview_size = None

    subdir_sizes = {}
    for s_subdir in iter_subdirs(s_dir):
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
    return resize(s_photo, t, config.PREVIEW)

def render_view(s_photo):
    t = t_photo(s_photo, '_view')
    return resize(s_photo, t, config.VIEW)

def render_photo_page(s_photo, view_size, s_prev, s_next):
    t = t_photopage(s_photo)
    if is_stale(s_photo, t):
        (w, h) = lazy_size(view_size, t_photo(s_photo, '_view'))
        breadcrumbs = [ {'title': config.title(p.name),
                         'link': f'{p.relative_to(t.parent.relative_to(target_root), walk_up=True)}/'}
                        for p in t.parent.relative_to(target_root).parents ]

        context = {
            'title': config.title(t.parent.name),
            'css_dir': str(target_root.relative_to(t.parent, walk_up=True)),
            'site': config.GALLERY_NAME,
            'breadcrumbs': reversed(breadcrumbs),
            'prev': f'{t_photodir(s_prev).relative_to(t.parent, walk_up=True)}/' if s_prev else None,
            'next': f'{t_photodir(s_next).relative_to(t.parent, walk_up=True)}/' if s_next else None,
            'photo': t_photo(s_photo, '').name,
            'view': t_photo(s_photo, '_view').name,
            'caption': config.caption(t.parent.name),
            'height': str(h),
            'width': str(w)
        }
        t.write_text(appeldryck.preprocess(context, 'photo.html.dryck'))
        print(f'* {t}')
    else:
        print(f'  {t}')

def render_dir_page(s_dir, preview_sizes, subdir_sizes):
    try:
        t = t_dirpage(s_dir)
        if is_stale(s_dir, t):
            breadcrumbs = [ {'title': config.title(p.name),
                             'link': f'{p.relative_to(t.parent.relative_to(target_root), walk_up=True)}/'}
                            for p in t.parent.relative_to(target_root).parents ]
            subdirs = [ {'link': f'{t_dirdir(f).relative_to(t.parent)}/',
                         'title': config.title(t_dirdir(f).name),
                         'preview': str(t_dirpreview(f).relative_to(t.parent)),
                         'width': str(lazy_size(subdir_sizes[f], t_dirpreview(f))[0]),
                         'height': str(lazy_size(subdir_sizes[f], t_dirpreview(f))[1]) }
                       for f in sorted(iter_subdirs(s_dir)) if not is_hidden(f) ]
            photos = [ {'link': f'{t_photodir(f).relative_to(t.parent)}/',
                        'preview': str(t_photo(f, '_preview').relative_to(t.parent)),
                        'caption': config.caption(target(f).stem),
                        'width': str(lazy_size(preview_sizes[f], t_photo(f, '_preview'))[0]),
                        'height': str(lazy_size(preview_sizes[f], t_photo(f, '_preview'))[1]) }
                      for f in sorted(iter_photos(s_dir)) ]
            context = {
                'title': config.title(t.parent.name),
                'site': config.GALLERY_NAME,
                'css_dir': str(target_root.relative_to(t.parent, walk_up=True)),
                'breadcrumbs': reversed(breadcrumbs),
                'subdirs': subdirs,
                'photos': photos
            }
            t.write_text(appeldryck.preprocess(context, 'dir.html.dryck'))
            print(f'* {t}')
        else:
            print(f'  {t}')
    except Exception as e:
        raise RuntimeError(f'Unable to render dir page for {s_dir}') from e


def is_stale(s, t):
    if s.is_dir():
        # TODO: What if there’s a change in a subdirectory?
        # How much do we care?
        mtime = max([p.stat().st_mtime for p in s.iterdir()])
    else:
        mtime = s.stat().st_mtime
    return not t.exists() or t.stat().st_mtime < mtime

def copy_css():
    script_dir = Path(__file__).parent
    maybe_copy(script_dir / 'carousel.css', target_root / 'carousel.css')

def maybe_copy(s, t):
    if is_stale(s, t):
        shutil.copy(s, t)
        print(f'* {t}')
    else:
        print(f'  {t}')

def resize(s, t, bounds):
    if is_stale(s, t):
        with Image.open(s) as img:
            img.thumbnail(bounds, resample=Image.Resampling.LANCZOS)
            img.save(t)
            print(f'* {t}')
            return img.size
    else:
        print(f'  {t}')
        return None

def lazy_size(maybe_size, f):
    if maybe_size:
        return maybe_size
    else:
        with Image.open(f) as img:
            return img.size

def target(s):
    rel = s.relative_to(source_root)
    return target_root / Path(*[targetize(p) for p in rel.parts])

def targetize(part):
    # Strip leading digits, e.g. 02_Foo -> Foo
    # Also strip leading underscore, e.g. _Bar -> Bar
    # (The latter is how we indicate a hidden directory.)
    return re.sub(r'^(\d\d|)_', '', part)

def t_dirdir(s):
    return target(s)

def t_dirpage(s):
    return t_dirdir(s) / 'index.html'

def t_dirpreview(s):
    return t_dirdir(s) / '.preview.jpeg'
    
def t_photodir(s):
    return target(s.parent / s.stem)

def t_photopage(s):
    return t_photodir(s) / 'index.html'

def t_photo(s, suffix):
    t_dir = t_photodir(s)
    name = config.jpeg_name(t_dir.relative_to(target_root).parts)
    return t_dir / f'{name}{suffix}.jpeg'


if __name__ == '__main__':
    main()
