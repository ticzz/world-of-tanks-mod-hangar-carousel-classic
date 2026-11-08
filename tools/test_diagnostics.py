"""Verify diagnostic instrumentation against the actual mod functions."""
from __future__ import absolute_import, division

import os
import types

from build_diagnostic import instrument
import test_dossier_cache as regression
from test_dossier_cache import Vehicle


class DiagnosticTests(regression.DossierCacheTests):
    def setUp(self):
        super(DiagnosticTests, self).setUp()
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        source_path = os.path.join(root, 'res', 'scripts', 'client', 'gui', 'mods',
                                   'mod_hangar_carousel_classic.py')
        with open(source_path, 'rb') as stream:
            source = stream.read()
        with open(os.path.join(root, 'tools', 'carousel_diagnostics.py'), 'rb') as stream:
            helpers = stream.read()
        code = instrument(source, helpers, source_path, '1.0.24-diagnostic')
        for value in code.co_consts:
            if isinstance(value, types.CodeType) and value.co_name in (
                    '_get_vehicle_dossier', '_invalidate_dossier_cache',
                    '_matches_marks_incomplete', '_build_stats', '_matches', '_filter_count'):
                defaults = self.ns[value.co_name].func_defaults
                self.ns[value.co_name] = types.FunctionType(value, self.ns,
                                                           argdefs=defaults)
        self.ns['ALPHA_DAMAGE_STATS'] = {'hits': 0, 'computed': 0}
        self.ns['MOD_VERSION'] = '1.0.24-diagnostic'
        self.ns['_build_payload'] = lambda: None
        exec compile(helpers, 'carousel_diagnostics.py', 'exec') in self.ns

    def test_profile_cold_and_warm_builds(self):
        now = [0.0]
        messages = []
        self.ns['_clock'] = lambda: now[0]
        logger = type('Logger', (), {'info': lambda logger, fmt, *args:
                                    messages.append(fmt % args)})()
        self.ns['LOGGER'] = logger
        original_fetch = self.items.getVehicleDossier

        def fetch(vehicle_id):
            now[0] += 0.002
            return original_fetch(vehicle_id)

        self.items.getVehicleDossier = fetch
        def marks_rating(dossier):
            now[0] += 0.001
            return 95.0

        def marks_level(dossier):
            now[0] += 0.001
            return dossier.marks

        self.ns['_marks_on_gun_rating'] = marks_rating
        self.ns['_marks_on_gun_level'] = marks_level

        def alpha(vehicle):
            now[0] += 0.003
            self.ns['ALPHA_DAMAGE_STATS']['computed'] += 1
            return 240

        self.ns['_alpha_damage'] = alpha

        def build():
            return [self.ns['_build_stats'](Vehicle(i), None, {}) for i in range(1, 926)]

        measured = self.ns['_hcc_payload'](build)
        cold = measured()
        warm = measured()
        self.assertEqual(cold, warm)
        self.assertEqual(len(messages), 2)
        self.assertIn('vehicles=925', messages[0])
        self.assertIn('alpha_ms=2775.000', messages[0])
        self.assertIn('dossier_fetch_ms=1850.000', messages[0])
        self.assertIn('dossier_extract_ms=1850.000', messages[0])
        self.assertIn('dossier_misses=925 dossier_fetches=925', messages[0])
        self.assertIn('dossier_hits=925 dossier_misses=0 dossier_fetches=0', messages[1])
        self.assertIn('dossier_fetch_ms=0.000', messages[1])
        self.assertIsNone(self.ns['_profile'])

    def test_lightweight_refresh_does_not_log(self):
        messages = []
        self.ns['LOGGER'] = type('Logger', (), {'info': lambda *args:
                                               messages.append(args)})()
        self.assertEqual(self.ns['_hcc_payload'](lambda: {'cached': True})(),
                         {'cached': True})
        self.assertEqual(messages, [])
        self.assertIsNone(self.ns['_profile'])

    def test_exception_restores_profile_and_propagates(self):
        def fail():
            raise ValueError('test')
        with self.assertRaises(ValueError):
            self.ns['_hcc_payload'](fail)()
        self.assertIsNone(self.ns['_profile'])


if __name__ == '__main__':
    import unittest
    unittest.main()
