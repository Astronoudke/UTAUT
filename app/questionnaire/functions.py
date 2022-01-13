# Het omdraaien van de score in het geval dat "reversed_score" geldt voor de vraag.
def reverse_value(value, scale):
    new_value = scale + 1 - int(value)
    return str(new_value)
