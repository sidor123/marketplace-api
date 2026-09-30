from datetime import datetime, timezone
import unittest

from pydantic import ValidationError

from app.schemas import PromoCodeCreate


class PromoCodeSchemaTests(unittest.TestCase):
    def promo(self, valid_from, valid_until):
        return PromoCodeCreate(
            code='SAVE10', discount_type='FIXED_AMOUNT', discount_value='10',
            max_uses=1, valid_from=valid_from, valid_until=valid_until)

    def test_dates_are_normalized_to_utc_before_comparison(self):
        for valid_from, valid_until in (
            ('2026-01-01T00:00:00', '2026-01-01T04:00:00+03:00'),
            ('2026-01-01T03:00:00+03:00', '2026-01-01T01:00:00'),
        ):
            with self.subTest(valid_from=valid_from, valid_until=valid_until):
                promo = self.promo(valid_from, valid_until)
                self.assertEqual(promo.valid_from, datetime(2026, 1, 1, tzinfo=timezone.utc))
                self.assertEqual(promo.valid_until, datetime(2026, 1, 1, 1, tzinfo=timezone.utc))
                self.assertEqual(promo.valid_from.tzinfo, timezone.utc)
                self.assertEqual(promo.valid_until.tzinfo, timezone.utc)

    def test_invalid_mixed_timezone_interval_is_validation_error(self):
        for valid_until in ('2026-01-01T02:00:00+03:00', '2026-01-01T00:00:00Z'):
            with self.subTest(valid_until=valid_until):
                with self.assertRaises(ValidationError):
                    self.promo('2026-01-01T00:00:00', valid_until)


if __name__ == '__main__':
    unittest.main()
