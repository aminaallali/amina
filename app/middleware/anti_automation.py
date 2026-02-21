"""Reusable anti-automation checks for interaction telemetry."""


def evaluate_interaction(
    interaction_data: dict,
    min_duration_ms: float,
    min_movement_events: int,
    require_direction_change: bool,
) -> dict:
    issues = []

    duration_ms = interaction_data.get("duration_ms", 0)
    if duration_ms < min_duration_ms:
        issues.append("مدة تفاعل قصيرة جداً")

    movement_count = interaction_data.get("movement_count", 0)
    if movement_count < min_movement_events:
        issues.append("حركات قليلة")

    direction_changes = interaction_data.get("direction_changes", 0)
    if require_direction_change and direction_changes < 1:
        issues.append("لم يتم تغيير اتجاه الدوران")

    timestamps = interaction_data.get("timestamps", [])
    if len(timestamps) >= 3:
        intervals = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
        mean_interval = sum(intervals) / len(intervals)
        variance = sum((value - mean_interval) ** 2 for value in intervals) / len(intervals)
        std_dev = variance ** 0.5
        if std_dev < 5:
            issues.append("توقيت منتظم بشكل مشبوه")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "metrics": {
            "duration_ms": duration_ms,
            "movement_count": movement_count,
            "direction_changes": direction_changes,
        },
    }
