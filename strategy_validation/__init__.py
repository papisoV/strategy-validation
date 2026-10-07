"""strategy_validation - is the screen selecting, or is it just the calendar?

The whole product is one question and one number: given the names the client's
screen picked each day, and every name it COULD have picked that same day,
where does the observed result sit among same-day same-size random draws?

Design rules carried over from insider-radar (each one was paid for):
  * a control must be SAME-DAY. Comparing against "the market" credits the
    screen for the day's own move; that is how a screen looks good in a bull
    week and is worthless in a flat one.
  * wrong input must RAISE. The insider backtest once returned purchases=0
    with no error because two functions shared a name and returned different
    shapes, and the render looked like a normal quiet day. Silence is not
    acceptable here.
  * every printed number must be recomputable from the inputs. Nothing is
    recalled, nothing is rounded for effect.
"""
__all__ = ["load", "control", "cost", "report"]
