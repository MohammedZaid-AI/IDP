import re

def detect_language(text):

    arabic = len(
        re.findall(
            r'[\u0600-\u06FF]',
            text
        )
    )

    if arabic > 50:
        return "arabic"

    if arabic > 0:
        return "mixed"

    return "english"