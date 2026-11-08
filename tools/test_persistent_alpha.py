"""Exercise persistent alpha reuse across sessions with actual mod functions."""
from __future__ import absolute_import, division
from collections import OrderedDict

import ast
import hashlib
import io
import json
import os
import shutil
import tempfile
import time
import types
import unittest

from test_alpha_damage import Object


class PersistentAlphaTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='hcc-persistent-test-')
        self.path = os.path.join(self.directory, 'alpha_cache.json')
        self.calls = []
        self.callbacks = []
        self.errors = []
        self.version = 'test-client-1'
        source = os.path.join(os.path.dirname(__file__), '..', 'res', 'scripts',
                              'client', 'gui', 'mods', 'mod_hangar_carousel_classic.py')
        with open(source, 'rb') as stream:
            tree = ast.parse(stream.read(), source)
        names = ('_load_persistent_alpha_cache', '_save_persistent_alpha_cache',
                 '_persistent_alpha_key', '_remember_persistent_alpha',
                 '_alpha_cache_key', '_alpha_damage', '_on_items_cache_sync_completed',
                 '_patch_items_invalidation')
        nodes = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
        self.assertEqual(len(nodes), len(names))
        test = self

        class NativeParams(object):
            def __init__(self, vehicle):
                test.calls.append(vehicle.intCD)
                self.avgDamage = vehicle.alpha

        self.ns = dict(
            os=os, io=io, json=json, tempfile=tempfile, hashlib=hashlib, time=time,
            OrderedDict=OrderedDict, PERSISTENT_ALPHA_MAX_ENTRIES=4096,
            ITEMS_INVALIDATION_CONTEXT={'result': None, 'full': True},
            PERSISTENT_ALPHA_PATH=self.path, VehicleParams=NativeParams,
            getClientVersion=lambda: self.version,
            getKpiFactors=lambda vehicle: Object(getFactor=lambda name: vehicle.kpi.get(name, 0)),
            _register_callback=lambda delay, callback: self.callbacks.append(callback) or len(self.callbacks),
            _refresh_all_models=lambda *args, **kwargs: None,
            GUI_ITEM_TYPE=Object(VEHICLE=1),
            CACHE_SYNC_REASON=Object(SHOW_GUI=1, CLIENT_UPDATE=2, SHOP_RESYNC=3,
                                     INVENTORY_RESYNC=4, DOSSIER_RESYNC=5, STATS_RESYNC=6),
            LOGGER=Object(info=lambda *args: None, warning=lambda *args: None,
                          exception=lambda *args: self.errors.append(args),
                          debug=lambda *args, **kwargs: None))
        exec compile(ast.Module(body=nodes), source, 'exec') in self.ns
        self.new_session()

    def tearDown(self):
        shutil.rmtree(self.directory)

    def new_session(self):
        self.ns['ALPHA_DAMAGE_CACHE'] = {}
        self.ns['ALPHA_DAMAGE_STATS'] = {'hits': 0, 'computed': 0}
        self.ns['PERSISTENT_ALPHA_STATE'] = dict(
            loaded=False, version=None, entries=OrderedDict(), dirty=False,
            legacy={}, scheduled=False, disabled=False)
        self.callbacks[:] = []

    def vehicle(self, cd, alpha=240):
        shell = Object(compactDescr=21, armorDamage=(240, 0), damageRandomization=0.25)
        descriptor = Object(gun=Object(compactDescr=11, shots=[Object(shell=shell)]),
                            shot=Object(shell=shell), activeGunShotIndex=0)
        return Object(intCD=cd, descriptor=descriptor, alpha=alpha, kpi={})

    def save(self):
        self.ns['_save_persistent_alpha_cache']()
        self.assertEqual(self.errors, [])
        self.assertFalse(self.ns['PERSISTENT_ALPHA_STATE']['dirty'])

    def test_925_vehicles_restart_and_one_new_vehicle(self):
        for cd in range(1, 926):
            self.assertEqual(self.ns['_alpha_damage'](self.vehicle(cd)), 240)
        self.assertEqual(len(self.calls), 925)
        self.assertEqual(len(self.callbacks), 1)
        self.save()
        self.new_session()
        for cd in range(1, 926):
            self.assertEqual(self.ns['_alpha_damage'](self.vehicle(cd)), 240)
        self.assertEqual(len(self.calls), 925)
        self.assertEqual(self.ns['ALPHA_DAMAGE_STATS'],
                         {'hits': 925, 'computed': 0, 'persistent': 925})
        self.assertEqual(self.callbacks, [])
        self.assertEqual(self.ns['_alpha_damage'](self.vehicle(926)), 240)
        self.assertEqual(self.calls[-1], 926)
        self.assertEqual(self.ns['ALPHA_DAMAGE_STATS']['computed'], 1)
        self.save()
        self.new_session()
        self.assertEqual(self.ns['_alpha_damage'](self.vehicle(926)), 240)
        self.assertEqual(len(self.calls), 926)

    def test_persistent_entries_are_bounded_across_saves_and_sessions(self):
        self.ns['_load_persistent_alpha_cache']()
        for i in range(4200):
            self.ns['_remember_persistent_alpha']((str(i + 1), '%064x' % i), 240)
        entries = self.ns['PERSISTENT_ALPHA_STATE']['entries']
        self.assertEqual(len(entries), 4096)
        self.assertNotIn('1', entries)
        self.assertIn('4200', entries)
        self.save()
        self.new_session()
        self.ns['_load_persistent_alpha_cache']()
        self.assertEqual(len(self.ns['PERSISTENT_ALPHA_STATE']['entries']), 4096)
        self.ns['_remember_persistent_alpha'](('5001', '%064x' % 5000), 250)
        self.assertEqual(len(self.ns['PERSISTENT_ALPHA_STATE']['entries']), 4096)
        self.save()

    def test_oversized_vehicle_cache_is_pruned(self):
        entries = OrderedDict((str(i + 1), {'fingerprint': '%064x' % i, 'alpha': 240})
                              for i in range(4200))
        with open(self.path, 'w') as stream:
            json.dump({'schema': 2, 'clientVersion': self.version, 'entries': entries}, stream)
        self.ns['_load_persistent_alpha_cache']()
        self.assertEqual(len(self.ns['PERSISTENT_ALPHA_STATE']['entries']), 4096)
        self.assertTrue(self.ns['PERSISTENT_ALPHA_STATE']['dirty'])
        self.save()

    def test_changed_damage_inputs_are_not_reused_between_sessions(self):
        for change in ('base', 'randomization', 'lower', 'upper', 'shell'):
            self.new_session()
            vehicle = self.vehicle(1)
            self.ns['_alpha_damage'](vehicle)
            self.save()
            self.new_session()
            vehicle.alpha = 250
            shell = vehicle.descriptor.shot.shell
            if change == 'base':
                shell.armorDamage = (250, 0)
            elif change == 'randomization':
                shell.damageRandomization = 0.1
            elif change == 'shell':
                shell.compactDescr = 22
            else:
                name = ('damageAndPiercingDistributionLowerBound' if change == 'lower'
                        else 'damageAndPiercingDistributionUpperBound')
                vehicle.kpi[name] = 2.0
            before = len(self.calls)
            self.assertEqual(self.ns['_alpha_damage'](vehicle), 250)
            self.assertEqual(len(self.calls), before + 1)

    def test_repeated_changes_replace_one_identifiable_vehicle_record(self):
        vehicle = self.vehicle(1)
        other = self.vehicle(2)
        self.ns['_alpha_damage'](other)
        for index in range(20):
            vehicle.kpi['damageAndPiercingDistributionUpperBound'] = index
            vehicle.alpha = 240 + index
            self.ns['_on_items_cache_sync_completed'](2, {1: {1}})
            self.callbacks[-1]()
            self.assertEqual(self.ns['_alpha_damage'](vehicle), 240 + index)
            entries = self.ns['PERSISTENT_ALPHA_STATE']['entries']
            self.assertEqual(set(entries), {'1', '2'})
            self.assertEqual(entries['1']['alpha'], 240 + index)
            self.assertEqual(entries['1']['fingerprint'], self.ns['_persistent_alpha_key'](vehicle)[1])
            self.assertEqual(entries['2']['alpha'], 240)
        self.save()
        with open(self.path, 'r') as stream:
            saved = json.load(stream)
        self.assertEqual(saved['schema'], 2)
        self.assertEqual(len(saved['entries']), 2)
        self.new_session()
        before = len(self.calls)
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 259)
        self.assertEqual(len(self.calls), before)
        vehicle.kpi['damageAndPiercingDistributionUpperBound'] = 0
        vehicle.alpha = 240
        self.ns['_on_items_cache_sync_completed'](2, {1: {1}})
        self.callbacks[-1]()
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 240)
        self.assertEqual(len(self.calls), before + 1)
        self.assertEqual(len(self.ns['PERSISTENT_ALPHA_STATE']['entries']), 2)

    def test_gun_switch_back_replaces_persistent_record_in_same_session(self):
        vehicle = self.vehicle(1)
        self.ns['_alpha_damage'](vehicle)
        vehicle.descriptor.gun.compactDescr = 12
        vehicle.descriptor.shot.shell.armorDamage = (320, 0)
        vehicle.alpha = 320
        self.ns['_alpha_damage'](vehicle)
        vehicle.descriptor.gun.compactDescr = 11
        vehicle.descriptor.shot.shell.armorDamage = (240, 0)
        vehicle.alpha = 240
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 240)
        self.assertEqual(self.calls, [1, 1, 1])
        self.assertEqual(len(self.ns['ALPHA_DAMAGE_CACHE']), 1)
        self.assertEqual(self.ns['PERSISTENT_ALPHA_STATE']['entries']['1']['alpha'], 240)

    def test_legacy_hashes_migrate_only_after_matching_live_vehicle_inputs(self):
        vehicle = self.vehicle(1)
        key = self.ns['_persistent_alpha_key'](vehicle)
        legacy = {key[1]: 240, 'f' * 64: 999}
        with open(self.path, 'w') as stream:
            json.dump({'schema': 1, 'clientVersion': self.version, 'entries': legacy}, stream)
        self.new_session()
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 240)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.ns['PERSISTENT_ALPHA_STATE']['entries'],
                         {'1': {'fingerprint': key[1], 'alpha': 240}})
        self.save()
        with open(self.path, 'r') as stream:
            saved = json.load(stream)
        self.assertEqual(saved['schema'], 2)
        self.assertEqual(set(saved['entries']), {'1'})
        self.new_session()
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 240)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.ns['_alpha_damage'](self.vehicle(2)), 240)
        self.assertEqual(self.calls, [2])

    def test_invalid_vehicle_record_ids_and_fingerprints_are_rejected(self):
        for key, record in (('01', {'fingerprint': '0' * 64, 'alpha': 240}),
                            ('0', {'fingerprint': '0' * 64, 'alpha': 240}),
                            ('1', {'fingerprint': 'invalid', 'alpha': 240}),
                            ('1', 240)):
            with open(self.path, 'w') as stream:
                json.dump({'schema': 2, 'clientVersion': self.version,
                           'entries': {key: record}}, stream)
            self.new_session()
            before = len(self.errors)
            self.ns['_alpha_damage'](self.vehicle(1))
            self.assertEqual(len(self.errors), before + 1)

    def test_927_legacy_configs_become_925_identifiable_vehicle_records(self):
        vehicles = [self.vehicle(i) for i in range(1, 926)]
        legacy = dict((self.ns['_persistent_alpha_key'](vehicle)[1], 240)
                      for vehicle in vehicles)
        legacy.update({'a' * 64: 250, 'b' * 64: 260})
        with open(self.path, 'w') as stream:
            json.dump({'schema': 1, 'clientVersion': self.version, 'entries': legacy}, stream)
        self.new_session()
        for vehicle in vehicles:
            self.assertEqual(self.ns['_alpha_damage'](vehicle), 240)
        self.assertEqual(self.calls, [])
        self.save()
        with open(self.path, 'r') as stream:
            saved = json.load(stream)
        self.assertEqual(saved['schema'], 2)
        self.assertEqual(set(saved['entries']), set(str(i) for i in range(1, 926)))
        self.assertEqual(len(saved['entries']), 925)

    def test_partial_sync_revalidates_changed_kpi_and_preserves_other_vehicle(self):
        changed, other = self.vehicle(1), self.vehicle(2)
        self.ns['_alpha_damage'](changed)
        self.ns['_alpha_damage'](other)
        changed.kpi['damageAndPiercingDistributionUpperBound'] = 2
        changed.alpha = 250
        self.ns['_on_items_cache_sync_completed'](2, {1: {1}})
        self.callbacks[-1]()
        self.assertEqual(self.ns['_alpha_damage'](changed), 250)
        self.assertEqual(self.ns['_alpha_damage'](other), 240)
        self.assertEqual(self.calls, [1, 2, 1])

    def test_same_alpha_inputs_after_full_sync_reuse_persistent_entries(self):
        vehicle = self.vehicle(1)
        self.ns['_alpha_damage'](vehicle)
        self.ns['_on_items_cache_sync_completed'](2, {})
        self.callbacks[-1]()
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 240)
        self.assertEqual(self.calls, [1])
        self.assertEqual(self.ns['ALPHA_DAMAGE_STATS']['persistent'], 1)

    def test_four_account_settings_updates_do_not_run_fingerprints_for_925_vehicles(self):
        vehicles = [self.vehicle(i) for i in range(1, 926)]
        for vehicle in vehicles:
            self.ns['_alpha_damage'](vehicle)
        class Items(object):
            def invalidateCache(self, diff=None):
                return {}
        items = Items()
        self.ns['SERVICES'] = Object(itemsCache=Object(items=items))
        self.ns['_patch_items_invalidation'](items)
        def unexpected(vehicle):
            raise AssertionError('Settings-only update must not run a fingerprint')
        self.ns['_persistent_alpha_key'] = unexpected
        for settings in ({74: 68}, {74: 4}, {73: 1073741824}, {73: 0}):
            result = items.invalidateCache({'intUserSettings': settings})
            self.ns['_on_items_cache_sync_completed'](2, result)
            self.callbacks[-1]()
            for vehicle in vehicles:
                self.assertEqual(self.ns['_alpha_damage'](vehicle), 240)
        self.assertEqual(len(self.calls), 925)
        self.assertEqual(self.ns['ALPHA_DAMAGE_STATS']['computed'], 925)
        self.assertEqual(self.ns['ALPHA_DAMAGE_STATS']['hits'], 3700)

    def test_client_update_and_schema_update_discard_saved_entries(self):
        self.ns['_alpha_damage'](self.vehicle(1))
        self.save()
        self.version = 'test-client-2'
        self.new_session()
        self.ns['_alpha_damage'](self.vehicle(1))
        self.assertEqual(self.calls, [1, 1])
        self.save()
        with open(self.path, 'r') as stream:
            data = json.load(stream)
        data['schema'] = 99
        with open(self.path, 'w') as stream:
            json.dump(data, stream)
        self.new_session()
        self.ns['_alpha_damage'](self.vehicle(1))
        self.assertEqual(self.calls, [1, 1, 1])

    def test_corrupt_cache_reports_error_and_rebuilds(self):
        with open(self.path, 'w') as stream:
            stream.write('not json')
        self.ns['_alpha_damage'](self.vehicle(1))
        self.assertEqual(len(self.errors), 1)
        self.assertEqual(self.calls, [1])
        self.errors[:] = []
        self.save()
        self.new_session()
        self.ns['_alpha_damage'](self.vehicle(1))
        self.assertEqual(self.calls, [1])

    def test_invalid_entry_is_rejected_not_used_as_alpha(self):
        with open(self.path, 'w') as stream:
            json.dump({'schema': 2, 'clientVersion': self.version,
                       'entries': {'1': {'fingerprint': '0' * 64, 'alpha': True}}}, stream)
        self.ns['_alpha_damage'](self.vehicle(1))
        self.assertEqual(len(self.errors), 1)
        self.assertEqual(self.calls, [1])

    def test_failed_replacement_preserves_previous_cache(self):
        self.ns['_alpha_damage'](self.vehicle(1))
        self.save()
        with open(self.path, 'rb') as stream:
            old = stream.read()
        self.ns['_alpha_damage'](self.vehicle(2))
        def rename(source, destination):
            if source.endswith('.tmp'):
                raise OSError('test write failure')
            os.rename(source, destination)
        self.ns['os'] = Object(**dict((name, getattr(os, name)) for name in (
            'path', 'makedirs', 'close', 'fsync', 'remove')))
        self.ns['os'].rename = rename
        self.ns['_save_persistent_alpha_cache']()
        self.assertEqual(len(self.errors), 1)
        self.assertTrue(self.ns['PERSISTENT_ALPHA_STATE']['dirty'])
        with open(self.path, 'rb') as stream:
            self.assertEqual(stream.read(), old)
        self.assertEqual(os.listdir(self.directory), ['alpha_cache.json'])

    def test_interrupted_save_recovers_backup_and_can_save_again(self):
        self.ns['_alpha_damage'](self.vehicle(1))
        self.save()
        os.rename(self.path, self.path + '.bak')
        self.new_session()
        self.assertEqual(self.ns['_alpha_damage'](self.vehicle(1)), 240)
        self.assertEqual(self.calls, [1])
        self.ns['_alpha_damage'](self.vehicle(2))
        self.save()
        self.assertEqual(os.listdir(self.directory), ['alpha_cache.json'])

    def test_mod_imports_do_not_require_ctypes(self):
        source = os.path.join(os.path.dirname(__file__), '..', 'res', 'scripts',
                              'client', 'gui', 'mods', 'mod_hangar_carousel_classic.py')
        with open(source, 'rb') as stream:
            tree = ast.parse(stream.read(), source)
        imports = [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
                   for alias in node.names]
        self.assertNotIn('ctypes', imports)
        self.assertNotIn('_ctypes', imports)

    def test_unknown_client_version_uses_native_without_persistence(self):
        self.version = ''
        self.ns['_alpha_damage'](self.vehicle(1))
        self.assertEqual(self.calls, [1])
        self.assertFalse(os.path.exists(self.path))
        self.assertEqual(self.callbacks, [])

    def test_fallback_value_is_not_persisted_under_primary_vehicle_inputs(self):
        vehicle = self.vehicle(1)
        fallback = self.vehicle(1, alpha=320)
        def provider(candidate):
            if candidate is vehicle:
                raise ValueError('primary native parameters unavailable')
            return Object(avgDamage=candidate.alpha)
        self.ns['VehicleParams'] = provider
        self.ns['SERVICES'] = Object(itemsCache=Object(items=Object(
            getItemByCD=lambda cd: fallback, getStockVehicle=lambda cd: None)))
        self.assertEqual(self.ns['_alpha_damage'](vehicle), 320)
        self.assertEqual(self.ns['PERSISTENT_ALPHA_STATE']['entries'], {})
        self.assertEqual(self.callbacks, [])

    def test_native_input_validation_has_no_vehicleparams_call(self):
        vehicle = self.vehicle(1)
        key = self.ns['_persistent_alpha_key'](vehicle)
        self.assertEqual(key[0], '1')
        self.assertEqual(len(key[1]), 64)
        self.assertEqual(self.calls, [])

    def test_second_start_diagnostic_counts_persistent_reuse_and_validation_time(self):
        from build_diagnostic import instrument
        vehicle = self.vehicle(1)
        self.ns['_alpha_damage'](vehicle)
        self.save()
        self.new_session()
        source = os.path.join(os.path.dirname(__file__), '..', 'res', 'scripts',
                              'client', 'gui', 'mods', 'mod_hangar_carousel_classic.py')
        with open(source, 'rb') as stream:
            text = stream.read()
        with open(os.path.join(os.path.dirname(__file__), 'carousel_diagnostics.py'), 'rb') as stream:
            helpers = stream.read()
        code = instrument(text, helpers, source)
        alpha = next(value for value in code.co_consts if isinstance(value, types.CodeType)
                     and value.co_name == '_alpha_damage')
        self.ns['_alpha_damage'] = types.FunctionType(alpha, self.ns)
        self.ns['_get_vehicle_dossier'] = lambda vehicle_id: None
        self.ns['_build_stats'] = lambda: self.ns['_alpha_damage'](vehicle)
        self.ns['_build_payload'] = lambda: self.ns['_build_stats']()
        self.ns.update(DOSSIER_CACHE_GENERATION=1, MOD_VERSION='test',
                       DOSSIER_CACHE={})
        exec compile(helpers, '<diagnostic helpers>', 'exec') in self.ns
        now = [0.0]
        self.ns['_clock'] = lambda: now[0]
        original = self.ns['_persistent_alpha_key']
        def fingerprint(vehicle):
            now[0] += 0.001
            return original(vehicle)
        self.ns['_persistent_alpha_key'] = fingerprint
        messages = []
        self.ns['LOGGER'].info = lambda fmt, *args: messages.append(fmt % args)
        self.assertEqual(self.ns['_build_payload'](), 240)
        self.assertEqual(self.calls, [1])
        profile = next(message for message in messages if 'HCC DIAG' in message)
        self.assertIn('alpha_persistent_reused=1', profile)
        self.assertIn('alpha_fingerprint_ms=1.000', profile)
        self.assertIn('alpha_reused=1 alpha_computed=0', profile)

    def test_fingerprint_tracks_actual_native_alpha_formula_and_kpi_aggregation(self):
        scripts = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..',
                                              'wot-src-EU', 'sources', 'res', 'scripts'))
        scripts = os.environ.get('WOT_SOURCE_ROOT', scripts)
        parameters = os.path.join(scripts, 'client', 'gui', 'shared', 'items_parameters')
        with open(os.path.join(parameters, 'params.py'), 'rb') as stream:
            tree = ast.parse(stream.read())
        native = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                      and node.name == 'VehicleParams')
        native.body = [node for node in native.body if isinstance(node, ast.FunctionDef)
                       and node.name in ('avgDamage', '__calculateDamageOrPiercingRandom',
                                         '__getattr__')]
        native.bases = [ast.Name(id='object', ctx=ast.Load())]
        with open(os.path.join(parameters, 'functions.py'), 'rb') as stream:
            functions = ast.parse(stream.read())
        nodes = [node for node in functions.body
                 if isinstance(node, (ast.ClassDef, ast.FunctionDef))
                 and node.name in ('_KpiDict', 'getKpiFactors')]
        from collections import defaultdict
        native_ns = dict(defaultdict=defaultdict, viewkeys=lambda data: set(data),
                         viewitems=lambda data: data.items(),
                         KPI=Object(Type=Object(MUL=1),
                                    Name=Object(hasValue=lambda name: name in (
                                        'damageAndPiercingDistributionLowerBound',
                                        'damageAndPiercingDistributionUpperBound'))),
                         kpiFromCrewSkills=lambda vehicle: vehicle.crew_kpis,
                         round_py2_style_int=lambda value: int(round(value)),
                         _DO_TTC_LOG=False)
        nodes.append(native)
        exec compile(ast.fix_missing_locations(ast.Module(body=nodes)),
                     '<native alpha reference>', 'exec') in native_ns
        self.ns['getKpiFactors'] = native_ns['getKpiFactors']
        vehicle = self.vehicle(1)
        device_kpis = []
        vehicle.descriptor.modifications = set()
        vehicle.postProgression = Object(iterUnorderedSteps=lambda: [])
        device = Object(descriptor=Object(categories=set()),
                        getKpi=lambda vehicle: device_kpis)
        vehicle.optDevices = Object(
            installed=[device],
            getSlot=lambda index: Object(item=Object(categories=set())))
        vehicle.consumables = Object(installed=[])
        vehicle.battleBoosters = Object(installed=[])
        vehicle.crew_kpis = []

        def reference(vehicle):
            provider = native_ns['VehicleParams']()
            provider._itemDescr = vehicle.descriptor
            provider._VehicleParams__kpi = native_ns['getKpiFactors'](vehicle)
            return provider

        self.ns['VehicleParams'] = reference
        initial_key = self.ns['_persistent_alpha_key'](vehicle)
        initial = self.ns['_alpha_damage'](vehicle)
        self.save()
        self.new_session()
        self.assertEqual(self.ns['_alpha_damage'](vehicle), initial)
        self.assertEqual(self.ns['ALPHA_DAMAGE_STATS']['computed'], 0)
        device_kpis.append(Object(name='damageAndPiercingDistributionUpperBound',
                                  value=2.0, type=0, specValue=None))
        self.new_session()
        self.assertNotEqual(self.ns['_persistent_alpha_key'](vehicle), initial_key)
        self.assertEqual(self.ns['_alpha_damage'](vehicle), reference(vehicle).avgDamage)
        self.assertNotEqual(reference(vehicle).avgDamage, initial)
        self.assertEqual(self.ns['ALPHA_DAMAGE_STATS']['computed'], 1)


if __name__ == '__main__':
    unittest.main()
