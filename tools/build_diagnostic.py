"""Create a separate Python 2.7 diagnostic package without editing the base build."""
from __future__ import absolute_import, print_function

import ast
import argparse
import imp
import marshal
import os
import struct
import sys
import time
import zipfile


class InstrumentCalls(ast.NodeTransformer):
    def __init__(self):
        self.function = None
        self.counts = {'alpha': 0, 'dossier': 0, 'extract': 0, 'fingerprint': 0}

    def visit_FunctionDef(self, node):
        previous = self.function
        self.function = node.name
        self.generic_visit(node)
        self.function = previous
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        category = None
        if (self.function == '_alpha_damage' and isinstance(node.func, ast.Name)
                and node.func.id == '_persistent_alpha_key'):
            category = 'fingerprint'
        if self.function == '_get_vehicle_dossier' and isinstance(node.func, ast.Attribute):
            if node.func.attr == 'getVehicleDossier':
                category = 'dossier'
        if self.function == '_build_stats':
            if isinstance(node.func, ast.Name):
                if node.func.id == '_alpha_damage':
                    category = 'alpha'
                elif node.func.id in ('_marks_on_gun_rating', '_marks_on_gun_level'):
                    category = 'extract'
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in ('getRandomStats', 'getBattlesCount',
                                      'getWinsEfficiency', 'getAvgDamage'):
                    category = 'extract'
        if category is None:
            return node
        self.counts[category] += 1
        wrapped = ast.Call(func=ast.Name(id='_hcc_timed', ctx=ast.Load()),
                           args=[ast.Str(s=category), node.func] + node.args,
                           keywords=node.keywords, starargs=node.starargs,
                           kwargs=node.kwargs)
        return ast.copy_location(wrapped, node)


def instrument(source, helpers, filename, version=None):
    tree = ast.parse(source, filename)
    if version is not None:
        versions = [node for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'MOD_VERSION'
                            for target in node.targets)]
        if len(versions) != 1:
            raise ValueError('Expected exactly one MOD_VERSION assignment.')
        versions[0].value = ast.copy_location(ast.Str(s=version), versions[0].value)
    transformer = InstrumentCalls()
    tree = transformer.visit(tree)
    if transformer.counts != {'alpha': 1, 'dossier': 1, 'extract': 6, 'fingerprint': 1}:
        raise ValueError('Unexpected profiling targets: %r' % transformer.counts)
    helper_tree = ast.parse(helpers)
    # Keep future imports at the beginning of the original module.
    helpers = [node for node in helper_tree.body
               if not isinstance(node, ast.ImportFrom) or node.module != '__future__']
    insertion = max(index for index, node in enumerate(tree.body)
                    if isinstance(node, ast.FunctionDef)) + 1
    tree.body[insertion:insertion] = helpers
    return compile(ast.fix_missing_locations(tree), filename, 'exec', dont_inherit=True)


def main():
    if sys.version_info[:2] != (2, 7):
        raise RuntimeError('Build this diagnostic package with Python 2.7.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', action='store_true',
                        help='Package edited source as a separate alpha-test build '
                             'using native resources from the base archive.')
    options = parser.parse_args()
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    source_path = os.path.join(root, 'res', 'scripts', 'client', 'gui', 'mods',
                               'mod_hangar_carousel_classic.py')
    with open(source_path, 'rb') as stream:
        source = stream.read()
    with open(os.path.join(root, 'tools', 'carousel_diagnostics.py'), 'rb') as stream:
        helpers = stream.read()
    version = '1.0.24'
    diagnostic_version = version + ('-alpha-test7' if options.candidate else '-diagnostic')
    code = instrument(source, helpers, source_path, diagnostic_version)
    base = os.path.join(root, 'dist', 'mod_hangar_carousel_classic_%s.wotmod' % version)
    output = os.path.join(root, 'dist', 'mod_hangar_carousel_classic_%s.wotmod' %
                          diagnostic_version)
    entry = 'res/scripts/client/gui/mods/mod_hangar_carousel_classic.pyc'
    with zipfile.ZipFile(base, 'r') as original:
        # Refuse to instrument source different from the already-tested package.
        original_code = marshal.loads(original.read(entry)[8:])
        if not options.candidate and original_code != compile(
                source, source_path, 'exec', dont_inherit=True):
            raise ValueError('Base package does not match the current source; rebuild it first.')
        bytecode = imp.get_magic() + struct.pack('<I', int(time.time())) + marshal.dumps(code)
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_STORED) as diagnostic:
            for info in original.infolist():
                # HCC injects into the native model; it has no standalone HTML layout.
                if info.filename == 'res/gui/gen_resources/hangar_carousel_classic.json':
                    continue
                data = original.read(info.filename)
                if info.filename == entry:
                    data = bytecode
                elif info.filename == 'meta.xml':
                    if data.count('<version>%s</version>' % version) != 1:
                        raise ValueError('Base package version does not match the test version.')
                    data = data.replace('<version>%s</version>' % version,
                                        '<version>%s</version>' % diagnostic_version)
                diagnostic.writestr(info, data, compress_type=zipfile.ZIP_STORED)
    print(output)


if __name__ == '__main__':
    main()
