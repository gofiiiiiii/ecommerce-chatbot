import re
from textblob import TextBlob

def extract_price(text):
    nums = re.findall(r'\d+', text)
    return int(nums[0]) if nums else None

def intent(text):
    text = text.lower()
    if any(x in text for x in ["hi", "hello"]):
        return "greet"
    if any(x in text for x in ["deal", "ok", "buy"]):
        return "accept"
    if any(x in text for x in ["expensive", "reduce", "costly"]):
        return "reject"
    if extract_price(text):
        return "offer"
    return "unknown"

def sentiment(text):
    p = TextBlob(text).sentiment.polarity
    return "negative" if p < -0.2 else "positive"
