"""Agent personality helpers."""


def explain_decision(ticker, decision, rationale, confidence):
    return f"I recommend a {decision.upper()} on {ticker}. Confidence: {confidence:.2f}. Rationale: {rationale}"
