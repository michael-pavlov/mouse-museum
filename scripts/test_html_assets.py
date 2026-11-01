import unittest
from html_test_helpers import assert_local_images


class LocalImageTests(unittest.TestCase):
    def test_local_images_and_exact_noscript_counter_are_allowed(self):
        assert_local_images(self, '<img src="../../assets/photo.webp"><noscript><img src="https://mc.yandex.ru/watch/113889111"></noscript>')

    def test_external_images_are_rejected(self):
        for src in ('https://example.com/photo.webp', 'http://example.com/photo.webp', '//example.com/photo.webp', 'https://mc.yandex.ru/watch/999'):
            with self.subTest(src=src), self.assertRaises(AssertionError):
                assert_local_images(self, f'<noscript><img src="{src}"></noscript>')

    def test_counter_is_only_exempt_inside_noscript(self):
        with self.assertRaises(AssertionError):
            assert_local_images(self, '<img src="https://mc.yandex.ru/watch/113889111">')
