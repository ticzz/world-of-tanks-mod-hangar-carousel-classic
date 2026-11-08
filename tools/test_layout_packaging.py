"""Regression coverage for native injection without a standalone WULF layout."""
from __future__ import absolute_import

import imp
import marshal
import os
import shutil
import struct
import sys
import tempfile
import unittest
import zipfile

import build_diagnostic


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OBSOLETE_LAYOUT = 'res/gui/gen_resources/hangar_carousel_classic.json'
MOD_ENTRY = 'res/scripts/client/gui/mods/mod_hangar_carousel_classic.pyc'


class LayoutPackagingTests(unittest.TestCase):
    def test_candidate_removes_obsolete_layout_and_preserves_injected_assets(self):
        root = tempfile.mkdtemp(prefix='hcc-layout-test-')
        original_file = build_diagnostic.__file__
        original_argv = sys.argv
        try:
            for directory in ('tools', 'dist', os.path.dirname(MOD_ENTRY)):
                os.makedirs(os.path.join(root, directory))
            source_path = os.path.join(ROOT, MOD_ENTRY[:-1])
            with open(source_path, 'rb') as stream:
                source = stream.read()
            version = build_diagnostic.source_version(source, source_path)
            for relative in (MOD_ENTRY[:-1], 'tools/carousel_diagnostics.py'):
                shutil.copyfile(os.path.join(ROOT, relative),
                                os.path.join(root, relative))
            entries = {'meta.xml': '<root><version>%s</version></root>' % version,
                       OBSOLETE_LAYOUT: '[{"type":"Layout","itemID":"HangarCarouselClassic"}]',
                       MOD_ENTRY: imp.get_magic() + struct.pack('<I', 0) +
                       marshal.dumps(compile('', '<base>', 'exec'))}
            assets_root = os.path.join(ROOT, 'res', 'gui', 'gameface', 'mods', 'hcc',
                                       'hangar_carousel_classic')
            destination = os.path.join(root, 'res', 'gui', 'gameface', 'mods', 'hcc',
                                       'hangar_carousel_classic')
            os.makedirs(destination)
            for filename in os.listdir(assets_root):
                shutil.copyfile(os.path.join(assets_root, filename),
                                os.path.join(destination, filename))
                with open(os.path.join(assets_root, filename), 'rb') as stream:
                    entries['res/gui/gameface/mods/hcc/hangar_carousel_classic/' +
                            filename] = stream.read()
            base = os.path.join(root, 'dist',
                                'mod_hangar_carousel_classic_%s.wotmod' % version)
            with zipfile.ZipFile(base, 'w', zipfile.ZIP_STORED) as archive:
                for name, data in entries.items():
                    archive.writestr(name, data)
            build_diagnostic.__file__ = os.path.join(root, 'tools', 'build_diagnostic.py')
            sys.argv = [build_diagnostic.__file__, '--candidate']
            build_diagnostic.main()
            candidate = os.path.join(root, 'dist',
                                     'mod_hangar_carousel_classic_%s-alpha-test9.wotmod' % version)
            with zipfile.ZipFile(candidate) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(set(archive.namelist()), set(entries) - {OBSOLETE_LAYOUT})
                for name, data in entries.items():
                    if name not in (OBSOLETE_LAYOUT, 'meta.xml', MOD_ENTRY):
                        self.assertEqual(archive.read(name), data)
                self.assertIn('%s-alpha-test9' % version, archive.read('meta.xml'))
                code = marshal.loads(archive.read(MOD_ENTRY)[8:])
                self.assertIn('gf_mod_inject', code.co_names)
                self.assertTrue(all(info.compress_type == zipfile.ZIP_STORED
                                    for info in archive.infolist()))
        finally:
            sys.argv = original_argv
            build_diagnostic.__file__ = original_file
            shutil.rmtree(root)

    def test_source_has_no_standalone_layout_or_build_copy(self):
        self.assertFalse(os.path.exists(os.path.join(ROOT, OBSOLETE_LAYOUT)))
        with open(os.path.join(ROOT, 'tools', 'build.ps1'), 'rb') as stream:
            build_script = stream.read()
        self.assertNotIn('gen_resources', build_script)
        self.assertIn('patch-native-frontline-carousel.ps1', build_script)
        with open(os.path.join(ROOT, 'tools', 'patch-native-frontline-carousel.ps1'),
                  'rb') as stream:
            frontline_patch = stream.read()
        self.assertIn('hccSortJson:r.hccSortJson', frontline_patch)
        self.assertIn('hcc.filtered||allowed.has(String(e.id))', frontline_patch)
        self.assertIn('hcc.filtered||allowed.has(String(a.id))', frontline_patch)
        self.assertIn('values[String(e.id)]', frontline_patch)
        self.assertIn('totalElements:1<h?x.length:b.length', frontline_patch)
        self.assertIn('for(let a=0;a<e.length;a+=h)t.push(e.slice(a,a+h))',
                      frontline_patch)
        self.assertIn('className:Sa(CR,2===s&&jR,3===s&&"hcc-native-carousel-page--3",'
                      '4===s&&"hcc-native-carousel-page--4")', frontline_patch)
        with open(os.path.join(ROOT, MOD_ENTRY[:-1]), 'rb') as stream:
            source = stream.read()
        self.assertIn("gf_mod_inject(self, 'HangarCarouselClassic', styles=[CSS_URL], "
                      "modules=[JS_URL])", source)


if __name__ == '__main__':
    unittest.main()
