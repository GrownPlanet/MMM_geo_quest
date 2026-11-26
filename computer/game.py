def calculate_points_with_difficulty(
    points: list[list[float]], difficulty: str
) -> list[list[float]]:
    if not points:
        return points

    if difficulty == "Easy":
        return points
    if difficulty == "Medium":
        return points[:-1:2] + [points[-1]]
    if difficulty == "Hard":
        return points[:-1:4] + [points[-1]]
    if difficulty == "Expert":
        return [points[-1]]

    print("Warning: unrecognized difficulty level, defaulting to Easy")
    return points
