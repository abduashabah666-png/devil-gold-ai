def evaluate_market_conditions(
    data_available=True,
    spread_available=False,
    data_is_fresh=False,
    demo_mode=True
):
    """
    Safety checks for the Devil Gold AI analysis system.
    This module does not place or close trades.
    """

    checks = {
        "data_available": data_available,
        "spread_available": spread_available,
        "data_is_fresh": data_is_fresh,
        "demo_mode": demo_mode,
    }

    blocked_reasons = []

    if not data_available:
        blocked_reasons.append("Market data unavailable")

    if not spread_available:
        blocked_reasons.append("Spread has not been verified")

    if not data_is_fresh:
        blocked_reasons.append("Data freshness has not been verified")

    if not demo_mode:
        blocked_reasons.append(
            "This project is restricted to testing and simulation"
        )

    return {
        "approved_for_simulation": len(blocked_reasons) == 0,
        "checks": checks,
        "blocked_reasons": blocked_reasons,
        "live_trading_enabled": False,
    }
