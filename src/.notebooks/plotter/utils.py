from typing import Dict, Union


def vanilla_dirname(comp: Dict[str, Union[int, float]], re: int = 0) -> str:
    return (
        f"I {comp['inserts']} U {comp['updates']} S {comp['range']} Y {comp['selectivity']} "
        f"T {comp['sizeRatio']} rq 0 re {re} E {comp['entrySize']} B {comp['entriesPerPage']}"
    )


def rqdc_dirname(
    comp: Dict[str, Union[int, float]],
    re: int = 0,
    rq_overlapping_count=0,
    rq_overlapping_percent=1,
) -> str:
    if rq_overlapping_count != 0:
        if rq_overlapping_percent != 1:
            return (
                f"I {comp['inserts']} U {comp['updates']} S {comp['range']} Y {comp['selectivity']} "
                f"T {comp['sizeRatio']} rq 1 re {re} E {comp['entrySize']} B {comp['entriesPerPage']} "
                f"lb {comp['lowerBound']} ub {comp['upperBound']} O {rq_overlapping_count} PO {rq_overlapping_percent}"
            )
        else:
            return (
                f"I {comp['inserts']} U {comp['updates']} S {comp['range']} Y {comp['selectivity']} "
                f"T {comp['sizeRatio']} rq 1 re {re} E {comp['entrySize']} B {comp['entriesPerPage']} "
                f"lb {comp['lowerBound']} ub {comp['upperBound']} O {rq_overlapping_count}"
            )

    return (
        f"I {comp['inserts']} U {comp['updates']} S {comp['range']} Y {comp['selectivity']} "
        f"T {comp['sizeRatio']} rq 1 re {re} E {comp['entrySize']} B {comp['entriesPerPage']} "
        f"lb {comp['lowerBound']} ub {comp['upperBound']}"
    )
