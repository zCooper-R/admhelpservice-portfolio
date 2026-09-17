import logging
import time

import requests


logger = logging.getLogger('adm.integrations.gps')


class GpsApi:
    BASE_URL = 'https://gps.avtocontrol.com/api-v2'

    def __init__(self, login, password):
        self.login = login
        self.password = password
        self._hash = None
        self.session = requests.Session()
        self._get_hash()

    def _request(self, method: str, endpoint: str, *, params=None, json=None, timeout=10):
        url = f'{self.BASE_URL}/{endpoint}'
        started_at = time.monotonic()
        response = self.session.request(method=method, url=url, params=params, json=json, timeout=timeout)
        duration_ms = int((time.monotonic() - started_at) * 1000)
        logger.info(
            'gps api request method=%s endpoint=%s status=%s duration_ms=%s',
            method,
            endpoint,
            response.status_code,
            duration_ms,
            extra={'event': 'gps_api_request', 'duration_ms': duration_ms},
        )
        response.raise_for_status()
        return response.json()

    def _get_hash(self) -> None:
        if self._hash is not None:
            return self._hash

        try:
            data = self._request(
                'GET',
                'user/auth',
                params={'login': self.login, 'password': self.password},
            )
            if data.get('success'):
                self._hash = data['hash']
                return self._hash
            logger.error('gps api authentication failed', extra={'event': 'gps_auth_failed'})
            raise RuntimeError('GPS API authentication failed')
        except requests.RequestException:
            logger.exception('gps api authentication request failed')
            raise

    def get_tracker_list(self) -> list:
        try:
            data = self._request('GET', 'tracker/list', params={'hash': self._hash})
            if data.get('success'):
                return data['list']
            raise RuntimeError('GPS API tracker list request failed')
        except requests.RequestException:
            logger.exception('gps api get tracker list failed')
            raise

    def get_tracker_counters(self, tracker_id: int, counter_type: str) -> list:
        try:
            data = self._request(
                'GET',
                'tracker/get_counters',
                params={'hash': self._hash, 'tracker_id': tracker_id, 'type': counter_type},
            )
            if data.get('success'):
                return data['list']
            raise RuntimeError(f'GPS API tracker counters request failed for tracker={tracker_id}')
        except requests.RequestException:
            logger.exception('gps api get tracker counters failed tracker_id=%s counter_type=%s', tracker_id, counter_type)
            raise

    def get_tracker_counter_value(self, tracker_id: int, counter_type: str) -> str:
        try:
            data = self._request(
                'GET',
                'tracker/counter/value/get',
                params={'hash': self._hash, 'tracker_id': tracker_id, 'type': counter_type},
            )
            if data.get('success'):
                return data['value']
            raise RuntimeError(f'GPS API tracker counter value request failed for tracker={tracker_id}')
        except requests.RequestException:
            logger.exception('gps api get tracker counter value failed tracker_id=%s counter_type=%s', tracker_id, counter_type)
            raise

    def get_tracker_counter_value_period(self, tracker_id: int, counter_type: str, start_time, end_time) -> list:
        try:
            data = self._request(
                'POST',
                'tracker/counter/data/read',
                json={'hash': self._hash, 'tracker_id': tracker_id, 'type': counter_type, 'from': start_time, 'to': end_time},
            )
            if data.get('success'):
                return data['list']
            raise RuntimeError(f'GPS API counter period request failed for tracker={tracker_id}')
        except requests.RequestException:
            logger.exception(
                'gps api get tracker counter period failed tracker_id=%s counter_type=%s start=%s end=%s',
                tracker_id,
                counter_type,
                start_time,
                end_time,
            )
            raise

    def get_trackers_counter_values(self, trackers_list, counter_type) -> dict:
        try:
            data = self._request(
                'POST',
                'tracker/counter/value/list',
                json={'hash': self._hash, 'trackers': trackers_list, 'type': counter_type},
            )
            if data.get('success'):
                return data['value']
            raise RuntimeError(f'GPS API counters list request failed for type={counter_type}')
        except requests.RequestException:
            logger.exception(
                'gps api get trackers counter values failed counter_type=%s trackers_count=%s',
                counter_type,
                len(trackers_list or []),
            )
            raise
