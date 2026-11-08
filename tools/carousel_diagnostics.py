"""Runtime helpers included only in the separate diagnostic WOTMOD."""
from __future__ import absolute_import, division

import time


_clock = time.clock
_profile = None


def _hcc_timed(category, function, *args, **kwargs):
    profile = _profile
    if profile is None:
        return function(*args, **kwargs)
    started = _clock()
    try:
        return function(*args, **kwargs)
    finally:
        profile[category] += _clock() - started
        profile[category + '_calls'] += 1


def _hcc_dossier(function):
    def measured(vehicle_id):
        if _profile is not None:
            key = (int(vehicle_id), DOSSIER_CACHE_GENERATION)
            _profile['dossier_hits' if key in DOSSIER_CACHE else 'dossier_misses'] += 1
        return function(vehicle_id)
    return measured


def _hcc_stats(function):
    def measured(*args, **kwargs):
        if _profile is not None:
            _profile['vehicles'] += 1
        return _hcc_timed('stats', function, *args, **kwargs)
    return measured


def _hcc_payload(function):
    def measured(*args, **kwargs):
        global _profile
        previous = _profile
        profile = dict((name, 0) for name in (
            'alpha', 'alpha_calls', 'dossier', 'dossier_calls',
            'extract', 'extract_calls', 'stats', 'stats_calls',
            'dossier_hits', 'dossier_misses', 'vehicles', 'fingerprint', 'fingerprint_calls'))
        alpha_before = dict(ALPHA_DAMAGE_STATS)
        _profile = profile
        started = _clock()
        completed = False
        try:
            result = function(*args, **kwargs)
            completed = True
            return result
        finally:
            elapsed = _clock() - started
            _profile = previous
            # Lightweight refreshes do not rebuild stats or emit a profile.
            if profile['vehicles'] or profile['dossier_misses']:
                LOGGER.info(
                    'HCC DIAG %s: complete=%s generation=%d vehicles=%d '
                    'payload_ms=%.3f stats_ms=%.3f alpha_ms=%.3f '
                    'dossier_fetch_ms=%.3f dossier_extract_ms=%.3f '
                    'alpha_reused=%d alpha_computed=%d '
                    'dossier_hits=%d dossier_misses=%d dossier_fetches=%d '
                    'alpha_persistent_reused=%d alpha_fingerprint_ms=%.3f',
                    MOD_VERSION, completed, DOSSIER_CACHE_GENERATION,
                    profile['vehicles'], elapsed * 1000, profile['stats'] * 1000,
                    profile['alpha'] * 1000, profile['dossier'] * 1000,
                    profile['extract'] * 1000,
                    ALPHA_DAMAGE_STATS['hits'] - alpha_before['hits'],
                    ALPHA_DAMAGE_STATS['computed'] - alpha_before['computed'],
                    profile['dossier_hits'], profile['dossier_misses'],
                    profile['dossier_calls'],
                    ALPHA_DAMAGE_STATS.get('persistent', 0) - alpha_before.get('persistent', 0),
                    profile['fingerprint'] * 1000)
    return measured


_get_vehicle_dossier = _hcc_dossier(_get_vehicle_dossier)
_build_stats = _hcc_stats(_build_stats)
_build_payload = _hcc_payload(_build_payload)
