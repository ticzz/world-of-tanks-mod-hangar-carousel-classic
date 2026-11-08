"""Python 2.7 regression tests for large-garage dossier consumers."""
from __future__ import absolute_import, division

import ast
import logging
import os
import unittest


class Vehicle(object):
    def __init__(self, vehicle_id):
        self.intCD = vehicle_id
        self.level = 8


class Dossier(object):
    def __init__(self, vehicle_id):
        self.marks = 3 if vehicle_id % 2 else 2

    def getRandomStats(self):
        return self

    def getBattlesCount(self):
        return 100

    def getWinsEfficiency(self):
        return 0.6

    def getAvgDamage(self):
        return 1500


class Items(object):
    def __init__(self):
        self.calls = 0
        self.unavailable = False

    def getVehicleDossier(self, vehicle_id):
        self.calls += 1
        return None if self.unavailable else Dossier(vehicle_id)


class DossierCacheTests(unittest.TestCase):
    def setUp(self):
        source = os.path.join(os.path.dirname(__file__), '..', 'res', 'scripts',
                              'client', 'gui', 'mods', 'mod_hangar_carousel_classic.py')
        with open(source, 'rb') as stream:
            tree = ast.parse(stream.read(), source)
        names = ('_get_vehicle_dossier', '_invalidate_dossier_cache',
                 '_matches_marks_incomplete', '_build_stats', '_matches', '_filter_count')
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name in names]
        self.assertEqual(len(functions), len(names))
        self.items = Items()
        services = type('Services', (), {})()
        services.itemsCache = type('ItemsCache', (), {})()
        services.itemsCache.items = self.items
        self.ns = {
            'SERVICES': services,
            'LOGGER': logging.getLogger('dossier-cache-test'),
            'DOSSIER_CACHE': {},
            'MARKS_INCOMPLETE_CACHE': {},
            'DOSSIER_CACHE_GENERATION': 0,
            'LAST_PAYLOAD_SIGNATURE': ('old',),
            'ACTIVE_FILTERS': set(),
            '_alpha_damage': lambda vehicle: 240,
            '_marks_on_gun': lambda dossier: dossier.marks,
            '_marks_on_gun_rating': lambda dossier: 95.0,
            '_marks_on_gun_level': lambda dossier: dossier.marks,
        }
        # Execute actual functions without importing unavailable WoT runtime modules.
        exec compile(ast.Module(body=functions), source, 'exec') in self.ns

    def check_garage(self, count, filter_first=False):
        vehicles = [Vehicle(i) for i in range(1, count + 1)]
        if filter_first:
            self.assertEqual(self.ns['_filter_count']('marks_incomplete', vehicles),
                             count // 2)
        for vehicle in vehicles:
            stats = self.ns['_build_stats'](vehicle, None, {})
            self.assertEqual(stats['averageDamage'], 1500)
            self.assertEqual(stats['marksOnGun'], 95.0)
            self.assertEqual(stats['marksOnGunLevel'], 3 if vehicle.intCD % 2 else 2)
            self.assertEqual(stats['battles'], 100)
            self.assertEqual(stats['winRate'], 60.0)
        allowed = [v.intCD for v in vehicles
                   if self.ns['_matches']('marks_incomplete', v)]
        self.assertEqual(allowed, list(range(2, count + 1, 2)))
        self.ns['ACTIVE_FILTERS'].add('marks_incomplete')
        cache = {}
        self.assertEqual(self.ns['_filter_count']('all', vehicles, cache), len(allowed))
        self.assertEqual(self.ns['_filter_count']('marks_incomplete', vehicles, cache),
                         len(allowed))
        self.assertEqual(self.items.calls, count)
        for vehicle in vehicles:
            self.ns['_get_vehicle_dossier'](vehicle.intCD)
        self.assertEqual(self.items.calls, count)

    def test_existing_small_garage(self):
        self.check_garage(132)

    def test_old_limit_boundary(self):
        self.check_garage(256)

    def test_first_vehicle_beyond_old_limit(self):
        self.check_garage(257)

    def test_large_garage_stats_before_filter(self):
        self.check_garage(925)

    def test_large_garage_filter_before_stats(self):
        self.check_garage(925, filter_first=True)

    def test_cache_invalidation(self):
        self.check_garage(925)
        self.ns['_invalidate_dossier_cache']('test')
        self.assertEqual(self.ns['DOSSIER_CACHE'], {})
        self.assertEqual(self.ns['MARKS_INCOMPLETE_CACHE'], {})
        self.assertEqual(self.ns['DOSSIER_CACHE_GENERATION'], 1)
        self.assertIsNone(self.ns['LAST_PAYLOAD_SIGNATURE'])
        self.ns['_get_vehicle_dossier'](925)
        self.assertEqual(self.items.calls, 926)

    def test_unavailable_dossier_preserves_fallback(self):
        self.items.unavailable = True
        vehicle = Vehicle(925)
        self.assertTrue(self.ns['_matches_marks_incomplete'](vehicle))
        stats = self.ns['_build_stats'](vehicle, None, {})
        self.assertEqual(stats['averageDamage'], 0)
        self.assertEqual(stats['marksOnGun'], 0.0)
        self.assertEqual(self.items.calls, 1)


if __name__ == '__main__':
    unittest.main()
