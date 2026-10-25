import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import io
import unittest
import urllib.error
from unittest.mock import patch, MagicMock

from scrapers.biolink_resolver import (
    is_biolink_url,
    extract_whatsapp_from_html,
    resolve_biolink_whatsapp,
)

MOCK_LINKTREE_HTML = """
<html><body>
<a class="LinkClickTrigger" href="https://wa.me/6281234567890?text=Halo">Chat WhatsApp</a>
<a href="https://instagram.com/toko">Instagram</a>
</body></html>
"""

MOCK_DESTY_HTML = """
<html><body>
<div data-url="https://api.whatsapp.com/send?phone=628567891234&amp;text=Order"></div>
</body></html>
"""

MOCK_TAPLINK_HTML = """
<html><body>
<a href="https://taplink.cc/id?wa=081122334455">Hubungi kami</a>
</body></html>
"""


class TestIsBiolinkUrl(unittest.TestCase):

    def test_supported_domains(self):
        for url in (
            'https://linktr.ee/tokomakassar',
            'https://desty.page/toko',
            'https://taplink.cc/toko',
            'https://beacons.ai/toko',
            'https://bio.site/toko',
            'https://biolinky.co/toko',
        ):
            self.assertTrue(is_biolink_url(url), url)

    def test_subdomain_supported(self):
        self.assertTrue(is_biolink_url('https://www.linktr.ee/toko'))

    def test_regular_url_not_biolink(self):
        self.assertFalse(is_biolink_url('https://tokopakaian.co.id'))
        self.assertFalse(is_biolink_url('https://wa.me/6281234567890'))

    def test_empty_and_none(self):
        self.assertFalse(is_biolink_url(''))
        self.assertFalse(is_biolink_url(None))


class TestExtractWhatsappFromHtml(unittest.TestCase):

    def test_linktree_wa_me_pattern(self):
        self.assertEqual(extract_whatsapp_from_html(MOCK_LINKTREE_HTML), '6281234567890')

    def test_desty_api_whatsapp_pattern(self):
        self.assertEqual(extract_whatsapp_from_html(MOCK_DESTY_HTML), '628567891234')

    def test_taplink_wa_param_pattern(self):
        self.assertEqual(extract_whatsapp_from_html(MOCK_TAPLINK_HTML), '6281122334455')

    def test_no_whatsapp_in_html(self):
        self.assertIsNone(extract_whatsapp_from_html('<html><body>Tidak ada nomor</body></html>'))

    def test_invalid_number_skipped(self):
        html = '<a href="https://wa.me/123">bukan nomor valid</a>'
        self.assertIsNone(extract_whatsapp_from_html(html))

    def test_empty_html(self):
        self.assertIsNone(extract_whatsapp_from_html(''))


class TestResolveBiolinkWhatsapp(unittest.TestCase):

    def test_non_biolink_url_returns_none_without_request(self):
        with patch('scrapers.biolink_resolver.urllib.request.urlopen') as mock_open:
            self.assertIsNone(resolve_biolink_whatsapp('https://example.com'))
            mock_open.assert_not_called()

    def test_resolve_linktree_success(self):
        response = MagicMock()
        response.status = 200
        response.read.return_value = MOCK_LINKTREE_HTML.encode('utf-8')
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        with patch('scrapers.biolink_resolver.urllib.request.urlopen', return_value=response):
            self.assertEqual(resolve_biolink_whatsapp('https://linktr.ee/toko'), '6281234567890')

    def test_resolve_desty_success(self):
        response = MagicMock()
        response.status = 200
        response.read.return_value = MOCK_DESTY_HTML.encode('utf-8')
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        with patch('scrapers.biolink_resolver.urllib.request.urlopen', return_value=response):
            self.assertEqual(resolve_biolink_whatsapp('https://desty.page/toko'), '628567891234')

    def test_http_error_returns_none(self):
        err = urllib.error.HTTPError('https://linktr.ee/x', 404, 'Not Found', {}, io.BytesIO(b''))
        with patch('scrapers.biolink_resolver.urllib.request.urlopen', side_effect=err):
            self.assertIsNone(resolve_biolink_whatsapp('https://linktr.ee/x'))

    def test_timeout_returns_none(self):
        with patch('scrapers.biolink_resolver.urllib.request.urlopen', side_effect=TimeoutError()):
            self.assertIsNone(resolve_biolink_whatsapp('https://linktr.ee/x'))

    def test_url_error_returns_none(self):
        with patch('scrapers.biolink_resolver.urllib.request.urlopen',
                   side_effect=urllib.error.URLError('dns gagal')):
            self.assertIsNone(resolve_biolink_whatsapp('https://linktr.ee/x'))

    def test_non_200_status_returns_none(self):
        response = MagicMock()
        response.status = 503
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        with patch('scrapers.biolink_resolver.urllib.request.urlopen', return_value=response):
            self.assertIsNone(resolve_biolink_whatsapp('https://linktr.ee/x'))


if __name__ == '__main__':
    unittest.main()
