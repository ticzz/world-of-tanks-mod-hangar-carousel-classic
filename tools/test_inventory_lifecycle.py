"""Python 2.7 regression tests for native inventory startup and recovery."""
from __future__ import absolute_import, division

import ast
import json
import os
import time
import unittest


class Logger(object):
    def __init__(self):
        self.messages = []

    def info(self, message, *args):
        self.messages.append(('info', message % args))

    def warning(self, message, *args):
        self.messages.append(('warning', message % args))

    def debug(self, message, *args):
        self.messages.append(('debug', message % args))

    def exception(self, message, *args):
        raise AssertionError(message % args)


class Model(object):
    def __init__(self):
        self.state = 'previous state'
        self.filters = 'previous filters'

    def setStateJson(self, value):
        self.state = value

    def setActiveFiltersJson(self, value):
        self.filters = value


class InventoryLifecycleTests(unittest.TestCase):
    def setUp(self):
        source = os.path.join(os.path.dirname(__file__), '..', 'res', 'scripts',
                              'client', 'gui', 'mods', 'mod_hangar_carousel_classic.py')
        with open(source, 'rb') as stream:
            tree = ast.parse(stream.read(), source)
        names = ('_inventory_vehicles', '_build_payload', '_publish_payload',
                 '_patch_vehicle_statistics_presenter', '_add_safe_provider',
                 '_is_frontline_filter', '_is_frontline_hangar_active',
                 '_is_allowed_hangar_path', '_is_hangar_context_active',
                 '_normalized_card_stats_config', '_refresh_all_models',
                 '_native_provider_method', '_refresh_native_provider',
                 '_refresh_native_vehicle_model', '_refresh_statistics_presenters',
                 '_set_filter_state', '_build_lightweight_payload', '_build_sort_json',
                 '_sync_sort_property', '_on_items_cache_sync_completed',
                 '_invalidate_dossier_cache', '_patch_items_invalidation')
        nodes = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
        self.assertEqual(len(nodes), len(names))
        model_class = next(node for node in tree.body
                           if isinstance(node, ast.ClassDef)
                           and node.name == 'HangarCarouselClassicModel')
        refresh = next(node for node in model_class.body
                       if isinstance(node, ast.FunctionDef) and node.name == 'refresh')
        refresh.name = 'refresh_model'
        nodes.append(refresh)
        self.logger = Logger()
        self.model = Model()
        self.callbacks = []
        self.ns = {
            'LOGGER': self.logger, 'json': json,
            'STATISTICS_PRESENTERS': [], 'INVENTORY_WAIT_STATE': None,
            'LAST_PAYLOAD': None, 'LAST_PAYLOAD_SIGNATURE': None,
            'LAST_DATA_SUMMARY': None, 'MOD_VERSION': 'test',
            'CONFIG': {'cardStats': {'enabled': False}},
            'RUNTIME_STATE': {}, 'ACTIVE_FILTERS': set(),
            'DOSSIER_CACHE_GENERATION': 0, 'FILTER_ORDER': [],
            'DOSSIER_CACHE': {}, 'MARKS_INCOMPLETE_CACHE': {},
            'ALPHA_DAMAGE_CACHE': {}, 'ALPHA_DAMAGE_STATS': {'hits': 0, 'computed': 0},
            'ITEMS_INVALIDATION_CONTEXT': {'result': None, 'full': True},
            'dependency': None, 'IHangarSpace': None,
            'HANGAR_GUARD_STATE': {'active': None, 'spacePath': None},
            'ALLOWED_HANGAR_PREFIXES': ('spaces/hangar_v4', 'spaces/h33_comp7'),
            'time': time,
            '_register_callback': lambda delay, callback: self.callbacks.append(callback),
            '_alpha_cache_key': lambda vehicle: getattr(vehicle, 'setup', None),
            '_build_stats': lambda vehicle, *args: {
                'alphaDamage': getattr(vehicle, 'alpha', 240)},
            '_get_configured_sorting_criteria': lambda: [],
            '_get_sort_value': lambda *args: 0,
            '_matches': lambda filter_id, vehicle: getattr(vehicle, 'allowed', True),
            'MODELS': [self.model],
            '_is_hangar_context_active': lambda: True,
            '_carousel_auto': lambda: False,
            '_sort_mode': lambda: 'default',
            '_sort_descending': lambda: False,
            '_get_sort_option_keys': lambda: [],
            '_current_carousel_payload': lambda count: {'rows': 1},
            '_remove_legacy_playlists': lambda: None,
            '_apply_auto_rows': lambda count: None,
            'getClientLanguage': lambda: 'en',
        }
        account = type('Items', (), {'getAccountDossier': lambda self: None})()
        cache = type('Cache', (), {'items': account})()
        self.ns['SERVICES'] = type('Services', (), {'itemsCache': cache})()
        exec compile(ast.Module(body=nodes), source, 'exec') in self.ns
        self.ns['FILTER_PROVIDERS'] = []
        self.ns['CACHE_SYNC_REASON'] = type('Reasons', (), dict(
            SHOW_GUI=1, CLIENT_UPDATE=2, SHOP_RESYNC=3, INVENTORY_RESYNC=4,
            DOSSIER_RESYNC=5, STATS_RESYNC=6))
        self.ns['GUI_ITEM_TYPE'] = type('ItemTypes', (), {'VEHICLE': 1})
        self.model.refresh = lambda: self.ns['refresh_model'](self.model)

    def add_presenter(self, vehicles):
        component = type('Component', (), {'vehicles': vehicles})()
        presenter = type('Presenter', (), {'_vehiclesComponent': component})()
        self.ns['STATISTICS_PRESENTERS'].append(presenter)
        return presenter

    def test_wait_preserves_state_and_cache_without_warning_spam(self):
        previous = {'totalVehicles': 3}
        self.ns['LAST_PAYLOAD'] = previous
        self.ns['LAST_PAYLOAD_SIGNATURE'] = ('previous',)
        for _ in range(3):
            self.model.refresh()
            self.ns['_publish_payload'](self.ns['_build_payload']())
        self.assertEqual(self.model.state, 'previous state')
        self.assertEqual(self.model.filters, 'previous filters')
        self.assertIs(self.ns['LAST_PAYLOAD'], previous)
        self.assertEqual(self.ns['LAST_PAYLOAD_SIGNATURE'], ('previous',))
        self.assertEqual(len(self.logger.messages), 1)
        self.assertEqual(self.logger.messages[0][0], 'info')

    def test_malformed_component_warns_once_and_recovers(self):
        presenter = self.add_presenter(None)
        self.assertIsNone(self.ns['_inventory_vehicles']())
        self.assertIsNone(self.ns['_inventory_vehicles']())
        self.assertEqual(len(self.logger.messages), 1)
        self.assertEqual(self.logger.messages[0][0], 'warning')
        presenter._vehiclesComponent.vehicles = {}
        self.assertEqual(self.ns['_inventory_vehicles'](), {})
        self.assertIsNone(self.ns['INVENTORY_WAIT_STATE'])
        self.assertEqual(self.logger.messages[-1][0], 'info')

    def test_empty_ready_inventory_publishes_valid_zero_payload(self):
        self.add_presenter({})
        self.model.refresh()
        payload = json.loads(self.model.state)
        self.assertEqual(payload['totalVehicles'], 0)
        self.assertEqual(payload['stats'], {})
        self.assertTrue(payload['hangarActive'])

    def test_frontline_hangar_is_detected_from_its_native_filter(self):
        frontline_filter_class = type(
            'BattleCarouselFilter', (), {'__module__': 'frontline.gui.carousel_filter'})
        frontline_filter = frontline_filter_class()
        provider = type('Provider', (), {
            '_VehicleFiltersDataProvider__filter': frontline_filter})()
        self.ns['FILTER_PROVIDERS'].append(provider)
        space = type('HangarSpace', (), {'spacePath': 'spaces/frontline'})()
        self.ns['dependency'] = type('Dependency', (), {
            'instance': lambda self, interface: space})()
        self.ns['IHangarSpace'] = object()
        self.ns['HANGAR_GUARD_STATE'] = {'active': None, 'spacePath': None}
        self.ns['ALLOWED_HANGAR_PREFIXES'] = ('spaces/hangar_v4', 'spaces/h33_comp7')

        self.assertTrue(self.ns['_is_frontline_filter'](provider))
        self.assertTrue(self.ns['_is_frontline_hangar_active']())
        self.assertTrue(self.ns['_is_hangar_context_active']())

        standard_filter_class = type(
            'CarouselFilter', (), {'__module__': 'gui.filters.carousel_filter'})
        standard_provider = type('Provider', (), {
            '_VehicleFiltersDataProvider__filter': standard_filter_class()})()
        self.assertFalse(self.ns['_is_frontline_filter'](standard_provider))
        self.ns['FILTER_PROVIDERS'] = [standard_provider]
        self.assertFalse(self.ns['_is_hangar_context_active']())

    def test_native_update_recovers_without_polling_and_finalize_waits_again(self):
        class Presenter(object):
            def __init__(self, component):
                self._vehiclesComponent = component
                self.updated = None

            def _VehiclesStatisticsPresenter__updateVehicles(self, vehicles):
                self.updated = vehicles

            def _finalize(self):
                self.finalized = True

        self.ns['VehiclesStatisticsPresenter'] = Presenter
        self.ns['_patch_vehicle_statistics_presenter']()
        self.model.refresh()
        vehicle = type('Vehicle', (), {'intCD': 123})()
        vehicles = {123: vehicle}
        component = type('Component', (), {'vehicles': vehicles})()
        presenter = Presenter(component)
        presenter._VehiclesStatisticsPresenter__updateVehicles(vehicles)
        self.assertIs(presenter.updated, vehicles)
        self.assertEqual(json.loads(self.model.state)['totalVehicles'], 1)
        self.assertIsNone(self.ns['INVENTORY_WAIT_STATE'])
        presenter._finalize()
        self.assertTrue(presenter.finalized)
        self.assertEqual(self.ns['STATISTICS_PRESENTERS'], [])
        previous = self.model.state
        self.model.refresh()
        self.assertEqual(self.model.state, previous)
        self.assertEqual(self.ns['INVENTORY_WAIT_STATE'], 'presenter loading')

    def test_filter_provider_with_only_update_carousel(self):
        calls = []
        provider = type('Provider', (), {
            '_VehicleFiltersDataProvider__updateCarousel': lambda self:
                calls.append('carousel')})()
        self.assertTrue(self.ns['_refresh_native_provider'](provider))
        self.assertEqual(calls, ['carousel'])
        self.assertEqual(self.logger.messages, [])

    def test_missing_carousel_method_still_warns_and_returns_false(self):
        self.assertFalse(self.ns['_refresh_native_provider'](object()))
        self.assertEqual(len(self.logger.messages), 1)
        self.assertEqual(self.logger.messages[0][0], 'warning')
        self.assertIn('__updateCarousel', self.logger.messages[0][1])

    def test_filter_toggle_updates_layout_and_separate_vehicle_statistics(self):
        calls = []
        vehicles = {123: object()}
        provider = type('Provider', (), {
            '_VehicleFiltersDataProvider__updateCarousel': lambda self:
                calls.append('carousel')})()
        presenter = type('Presenter', (), {
            '_vehiclesComponent': type('Component', (), {'vehicles': vehicles})(),
            '_VehiclesStatisticsPresenter__updateVehicles': lambda self, values:
                calls.append(('statistics', values))})()
        self.ns.update({
            'FILTER_PROVIDERS': [provider],
            'STATISTICS_PRESENTERS': [presenter],
            'FILTER_ORDER': ['marks_incomplete'],
            'MODELS': [],
            '_save_runtime': lambda: None,
            '_sync_msa_filter_settings': lambda: None,
            '_sync_sort_property': lambda: None,
        })
        self.ns['_set_filter_state']('marks_incomplete')
        self.assertEqual(calls, ['carousel', ('statistics', vehicles)])
        self.assertEqual(self.ns['ACTIVE_FILTERS'], set(['marks_incomplete']))
        self.assertFalse(any(level == 'warning' for level, _ in self.logger.messages))

    def test_wait_does_not_publish_empty_native_filter_allowlist(self):
        self.ns['ACTIVE_FILTERS'].add('marks_incomplete')
        self.assertIsNone(self.ns['_build_sort_json']())
        writes = []
        view_model = type('ViewModel', (), {
            'transaction': lambda model: self.transaction(model),
            'setHccSortJson': lambda model, value: writes.append(value)})()
        self.ns['FILTER_PROVIDERS'] = [type('Provider', (), {'viewModel': view_model})()]
        self.ns['_sync_sort_property']()
        self.assertEqual(writes, [])
        vehicle = type('Vehicle', (), {'intCD': 123})()
        presenter = self.add_presenter({123: vehicle})
        self.ns['_sync_sort_property']()
        ready = json.loads(writes[-1])
        self.assertTrue(ready['filtered'])
        self.assertEqual(ready['allowed'], ['123'])
        presenter._vehiclesComponent.vehicles = {}
        self.ns['_sync_sort_property']()
        empty = json.loads(writes[-1])
        self.assertTrue(empty['filtered'])
        self.assertEqual(empty['allowed'], [])

    @staticmethod
    def transaction(model):
        class Transaction(object):
            def __enter__(self):
                return model
            def __exit__(self, *args):
                return False
        return Transaction()

    def test_gun_change_rebuilds_payload_with_same_vehicle_ids(self):
        self.ns['CONFIG']['cardStats']['enabled'] = True
        vehicle = type('Vehicle', (), {'intCD': 123, 'setup': (11, 21), 'alpha': 240})()
        self.add_presenter({123: vehicle})
        self.assertEqual(self.ns['_build_payload']()['stats']['123']['alphaDamage'], 240)
        vehicle.setup = (12, 21)
        vehicle.alpha = 320
        self.assertEqual(self.ns['_build_payload']()['stats']['123']['alphaDamage'], 320)

    def test_stats_reenable_rebuilds_and_unchanged_refresh_stays_lightweight(self):
        vehicle = type('Vehicle', (), {'intCD': 123})()
        self.add_presenter({123: vehicle})
        self.assertEqual(self.ns['_build_payload']()['stats'], {})
        self.ns['CONFIG']['cardStats']['enabled'] = True
        calls = []
        self.ns['_build_stats'] = lambda v, *args: calls.append(v) or {'alphaDamage': 240}
        enabled = self.ns['_build_lightweight_payload']()
        self.assertEqual(enabled['stats']['123']['alphaDamage'], 240)
        self.ns['_build_payload']()
        self.ns['_build_lightweight_payload']()
        self.assertEqual(len(calls), 1)
        self.ns['CONFIG']['cardStats']['enabled'] = False
        self.assertEqual(self.ns['_build_lightweight_payload']()['stats'], {})
        self.ns['CONFIG']['cardStats']['enabled'] = True
        self.ns['_build_lightweight_payload']()
        self.assertEqual(len(calls), 2)

    def test_stats_reenable_emits_new_diagnostic_for_all_vehicles(self):
        helper = os.path.join(os.path.dirname(__file__), 'carousel_diagnostics.py')
        with open(helper, 'rb') as stream:
            helpers = stream.read()
        self.ns['_get_vehicle_dossier'] = lambda vehicle_id: None
        exec compile(helpers, helper, 'exec') in self.ns
        vehicles = dict((i, type('Vehicle', (), {'intCD': i})())
                        for i in range(1, 926))
        self.add_presenter(vehicles)
        self.ns['_build_payload']()
        self.ns['CONFIG']['cardStats']['enabled'] = True
        payload = self.ns['_build_lightweight_payload']()
        self.assertEqual(len(payload['stats']), 925)
        profiles = [message for _, message in self.logger.messages if 'HCC DIAG' in message]
        self.assertEqual(len(profiles), 1)
        self.assertIn('vehicles=925', profiles[0])
        self.ns['_build_lightweight_payload']()
        profiles = [message for _, message in self.logger.messages if 'HCC DIAG' in message]
        self.assertEqual(len(profiles), 1)

    def test_inventory_and_crew_sync_invalidates_caches_before_refresh(self):
        calls = []
        def refreshed(reason, invalidate_dossier=False):
            self.assertEqual(self.ns['ALPHA_DAMAGE_CACHE'], {})
            self.assertTrue(invalidate_dossier)
            calls.append(reason)
        self.ns['_refresh_all_models'] = refreshed
        reasons = self.ns['CACHE_SYNC_REASON']
        for reason in (reasons.SHOW_GUI, reasons.CLIENT_UPDATE, reasons.SHOP_RESYNC,
                       reasons.INVENTORY_RESYNC, reasons.STATS_RESYNC):
            self.ns['ALPHA_DAMAGE_CACHE'][(123, 11, 21)] = 240
            self.ns['_on_items_cache_sync_completed'](reason, {})
            self.assertEqual(len(self.callbacks), 1)
            self.callbacks.pop(0)()
        self.assertEqual(len(calls), 5)

    def test_dossier_only_sync_preserves_alpha_cache(self):
        self.ns['ALPHA_DAMAGE_CACHE']['setup'] = 240
        calls = []
        self.ns['_refresh_all_models'] = lambda *args, **kwargs: calls.append(kwargs)
        self.ns['_on_items_cache_sync_completed'](self.ns['CACHE_SYNC_REASON'].DOSSIER_RESYNC)
        self.assertEqual(self.ns['ALPHA_DAMAGE_CACHE'], {'setup': 240})
        self.assertEqual(calls, [{'invalidate_dossier': True}])

    def test_partial_sync_invalidates_only_all_setups_of_affected_vehicles(self):
        cache = self.ns['ALPHA_DAMAGE_CACHE']
        cache.update({(123, 11): 240, (123, 12): 320, (456, 11): 400})
        self.ns['_refresh_all_models'] = lambda *args, **kwargs: None
        changed = {1: {123}, 8: {999}}
        self.ns['_on_items_cache_sync_completed'](
            self.ns['CACHE_SYNC_REASON'].CLIENT_UPDATE, changed)
        changed[1].clear()
        self.assertEqual(len(cache), 3)
        self.callbacks.pop(0)()
        self.assertEqual(cache, {(456, 11): 400})

    def test_nonvehicle_partial_sync_preserves_alpha_cache(self):
        self.ns['ALPHA_DAMAGE_CACHE'][(123, 11)] = 240
        self.ns['_refresh_all_models'] = lambda *args, **kwargs: None
        self.ns['_on_items_cache_sync_completed'](
            self.ns['CACHE_SYNC_REASON'].CLIENT_UPDATE, {8: {999}})
        self.callbacks.pop(0)()
        self.assertEqual(self.ns['ALPHA_DAMAGE_CACHE'], {(123, 11): 240})

    def test_native_settings_only_empty_diff_preserves_925_alpha_entries(self):
        class Items(object):
            def invalidateCache(self, diff=None):
                return {}
        items = Items()
        self.ns['SERVICES'].itemsCache.items = items
        self.ns['_patch_items_invalidation'](items)
        self.ns['_patch_items_invalidation'](items)
        cache = self.ns['ALPHA_DAMAGE_CACHE']
        cache.update(((i, 11), 240) for i in range(1, 926))
        self.ns['_refresh_all_models'] = lambda *args, **kwargs: None
        for settings in ({74: 68}, {74: 4}, {73: 1073741824}, {73: 0}):
            result = items.invalidateCache({'intUserSettings': settings})
            self.ns['_on_items_cache_sync_completed'](2, result)
            self.callbacks.pop(0)()
            self.assertEqual(len(cache), 925)
        result = items.invalidateCache()
        self.ns['_on_items_cache_sync_completed'](2, result)
        self.callbacks.pop(0)()
        self.assertEqual(cache, {})

    def test_invalidation_hook_preserves_return_identity_and_exception(self):
        result = {1: {123}}
        class Items(object):
            def invalidateCache(self, diff=None):
                if diff == 'fail':
                    raise ValueError('native failure')
                return result
        items = Items()
        self.ns['SERVICES'].itemsCache.items = items
        self.ns['_patch_items_invalidation'](items)
        self.assertIs(items.invalidateCache({'inventory': {}}), result)
        self.assertIs(self.ns['ITEMS_INVALIDATION_CONTEXT']['result'], result)
        with self.assertRaises(ValueError):
            items.invalidateCache('fail')
        # Equal but distinct empty maps cannot inherit partial provenance.
        self.ns['ITEMS_INVALIDATION_CONTEXT'].update(result={}, full=False)
        self.ns['ALPHA_DAMAGE_CACHE'][(123, 11)] = 240
        self.ns['_refresh_all_models'] = lambda *args, **kwargs: None
        self.ns['_on_items_cache_sync_completed'](2, {})
        self.callbacks.pop(0)()
        self.assertEqual(self.ns['ALPHA_DAMAGE_CACHE'], {})

    def test_client_sync_refreshes_displayed_values_without_setup_change(self):
        vehicle = type('Vehicle', (), {'intCD': 123, 'setup': (11, 21), 'alpha': 240})()
        self.add_presenter({123: vehicle})
        self.ns['CONFIG']['cardStats']['enabled'] = True
        self.model.refresh()
        vehicle.alpha = 250
        self.ns['ALPHA_DAMAGE_CACHE']['old'] = 240
        self.ns['_on_items_cache_sync_completed'](self.ns['CACHE_SYNC_REASON'].CLIENT_UPDATE, {})
        self.callbacks.pop(0)()
        self.assertEqual(json.loads(self.model.state)['stats']['123']['alphaDamage'], 250)
        self.assertEqual(self.ns['ALPHA_DAMAGE_CACHE'], {})

    def test_inventory_sync_waits_until_native_component_has_updated(self):
        old = type('Vehicle', (), {'intCD': 123, 'setup': (11, 21), 'alpha': 240})()
        presenter = self.add_presenter({123: old})
        self.ns['CONFIG']['cardStats']['enabled'] = True
        self.model.refresh()
        self.ns['_on_items_cache_sync_completed'](self.ns['CACHE_SYNC_REASON'].CLIENT_UPDATE, {})
        self.assertEqual(json.loads(self.model.state)['stats']['123']['alphaDamage'], 240)
        new = type('Vehicle', (), {'intCD': 123, 'setup': (12, 21), 'alpha': 320})()
        presenter._vehiclesComponent.vehicles = {123: new}
        self.callbacks.pop(0)()
        self.assertEqual(json.loads(self.model.state)['stats']['123']['alphaDamage'], 320)


if __name__ == '__main__':
    unittest.main()
