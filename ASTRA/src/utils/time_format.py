def format_duration(delta):
    """Render a timedelta as a short human string, e.g. '5s', '2m 5s', '1h 3m'."""
    total_seconds = max(0, int(delta.total_seconds()))
    if total_seconds < 60:
        return f"{total_seconds}s"

    minutes, seconds = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"

    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m"

    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"
