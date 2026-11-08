"""Verify the targeted native alpha lookup, caching, and lazy fallbacks."""
from __future__ import absolute_import, division

import ast
import logging
import os
import unittest


class Object(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class AlphaDamageTests(unittest.TestCase):
    def setUp(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.native_calls = []
        test = self

        class NativeParams(object):
            def __init__(self, vehicle):
                test.native_calls.append(vehicle)
                self.vehicle = vehicle

            @property
            def avgDamage(self):
                if self.vehicle.unavailable:
                    raise ValueError('native parameters unavailable')
                return self.vehicle.alpha

        self.item_calls = []
        items = Object(
            getItemByCD=lambda cd: self.lookup('cached', cd),
            getStockVehicle=lambda cd: self.lookup('stock', cd))
        self.cached = None
        self.stock = None
        self.ns = dict(
            VehicleParams=NativeParams,
            SERVICES=Object(itemsCache=Object(items=items)),
            ALPHA_DAMAGE_CACHE={}, ALPHA_DAMAGE_STATS={'hits': 0, 'computed': 0},
            _persistent_alpha_key=lambda vehicle: None,
            _remember_persistent_alpha=lambda key, value: None,
            LOGGER=logging.getLogger('alpha-tests'))
        source = os.path.join(root, 'res', 'scripts', 'client', 'gui', 'mods',
                              'mod_hangar_carousel_classic.py')
        with open(source, 'rb') as stream:
            tree = ast.parse(stream.read(), source)
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name in ('_alpha_cache_key', '_alpha_damage',
                                       '_on_items_cache_sync_completed')]
        self.assertEqual(len(functions), 3)
        exec compile(ast.Module(body=functions), source, 'exec') in self.ns

    def lookup(self, name, cd):
        self.item_calls.append((name, cd))
        return self.cached if name == 'cached' else self.stock

    def vehicle(self, cd=1, alpha=240, gun_cd=11, shell_cd=21, unavailable=False):
        shell = Object(compactDescr=shell_cd, armorDamage=(alpha, 0))
        gun = Object(compactDescr=gun_cd, shots=(Object(shell=shell),))
        return Object(intCD=cd, descriptor=Object(gun=gun), alpha=alpha,
                      unavailable=unavailable)

    def test_native_value_and_cache_skip_all_fallback_lookups(self):
        vehicle = self.vehicle(alpha=243)
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 243)
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 243)
        self.assertEqual(len(self.native_calls), 1)
        self.assertEqual(self.item_calls, [])
        self.assertEqual(self.ns['ALPHA_DAMAGE_STATS'], {'hits': 1, 'computed': 1})

    def test_gun_and_shell_changes_recompute(self):
        for vehicle in (self.vehicle(), self.vehicle(alpha=320, gun_cd=12),
                        self.vehicle(alpha=400, shell_cd=22)):
            self.assertEqual(self.ns['_alpha_damage'](vehicle), vehicle.alpha)
        self.assertEqual(len(self.native_calls), 3)

    def test_selected_shot_change_recomputes(self):
        vehicle = self.vehicle()
        vehicle.descriptor.shot = Object(shell=Object(compactDescr=21))
        vehicle.descriptor.activeGunShotIndex = 0
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 240)
        vehicle.alpha = 320
        vehicle.descriptor.shot = Object(shell=Object(compactDescr=22))
        vehicle.descriptor.activeGunShotIndex = 1
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 320)
        self.assertEqual(len(self.native_calls), 2)

    def test_equipment_or_crew_change_with_same_gun_and_shells_recomputes_after_sync(self):
        vehicle = self.vehicle()
        callbacks = []
        reasons = Object(SHOW_GUI=1, CLIENT_UPDATE=2, SHOP_RESYNC=3,
                         INVENTORY_RESYNC=4, DOSSIER_RESYNC=5, STATS_RESYNC=6)
        self.ns.update({
            'CACHE_SYNC_REASON': reasons,
            'GUI_ITEM_TYPE': Object(VEHICLE=1),
            '_register_callback': lambda delay, callback: callbacks.append(callback),
            '_refresh_all_models': lambda *args, **kwargs: None,
        })
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 240)
        key = self.ns['_alpha_cache_key'](vehicle)
        vehicle.alpha = 250
        self.assertEqual(self.ns['_alpha_cache_key'](vehicle), key)
        self.ns['_on_items_cache_sync_completed'](reasons.CLIENT_UPDATE, {1: {vehicle.intCD}})
        callbacks.pop(0)()
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 250)
        self.assertEqual(len(self.native_calls), 2)

    def test_one_vehicle_equipment_update_recomputes_one_of_925(self):
        vehicles = [self.vehicle(cd=i) for i in range(1, 926)]
        callbacks = []
        reasons = Object(SHOW_GUI=1, CLIENT_UPDATE=2, SHOP_RESYNC=3,
                         INVENTORY_RESYNC=4, DOSSIER_RESYNC=5, STATS_RESYNC=6)
        self.ns.update({
            'CACHE_SYNC_REASON': reasons, 'GUI_ITEM_TYPE': Object(VEHICLE=1),
            '_register_callback': lambda delay, callback: callbacks.append(callback),
            '_refresh_all_models': lambda *args, **kwargs: None,
        })
        for vehicle in vehicles:
            self.ns['_alpha_damage'](vehicle)
        self.assertEqual(len(self.native_calls), 925)
        for changed in (vehicles[0], vehicles[400], vehicles[0]):
            changed.alpha += 10
            self.ns['_on_items_cache_sync_completed'](
                reasons.CLIENT_UPDATE, {1: {changed.intCD}})
            callbacks.pop(0)()
            self.ns['ALPHA_DAMAGE_STATS'].update(hits=0, computed=0)
            for vehicle in vehicles:
                self.assertEqual(self.ns['_alpha_damage'](vehicle), vehicle.alpha)
            self.assertEqual(self.ns['ALPHA_DAMAGE_STATS'], {'hits': 924, 'computed': 1})
        self.assertEqual(len(self.native_calls), 928)

    def test_cached_then_stock_candidates_remain_lazy(self):
        self.cached = self.vehicle(alpha=320)
        self.assertEqual(self.ns['_alpha_damage'](self.vehicle(unavailable=True)), 320)
        self.assertEqual(self.item_calls, [('cached', 1)])
        self.ns['ALPHA_DAMAGE_CACHE'].clear()
        self.item_calls[:] = []
        self.cached = None
        self.stock = self.vehicle(alpha=400)
        self.assertEqual(self.ns['_alpha_damage'](self.vehicle(unavailable=True)), 400)
        self.assertEqual(self.item_calls, [('cached', 1), ('stock', 1)])

    def test_descriptor_fallback_uses_armor_not_module_damage(self):
        vehicle = self.vehicle(alpha=240, unavailable=True)
        vehicle.descriptor.gun.shots[0].shell.damage = (90, 0)
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 240)

    def test_large_garage_calls_native_provider_only_once_per_setup(self):
        vehicles = [self.vehicle(cd=i, alpha=240 + i) for i in range(1, 926)]
        for _ in range(2):
            for vehicle in vehicles:
                self.assertEqual(self.ns['_alpha_damage'](vehicle), vehicle.alpha)
        self.assertEqual(len(self.native_calls), 925)
        self.assertEqual(self.item_calls, [])
        self.assertEqual(self.ns['ALPHA_DAMAGE_STATS'], {'hits': 925, 'computed': 925})

    def test_matches_local_client_alpha_formula_with_distribution_modifiers(self):
        client = os.environ.get('WOT_SOURCE_ROOT', os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..', 'wot-src-EU')))
        source = os.path.join(client, 'sources', 'res', 'scripts', 'client',
                              'gui', 'shared', 'items_parameters', 'params.py')
        if not os.path.isfile(source):
            self.skipTest('Local WoT source unavailable; set WOT_SOURCE_ROOT.')
        with open(source, 'rb') as stream:
            tree = ast.parse(stream.read(), source)
        native_class = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                            and node.name == 'VehicleParams')
        methods = [node for node in native_class.body if isinstance(node, ast.FunctionDef)
                   and node.name in ('avgDamage', '__calculateDamageOrPiercingRandom')]
        self.assertEqual(len(methods), 2)
        native_class.body = methods
        native_class.bases = [ast.Name(id='object', ctx=ast.Load())]
        ns = {'round_py2_style_int': lambda value: int(round(value)), '_DO_TTC_LOG': False}
        exec compile(ast.fix_missing_locations(ast.Module(body=[native_class])),
                     source, 'exec') in ns
        reference = ns['VehicleParams']

        def targeted(vehicle):
            result = reference()
            result._itemDescr = vehicle.descriptor
            result.damageAndPiercingDistributionLowerBound = vehicle.lower
            result.damageAndPiercingDistributionUpperBound = vehicle.upper
            return result

        self.ns['VehicleParams'] = targeted
        for index, (damage, randomization, lower, upper) in enumerate((
                (240, 0.25, 0, 0), (390, 0.25, 2, 0),
                (440, 0.25, 0, -3), (150, 0.1, 1, 2),
                (750, 0, 0, 0))):
            vehicle = self.vehicle(cd=index + 1, alpha=damage)
            vehicle.lower, vehicle.upper = lower, upper
            vehicle.descriptor.shot = Object(shell=Object(
                armorDamage=(damage, 0), damageRandomization=randomization))
            expected = targeted(vehicle).avgDamage
            self.assertEqual(self.ns['_alpha_damage'](vehicle), expected)


if __name__ == '__main__':
    unittest.main()
