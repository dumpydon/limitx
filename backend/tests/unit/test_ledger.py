from limitx.analytics.ledger import AccountLedger


def test_ledger_updates_buyer_and_seller_deterministically():
    ledger = AccountLedger()
    ledger.apply_trade(
        "BTC-USD",
        {
            "taker_account_id": "buyer",
            "maker_account_id": "seller",
            "aggressor_side": "BUY",
            "price_ticks": 100,
            "quantity": 5,
        },
    )
    assert ledger.account("buyer", {"BTC-USD": 105})["BTC-USD"]["position"] == 5
    assert ledger.account("seller", {"BTC-USD": 105})["BTC-USD"]["position"] == -5
