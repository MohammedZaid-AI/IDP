def confidence_score(validation):

    if not validation["valid"]:
        return 0.5

    issue_count = len(validation["issues"])

    score = 1.0 - (issue_count * 0.1)

    return round(max(score, 0.0), 2)