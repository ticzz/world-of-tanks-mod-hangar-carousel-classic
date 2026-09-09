"""Hangar Carousel Classic bootstrap for the World of Tanks 2.x client.

The client embeds Python 2.7, so this module deliberately avoids Python 3-only
syntax. Custom filter predicates narrow the native vehicle-statistics model;
the Gameface layer supplies independent toggles and card overlays.
"""
from __future__ import absolute_import, division
import hashlib
import io
import json
import logging
import os
import random
import time
import zipfile
import BigWorld
import BattleReplay
from PlayerEvents import g_playerEvents
from helpers import getClientLanguage, getPreferencesDirPath
from dossiers2.ui.achievements import MARK_ON_GUN_RECORD
from frameworks.wulf import ViewModel
from gui.impl.gen.view_models.views.lobby.hangar.sub_views.vehicle_filter_model import VehicleFilterModel
from gui.impl.gen.view_models.views.lobby.tooltips.carousel_vehicle_tooltip_model import CarouselVehicleTooltipModel
from gui.impl.lobby.hangar.presenters.vehicle_filters_presenter import VehicleFiltersDataProvider
from gui.impl.lobby.hangar.presenters.vehicle_statistics_presenter import VehiclesStatisticsPresenter
from gui.impl.lobby.hangar.presenters.vehicle_playlists_presenter import VehiclePlaylistsPresenter
from gui.impl.lobby.tooltips.carousel_vehicle_tooltip import CarouselVehicleTooltipView
from gui.shared.items_parameters import params_helper as items_params_helper
from gui.veh_post_progression.models.progression import PostProgressionCompletion
from helpers import dependency
from openwg_gameface import gf_mod_inject
from skeletons.gui.game_control import IBattlePassController, IVehiclePlaylistsController
from skeletons.gui.shared import IItemsCache

try:
    from skeletons.gui.shared.utils import IHangarSpace
except Exception:
    IHangarSpace = None

try:
    from gui.filters import carousel_filter as carousel_filter_module
except Exception:
    carousel_filter_module = None
MOD_ID = 'mod_hangar_carousel_classic'
MOD_VERSION = '1.0.16'
MOD_LINKAGE_ID = 'mod_hangar.carousel.classic'
PLAYLIST_ID_PREFIX = 'mhcc_'
PREFERENCES_DIR = getPreferencesDirPath()
CONFIG_PATH = os.path.join(PREFERENCES_DIR, 'mods', 'mod_hangar_carousel_classic', 'config.json')
RUNTIME_PATH = os.path.join(PREFERENCES_DIR, 'mods', 'mod_hangar_carousel_classic', 'runtime.json')
LEGACY_CONFIG_PATH = os.path.join('res_mods', 'configs', 'hangar_carousel_classic', 'config.json')
LEGACY_RUNTIME_PATH = os.path.join('res_mods', 'configs', 'hangar_carousel_classic', 'runtime.json')
CONFIG_NEEDS_SAVE = False
JS_URL = 'coui://gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.js'
CSS_URL = 'coui://gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.css'
TOOLTIP_JS_URL = 'coui://gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.tooltip.js'
TOOLTIP_CSS_URL = 'coui://gui/gameface/mods/hcc/hangar_carousel_classic/hangar_carousel_classic.tooltip.css'
LOGGER = logging.getLogger('HangarCarouselClassic')
NATIVE_RESOURCE_HASHES = (
        ('res/packages/gui-part3.pkg', 'gui/gameface/_dist/production/mono/hangar/views/main/main.html/bundle.js',
         ('753102BFFDFE1A52B23706606F804CAC236463CB1A827A0EA3449E1D263FC6CE',
            '21B48CFFF0EDA9247413338CBEF3EDC2DD7BE0D1B6504F67AF05E163A22DF1A6',
            '21C58DA5788BDDF31655B3510B027505A2418355D299D50773E6F414F28779D0',
            '98D4D4060C141B5728F9126E4B43AD9E0E0BD6BA3FC72E14156391DB54737FBA')),
        ('res/packages/gui-part4.pkg', 'gui/gameface/_dist/production/mono/hangar/views/vehicle_tooltip/vehicle_tooltip.html/bundle.js',
         ('B1CBC96E18174947F5CC83E46A5511924DA9D7AEF139DFA8CB75AA79B366DA4E',
            '66AACCC3D55B62EFC6264359F133D51F04270A8E7E737FE1BB2FFB6461ECC1E4',
            '9E3C202258E9182E2788BAD4B09C3EDA969AB8F5A73A08CAA6A2B7E377C342C5')),
        ('res/packages/gui-part2.pkg', 'gui/gameface/_dist/production/mono/hangar/vehicle_tooltip/vehicle_tooltip.css',
         ('4D9D45F739F642F5CCD443386722045F319EC873352B159B36BAEA210249D822',
            'FED446477AD05AFC9556AC3FD92DF45573E8F9121466A562105BAAF695C61726'))
)
DEFAULT_CONFIG = {'schemaVersion': 5,
 'enabled': True,
 'filtering': {'enabled': True},
 'tankfilters': {'non_elite': {'enabled': False},
                 'not_ready': {'enabled': False},
                 'marks_incomplete': {'enabled': False},
                 'crew_not_maxed': {'enabled': False}},
 'cardStats': {'enabled': True,
               'fields': ['battles',
                          'winRate',
                          'averageDamage',
                          'alphaDamage',
                          'mastery',
                          'marksOnGun'],
               'minimumBattles': 1},
 'sorting': {'enabled': True,
             'nations_order': [],
             'types_order': [],
             'available_criteria': ['nation', 'type', 'level', '-level', 'maxBattleTier', '-maxBattleTier', 'premium', '-premium',
                                    'battles', '-battles', 'winRate', '-winRate', 'markOfMastery', '-markOfMastery',
                                    'averageDamage', '-averageDamage', 'alphaDamage', '-alphaDamage', 'marksOnGun', '-marksOnGun',
                                    'battlePassPoints', '-battlePassPoints'],
             'sorting_criteria': ['nation', 'type', 'level']},
 'actionCards': {'hideBuyTank': False,
                 'hideBuySlot': False,
                 'hideRestoreTank': False},
 'debug': False}
RUNTIME_DEFAULT = {'lastPlayed': {},
 'carouselRows': 0,
 'carouselRowsMode': 'manual',
 'activeFilters': [],
 'sortMode': 'nation',
 'sortDescending': False}

class _Services(object):
    itemsCache = dependency.descriptor(IItemsCache)
    playlists = dependency.descriptor(IVehiclePlaylistsController)
    battlePass = dependency.descriptor(IBattlePassController)


SERVICES = _Services()
FILTER_ORDER = ('all', 'non_elite', 'not_ready', 'marks_incomplete', 'crew_not_maxed')
SORT_CRITERIA_ORDER = ('nation', 'type', 'level', '-level', 'maxBattleTier', '-maxBattleTier', 'premium', '-premium',
                       'battles', '-battles', 'winRate', '-winRate', 'markOfMastery', '-markOfMastery',
                       'averageDamage', '-averageDamage', 'alphaDamage', '-alphaDamage', 'marksOnGun', '-marksOnGun',
                       'battlePassPoints', '-battlePassPoints', 'lastPlayed', '-lastPlayed')
SORT_DEFAULT_CRITERIA = ('nation', 'type', 'level')
SORT_UI_OPTION_ORDER = ('nation', 'type', 'level', 'maxBattleTier', 'premium', 'battles', 'winRate', 'markOfMastery',
                       'averageDamage', 'alphaDamage', 'marksOnGun', 'battlePassPoints', 'lastPlayed')
SORT_CRITERION_ALIASES = {'tier': 'level',
 'damageRating': 'averageDamage'}


def _default_sorting_criteria():
    return list(SORT_DEFAULT_CRITERIA)


def _normalize_sort_criterion(criterion):
    if not isinstance(criterion, basestring):
        return None
    token = criterion.strip()
    if not token:
        return None
    quote_chars = u'"\'\u2018\u2019\u201c\u201d\u201e\u201f'
    token = token.strip(quote_chars)
    if not token:
        return None
    reverse = token.startswith('-')
    name = token[1:] if reverse else token
    name = SORT_CRITERION_ALIASES.get(name, name)
    normalized = '%s%s' % ('-' if reverse else '', name)
    if normalized not in SORT_CRITERIA_ORDER:
        return None
    return normalized


def _normalize_sort_criteria(criteria, fallback=None):
    normalized = []
    seen = set()
    for criterion in criteria or []:
        normalized_criterion = _normalize_sort_criterion(criterion)
        if normalized_criterion is None or normalized_criterion in seen:
            continue
        normalized.append(normalized_criterion)
        seen.add(normalized_criterion)

    if normalized:
        return normalized
    if fallback is None:
        fallback = _default_sorting_criteria()
    return list(fallback)


def _get_available_sort_criteria():
    sorting = CONFIG.get('sorting', {})
    return _normalize_sort_criteria(sorting.get('available_criteria', SORT_CRITERIA_ORDER), fallback=SORT_CRITERIA_ORDER)


def _get_configured_sorting_criteria():
    sorting = CONFIG.get('sorting', {})
    raw_criteria = sorting.get('sorting_criteria')
    if raw_criteria is None:
        return _default_sorting_criteria()
    return _normalize_sort_criteria(raw_criteria, fallback=[])


def _get_sort_option_keys():
    allowed = set((criterion[1:] if criterion.startswith('-') else criterion for criterion in _get_available_sort_criteria()))
    return [ key for key in SORT_UI_OPTION_ORDER if key in allowed ]


def _patch_carousel_filter_compat():
    """Guard the native carousel filter against missing canInstallAttachments criteria."""
    if carousel_filter_module is None:
        return
    if getattr(carousel_filter_module, '_hcc_can_install_attachments_patched', False):
        return

    def _wrap_target(target, method_name):
        original_method = getattr(target, method_name, None)
        if not callable(original_method):
            return False
        if getattr(original_method, '_hcc_wrapped', False):
            return True

        def patched_method(*args, **kwargs):
            criteria = None
            if len(args) > 1:
                criteria = args[1]
            elif len(args) == 1:
                criteria = args[0]
            if criteria is None and 'criteria' in kwargs:
                criteria = kwargs['criteria']
            if hasattr(criteria, 'setdefault'):
                try:
                    criteria.setdefault('canInstallAttachments', False)
                except Exception:
                    pass
            try:
                return original_method(*args, **kwargs)
            except KeyError:
                if hasattr(criteria, 'setdefault'):
                    try:
                        criteria.setdefault('canInstallAttachments', False)
                        return original_method(*args, **kwargs)
                    except Exception:
                        return None
                return None
            except Exception:
                LOGGER.debug('Unable to apply HCC carousel filter compatibility patch', exc_info=True)
                return None

        patched_method._hcc_wrapped = True
        setattr(target, method_name, patched_method)
        return True

    patched = False
    patched = _wrap_target(carousel_filter_module, '_setCanInstallAttachmentsCriteria') or patched
    for value in vars(carousel_filter_module).values():
        if isinstance(value, type):
            patched = _wrap_target(value, '_setCanInstallAttachmentsCriteria') or patched

    if patched:
        carousel_filter_module._hcc_can_install_attachments_patched = True


def _deep_merge(base, override):
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def _migrate_config(loaded):
    """Migrate old config format to new sorting schema."""
    schema = loaded.get('schemaVersion', 0)
    
    # v0-4 -> v5: Convert old sortMode/descending to sorting_criteria
    if schema < 5:
        sorting = loaded.get('sorting', {})
        if 'sortMode' in sorting or 'descending' in sorting:
            old_mode = sorting.get('sortMode', 'default')
            old_descending = sorting.get('descending', True)
            
            # Map old modes to new sorting_criteria format
            if old_mode == 'default':
                sorting['sorting_criteria'] = _default_sorting_criteria()
            elif old_mode == 'battles':
                sorting['sorting_criteria'] = ['-battles' if old_descending else 'battles']
            elif old_mode == 'winRate':
                sorting['sorting_criteria'] = ['-winRate' if old_descending else 'winRate']
            elif old_mode == 'averageDamage':
                sorting['sorting_criteria'] = ['-averageDamage' if old_descending else 'averageDamage']
            elif old_mode == 'marksOnGun':
                sorting['sorting_criteria'] = ['-marksOnGun' if old_descending else 'marksOnGun']
            elif old_mode == 'lastPlayed':
                sorting['sorting_criteria'] = ['-lastPlayed' if old_descending else 'lastPlayed']
            
            # Remove old keys
            sorting.pop('sortMode', None)
            sorting.pop('descending', None)
            sorting.pop('options', None)
            sorting.pop('default', None)
            loaded['sorting'] = sorting
            LOGGER.info('Migrated config from sortMode/descending to sorting_criteria')

    tankfilters = loaded.get('tankfilters')
    if isinstance(tankfilters, dict) and 'favorite' in tankfilters:
        tankfilters.pop('favorite')
        LOGGER.info('Removed deprecated tankfilters.favorite; the vanilla client provides this filter')

    loaded['schemaVersion'] = 5
    return loaded


def _load_config():
    global CONFIG_NEEDS_SAVE
    for path in (CONFIG_PATH, LEGACY_CONFIG_PATH):
        try:
            with io.open(path, 'r', encoding='utf-8-sig') as config_file:
                loaded = json.load(config_file)
            if not isinstance(loaded, dict):
                raise ValueError('root value must be an object')
            if path != CONFIG_PATH:
                LOGGER.info('Loaded legacy config from %s; future saves will use %s', path, CONFIG_PATH)
            tankfilters = loaded.get('tankfilters')
            if path != CONFIG_PATH or (isinstance(tankfilters, dict) and 'favorite' in tankfilters):
                CONFIG_NEEDS_SAVE = True
            return _deep_merge(DEFAULT_CONFIG, _migrate_config(loaded))
        except IOError:
            continue
        except Exception:
            LOGGER.exception('Invalid config at %s', path)

    LOGGER.info('No user config at %s; using defaults', CONFIG_PATH)
    return _deep_merge(DEFAULT_CONFIG, {})


def _load_runtime():
    for path in (RUNTIME_PATH, LEGACY_RUNTIME_PATH):
        try:
            with io.open(path, 'r', encoding='utf-8-sig') as runtime_file:
                loaded = json.load(runtime_file)
            if isinstance(loaded, dict):
                if path != RUNTIME_PATH:
                    LOGGER.info('Loaded legacy runtime from %s; future saves will use %s', path, RUNTIME_PATH)
                return _deep_merge(RUNTIME_DEFAULT, loaded)
        except IOError:
            continue
        except Exception:
            LOGGER.exception('Invalid runtime state at %s', path)

    return _deep_merge(RUNTIME_DEFAULT, {})


def _playlist_id_prefix():
    return PLAYLIST_ID_PREFIX


def _is_hcc_playlist_id(value):
    return isinstance(value, basestring) and value.startswith(_playlist_id_prefix())


CONFIG = _load_config()
RUNTIME_STATE = _load_runtime()
if not os.path.isfile(CONFIG_PATH) and os.path.isfile(LEGACY_CONFIG_PATH):
    CONFIG_NEEDS_SAVE = True
if not os.path.isfile(RUNTIME_PATH) and os.path.isfile(LEGACY_RUNTIME_PATH):
    _save_runtime()
ACTIVE_FILTERS = set((filter_id for filter_id in RUNTIME_STATE.get('activeFilters', []) if filter_id in FILTER_ORDER and filter_id != 'all'))
MODELS = []
FILTER_PROVIDERS = []
STATISTICS_PRESENTERS = []
CALLBACK_IDS = []
FINAL_VISIBLE_VEHICLE_COUNT = None
LAST_DATA_SUMMARY = None
LAST_PAYLOAD = None
LAST_PAYLOAD_SIGNATURE = None
LEGACY_PLAYLISTS_REMOVED = False
TOOLTIP_PAYLOAD_LOGGED = False
ALLOWED_HANGAR_PREFIXES = ('spaces/hangar_v4',)
HANGAR_GUARD_STATE = {'active': None, 'spacePath': None}
SETTINGS_REGISTERED = False
MSA_API = None
MSA_SETTINGS = {}
MSA_SYNCING = False
SETTINGS_REGISTRATION_STATE = {
    'tries': 0,
    'delay': 0.35,
    'maxDelay': 8.0,
    'maxTries': 20,
    'unavailableLogged': False,
    'exhaustedLogged': False
}
DOSSIER_CACHE = {}
DOSSIER_CACHE_GENERATION = 0
DOSSIER_FETCH_COUNTER = 0
MAX_DOSSIER_FETCHES_PER_REFRESH = 256
COMPATIBILITY_WARNING_SHOWN = False

def _register_callback(delay, callback):
    # BigWorld callbacks are one-shot: once they fire, their id becomes
    # invalid. Without removing the id here, fini() would try to cancel
    # already-fired callbacks on shutdown and log spurious warnings.
    def _wrapped(*args, **kwargs):
        try:
            callback(*args, **kwargs)
        finally:
            try:
                CALLBACK_IDS.remove(callback_id[0])
            except (ValueError, IndexError):
                pass
    callback_id = [None]
    try:
        callback_id[0] = BigWorld.callback(delay, _wrapped)
        CALLBACK_IDS.append(callback_id[0])
        return callback_id[0]
    except Exception:
        LOGGER.exception('Unable to schedule callback %s', getattr(callback, '__name__', callback))


def _check_native_client_compatibility():
    global COMPATIBILITY_WARNING_SHOWN
    if COMPATIBILITY_WARNING_SHOWN:
        return
    try:
        game_root = os.getcwd()
        for package_rel_path, entry_path, supported_hashes in NATIVE_RESOURCE_HASHES:
            package_path = os.path.join(game_root, package_rel_path)
            if not os.path.isfile(package_path):
                return
            archive = zipfile.ZipFile(package_path, 'r')
            try:
                source = archive.read(entry_path)
            finally:
                archive.close()
            if hashlib.sha256(source).hexdigest().upper() not in supported_hashes:
                COMPATIBILITY_WARNING_SHOWN = True
                from gui import SystemMessages
                SystemMessages.pushMessage(
                    u'[Hangar Carousel Classic] Your World of Tanks client was updated. Please install a compatible mod update.',
                    type=SystemMessages.SM_TYPE.Warning)
                return
    except Exception:
        LOGGER.debug('Unable to verify native client resources', exc_info=True)


def _invalidate_dossier_cache(reason='unknown'):
    global DOSSIER_CACHE_GENERATION, LAST_PAYLOAD_SIGNATURE
    try:
        DOSSIER_CACHE.clear()
        DOSSIER_CACHE_GENERATION += 1
        LAST_PAYLOAD_SIGNATURE = None
        LOGGER.debug('Dossier cache invalidated (%s), generation=%d', reason, DOSSIER_CACHE_GENERATION)
    except Exception:
        LOGGER.exception('Unable to invalidate dossier cache (%s)', reason)


def _refresh_all_models(reason='unknown', invalidate_dossier=False):
    try:
        if invalidate_dossier:
            _invalidate_dossier_cache(reason)
        _sync_sort_property()
        for model in list(MODELS):
            try:
                model.refresh()
            except Exception:
                LOGGER.exception('Unable to refresh HCC model (%s)', reason)
    except Exception:
        LOGGER.exception('Unable to run global HCC refresh (%s)', reason)


def _schedule_post_battle_refresh():
    # Staggered refresh: immediate + delayed passes to catch late dossier updates.
    def refresh_after_battle():
        _refresh_all_models('post battle refresh', invalidate_dossier=True)
    for delay in (0.2, 1.5, 4.0):
        _register_callback(delay, refresh_after_battle)


def _on_account_become_player(*_args, **_kwargs):
    # Fires when entering the hangar account context (e.g. after battle end).
    _schedule_post_battle_refresh()


def _add_safe_provider(provider_list, provider):
    """Track a provider without finalizing native objects owned by the game."""
    if provider in provider_list:
        return  # Already tracking this provider
    provider_list.append(provider)


def _native_provider_method(provider, name):
    method = getattr(provider, name, None)
    if not callable(method):
        LOGGER.warning('Native provider method unavailable: %s', name)
        return None
    return method


def _set_native_provider_rows(provider, rows):
    if not hasattr(provider, '_VehicleFiltersDataProvider__rowCount'):
        LOGGER.warning('Native provider row-count attribute unavailable')
        return False
    update_carousel = _native_provider_method(provider, '_VehicleFiltersDataProvider__updateCarousel')
    if update_carousel is None:
        return False
    setattr(provider, '_VehicleFiltersDataProvider__rowCount', rows)
    update_carousel()
    return True


def _refresh_native_provider(provider):
    update_vehicles = _native_provider_method(provider, '_VehicleFiltersDataProvider__updateVehicles')
    update_carousel = _native_provider_method(provider, '_VehicleFiltersDataProvider__updateCarousel')
    if update_vehicles is None or update_carousel is None:
        return False
    update_vehicles()
    update_carousel()
    return True


def fini():
    global SETTINGS_REGISTERED, DOSSIER_CACHE_GENERATION, DOSSIER_FETCH_COUNTER, FINAL_VISIBLE_VEHICLE_COUNT, LAST_DATA_SUMMARY, LAST_PAYLOAD, LAST_PAYLOAD_SIGNATURE, TOOLTIP_PAYLOAD_LOGGED, LEGACY_PLAYLISTS_REMOVED, CONFIG, RUNTIME_STATE, ACTIVE_FILTERS, MSA_API, MSA_SETTINGS, MSA_SYNCING
    try:
        g_playerEvents.onAvatarReady -= _track_last_played
    except Exception:
        pass
    try:
        if hasattr(g_playerEvents, 'onAccountBecomePlayer'):
            g_playerEvents.onAccountBecomePlayer -= _on_account_become_player
    except Exception:
        pass
    while CALLBACK_IDS:
        callback_id = CALLBACK_IDS.pop()
        try:
            BigWorld.cancelCallback(callback_id)
        except Exception:
            # Can happen if the callback fired between the pop above and this
            # call; not an error, so avoid warning-level log spam on exit.
            LOGGER.debug('Unable to cancel callback %s', callback_id)
    MODELS[:] = []
    FILTER_PROVIDERS[:] = []
    STATISTICS_PRESENTERS[:] = []
    FINAL_VISIBLE_VEHICLE_COUNT = None
    DOSSIER_CACHE.clear()
    DOSSIER_CACHE_GENERATION += 1
    DOSSIER_FETCH_COUNTER = 0
    LAST_DATA_SUMMARY = None
    LAST_PAYLOAD = None
    LAST_PAYLOAD_SIGNATURE = None
    TOOLTIP_PAYLOAD_LOGGED = False
    LEGACY_PLAYLISTS_REMOVED = False
    CONFIG = {}
    RUNTIME_STATE = {}
    ACTIVE_FILTERS = set()  # Reinit; clear() unnecessary
    SETTINGS_REGISTERED = False
    MSA_API = None
    MSA_SETTINGS = {}
    MSA_SYNCING = False


def _save_config():
    try:
        directory = os.path.dirname(CONFIG_PATH)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        with io.open(CONFIG_PATH, 'w', encoding='utf-8') as config_file:
            payload = json.dumps(CONFIG, ensure_ascii=False, indent=2, sort_keys=True)
            if not isinstance(payload, unicode):
                payload = payload.decode('utf-8')
            config_file.write(payload)
            config_file.write(u'\n')
    except Exception:
        LOGGER.exception('Unable to save configuration at %s', CONFIG_PATH)


def _save_runtime():
    try:
        directory = os.path.dirname(RUNTIME_PATH)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        with io.open(RUNTIME_PATH, 'w', encoding='utf-8') as runtime_file:
            payload = json.dumps(RUNTIME_STATE, ensure_ascii=False, separators=(',', ':'))
            if not isinstance(payload, unicode):
                payload = payload.decode('utf-8')
            runtime_file.write(payload)
    except Exception:
        LOGGER.exception('Unable to save runtime state at %s', RUNTIME_PATH)


if CONFIG_NEEDS_SAVE:
    _save_config()
    CONFIG_NEEDS_SAVE = False


def _carousel_rows():
    try:
        rows = int(RUNTIME_STATE.get('carouselRows', 0))
        if 1 <= rows <= 4:
            return rows
        return 0
    except (TypeError, ValueError):
        return 0


def _carousel_auto():
    return RUNTIME_STATE.get('carouselRowsMode', 'manual') == 'auto'


def _auto_rows_for_vehicle_count(vehicle_count):
    try:
        count = max(0, int(vehicle_count))
    except (TypeError, ValueError):
        return 2
    if count <= 8:
        return 1
    if count <= 16:
        return 2
    if count <= 24:
        return 3
    return 4


def _normalize_row_count(rows, fallback=2):
    try:
        value = int(rows)
    except (TypeError, ValueError):
        return int(fallback)
    if value < 1:
        return int(fallback)
    return max(1, min(4, value))


def _provider_row_count(provider):
    try:
        current = getattr(provider, '_VehicleFiltersDataProvider__rowCount', None)
        if current is not None:
            return _normalize_row_count(current, fallback=2)
    except Exception:
        pass
    try:
        model = getattr(provider, 'viewModel', None)
        if model is not None and hasattr(model, 'getCarouselRowCount'):
            return _normalize_row_count(model.getCarouselRowCount(), fallback=2)
    except Exception:
        pass
    return 2


def _sync_provider_row_count(provider, rows, force=False):
    target_rows = _normalize_row_count(rows, fallback=2)
    current_rows = _provider_row_count(provider)
    if not force and current_rows == target_rows:
        return False
    return _set_native_provider_rows(provider, target_rows)


def _sync_runtime_target_for_auto(rows):
    global LAST_PAYLOAD_SIGNATURE
    target_rows = _normalize_row_count(rows, fallback=2)
    current_rows = int(RUNTIME_STATE.get('carouselRows', 0) or 0)
    if current_rows == target_rows:
        return target_rows
    RUNTIME_STATE['carouselRows'] = target_rows
    LAST_PAYLOAD_SIGNATURE = None
    _save_runtime()
    return target_rows


def _sync_auto_runtime_rows(vehicle_count=None):
    global LAST_PAYLOAD_SIGNATURE
    if not _carousel_auto():
        return _carousel_rows() or 2
    # The final Gameface filter list is the only authoritative Auto input.
    # ``vehicle_count`` remains for compatibility with existing call sites.
    if FINAL_VISIBLE_VEHICLE_COUNT is None:
        return _sync_runtime_target_for_auto(2)
    rows = _auto_rows_for_vehicle_count(FINAL_VISIBLE_VEHICLE_COUNT)
    current_rows = int(RUNTIME_STATE.get('carouselRows', 0) or 0)
    if current_rows != rows:
        _sync_runtime_target_for_auto(rows)
    elif rows <= 2 and current_rows not in (1, 2):
        LAST_PAYLOAD_SIGNATURE = None
    return rows


def _effective_carousel_rows(vehicle_count=None):
    if _carousel_auto():
        return _sync_auto_runtime_rows(vehicle_count)
    return _carousel_rows() or 2


def _auto_uses_native_rows(rows):
    return _carousel_auto() and int(rows) <= 2


def _apply_auto_rows(vehicle_count=None):
    global FINAL_VISIBLE_VEHICLE_COUNT
    if not _carousel_auto():
        return
    if vehicle_count is not None:
        try:
            FINAL_VISIBLE_VEHICLE_COUNT = max(0, int(vehicle_count))
        except (TypeError, ValueError):
            return
    rows = _sync_auto_runtime_rows()
    for provider in list(FILTER_PROVIDERS):
        try:
            _sync_provider_row_count(provider, rows)
        except Exception:
            LOGGER.exception('Unable to apply automatic carousel rows after filter update (%d)', rows)
    for model in list(MODELS):
        try:
            model.refresh()
        except Exception:
            LOGGER.exception('Unable to refresh model after automatic row update')


def _sync_carousel_auto_property(enabled):
    for provider in list(FILTER_PROVIDERS):
        try:
            with provider.viewModel.transaction() as model:
                model.setHccCarouselAuto(bool(enabled))
        except Exception:
            LOGGER.exception('Unable to update automatic carousel mode')


def _current_carousel_payload(total_vehicles=0):
    return {'rows': _effective_carousel_rows(total_vehicles),
            'mode': 'auto' if _carousel_auto() else 'manual',
            'supportedRows': [1, 2, 3, 4]}


def _publish_payload(payload):
    state_json = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    active_filters_json = json.dumps(sorted(ACTIVE_FILTERS), separators=(',', ':'))
    for model in list(MODELS):
        try:
            model.setStateJson(state_json)
            model.setActiveFiltersJson(active_filters_json)
        except Exception:
            LOGGER.exception('Unable to publish lightweight HCC model update')


def _build_lightweight_payload():
    if not _is_hangar_context_active():
        return {'version': MOD_VERSION, 'enabled': False, 'hangarActive': False}
    if not LAST_PAYLOAD or LAST_PAYLOAD.get('hangarActive') is False:
        return _build_payload()
    total_vehicles = int(LAST_PAYLOAD.get('totalVehicles', 0) or 0)
    payload = dict(LAST_PAYLOAD)
    payload['enabled'] = bool(CONFIG.get('enabled', True))
    payload['hangarActive'] = True
    payload['filtering'] = {'enabled': bool(CONFIG.get('filtering', {}).get('enabled', True))}
    payload['statsConfig'] = _normalized_card_stats_config(CONFIG.get('cardStats', {}))
    payload['sorting'] = {'enabled': bool(CONFIG.get('sorting', {}).get('enabled', True)),
                          'options': _get_sort_option_keys(),
                          'criteria': [criterion[1:] if criterion.startswith('-') else criterion for criterion in _get_configured_sorting_criteria()] if _sort_mode() != 'default' else [],
                          'signedCriteria': _get_configured_sorting_criteria() if _sort_mode() != 'default' else [],
                          'mode': _sort_mode(),
                          'descending': _sort_descending()}
    payload['actionCards'] = CONFIG.get('actionCards', {})
    payload['carousel'] = _current_carousel_payload(total_vehicles)
    return payload


def _refresh_models_lightweight(reason='unknown'):
    try:
        payload = _build_lightweight_payload()
        _publish_payload(payload)
    except Exception:
        LOGGER.exception('Unable to refresh lightweight HCC model (%s)', reason)


def _sort_mode():
    """Return current sort mode."""
    return RUNTIME_STATE.get('sortMode', 'nation')


def _sort_descending():
    """Return current descending flag."""
    return RUNTIME_STATE.get('sortDescending', False)


def _refresh_native_vehicle_model():
    """Refresh native vehicle filter model with current filters."""
    try:
        for provider in list(FILTER_PROVIDERS):
            try:
                _refresh_native_provider(provider)
            except Exception:
                LOGGER.debug('Unable to refresh filter provider')
    except Exception:
        LOGGER.debug('Unable to refresh native vehicle model')


def _refresh_statistics_presenters():
    """Rebuild native statistics after an HCC-only filter state change."""
    for presenter in list(STATISTICS_PRESENTERS):
        update_vehicles = getattr(presenter, '_VehiclesStatisticsPresenter__updateVehicles', None)
        vehicles_component = getattr(presenter, '_vehiclesComponent', None)
        vehicles = getattr(vehicles_component, 'vehicles', None)
        if not callable(update_vehicles) or vehicles is None:
            LOGGER.warning('Native statistics presenter refresh unavailable')
            continue
        try:
            update_vehicles(vehicles)
        except Exception:
            LOGGER.exception('Unable to refresh native statistics after HCC filter change')


def _sync_sort_property():
    """Sync sorting configuration to all models."""
    sort_json = _build_sort_json()
    for provider in list(FILTER_PROVIDERS):
        try:
            with provider.viewModel.transaction() as model:
                model.setHccSortJson(sort_json)
        except Exception:
            LOGGER.exception('Unable to sync sort property to model')


def _set_carousel_rows(rows, automatic=False, refresh=True):
    rows = int(rows)
    if rows == 0:
        if _carousel_auto():
            effective_rows = _sync_auto_runtime_rows()
            for provider in list(FILTER_PROVIDERS):
                try:
                    _set_native_provider_rows(provider, effective_rows)
                except Exception:
                    LOGGER.exception('Unable to apply automatic carousel rows (%d)', effective_rows)
            if refresh:
                _refresh_models_lightweight('carousel row mode unchanged')
            return
        RUNTIME_STATE['carouselRowsMode'] = 'auto'
        effective_rows = _sync_auto_runtime_rows()
        LAST_PAYLOAD_SIGNATURE = None
        _save_runtime()
        _sync_carousel_auto_property(True)
        for provider in list(FILTER_PROVIDERS):
            try:
                _set_native_provider_rows(provider, effective_rows)
            except Exception:
                LOGGER.exception('Unable to apply automatic carousel rows (%d)', effective_rows)
        if refresh:
            _refresh_models_lightweight('automatic carousel row mode enabled')

        LOGGER.info('Automatic carousel row mode enabled')
        return
    rows = max(1, min(4, int(rows)))
    current_rows = int(RUNTIME_STATE.get('carouselRows', 0) or 0)
    current_mode = RUNTIME_STATE.get('carouselRowsMode', 'manual')
    if automatic:
        if not _carousel_auto():
            return
    else:
        if current_mode == 'manual' and current_rows == rows:
            if refresh:
                _refresh_models_lightweight('carousel row count unchanged')
            return
        RUNTIME_STATE['carouselRowsMode'] = 'manual'
    RUNTIME_STATE['carouselRows'] = rows
    LAST_PAYLOAD_SIGNATURE = None
    _save_runtime()
    _sync_carousel_auto_property(_carousel_auto())
    for provider in list(FILTER_PROVIDERS):
        try:
            _set_native_provider_rows(provider, rows)
        except Exception:
            LOGGER.exception('Unable to apply %d carousel rows', rows)

    if refresh:
        _refresh_models_lightweight('carousel row count changed')

    LOGGER.info('Carousel row count changed to %d%s', rows, ' automatically' if automatic else '')


def _inventory_vehicles():
    for presenter in reversed(list(STATISTICS_PRESENTERS)):
        vehicles_component = getattr(presenter, '_vehiclesComponent', None)
        presenter_vehicles = getattr(vehicles_component, 'vehicles', None)
        if isinstance(presenter_vehicles, dict):
            return presenter_vehicles
    LOGGER.warning('Native statistics vehicle component unavailable; skipping payload build')
    return {}

def _marks_on_gun(vehicle_dossier):
    try:
        achievement = vehicle_dossier.getTotalStats().getAchievement(MARK_ON_GUN_RECORD)
        return int(achievement.getValue())
    except Exception:
        return 0


def _marks_on_gun_rating(vehicle_dossier):
    try:
        random_stats = vehicle_dossier.getRandomStats()
        if random_stats is None:
            return 0.0
        achievement = random_stats.getAchievement(MARK_ON_GUN_RECORD)
        if achievement is None:
            return 0.0
        return round(float(achievement.getDamageRating() or 0.0), 2)
    except Exception:
        return 0.0


def _marks_on_gun_level(vehicle_dossier):
    try:
        achievement = vehicle_dossier.getRandomStats().getAchievement(MARK_ON_GUN_RECORD)
        if achievement is None:
            return 0
        return int(achievement.getValue() or 0)
    except Exception:
        return 0


def _alpha_damage(vehicle):
    """Return nominal alpha damage using the same vehicle params source as the hangar panel."""
    def _from_params(vehicle_like):
        if vehicle_like is None:
            return None
        try:
            params = items_params_helper.getParameters(vehicle_like)
            if isinstance(params, dict):
                value = params.get('avgDamage')
                if value is not None:
                    return int(round(float(value)))
        except Exception:
            pass
        try:
            comparator = items_params_helper.similarCrewComparator(vehicle_like)
            if comparator is not None:
                param = comparator.getExtendedData('avgDamage')
                value = getattr(param, 'value', None) if param is not None else None
                if value is not None:
                    return int(round(float(value)))
        except Exception:
            pass
        return None

    for candidate in (vehicle,
     SERVICES.itemsCache.items.getItemByCD(vehicle.intCD) if SERVICES.itemsCache else None,
     SERVICES.itemsCache.items.getStockVehicle(vehicle.intCD) if SERVICES.itemsCache else None):
        try:
            result = _from_params(candidate)
            if result is not None and result > 0:
                return result
        except Exception:
            pass

    try:
        value = _from_params(vehicle)
        if value is not None:
            return value
    except Exception:
        LOGGER.debug('Unable to extract alpha damage from params_helper for vehicle %s', getattr(vehicle, 'intCD', 'unknown'))

    try:
        cached_vehicle = SERVICES.itemsCache.items.getItemByCD(vehicle.intCD)
        if cached_vehicle is not None:
            value = _from_params(cached_vehicle)
            if value is not None:
                return value
    except Exception:
        LOGGER.debug('Unable to extract alpha damage from cached vehicle for %s', getattr(vehicle, 'intCD', 'unknown'))

    try:
        descriptor = getattr(vehicle, 'descriptor', None)
        if descriptor is None:
            descriptor = getattr(vehicle, 'typeDescriptor', None)
        if descriptor is None:
            return 0
        gun = getattr(descriptor, 'gun', None)
        if gun is None:
            return 0

        shots = getattr(gun, 'shots', None)
        if shots is None and hasattr(gun, 'get'):
            shots = gun.get('shots')
        if not shots:
            return 0

        for shot in shots:
            shell = getattr(shot, 'shell', None)
            if shell is None and isinstance(shot, dict):
                shell = shot.get('shell')
            if shell is None:
                continue

            damage = getattr(shell, 'damage', None)
            if damage is None and isinstance(shell, dict):
                damage = shell.get('damage')
            if not damage:
                continue

            if isinstance(damage, (list, tuple)):
                try:
                    return int(round(float(damage[0])))
                except Exception:
                    continue
            try:
                return int(round(float(damage)))
            except Exception:
                continue
    except Exception:
        LOGGER.debug('Unable to extract alpha damage for vehicle %s', getattr(vehicle, 'intCD', 'unknown'))
    return 0


def _build_stats(vehicle, account_random_stats, vehicle_cuts):
    global DOSSIER_FETCH_COUNTER
    battles = 0
    wins = 0
    mastery = 0
    if vehicle.intCD <= 0:
        LOGGER.debug('Invalid intCD for vehicle: %s', vehicle.intCD)
        return {'battles': 0,
         'winRate': 0,
         'averageDamage': 0,
         'alphaDamage': 0,
         'mastery': 0,
         'marksOnGun': 0.0,
         'marksOnGunLevel': 0}
    if vehicle.intCD in vehicle_cuts:
        battles, wins, _ = vehicle_cuts[vehicle.intCD]
        mastery = account_random_stats.getMarkOfMasteryForVehicle(vehicle.intCD) if account_random_stats is not None else 0
    average_damage = 0
    alpha_damage = _alpha_damage(vehicle)
    marks_on_gun = 0.0
    marks_on_gun_level = 0
    try:
        # Use cache to avoid redundant dossier lookups
        cache_key = (vehicle.intCD, DOSSIER_CACHE_GENERATION)
        if cache_key not in DOSSIER_CACHE:
            # Limit concurrent dossier fetches to prevent UI blocking on large fleets
            if DOSSIER_FETCH_COUNTER >= MAX_DOSSIER_FETCHES_PER_REFRESH:
                LOGGER.debug('Dossier fetch limit reached for this refresh cycle (vehicle %d deferred)', vehicle.intCD)
                raise Exception('Dossier fetch rate limit (MAX=%d)' % MAX_DOSSIER_FETCHES_PER_REFRESH)
            DOSSIER_FETCH_COUNTER += 1  # Increment BEFORE fetch to prevent off-by-one
            vehicle_dossier = SERVICES.itemsCache.items.getVehicleDossier(vehicle.intCD)
            if vehicle_dossier is None:
                LOGGER.debug('Dossier unavailable for vehicle %d', vehicle.intCD)
                DOSSIER_CACHE[cache_key] = None
                raise Exception('Dossier unavailable for vehicle %d' % vehicle.intCD)
            DOSSIER_CACHE[cache_key] = vehicle_dossier
        else:
            vehicle_dossier = DOSSIER_CACHE[cache_key]
            if vehicle_dossier is None:
                raise Exception('Cached dossier is None for vehicle %d' % vehicle.intCD)
        
        try:
            random_stats = vehicle_dossier.getRandomStats()
            if random_stats is None:
                raise Exception('RandomStats unavailable for vehicle %d' % vehicle.intCD)
        except Exception:
            LOGGER.debug('RandomStats extraction failed for vehicle %d', vehicle.intCD)
            raise
        average_damage = int(random_stats.getAvgDamage() or 0)
        marks_on_gun = _marks_on_gun_rating(vehicle_dossier)
        marks_on_gun_level = _marks_on_gun_level(vehicle_dossier)
    except Exception:
        LOGGER.debug('Dossier stats unavailable for vehicle %d; using defaults', vehicle.intCD)

    return {'battles': int(battles),
     'winRate': round(100.0 * wins / battles, 1) if battles else 0.0,
     'averageDamage': average_damage,
     'alphaDamage': alpha_damage,
     'mastery': int(mastery),
     'marksOnGun': marks_on_gun,
     'marksOnGunLevel': int(marks_on_gun_level)}


def _normalized_card_stats_config(raw_stats_config):
    """Validate selectable card-stat fields while preserving configured order."""
    stats_config = dict(raw_stats_config or {})
    fields = stats_config.get('fields', [])
    if not isinstance(fields, list):
        fields = []
    allowed_fields = ('battles', 'winRate', 'averageDamage', 'alphaDamage', 'mastery', 'marksOnGun')
    normalized_fields = []
    seen = set()
    for field in fields:
        if isinstance(field, basestring) and field in allowed_fields and field not in seen:
            normalized_fields.append(field)
            seen.add(field)
    stats_config['fields'] = normalized_fields
    stats_config['enabled'] = bool(stats_config.get('enabled', True))
    try:
        stats_config['minimumBattles'] = max(0, int(stats_config.get('minimumBattles', 1)))
    except Exception:
        stats_config['minimumBattles'] = 1
    return stats_config


def _normalize_nation_token(value):
    if value is None:
        return None
    if isinstance(value, (int, long)):
        # WoT nationID mapping for current client generation.
        nation_ids = {0: 'ussr', 1: 'germany', 2: 'usa', 3: 'china', 4: 'france', 5: 'uk', 6: 'japan', 7: 'czech', 8: 'sweden', 9: 'poland', 10: 'italy'}
        return nation_ids.get(int(value))
    if isinstance(value, basestring):
        token = value.strip().lower().replace(' ', '').replace('_', '').replace('-', '')
        aliases = {'ussr': 'ussr', 'sovietunion': 'ussr', 'soviet': 'ussr', 'germany': 'germany', 'de': 'germany', 'usa': 'usa', 'american': 'usa', 'france': 'france', 'fr': 'france', 'uk': 'uk', 'britain': 'uk', 'england': 'uk', 'unitedkingdom': 'uk', 'china': 'china', 'cn': 'china', 'japan': 'japan', 'jp': 'japan', 'czech': 'czech', 'czechoslovakia': 'czech', 'poland': 'poland', 'pl': 'poland', 'sweden': 'sweden', 'se': 'sweden', 'italy': 'italy', 'it': 'italy'}
        return aliases.get(token)
    try:
        return _normalize_nation_token(int(value))
    except Exception:
        return None


def _normalized_nations_order():
    raw_order = CONFIG.get('sorting', {}).get('nations_order', [])
    normalized = []
    seen = set()
    for nation in raw_order:
        token = _normalize_nation_token(nation)
        if token is None or token in seen:
            continue
        normalized.append(token)
        seen.add(token)
    return normalized


def _get_nation_index(vehicle):
    """Return nation index for sorting priority."""
    nations_order = _normalized_nations_order()
    try:
        nation_candidates = []
        for attr in ('nationID', 'nation', 'nationName'):
            if hasattr(vehicle, attr):
                nation_candidates.append(getattr(vehicle, attr))
        if hasattr(vehicle, 'getNationID'):
            try:
                nation_candidates.append(vehicle.getNationID())
            except Exception:
                pass
        for nation in nation_candidates:
            normalized = _normalize_nation_token(nation)
            if normalized is None:
                continue
            if nations_order and normalized in nations_order:
                return nations_order.index(normalized)
            if nations_order and nation in nations_order:
                return nations_order.index(nation)
            break
        return 999  # Unmapped nations sort last
    except Exception:
        return 999


def _get_type_index(vehicle):
    """Return vehicle type index for sorting priority."""
    types_order = CONFIG.get('sorting', {}).get('types_order', [])
    try:
        vtype = vehicle.type or ''
        if types_order and vtype in types_order:
            return types_order.index(vtype)
        return 999  # Unmapped types sort last
    except Exception:
        return 999


def _get_sort_value(vehicle, criterion, account_random_stats, vehicle_cuts):
    """Extract sort value for a given criterion (nation, type, level, battles, etc.)."""
    normalized_criterion = _normalize_sort_criterion(criterion)
    if normalized_criterion is None:
        return 0
    reverse = normalized_criterion.startswith('-')
    key = normalized_criterion[1:] if reverse else normalized_criterion
    value = 0
    
    try:
        if key == 'nation':
            value = _get_nation_index(vehicle)
        elif key == 'type':
            value = _get_type_index(vehicle)
        elif key in ('level', 'tier'):
            try:
                if hasattr(vehicle, 'level') and vehicle.level is not None:
                    value = int(vehicle.level)
                else:
                    value = 0
            except (TypeError, ValueError):
                value = 0
        elif key == 'maxBattleTier':
            try:
                value = int(vehicle.maxBattleTier) if vehicle.maxBattleTier is not None else 0
            except (TypeError, ValueError):
                value = 0
        elif key == 'premium':
            # 0 = premium, 1 = regular so ascending `premium` keeps premium first.
            value = 0 if bool(getattr(vehicle, 'isPremium', False)) else 1
        elif key == 'battles':
            if vehicle.intCD in vehicle_cuts:
                battles, _, _ = vehicle_cuts[vehicle.intCD]
                value = int(battles)
        elif key == 'winRate':
            if vehicle.intCD in vehicle_cuts:
                battles, wins, _ = vehicle_cuts[vehicle.intCD]
                # Store as percentage * 100 (e.g., 75.5% = 7550)
                value = int((wins * 10000.0 / battles) if battles else 0)
        elif key == 'markOfMastery':
            if account_random_stats:
                value = int(account_random_stats.getMarkOfMasteryForVehicle(vehicle.intCD) or 0)
        elif key == 'averageDamage':
            stats = _build_stats(vehicle, account_random_stats, vehicle_cuts)
            value = int(stats.get('averageDamage', 0))
        elif key == 'alphaDamage':
            stats = _build_stats(vehicle, account_random_stats, vehicle_cuts)
            value = int(stats.get('alphaDamage', 0))
        elif key == 'marksOnGun':
            stats = _build_stats(vehicle, account_random_stats, vehicle_cuts)
            value = int(round(float(stats.get('marksOnGun', 0.0)) * 100))
        elif key == 'battlePassPoints':
            # Fetch Battle Pass points from controller if available
            try:
                value = int(SERVICES.battlePass.getPoints() or 0)
            except Exception:
                value = 0
        elif key == 'lastPlayed':
            last_played = RUNTIME_STATE.get('lastPlayed', {})
            try:
                timestamp = long(last_played.get(str(vehicle.intCD), 0))
            except (TypeError, ValueError):
                timestamp = 0
            value = timestamp
    except Exception:
        LOGGER.debug('Unable to extract sort value for vehicle %d, criterion %s', vehicle.intCD, key)
        value = 0
    
    return -value if reverse else value


def _build_sort_json(account_random_stats=None, vehicle_cuts=None):
    """Build JSON payload with hierarchical sorting criteria (nation -> type -> tier etc.)."""
    sorting_enabled = bool(CONFIG.get('sorting', {}).get('enabled', True))
    filtering_enabled = bool(CONFIG.get('filtering', {}).get('enabled', True))
    sorting_criteria = [] if (not sorting_enabled or _sort_mode() == 'default') else _get_configured_sorting_criteria()
    # Tuple comparator reads from index 0 to N, so keep the user order intact:
    # first configured criterion is the primary key.
    applied_criteria = list(sorting_criteria)
    
    vehicles = _inventory_vehicles()
    
    # Fetch account stats if not provided
    if account_random_stats is None:
        try:
            account_dossier = SERVICES.itemsCache.items.getAccountDossier()
            if account_dossier is not None:
                account_random_stats = account_dossier.getRandomStats()
            else:
                account_random_stats = None
        except Exception:
            LOGGER.warning('Unable to fetch account dossier for sorting')
            account_random_stats = None
    
    if vehicle_cuts is None:
        if account_random_stats is not None:
            try:
                vehicle_cuts = account_random_stats.getVehicles()
                if vehicle_cuts is None:
                    vehicle_cuts = {}
            except Exception:
                vehicle_cuts = {}
        else:
            vehicle_cuts = {}
    
    # Build hierarchical sort key for each vehicle
    payload = {'criteria': applied_criteria, 'values': {}, 'allowed': [],
               'filtered': bool(filtering_enabled and ACTIVE_FILTERS)}
    if vehicles:
        for vehicle in vehicles.values():
            sort_key = tuple(_get_sort_value(vehicle, c, account_random_stats, vehicle_cuts) for c in applied_criteria)
            vehicle_id = int(vehicle.intCD)
            payload['values'][str(vehicle_id)] = sort_key
            inventory_id = getattr(vehicle, 'inventoryId', getattr(vehicle, 'inventoryID', None))
            if inventory_id is not None:
                payload['values'][str(inventory_id)] = sort_key
            if (not filtering_enabled or not ACTIVE_FILTERS or
                    all(_matches(filter_id, vehicle) for filter_id in ACTIVE_FILTERS)):
                payload['allowed'].append(str(vehicle_id))
                if inventory_id is not None:
                    payload['allowed'].append(str(inventory_id))
    
    return json.dumps(payload, separators=(',', ':'), default=str)


def _coerce_criteria_sequence(criteria):
    """Accept Gameface array proxies as well as plain Python sequences."""
    if criteria is None:
        return []
    if isinstance(criteria, (list, tuple)):
        return list(criteria)
    if isinstance(criteria, basestring):
        return [criteria]
    try:
        return [item for item in criteria]
    except TypeError:
        return []


def _infer_descending(criteria):
    for c in criteria or []:
        name = c[1:] if c.startswith("-") else c
        if name not in ("nation", "type"):
            return c.startswith("-")
    return any(c.startswith("-") for c in (criteria or []))


def _set_sorting_criteria(criteria, descending=None):
    """Update sorting criteria and refresh."""
    criteria = _coerce_criteria_sequence(criteria)
    normalized = _normalize_sort_criteria(criteria, fallback=[])
    target_descending = bool(descending) if descending is not None else _infer_descending(normalized)
    if normalized == _get_configured_sorting_criteria() and target_descending == RUNTIME_STATE.get("sortDescending", False):
        return
    CONFIG.setdefault("sorting", {})["sorting_criteria"] = normalized
    RUNTIME_STATE["sortMode"] = normalized[0][1:] if normalized and normalized[0].startswith("-") else (normalized[0] if normalized else "default")
    RUNTIME_STATE["sortDescending"] = target_descending
    _save_config()
    _save_runtime()
    _sync_sort_property()
    _refresh_models_lightweight("sorting criteria changed")
    LOGGER.info("Carousel sorting criteria changed to: %s (descending=%s)", ", ".join(normalized), target_descending)


def _set_nations_order(nations):
    """Update nation sort priority."""
    if not isinstance(nations, list):
        nations = []
    normalized = []
    seen = set()
    for nation in nations:
        token = _normalize_nation_token(nation)
        if token is None or token in seen:
            continue
        normalized.append(token)
        seen.add(token)
    if normalized == list(CONFIG.get('sorting', {}).get('nations_order', [])):
        return
    CONFIG.setdefault('sorting', {})['nations_order'] = normalized
    _save_config()
    _sync_sort_property()
    _refresh_models_lightweight('nation sort order changed')
    if normalized:
        LOGGER.info('Nation sort order updated: %s', ', '.join(normalized))


def _set_types_order(types):
    """Update vehicle type sort priority."""
    if not isinstance(types, list):
        types = []
    if types == list(CONFIG.get('sorting', {}).get('types_order', [])):
        return
    CONFIG.setdefault('sorting', {})['types_order'] = types
    _save_config()
    _sync_sort_property()
    _refresh_models_lightweight('vehicle type sort order changed')
    if types:
        LOGGER.info('Vehicle type sort order updated: %s', ', '.join(types))


def _set_sorting(mode, descending=None):
    if mode not in SORT_UI_OPTION_ORDER and mode != 'default':
        mode = 'nation'
    old_mode = _sort_mode()
    old_descending = _sort_descending()
    RUNTIME_STATE['sortMode'] = mode
    if descending is not None:
        RUNTIME_STATE['sortDescending'] = bool(descending)
    if old_mode == mode and old_descending == _sort_descending():
        _refresh_models_lightweight('sorting unchanged')
        return
    if mode == 'default':
        CONFIG.setdefault('sorting', {})['sorting_criteria'] = []
    else:
        criteria = [('%s%s' % ('-' if _sort_descending() else '', mode))]
        CONFIG.setdefault('sorting', {})['sorting_criteria'] = _normalize_sort_criteria(criteria)
    _save_config()
    _save_runtime()
    _sync_sort_property()
    _refresh_models_lightweight('carousel sorting changed')

    LOGGER.info('Carousel sorting changed to %s (%s)', mode, 'descending' if _sort_descending() else 'ascending')
    return
def _remove_legacy_playlists():
    global LEGACY_PLAYLISTS_REMOVED
    if LEGACY_PLAYLISTS_REMOVED or not SERVICES.playlists.isEnabled:
        return
    # Prevent concurrent execution via flag check-and-set pattern
    if LEGACY_PLAYLISTS_REMOVED:
        return
    try:
        legacy_ids = [ playlist_id for playlist_id, _ in SERVICES.playlists.iterPlaylists() if _is_hcc_playlist_id(playlist_id) ]
        selected_id = SERVICES.playlists.getSelectedID()
        for playlist_id in legacy_ids:
            try:
                SERVICES.playlists.deletePlaylist(playlist_id)
            except Exception as e:
                LOGGER.warning('Failed to delete legacy playlist %s: %s', playlist_id, e)
        if legacy_ids:
            try:
                SERVICES.playlists.setSelectedID('' if selected_id in legacy_ids else selected_id or '')
            except Exception as e:
                LOGGER.warning('Failed to set playlist selection: %s', e)
        LEGACY_PLAYLISTS_REMOVED = True
        if legacy_ids:
            LOGGER.info('Removed %d legacy HCC dynamic playlists', len(legacy_ids))
    except Exception as e:
        LOGGER.error('Error removing legacy playlists: %s', e)


def _track_last_played():
    try:
        if getattr(BattleReplay.g_replayCtrl, 'isPlaying', False):
            return
        avatar = BigWorld.player()
        if avatar is None or not hasattr(avatar, 'playerVehicleID'):
            return
        vehicle = BigWorld.entity(avatar.playerVehicleID)
        if vehicle is None:
            return
        type_descriptor = getattr(vehicle, 'typeDescriptor', None)
        if type_descriptor is None or not hasattr(type_descriptor, 'type'):
            return
        int_cd = type_descriptor.type.compactDescr
        RUNTIME_STATE.setdefault('lastPlayed', {})[int_cd] = int(time.time())
        _save_runtime()
        if _sort_mode() == 'lastPlayed':
            _sync_sort_property()
    except Exception:
        LOGGER.exception('Unable to track the last-played vehicle')

    return


def _matches(filter_id, vehicle):
    """Check if vehicle matches the given filter."""
    if filter_id == 'all':
        return True
    if filter_id == 'non_elite':
        return not bool(getattr(vehicle, 'isElite', False))
    elif filter_id == 'not_ready':
        try:
            return bool(getattr(vehicle, 'isBroken', False) or not getattr(vehicle, 'isCrewFull', True) or not getattr(vehicle, 'isAmmoFull', True))
        except Exception:
            return False
    elif filter_id == 'marks_incomplete':
        try:
            try:
                level = int(vehicle.level) if vehicle.level is not None else 0
            except (TypeError, ValueError):
                LOGGER.debug('Invalid level for vehicle %d: %s', vehicle.intCD, vehicle.level)
                return False
            if level < 5:
                return False
            vehicle_dossier = SERVICES.itemsCache.items.getVehicleDossier(vehicle.intCD)
            if vehicle_dossier is None:
                return False
            marks = _marks_on_gun(vehicle_dossier)
            return marks < 3
        except Exception:
            return False
    elif filter_id == 'crew_not_maxed':
        try:
            return not bool(getattr(vehicle, 'isCrewFullyTrained', True))
        except Exception:
            return False
    return False


def _filter_count(filter_id, vehicles):
    active_filters = set(ACTIVE_FILTERS)
    if filter_id == 'all':
        required_filters = active_filters
    else:
        required_filters = active_filters | set((filter_id,))
    return sum((1 for vehicle in vehicles if all((_matches(current_filter, vehicle) for current_filter in required_filters))))


def _set_filter_state(filter_id):
    """Toggle filter state with atomic snapshot to prevent race conditions during model refresh."""
    if filter_id == 'all':
        ACTIVE_FILTERS.clear()
    elif filter_id in FILTER_ORDER:
        if filter_id in ACTIVE_FILTERS:
            ACTIVE_FILTERS.discard(filter_id)
        else:
            ACTIVE_FILTERS.add(filter_id)
        ACTIVE_FILTERS.discard('all')
    
    RUNTIME_STATE['activeFilters'] = sorted(ACTIVE_FILTERS)
    _save_runtime()
    _sync_msa_filter_settings()
    _sync_sort_property()
    _refresh_native_vehicle_model()
    _refresh_statistics_presenters()
    
    # Snapshot for logging (avoid race condition if ACTIVE_FILTERS modified during refresh)
    active_snapshot = set(ACTIVE_FILTERS)
    for model in list(MODELS):
        try:
            model.refresh()
        except Exception:
            LOGGER.exception('Error refreshing model after filter state change')
    LOGGER.info('Filter state toggled for %s; active filters: %s', filter_id, sorted(active_snapshot))


def _sync_msa_filter_settings():
    """Persist HCC filter changes to MSA without reloading an open settings window."""
    global MSA_SYNCING
    if MSA_API is None or not MSA_SETTINGS or MSA_SYNCING:
        return
    update_settings = dict(MSA_SETTINGS)
    for filter_id in FILTER_ORDER:
        if filter_id == 'all':
            continue
        update_settings['filter_%s' % filter_id] = filter_id in ACTIVE_FILTERS
    try:
        update_method = getattr(MSA_API, 'updateModSettings', None)
        if callable(update_method):
            MSA_SYNCING = True
            update_method(MOD_LINKAGE_ID, update_settings)
            MSA_SETTINGS.clear()
            MSA_SETTINGS.update(update_settings)
    except Exception:
        LOGGER.exception('Unable to synchronize HCC filters to ModsSettingsAPI')
    finally:
        MSA_SYNCING = False


def _apply_msa_filter_settings(settings):
    """Apply individual MSA filter checkboxes to the shared HCC filter state."""
    global ACTIVE_FILTERS
    changed = False
    active_filters = set(ACTIVE_FILTERS)
    for filter_id in FILTER_ORDER:
        if filter_id == 'all':
            continue
        setting_key = 'filter_%s' % filter_id
        if setting_key not in settings:
            continue
        enabled = bool(settings.get(setting_key))
        if enabled and filter_id not in active_filters:
            active_filters.add(filter_id)
            changed = True
        elif not enabled and filter_id in active_filters:
            active_filters.discard(filter_id)
            changed = True
    if not changed:
        return
    ACTIVE_FILTERS = active_filters
    RUNTIME_STATE['activeFilters'] = sorted(ACTIVE_FILTERS)
    _save_runtime()
    _sync_sort_property()
    _refresh_native_vehicle_model()
    _refresh_statistics_presenters()
    _refresh_models_lightweight('MSA filter change')
    LOGGER.info('Filter state synchronized from ModsSettingsAPI: %s', sorted(ACTIVE_FILTERS))


def _build_payload():
    global LAST_DATA_SUMMARY, LAST_PAYLOAD, LAST_PAYLOAD_SIGNATURE, DOSSIER_FETCH_COUNTER
    DOSSIER_FETCH_COUNTER = 0  # Reset fetch counter for this refresh cycle
    # Outside the standard hangar the JS layer only needs the inactive flag to
    # drop its global decorations. Skip the expensive dossier/stats build.
    if not _is_hangar_context_active():
        LAST_PAYLOAD = {'version': MOD_VERSION, 'enabled': False, 'hangarActive': False}
        return LAST_PAYLOAD
    try:
        vehicles = _inventory_vehicles()
    except Exception as e:
        LOGGER.error('Failed to get inventory vehicles: %s', e)
        return {}
    if vehicles is None or not vehicles:
        LOGGER.warning('Inventory vehicles unavailable or empty; skipping payload build')
        return {}
    values = list(vehicles.values())
    stats_config = _normalized_card_stats_config(CONFIG.get('cardStats', {}))
    stats_enabled = bool(stats_config.get('enabled', True))
    try:
        vehicle_signature = tuple(sorted((int(vehicle.intCD) for vehicle in values)))
    except Exception:
        vehicle_signature = tuple()
    payload_signature = (
        vehicle_signature,
        stats_enabled,
        bool(_carousel_auto()),
        int(RUNTIME_STATE.get('carouselRows', 0) or 0),
        tuple(sorted(ACTIVE_FILTERS)),
        _sort_mode(),
        bool(_sort_descending()),
        DOSSIER_CACHE_GENERATION,
    )
    if LAST_PAYLOAD is not None and LAST_PAYLOAD_SIGNATURE == payload_signature and LAST_PAYLOAD.get('hangarActive') is not False:
        return _build_lightweight_payload()
    # Cache account dossier to prevent race condition between sort and stats builds
    try:
        account_dossier = SERVICES.itemsCache.items.getAccountDossier()
        account_random_stats = account_dossier.getRandomStats() if account_dossier else None
    except Exception:
        LOGGER.warning('Unable to fetch account dossier for payload build')
        account_random_stats = None
    if account_random_stats is not None:
        try:
            vehicle_cuts = account_random_stats.getVehicles()
            if vehicle_cuts is None:
                vehicle_cuts = {}
        except Exception:
            vehicle_cuts = {}
    else:
        vehicle_cuts = {}
    stats = {}
    if stats_enabled:
        for vehicle in values:
            stats[str(vehicle.intCD)] = _build_stats(vehicle, account_random_stats, vehicle_cuts)

    summary = (len(values), len(stats), sum((1 for value in stats.values() if value.get('battles', 0) > 0)))
    # Only log if vehicle count or stats changed (not every single refresh)
    if LAST_DATA_SUMMARY is None or summary[0] != LAST_DATA_SUMMARY[0] or summary[1] != LAST_DATA_SUMMARY[1]:
        LAST_DATA_SUMMARY = summary
        LOGGER.info('Carousel data: %d vehicles, %d stat records, %d with battles', *summary)
    
    # HCC badges intentionally count HCC filters against the complete inventory.
    filters = []
    for filter_id in FILTER_ORDER:
        count = _filter_count(filter_id, values)
        filters.append({'id': filter_id, 'count': count})
    
    LAST_PAYLOAD = {'version': MOD_VERSION,
     'language': getClientLanguage(),
     'enabled': bool(CONFIG.get('enabled', True)),
     'hangarActive': _is_hangar_context_active(),
     'filterMode': 'native_toggles',
     'filters': filters,
     'filtering': {'enabled': bool(CONFIG.get('filtering', {}).get('enabled', True))},
     'stats': stats,
     'statsConfig': stats_config,
     'sorting': {'enabled': bool(CONFIG.get('sorting', {}).get('enabled', True)),
                 'options': _get_sort_option_keys(),
                 'criteria': [criterion[1:] if criterion.startswith('-') else criterion for criterion in _get_configured_sorting_criteria()] if _sort_mode() != 'default' else [],
                 'signedCriteria': _get_configured_sorting_criteria() if _sort_mode() != 'default' else [],
                 'mode': _sort_mode(),
                 'descending': _sort_descending()},
     'actionCards': CONFIG.get('actionCards', {}),
     'nativeFeatures': ['premium',
                        'elite',
                        'rented',
                        'daily_bonus',
                        'battle_pass_available'],
     'carousel': _current_carousel_payload(len(values)),
     'trackedLastPlayed': len(RUNTIME_STATE.get('lastPlayed', {})),
     'totalVehicles': len(values)}
    LAST_PAYLOAD_SIGNATURE = payload_signature
    return LAST_PAYLOAD


class HangarCarouselClassicModel(ViewModel):
    __slots__ = ('onToggleFilter', 'onRefresh', 'onSetCarouselRows', 'onSetSorting')

    def __init__(self, properties=2, commands=4):
        super(HangarCarouselClassicModel, self).__init__(properties=properties, commands=commands)
        self.onToggleFilter += self.__on_toggle_filter
        self.onRefresh += self.__on_refresh
        self.onSetCarouselRows += self.__on_set_carousel_rows
        self.onSetSorting += self.__on_set_sorting
        MODELS.append(self)
        _register_callback(0.1, self.refresh)

    def getStateJson(self):
        return self._getString(0)

    def setStateJson(self, value):
        self._setString(0, value)

    def getActiveFiltersJson(self):
        return self._getString(1)

    def setActiveFiltersJson(self, value):
        self._setString(1, value)

    def _initialize(self):
        super(HangarCarouselClassicModel, self)._initialize()
        self._addStringProperty('stateJson', '{}')
        self._addStringProperty('activeFiltersJson', '[]')
        self.onToggleFilter = self._addCommand('onToggleFilter')
        self.onRefresh = self._addCommand('onRefresh')
        self.onSetCarouselRows = self._addCommand('onSetCarouselRows')
        self.onSetSorting = self._addCommand('onSetSorting')

    def refresh(self):
        try:
            _remove_legacy_playlists()
            payload = _build_payload()
            self.setStateJson(json.dumps(payload, ensure_ascii=False, separators=(',', ':')))
            self.setActiveFiltersJson(json.dumps(sorted(ACTIVE_FILTERS), separators=(',', ':')))
        except Exception:
            LOGGER.exception('Unable to refresh Hangar Carousel Classic data')

    def __on_toggle_filter(self, args):
        try:
            filter_id = args.get('filterId') if args else None
            if filter_id:
                _set_filter_state(filter_id)
        except Exception:
            LOGGER.exception('Unable to toggle filter state')

    def __on_refresh(self, *_args, **_kwargs):
        _refresh_native_vehicle_model()
        self.refresh()

    def __on_set_carousel_rows(self, args):
        try:
            _set_carousel_rows(args.get('rows', 2) if args else 2)
        except Exception:
            LOGGER.exception('Unable to change carousel row count')

    def __on_set_sorting(self, args):
        try:
            if args:
                descending = args.get("descending", None)
                criteria_json = args.get("criteriaJson", None)
                if isinstance(criteria_json, basestring):
                    try:
                        parsed = json.loads(criteria_json)
                        _set_sorting_criteria(parsed, descending=descending)
                        return
                    except (TypeError, ValueError):
                        LOGGER.warning("Invalid sorting criteria JSON from Gameface: %r", criteria_json)
                _set_sorting(args.get("mode", "default"), descending)
            else:
                _set_sorting("default")
        except Exception:
            LOGGER.exception("Unable to change carousel sorting")

        return
class HangarCarouselClassicTooltipModel(ViewModel):
    __slots__ = ()

    def __init__(self, properties=1, commands=0):
        super(HangarCarouselClassicTooltipModel, self).__init__(properties=properties, commands=commands)

    def getStateJson(self):
        return self._getString(0)

    def setStateJson(self, value):
        self._setString(0, value)

    def _initialize(self):
        super(HangarCarouselClassicTooltipModel, self)._initialize()
        self._addStringProperty('stateJson', '{}')


def _patch_vehicle_filter_model():
    if getattr(VehicleFilterModel, '_hcc_patched', False):
        return
    original_init = VehicleFilterModel.__init__
    original_initialize = VehicleFilterModel._initialize

    def patched_init(self, properties=4, commands=3):
        original_init(self, properties=properties + 4, commands=commands)

    def patched_initialize(self):
        original_initialize(self)
        try:
            gf_mod_inject(self, 'HangarCarouselClassic', styles=[CSS_URL], modules=[JS_URL])
        except Exception:
            LOGGER.exception('Unable to inject Gameface assets; carousel features may be unavailable')
        self._addViewModelProperty('hangarCarouselClassic', HangarCarouselClassicModel())
        self._addBoolProperty('hccCarouselAuto', _carousel_auto())
        self._addStringProperty('hccSortJson', _build_sort_json())

    def get_hcc_carousel_auto(self):
        return self._getBool(6)

    def set_hcc_carousel_auto(self, value):
        self._setBool(6, value)

    def get_hcc_sort_json(self):
        return self._getString(7)

    def set_hcc_sort_json(self, value):
        self._setString(7, value)

    VehicleFilterModel.__init__ = patched_init
    VehicleFilterModel._initialize = patched_initialize
    VehicleFilterModel.getHccCarouselAuto = get_hcc_carousel_auto
    VehicleFilterModel.setHccCarouselAuto = set_hcc_carousel_auto
    VehicleFilterModel.getHccSortJson = get_hcc_sort_json
    VehicleFilterModel.setHccSortJson = set_hcc_sort_json
    VehicleFilterModel._hcc_patched = True


def _build_tooltip_payload(vehicle):
    try:
        account_dossier = SERVICES.itemsCache.items.getAccountDossier()
        if account_dossier is None:
            LOGGER.debug('Account dossier unavailable; using empty stats')
            account_random_stats = None
            vehicle_cuts = {}
        else:
            account_random_stats = account_dossier.getRandomStats()
            vehicle_cuts = account_random_stats.getVehicles() if account_random_stats is not None else {}
    except Exception:
        LOGGER.debug('Unable to fetch account dossier; using defaults')
        account_random_stats = None
        vehicle_cuts = {}
    return {'version': MOD_VERSION,
     'stats': _build_stats(vehicle, account_random_stats, vehicle_cuts),
     'statsConfig': CONFIG.get('cardStats', {})}


def _patch_vehicle_tooltip():
    if getattr(CarouselVehicleTooltipModel, '_hcc_patched', False):
        return
    original_model_init = CarouselVehicleTooltipModel.__init__
    original_model_initialize = CarouselVehicleTooltipModel._initialize
    original_view_loading = CarouselVehicleTooltipView._onLoading

    def patched_model_init(self, properties=7, commands=0):
        original_model_init(self, properties=properties + 1, commands=commands)

    def patched_model_initialize(self):
        original_model_initialize(self)
        self._addViewModelProperty('hangarCarouselClassicTooltip', HangarCarouselClassicTooltipModel())

    def get_hcc_tooltip_model(self):
        return self._getViewModel(7)

    def patched_view_loading(self, *args, **kwargs):
        global TOOLTIP_PAYLOAD_LOGGED
        result = original_view_loading(self, *args, **kwargs)
        if not _is_hangar_context_active():
            return result
        try:
            vehicle = self._itemsCache.items.getVehicle(self._inventoryId)
            if vehicle is None:
                return result
            payload = _build_tooltip_payload(vehicle)
            with self.viewModel.transaction() as model:
                model.hangarCarouselClassicTooltip.setStateJson(json.dumps(payload, ensure_ascii=False, separators=(',', ':')))
            if not TOOLTIP_PAYLOAD_LOGGED:
                TOOLTIP_PAYLOAD_LOGGED = True
                LOGGER.info('Vehicle tooltip statistics model populated for %s', vehicle.intCD)
        except Exception:
            LOGGER.exception('Unable to populate HCC vehicle tooltip statistics')

        return result

    CarouselVehicleTooltipModel.__init__ = patched_model_init
    CarouselVehicleTooltipModel._initialize = patched_model_initialize
    CarouselVehicleTooltipModel.hangarCarouselClassicTooltip = property(get_hcc_tooltip_model)
    CarouselVehicleTooltipView._onLoading = patched_view_loading
    CarouselVehicleTooltipModel._hcc_patched = True


def _is_frontline_filter(provider):
    carousel_filter = getattr(provider, '_VehicleFiltersDataProvider__carouselFilter', None)
    filter_class = getattr(carousel_filter, '__class__', None)
    filter_module = getattr(filter_class, '__module__', '')
    return filter_module.startswith('frontline.')


def _is_allowed_hangar_path(space_path):
    if not space_path:
        return False
    normalized_path = space_path.lower()
    return any(normalized_path.startswith(prefix.lower()) for prefix in ALLOWED_HANGAR_PREFIXES)


def _is_hangar_context_active():
    """Keep the mod out of event hangars such as Onslaught (spaces/h33_comp7).

    Fail-closed while the hangar space is still loading, because the client
    restores the last used game mode on startup and may open an event hangar
    directly.  Space events re-evaluate the state as soon as it is known.
    """
    if dependency is None or IHangarSpace is None:
        return True
    try:
        hangar_space = dependency.instance(IHangarSpace)
    except Exception:
        hangar_space = None
    if hangar_space is None:
        return True
    try:
        space_path = hangar_space.spacePath
    except Exception:
        space_path = None
    active = _is_allowed_hangar_path(space_path)
    if active != HANGAR_GUARD_STATE.get('active') or space_path != HANGAR_GUARD_STATE.get('spacePath'):
        HANGAR_GUARD_STATE['active'] = active
        HANGAR_GUARD_STATE['spacePath'] = space_path
        LOGGER.info('hangar context %s for path=%r', 'active' if active else 'inactive', space_path)
    return active


def _is_provider_disabled(provider):
    return _is_frontline_filter(provider)


def _reapply_provider_carousel_state(provider):
    global LAST_PAYLOAD_SIGNATURE
    """Re-sync HCC properties and native row count for a tracked provider.

    Needed because a provider can finish loading while the hangar context is
    still resolving (e.g. right after returning from an event hangar), which
    means the one-shot row application in patched_on_loading was skipped.
    """
    try:
        with provider.viewModel.transaction() as model:
            model.setHccCarouselAuto(_carousel_auto())
            model.setHccSortJson(_build_sort_json())
    except Exception:
        LOGGER.exception('Unable to sync HCC properties in VehicleFilterModel')
    try:
        rows = _effective_carousel_rows() if _carousel_auto() else _carousel_rows() or 2
        if rows != _provider_row_count(provider):
            LAST_PAYLOAD_SIGNATURE = None
            _sync_provider_row_count(provider, rows, force=True)
    except Exception:
        LOGGER.exception('Unable to reapply HCC carousel row configuration')


def _on_hangar_space_event(*_args, **_kwargs):
    became_active = _is_hangar_context_active()
    if became_active:
        for provider in list(FILTER_PROVIDERS):
            _reapply_provider_carousel_state(provider)
    _refresh_all_models('hangar space event')


def _bind_hangar_space_events():
    if HANGAR_GUARD_STATE.get('bound') or dependency is None or IHangarSpace is None:
        return
    try:
        hangar_space = dependency.instance(IHangarSpace)
    except Exception:
        hangar_space = None
    if hangar_space is None:
        tries = int(HANGAR_GUARD_STATE.get('bindTries', 0))
        if tries >= 20:
            return
        HANGAR_GUARD_STATE['bindTries'] = tries + 1
        delay = min(0.35 * (1.6 ** tries), 8.0)
        _register_callback(delay + random.uniform(0.0, 0.2), _bind_hangar_space_events)
        return
    try:
        hangar_space.onSpaceCreate += _on_hangar_space_event
        hangar_space.onSpaceChanged += _on_hangar_space_event
        hangar_space.onSpaceDestroy += _on_hangar_space_event
        HANGAR_GUARD_STATE['bound'] = True
    except Exception:
        LOGGER.debug('Unable to bind hangar space events', exc_info=True)


def _patch_vehicle_filters_provider():
    if getattr(VehicleFiltersDataProvider, '_hcc_rows_patched', False):
        return
    original_on_loading = VehicleFiltersDataProvider._onLoading
    original_finalize = VehicleFiltersDataProvider._finalize

    def patched_on_loading(self, *args, **kwargs):
        result = original_on_loading(self, *args, **kwargs)
        # Track every non-frontline provider regardless of the current hangar
        # context. The hangar space path can still be stale/updating right
        # when this fires (e.g. returning from an event hangar), so relying
        # on a one-shot "is active now" check here would permanently skip
        # applying the configured row count to this provider instance.
        if _is_provider_disabled(self):
            return result
        _add_safe_provider(FILTER_PROVIDERS, self)
        if not _is_hangar_context_active():
            return result
        try:
            with self.viewModel.transaction() as model:
                model.setHccCarouselAuto(_carousel_auto())
                model.setHccSortJson(_build_sort_json())
        except Exception:
            LOGGER.exception('Unable to initialize HCC properties in VehicleFilterModel')
        try:
            rows = _effective_carousel_rows() if _carousel_auto() else _carousel_rows() or 2
            if rows != _provider_row_count(self):
                _sync_provider_row_count(self, rows, force=True)
        except Exception:
            LOGGER.exception('Unable to apply HCC carousel row configuration')
        return result

    def patched_finalize(self):
        try:
            if self in FILTER_PROVIDERS:
                # Create copy to avoid iterator invalidation during concurrent iteration
                providers_copy = list(FILTER_PROVIDERS)
                if self in providers_copy:
                    FILTER_PROVIDERS.remove(self)
        except Exception as e:
            LOGGER.warning('Error removing filter provider: %s', e)
        finally:
            original_finalize(self)

    VehicleFiltersDataProvider._onLoading = patched_on_loading
    VehicleFiltersDataProvider._finalize = patched_finalize
    VehicleFiltersDataProvider._hcc_rows_patched = True


def _patch_vehicle_statistics_presenter():
    if getattr(VehiclesStatisticsPresenter, '_hcc_patched', False):
        return
    original_init = VehiclesStatisticsPresenter.__init__
    original_finalize = VehiclesStatisticsPresenter._finalize
    original_update_vehicles = getattr(VehiclesStatisticsPresenter, '_VehiclesStatisticsPresenter__updateVehicles', None)

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _add_safe_provider(STATISTICS_PRESENTERS, self)

    def patched_finalize(self):
        try:
            if self in STATISTICS_PRESENTERS:
                STATISTICS_PRESENTERS.remove(self)
        finally:
            original_finalize(self)

    def patched_update_vehicles(self, vehicles):
        hangar_active = _is_hangar_context_active()
        filtered_vehicles = vehicles
        if hangar_active and CONFIG.get('filtering', {}).get('enabled', True) and ACTIVE_FILTERS and vehicles is not None:
            filtered_vehicles = dict(((int_cd, vehicle) for int_cd, vehicle in vehicles.items()
             if all((_matches(filter_id, vehicle) for filter_id in ACTIVE_FILTERS))))
        if original_update_vehicles:
            original_update_vehicles(self, filtered_vehicles)
        if hangar_active:
            try:
                _apply_auto_rows(len(filtered_vehicles) if filtered_vehicles is not None else None)
            except Exception:
                LOGGER.exception('Unable to apply automatic rows from statistics presenter')
        _refresh_all_models('statistics presenter update')

    VehiclesStatisticsPresenter.__init__ = patched_init
    VehiclesStatisticsPresenter._finalize = patched_finalize
    if original_update_vehicles:
        VehiclesStatisticsPresenter._VehiclesStatisticsPresenter__updateVehicles = patched_update_vehicles
    VehiclesStatisticsPresenter._hcc_patched = True


def _patch_legacy_playlist_cleanup():
    if getattr(VehiclePlaylistsPresenter, '_hcc_cleanup_patched', False):
        return
    original_on_loading = VehiclePlaylistsPresenter._onLoading

    def patched_on_loading(self, *args, **kwargs):
        _remove_legacy_playlists()
        return original_on_loading(self, *args, **kwargs)

    VehiclePlaylistsPresenter._onLoading = patched_on_loading
    VehiclePlaylistsPresenter._hcc_cleanup_patched = True


def _settings_tooltip(title, body):
    try:
        from gui.shared.utils.functions import makeTooltip
        return makeTooltip(title, body)
    except Exception:
        return u'%s\n%s' % (title, body)


SETTINGS_TEXT = {'en': {'display': u'Carousel and cards',
    'filtering': u'Filtering',
    'filteringTooltip': u'Enable or disable filtering. Individual filters can be toggled here in MSA or in the HCC filter panel. Counts use the current native vehicle list: ALL shows vehicles matching every active filter, and each filter count shows matching vehicles within that current selection. HCC changes synchronize the MSA values and vehicle list; MSA changes synchronize the HCC panel and vehicle list.',
    'filterNonElite': u'Non-elite tanks',
    'filterNonEliteTooltip': u'Show only vehicles that do not have elite status.',
    'filterNotReady': u'Broken / crew incomplete',
    'filterNotReadyTooltip': u'Show only vehicles that are broken, have an incomplete crew, or do not have a full ammunition load.',
    'filterMarksIncomplete': u'Marks incomplete (Tier V+)',
    'filterMarksIncompleteTooltip': u'Show only Tier V or higher vehicles with less than three Marks of Excellence.',
    'filterCrewNotMaxed': u'Crew not fully trained',
    'filterCrewNotMaxedTooltip': u'Show only vehicles whose currently assigned crew is not fully trained for that vehicle, according to the client crew state.',
    'sorting': u'Sorting',
    'sortingTooltip': u'Enable or disable HCC sorting. The buttons in the HCC panel set one sorting rule at a time. Use the MSA Sort criteria field below to configure multiple rules as a hierarchy.',
    'cardStatsFields': u'Card statistics fields',
    'native': u'Already provided by the client: Premium, Elite, rented/temporary, daily bonus and Battle Pass points available.',
    'enabled': u'Enable Hangar Carousel Classic',
    'cardStats': u'Show statistics on vehicle cards',
    'cardStatsTooltip': u'Enable or disable the statistics overlay on vehicle cards. The fields below control which values are shown.',
    'minBattles': u'Minimum battles for card statistics',
    'minBattlesTooltip': u'Only vehicles with at least this many battles receive a card-statistics overlay.',
    'rows': u'Carousel rows',
    'rowsTooltip': u'Choose the number of vehicle rows. Automatic mode adapts the row count to the number of matching vehicles.',
    'auto': u'Automatic',
    'sortingCriteria': u'Sort criteria',
    'sortingCriteriaTooltip': u'Configure multiple sorting rules as a hierarchy. The first value is primary, followed by tie-breakers. HCC panel buttons set one rule at a time. Supported values: nation, type, level, maxBattleTier, premium, battles, winRate, markOfMastery, averageDamage, alphaDamage, marksOnGun, battlePassPoints, lastPlayed. Prefix a value with - to reverse its order (examples: -averageDamage, -alphaDamage).',
    'nationsOrder': u'Nation order',
    'nationsOrderTooltip': u'Comma-separated nation priority, for example: ussr, germany, usa, china, france, uk, japan, czech, poland, sweden, italy.',
    'typesOrder': u'Type order',
    'typesOrderTooltip': u'Comma-separated vehicle type priority, for example: lightTank, mediumTank, heavyTank, AT-SPG, SPG.',
    'hideBuyTank': u'Hide "Buy vehicle" cell',
    'hideBuyTankTooltip': u'Hide the client cell used to buy a vehicle.',
    'hideBuySlot': u'Hide "Buy slot" cell',
    'hideBuySlotTooltip': u'Hide the client cell used to buy a garage slot.',
    'hideRestoreTank': u'Hide "Restore vehicle" cell',
    'hideRestoreTankTooltip': u'Hide the client cell used to restore a vehicle.',
    'restart': u'Changes are applied immediately; restart the client after changing the master switch.'}}


def _resolve_mods_settings_api():
    try:
        from gui.aslainMenu import g_modsSettingsApi, templates
        return g_modsSettingsApi, templates
    except Exception:
        pass
    try:
        from gui.modsSettingsApi import g_modsSettingsApi, templates
        return g_modsSettingsApi, templates
    except ImportError:
        return None, None


def _schedule_settings_registration():
    state = SETTINGS_REGISTRATION_STATE
    if SETTINGS_REGISTERED or int(state.get('tries', 0)) >= int(state.get('maxTries', 20)):
        if not SETTINGS_REGISTERED and not state.get('exhaustedLogged'):
            state['exhaustedLogged'] = True
            LOGGER.warning('ModsSettingsApi unavailable after %d attempts; settings panel not registered',
                           int(state.get('tries', 0)))
        return
    current_delay = float(state.get('delay', 0.35))
    jitter = random.uniform(0.0, max(0.05, current_delay * 0.3))
    _register_callback(min(current_delay + jitter, float(state.get('maxDelay', 8.0))), _register_settings)
    state['delay'] = min(max(0.35, current_delay * 1.6), float(state.get('maxDelay', 8.0)))


def _set_mods_settings_template(g_mods_settings_api, template):
    try:
        g_mods_settings_api.setModTemplate(MOD_LINKAGE_ID, template, _on_settings_changed)
        return
    except TypeError:
        try:
            g_mods_settings_api.setModTemplate(MOD_LINKAGE_ID, template, _on_settings_changed, None)
            return
        except TypeError:
            g_mods_settings_api.setModTemplate(MOD_LINKAGE_ID, template)


def _register_settings():
    global SETTINGS_REGISTERED, MSA_API, MSA_SETTINGS
    if SETTINGS_REGISTERED:
        return
    state = SETTINGS_REGISTRATION_STATE
    state['tries'] = int(state.get('tries', 0)) + 1
    try:
        g_mods_settings_api, templates = _resolve_mods_settings_api()
        if g_mods_settings_api is None or templates is None:
            if not state.get('unavailableLogged'):
                state['unavailableLogged'] = True
                LOGGER.info('ModsSettingsApi not available yet; retrying settings registration')
            _schedule_settings_registration()
            return
        text = SETTINGS_TEXT['en']
        
        # Current config values
        filtering_enabled = bool(CONFIG.get('filtering', {}).get('enabled', True))
        sorting_enabled = bool(CONFIG.get('sorting', {}).get('enabled', True))
        sorting_criteria = _get_configured_sorting_criteria()
        nations_order = CONFIG.get('sorting', {}).get('nations_order', [])
        types_order = CONFIG.get('sorting', {}).get('types_order', [])
        rows_value = 0 if _carousel_auto() else _carousel_rows() or 2
        card_stats = _normalized_card_stats_config(CONFIG.get('cardStats', {}))
        card_stat_fields = card_stats.get('fields', [])
        
        # Format for display in UI (join with commas)
        criteria_str = ', '.join(sorting_criteria) if sorting_criteria else ', '.join(_default_sorting_criteria())
        nations_str = ', '.join(nations_order) if nations_order else ''
        types_str = ', '.join(types_order) if types_order else ''
        
        # Build UI columns
        column1 = [templates.createLabel(text['display']),
         templates.createCheckbox(text['cardStats'], 'cardStatsEnabled', bool(card_stats.get('enabled', True)),
                                  tooltip=_settings_tooltip(text['cardStats'], text['cardStatsTooltip'])),
         templates.createNumericStepper(text['minBattles'], 'minimumBattles', int(card_stats.get('minimumBattles', 1)), 0, 1000, 1,
                                        manual=True, tooltip=_settings_tooltip(text['minBattles'], text['minBattlesTooltip'])),
         templates.createLabel(text['cardStatsFields']),
         templates.createCheckbox(u'Battles', 'showBattles', 'battles' in card_stat_fields),
         templates.createCheckbox(u'Win rate', 'showWinRate', 'winRate' in card_stat_fields),
         templates.createCheckbox(u'Average damage', 'showAverageDamage', 'averageDamage' in card_stat_fields),
         templates.createCheckbox(u'Alpha damage', 'showAlphaDamage', 'alphaDamage' in card_stat_fields),
         templates.createCheckbox(u'Mastery badge', 'showMastery', 'mastery' in card_stat_fields),
         templates.createCheckbox(u'Marks of Excellence', 'showMarksOnGun', 'marksOnGun' in card_stat_fields),
         templates.createDropdown(text['rows'], 'carouselRows', [text['auto'],
          u'1',
          u'2',
         u'3',
         u'4'], rows_value, tooltip=_settings_tooltip(text['rows'], text['rowsTooltip']))]
        
        filter_settings = (
            ('non_elite', 'filterNonElite', 'filterNonEliteTooltip'),
            ('not_ready', 'filterNotReady', 'filterNotReadyTooltip'),
            ('marks_incomplete', 'filterMarksIncomplete', 'filterMarksIncompleteTooltip'),
            ('crew_not_maxed', 'filterCrewNotMaxed', 'filterCrewNotMaxedTooltip')
        )
        filter_controls = [templates.createLabel(text['filtering']),
         templates.createCheckbox(text['filtering'], 'filteringEnabled', filtering_enabled,
                                  tooltip=_settings_tooltip(text['filtering'], text['filteringTooltip']))]
        for filter_id, text_key, tooltip_key in filter_settings:
            filter_controls.append(templates.createCheckbox(
                text[text_key], 'filter_%s' % filter_id, filter_id in ACTIVE_FILTERS,
                tooltip=_settings_tooltip(text[text_key], text[tooltip_key])))
        column2 = filter_controls + [
         templates.createLabel(text['sorting']),
         templates.createCheckbox(text['sorting'], 'sortingEnabled', sorting_enabled,
                                  tooltip=_settings_tooltip(text['sorting'], text['sortingTooltip'])),
         templates.createInput(text['sortingCriteria'], 'sortingCriteria', criteria_str, tooltip=_settings_tooltip(text['sortingCriteria'], text['sortingCriteriaTooltip'])),
         templates.createInput(text['nationsOrder'], 'nationsOrder', nations_str, tooltip=_settings_tooltip(text['nationsOrder'], text['nationsOrderTooltip'])),
         templates.createInput(text['typesOrder'], 'typesOrder', types_str, tooltip=_settings_tooltip(text['typesOrder'], text['typesOrderTooltip'])),
         templates.createEmpty(8),
         templates.createCheckbox(text['hideBuyTank'], 'hideBuyTank', bool(CONFIG.get('actionCards', {}).get('hideBuyTank', False)),
                                  tooltip=_settings_tooltip(text['hideBuyTank'], text['hideBuyTankTooltip'])),
         templates.createCheckbox(text['hideBuySlot'], 'hideBuySlot', bool(CONFIG.get('actionCards', {}).get('hideBuySlot', False)),
                                  tooltip=_settings_tooltip(text['hideBuySlot'], text['hideBuySlotTooltip'])),
         templates.createCheckbox(text['hideRestoreTank'], 'hideRestoreTank', bool(CONFIG.get('actionCards', {}).get('hideRestoreTank', False)),
                                  tooltip=_settings_tooltip(text['hideRestoreTank'], text['hideRestoreTankTooltip']))]
        
        template = {'modDisplayName': u'Hangar Carousel Classic',
         'settingsVersion': 7,
         'enabled': bool(CONFIG.get('enabled', True)),
         'column1': column1,
         'column2': column2}
        # ModsSettingsAPI auto-deregisters callback on mod unload; no manual deregister needed
        _set_mods_settings_template(g_mods_settings_api, template)
        MSA_API = g_mods_settings_api
        saved_settings = g_mods_settings_api.getModSettings(MOD_LINKAGE_ID, template)
        if isinstance(saved_settings, dict):
            MSA_SETTINGS = dict(saved_settings)
        SETTINGS_REGISTERED = True
        LOGGER.info('ModsSettingsAPI integration registered (sorting + 4 HCC filters)')
    except Exception:
        LOGGER.exception('Unable to register ModsSettingsAPI integration')
        _schedule_settings_registration()


def _on_settings_changed(linkage, settings):
    if linkage != MOD_LINKAGE_ID:
        return
    try:
        global CONFIG, MSA_SETTINGS
        if MSA_SYNCING:
            MSA_SETTINGS.clear()
            MSA_SETTINGS.update(settings or {})
            return
        if isinstance(settings, dict):
            MSA_SETTINGS = dict(settings)
        current_config = json.loads(json.dumps(CONFIG)) if CONFIG else {}
        was_enabled = bool(CONFIG.get('enabled', True)) if CONFIG else False
        is_enabled = bool(settings.get('enabled', was_enabled))
        current_config['enabled'] = is_enabled
        CONFIG.clear()
        CONFIG.update(current_config)
        
        # If mod was disabled, clean up and exit early
        if was_enabled and not is_enabled:
            _save_config()
            fini()
            CONFIG = current_config
            LOGGER.info('Hangar Carousel Classic disabled via MSA')
            return
        
        # If mod was enabled, reinitialize patches
        if not was_enabled and is_enabled:
            try:
                _patch_vehicle_filter_model()
                _patch_vehicle_filters_provider()
                _patch_vehicle_tooltip()
                _patch_vehicle_statistics_presenter()
                _patch_legacy_playlist_cleanup()
                _bind_hangar_space_events()
                g_playerEvents.onAvatarReady += _track_last_played
                if hasattr(g_playerEvents, 'onAccountBecomePlayer'):
                    g_playerEvents.onAccountBecomePlayer += _on_account_become_player
                LOGGER.info('Hangar Carousel Classic re-enabled via MSA')
            except Exception:
                LOGGER.exception('Unable to re-enable Hangar Carousel Classic')
                return
        
        card_stats = CONFIG.setdefault('cardStats', {})
        if card_stats is not None:
            card_stats['enabled'] = bool(settings.get('cardStatsEnabled', True))
            card_stats['minimumBattles'] = max(0, int(settings.get('minimumBattles', 1)))
            field_settings = (
                ('battles', 'showBattles'),
                ('winRate', 'showWinRate'),
                ('averageDamage', 'showAverageDamage'),
                ('alphaDamage', 'showAlphaDamage'),
                ('mastery', 'showMastery'),
                ('marksOnGun', 'showMarksOnGun')
            )
            current_fields = _normalized_card_stats_config(card_stats).get('fields', [])
            card_stats['fields'] = [field for field, setting_key in field_settings
                                    if bool(settings.get(setting_key, field in current_fields))]
        sorting = CONFIG.setdefault('sorting', {})
        filtering = CONFIG.setdefault('filtering', {})
        if filtering is not None:
            filtering['enabled'] = bool(settings.get('filteringEnabled', True))
        _apply_msa_filter_settings(settings)
        if sorting is not None:
            sorting['enabled'] = bool(settings.get('sortingEnabled', True))
        
        # Parse sorting criteria from comma-separated input
        criteria_input = settings.get('sortingCriteria', None)
        if criteria_input is None:
            sorting_criteria = _get_configured_sorting_criteria()
        else:
            sorting_criteria = [c.strip() for c in criteria_input.split(',') if c.strip()]
        _set_sorting_criteria(sorting_criteria)
        
        # Parse nations order from comma-separated input
        nations_input = settings.get('nationsOrder', '')
        nations_order = [n.strip() for n in nations_input.split(',') if n.strip()]
        _set_nations_order(nations_order)
        
        # Parse vehicle types order from comma-separated input
        types_input = settings.get('typesOrder', '')
        types_order = [t.strip() for t in types_input.split(',') if t.strip()]
        _set_types_order(types_order)
        
        # Apply action card visibility settings
        actions = CONFIG.setdefault('actionCards', {})
        actions['hideBuyTank'] = bool(settings.get('hideBuyTank', False))
        actions['hideBuySlot'] = bool(settings.get('hideBuySlot', False))
        actions['hideRestoreTank'] = bool(settings.get('hideRestoreTank', False))
        
        _save_config()
        _set_carousel_rows(int(settings.get('carouselRows', 0)), refresh=False)
        _refresh_models_lightweight('MSA settings changed')

    except Exception:
        LOGGER.exception('Unable to apply ModsSettingsAPI settings')


try:
    _patch_carousel_filter_compat()
except Exception:
    LOGGER.exception('Unable to apply carousel filter compatibility patch')

try:
    _register_callback(0.1, _register_settings)
except Exception:
    LOGGER.exception('Hangar Carousel Classic services failed to initialize')

if CONFIG.get('enabled', True):
    try:
        _patch_carousel_filter_compat()
        _patch_vehicle_filter_model()
        _patch_vehicle_filters_provider()
        _patch_vehicle_tooltip()
        _patch_vehicle_statistics_presenter()
        _patch_legacy_playlist_cleanup()
        _bind_hangar_space_events()
        g_playerEvents.onAvatarReady += _track_last_played
        if hasattr(g_playerEvents, 'onAccountBecomePlayer'):
            g_playerEvents.onAccountBecomePlayer += _on_account_become_player
        _register_callback(1.0, _check_native_client_compatibility)
        LOGGER.info('Hangar Carousel Classic %s loaded', MOD_VERSION)
    except Exception:
        LOGGER.exception('Hangar Carousel Classic failed to initialize')
