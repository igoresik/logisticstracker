def net_profit(sale_price, cost_price, fee_pct, fee_fixed=0.0, shipping_cost=0.0):
    """Return (platform fee, net profit, margin % of sale price)."""
    fee = round(sale_price * fee_pct / 100 + fee_fixed, 2)
    net = round(sale_price - fee - cost_price - shipping_cost, 2)
    margin = round(net / sale_price * 100, 1) if sale_price else 0.0
    return fee, net, margin
