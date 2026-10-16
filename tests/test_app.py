"""Offline checks: fake EE responses explicitly; never authenticate or use network."""
import unittest
from unittest.mock import MagicMock, patch

import app as web
import config


class BaselineTests(unittest.TestCase):
    def setUp(self):
        web.app.config['TESTING'] = True
        web.limiter.reset()
        self.client = web.app.test_client()

    def test_home_without_ee(self):
        with patch('app.initialize_ee') as init:
            response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'TerraWatch AI', response.data)
        self.assertNotIn(b'{{', response.data)
        init.assert_not_called()
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')

    def test_health_is_only_liveness(self):
        self.assertEqual(self.client.get('/healthz').json,
                         {'status': 'ok', 'earth_engine': 'not_checked'})

    def test_invalid_dates_never_call_ee(self):
        queries = ['', '?start=foo&end=bar', '?start=2024-02-30&end=2024-03-01',
                   '?start=2024-02-01&end=2024-01-01', '?start=2024-01-01&end=2024-01-01',
                   '?start=2010-01-01&end=2010-02-01', '?start=2020-01-01&end=2024-01-01',
                   '?start=2999-01-01&end=2999-02-01', '?start=20240101&end=20240201']
        with patch('app.initialize_ee') as init:
            for query in queries:
                with self.subTest(query=query):
                    self.assertEqual(self.client.get('/get_stats'+query).status_code, 400)
            init.assert_not_called()

    def test_missing_project(self):
        with patch.object(config, 'PROJECT_ID', ''):
            response = self.client.get('/get_stats?start=2024-01-01&end=2024-02-01')
        self.assertEqual(response.status_code, 503)
        self.assertIn('EE_PROJECT', response.json['error'])

    def test_failed_auth_is_sanitized(self):
        with patch.object(config, 'PROJECT_ID', 'test-project'), patch.object(config, '_ready', False), \
                patch('config.ee.Initialize', side_effect=RuntimeError('SECRET')):
            response = self.client.get('/get_stats?start=2024-01-01&end=2024-02-01')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('SECRET', response.get_data(as_text=True))

    def test_initialize_once_with_explicit_project(self):
        with patch.object(config, 'PROJECT_ID', 'test-project'), patch.object(config, '_ready', False), \
                patch('config.ee.Initialize') as init, patch('config.ee.data.setDeadline'):
            config.initialize_ee()
            config.initialize_ee()
            init.assert_called_once_with(project='test-project')

    def analysis(self, count=1, value=0.0):
        collection, image, ndvi = MagicMock(), MagicMock(), MagicMock()
        collection.size.return_value.getInfo.return_value = count
        collection.map.return_value.median.return_value.clip.return_value = image
        image.expression.return_value.rename.return_value = ndvi
        ndvi.reduceRegion.return_value.get.return_value.getInfo.return_value = value
        image.getMapId.return_value = {'tile_fetcher': MagicMock(url_format='https://example.test/rgb/{z}/{x}/{y}')}
        ndvi.getMapId.return_value = {'tile_fetcher': MagicMock(url_format='https://example.test/ndvi/{z}/{x}/{y}')}
        with patch('app.initialize_ee'), patch('app.get_roi', return_value='roi'), \
                patch('app.get_landsat', return_value=collection), patch('app.ee.Reducer'):
            response = self.client.get('/get_stats?start=2024-01-01&end=2024-02-01')
        return response, collection, ndvi

    def test_zero_ndvi_is_valid_and_scaling_precedes_median(self):
        response, collection, ndvi = self.analysis()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mean_ndvi'], 0.0)
        self.assertIn('rgb', response.json)
        collection.map.assert_called_once_with(web.scale)
        self.assertEqual(ndvi.reduceRegion.call_args.kwargs['maxPixels'], 10_000_000)

    def test_empty_collection(self):
        response, _, _ = self.analysis(count=0)
        self.assertEqual(response.status_code, 404)

    def test_no_valid_pixels(self):
        response, _, _ = self.analysis(value=None)
        self.assertEqual(response.status_code, 404)

    def test_backend_failure_sanitized(self):
        with patch('app.initialize_ee'), patch('app.get_roi', side_effect=RuntimeError('PRIVATE DETAIL')), \
                self.assertLogs(web.app.logger, level='ERROR'):
            response = self.client.get('/get_stats?start=2024-01-01&end=2024-02-01')
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('PRIVATE DETAIL', response.get_data(as_text=True))

    def test_rate_limit_returns_json(self):
        for _ in range(10):
            self.client.get('/get_stats')
        response = self.client.get('/get_stats')
        self.assertEqual(response.status_code, 429)
        self.assertIn('error', response.json)


if __name__ == '__main__':
    unittest.main()
