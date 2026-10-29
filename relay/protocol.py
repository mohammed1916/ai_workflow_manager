"""Question-specific comparison contracts. Never infer missing result values from a contract."""
import re

from .semantics import PLAN


def contract(raw):
    from .semantics import contract as build_contract
    return build_contract(raw)


def protocol_of(metric):
    value = metric.get('protocol',{})
    return value if isinstance(value,dict) else {}

def factor_keys(metric):
    return [f['key'] for f in protocol_of(metric).get('factors',[]) if isinstance(f,dict) and re.fullmatch(r'factor_[a-z0-9_]{1,40}',str(f.get('key','')))]

def forecasting(metric):
    return protocol_of(metric).get('task','forecasting') == 'forecasting'
