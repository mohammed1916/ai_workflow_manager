"""User-selected workload limits; call batch sizes are separate from total work."""
from .core import RelayError


def count(value, default, label):
    if value is None: return default
    if value == 'all': return None
    if isinstance(value,bool) or not isinstance(value,int) or value < 1:
        raise RelayError('INVALID_LIMIT', label+' must be a positive whole number or all.')
    return value


def take(items, value, default, label):
    maximum=count(value,default,label)
    return items if maximum is None else items[:maximum]
