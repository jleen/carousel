import re
import shutil
import sys

from functools import cache
from typing import NewType
from PIL import Image
from pathlib import Path

import appeldryck

import config

type ImgSize = tuple[int, int]
SourcePath = NewType('SourcePath', Path)
TargetPath = NewType('TargetPath', Path)


script_root = Path(__file__).parent
source_root = SourcePath(Path(sys.argv[1]))
target_root = TargetPath(Path(sys.argv[2]))

def main() -> None:
    copy_css()
    traverse_dir(source_root)

def iter_photos(s_dir: SourcePath) -> list[SourcePath]:
    return [SourcePath(p) for p in s_dir.iterdir()
            if p.is_file()
            and p.suffix == '.jpeg'
            and not p.name.startswith('.')]

def iter_subdirs(s_dir: SourcePath) -> list[SourcePath]:
    return [SourcePath(p) for p in s_dir.iterdir()
            if p.is_dir()]

def iter_stubs(s_dir: SourcePath) -> list[tuple[SourcePath, ImgSize]]:
    stub_re = re.compile(r'^(.+)\.stub\.(\d+)x(\d+)$')
    return [(SourcePath(s_dir / m.group(1)), (int(m.group(2)), int(m.group(3))))
            for p in s_dir.iterdir()
            if p.is_file()
            if (m := stub_re.match(p.name))]

def traverse_dir(s_dir: SourcePath) -> ImgSize | None:
    create_target_dir(s_dir)

    s_photos = iter_photos(s_dir)
    preview_sizes: dict[SourcePath, ImgSize | None] = {}
    for i, s_photo in enumerate(sorted(s_photos)):
        preview_sizes[s_photo] = traverse_photo(
            s_photo,
            s_prev = s_photos[i-1] if i > 0 else None,
            s_next = s_photos[i+1] if i < len(s_photos)-1 else None)

    s_preview = SourcePath(s_dir / '.preview.jpeg')
    if s_preview.exists():
        preview_size = resize(s_preview, t_dirpreview(s_dir), config.DIR)
    else:
        preview_size = None

    subdir_sizes: dict[SourcePath, ImgSize | None] = {}
    for s_subdir in iter_subdirs(s_dir):
        subdir_sizes[s_subdir] = traverse_dir(s_subdir)
    for (stub, size) in iter_stubs(s_dir):
        subdir_sizes[stub] = size

    render_dir_page(s_dir, preview_sizes, subdir_sizes)
    return preview_size

def create_target_dir(s_dir: SourcePath) -> None:
    t_dirdir(s_dir).mkdir(exist_ok=True)

def create_photo_dir(s_photo: SourcePath) -> None:
    t_photodir(s_photo).mkdir(exist_ok=True)

def traverse_photo(s_photo: SourcePath, s_prev: SourcePath | None, s_next: SourcePath | None) -> ImgSize | None:
    create_photo_dir(s_photo)
    preview_size = render_preview(s_photo)
    view_size = render_view(s_photo)
    render_photo(s_photo)

    render_photo_page(s_photo, view_size, s_prev, s_next)
    return preview_size

def render_photo(s_photo: SourcePath) -> None:
    t = t_photo(s_photo, '')
    maybe_copy(s_photo, t)

def render_preview(s_photo: SourcePath) -> ImgSize | None:
    t = t_photo(s_photo, '_preview')
    return resize(s_photo, t, config.PREVIEW)

def render_view(s_photo: SourcePath) -> ImgSize | None:
    t = t_photo(s_photo, '_view')
    return resize(s_photo, t, config.VIEW)

def render_photo_page(s_photo: SourcePath, view_size: ImgSize | None, s_prev: SourcePath | None, s_next: SourcePath | None) -> None:
    t = t_photopage(s_photo)
    # Check the directory for staleness too, because it's the only way to catch deletions.
    if is_stale(s_photo, t) or is_stale(SourcePath(s_photo.parent), t):
        (w, h) = lazy_size(view_size, t_photo(s_photo, '_view'))
        breadcrumbs = [ {'title': config.title(p.name),
                         'link': f'{p.relative_to(t.parent.relative_to(target_root), walk_up=True)}/'}
                        for p in t.parent.relative_to(target_root).parents ]

        context = {
            'title': config.title(t.parent.name),
            'css_dir': str(target_root.relative_to(t.parent, walk_up=True)),
            'site': config.GALLERY_PAGE_TITLE,
            'breadcrumbs': reversed(breadcrumbs),
            'prev': f'{t_photodir(s_prev).relative_to(t.parent, walk_up=True)}/' if s_prev else None,
            'next': f'{t_photodir(s_next).relative_to(t.parent, walk_up=True)}/' if s_next else None,
            'photo': t_photo(s_photo, '').name,
            'view': t_photo(s_photo, '_view').name,
            'caption': config.caption(t.parent.name),
            'height': str(h),
            'width': str(w)
        }
        t.write_text(appeldryck.preprocess(context, script_root / 'photo.html.dryck'))
        print(f'* {t}')
    else:
        print(f'  {t}')

def render_dir_page(s_dir: SourcePath, preview_sizes: dict[SourcePath, ImgSize | None], subdir_sizes: dict[SourcePath, ImgSize | None]) -> None:
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
                       for f in sorted(subdir_sizes.keys()) if not config.is_hidden(f) ]
            photos = [ {'link': f'{t_photodir(f).relative_to(t.parent)}/',
                        'preview': str(t_photo(f, '_preview').relative_to(t.parent)),
                        'caption': config.caption(target(f).stem),
                        'width': str(lazy_size(preview_sizes[f], t_photo(f, '_preview'))[0]),
                        'height': str(lazy_size(preview_sizes[f], t_photo(f, '_preview'))[1]) }
                      for f in sorted(iter_photos(s_dir)) ]
            parent_name = t.parent.relative_to(target_root).name
            context = {
                'title': config.title(parent_name),
                'site': config.GALLERY_PAGE_TITLE,
                'css_dir': str(target_root.relative_to(t.parent, walk_up=True)),
                'breadcrumbs': reversed(breadcrumbs),
                'subdirs': subdirs,
                'photos': photos,
                'root': len(parent_name) == 0
            }
            t.write_text(appeldryck.preprocess(context, script_root / 'dir.html.dryck'))
            print(f'* {t}')
        else:
            print(f'  {t}')
    except Exception as e:
        raise RuntimeError(f'Unable to render dir page for {s_dir}') from e


@cache
def get_mtime(s: SourcePath) -> float:
    if s.is_dir():
        # The directory’s mtime should usually be sufficient.
        # But check the mtime for each of its contents, too, to handle edge cases
        # like edited image files.
        #
        # TODO: What if there’s a change inside a subdirectory?
        #       How much do we care?
        mtime = max([p.stat().st_mtime for p in s.iterdir()])
        return max(mtime, s.stat().st_mtime)
    else:
        return s.stat().st_mtime

def is_stale(s: SourcePath, t: TargetPath) -> bool:
    return not t.exists() or t.stat().st_mtime < get_mtime(s)

def copy_css() -> None:
    script_dir = Path(__file__).parent
    maybe_copy(SourcePath(script_dir / 'carousel.css'), TargetPath(target_root / 'carousel.css'))

def maybe_copy(s: SourcePath, t: TargetPath) -> None:
    if is_stale(s, t):
        shutil.copy(s, t)
        print(f'* {t}')
    else:
        print(f'  {t}')

def resize(s: SourcePath, t: TargetPath, bounds: ImgSize) -> ImgSize | None:
    if is_stale(s, t):
        with Image.open(s) as img:
            img.thumbnail(bounds, resample=Image.Resampling.LANCZOS)
            img.save(t)
            print(f'* {t}')
            return img.size
    else:
        print(f'  {t}')
        return None

def lazy_size(maybe_size: ImgSize | None, f: TargetPath) -> ImgSize:
    if maybe_size:
        return maybe_size
    else:
        with Image.open(f) as img:
            return img.size

def target(s: SourcePath) -> TargetPath:
    rel = s.relative_to(source_root)
    return TargetPath(target_root / Path(*[targetize(p) for p in rel.parts]))

def targetize(part: str) -> str:
    # Make typography URL-safe.
    part = part.replace(' ', '_')
    part = part.replace('’', "'")
    # Strip leading digits, e.g. 02_Foo -> Foo
    # Also strip leading underscore, e.g. _Bar -> Bar
    # (The latter is how we indicate a hidden directory.)
    return re.sub(r'^(\d\d|)_', '', part)

def t_dirdir(s: SourcePath) -> TargetPath:
    return target(s)

def t_dirpage(s: SourcePath) -> TargetPath:
    return TargetPath(t_dirdir(s) / 'index.html')

def t_dirpreview(s: SourcePath) -> TargetPath:
    return TargetPath(t_dirdir(s) / '.preview.jpeg')

def t_photodir(s: SourcePath) -> TargetPath:
    return target(SourcePath(s.parent / s.stem))

def t_photopage(s: SourcePath) -> TargetPath:
    return TargetPath(t_photodir(s) / 'index.html')

def t_photo(s: SourcePath, suffix: str) -> TargetPath:
    t_dir = t_photodir(s)
    name = config.jpeg_name(t_dir.relative_to(target_root).parts)
    return TargetPath(t_dir / f'{name}{suffix}.jpeg')


if __name__ == '__main__':
    main()
