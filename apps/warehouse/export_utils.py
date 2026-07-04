"""Shared export utilities for warehouse and accounts apps."""


def format_export_datetime(dt):
    """Format a datetime for CSV export. Returns empty string if None."""
    if dt is None:
        return ''
    return dt.strftime('%Y-%m-%d %H:%M')
