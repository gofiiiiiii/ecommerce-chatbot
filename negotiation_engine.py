def negotiate(user_price, product, round_no):
    offer = product["price"] - (round_no * 500)
    offer = max(offer, product["min_price"])

    if user_price and user_price >= offer:
        return True, user_price

    return False, offer
