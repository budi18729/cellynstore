def hitung_fee(nominal):
    if nominal < 1000:
        return None
    elif nominal <= 9000:
        return 1500
    elif nominal <= 49000:
        return 2500
    elif nominal <= 99000:
        return 4500
    elif nominal <= 199000:
        return 6500
    elif nominal <= 499000:
        return 10000
    elif nominal <= 1000000:
        return 15000
    else:
        return 20000


def format_nominal(nominal):
    return f"Rp {nominal:,}".replace(",", ".")
