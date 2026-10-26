"""Bounded, deterministic CSV profiling supplied to the planner as evidence."""
import csv, io, math

def profile_csv(content):
    rows=list(csv.reader(io.StringIO(content),strict=True))
    if not rows or len(rows)>5001: raise ValueError('CSV must contain a header and at most 5,000 data rows.')
    header=rows[0]
    if not header or len(set(header))!=len(header) or len(header)>100: raise ValueError('CSV needs unique headers and at most 100 columns.')
    if any(len(r)!=len(header) for r in rows[1:]):raise ValueError('CSV rows have inconsistent column counts.')
    result={'rows':len(rows)-1,'columns':{},'duplicate_rows':len(rows[1:])-len(set(tuple(r) for r in rows[1:]))}
    for i,name in enumerate(header):
        vals=[r[i] for r in rows[1:]];present=[v for v in vals if v.strip()]
        entry={'missing':len(vals)-len(present),'distinct':len(set(present))}
        try:
            nums=[float(v) for v in present]
            if nums and all(math.isfinite(v) for v in nums):entry.update(min=min(nums),max=max(nums),sum=math.fsum(nums),mean=math.fsum(nums)/len(nums))
        except (ValueError,OverflowError):pass
        result['columns'][name]=entry
    return result
