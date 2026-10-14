from decimal import ROUND_HALF_UP, Decimal


def to_cents(euros):
    """Euros as typed (float or text) to whole cents, rounding half up."""
    return int((Decimal(str(euros)) * 100).quantize(Decimal(1), ROUND_HALF_UP))


def to_bps(percent):
    """A fee percentage to basis points: 12.8 -> 1280."""
    return to_cents(percent)


def net_profit(sale_cents, cost_cents, fee_bps, fee_fixed_cents=0, shipping_cents=0):
    """All amounts in cents. Return (platform fee, net profit, margin % of the sale price)."""
    fee = (sale_cents * fee_bps + 5_000) // 10_000 + fee_fixed_cents  # rounded half up to the cent
    net = sale_cents - fee - cost_cents - shipping_cents
    margin = Decimal(net * 100) / sale_cents if sale_cents else Decimal(0)
    return fee, net, margin.quantize(Decimal("0.1"), ROUND_HALF_UP)
