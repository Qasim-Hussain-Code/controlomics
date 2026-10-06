"""Local numeric input checks without retaining identifiers or raw measurements."""

import hashlib
from typing import Annotated, Literal

from pydantic import Field, model_validator

from controlomics.schemas import Record, Sha256, Text
from controlomics.statistics import read_numeric_bytes, read_paired_bytes

MAX_INPUT = 2 * 1024 * 1024
Adapter = Literal['INDEPENDENT_REFERENCE', 'PAIRED_DIFFERENCE']


class NumericInputSummary(Record):
    adapter: Adapter
    input_sha256: Sha256
    input_bytes: Annotated[int, Field(ge=1, le=MAX_INPUT)]
    rows: Annotated[int, Field(ge=4, le=2000)]
    group_zero_units: Annotated[int, Field(ge=0, le=2000)]
    group_one_units: Annotated[int, Field(ge=0, le=2000)]
    complete_pairs: Annotated[int, Field(ge=2, le=1000)] | None
    utf8_bom: bool
    limitations: tuple[Text, ...]

    @model_validator(mode='after')
    def consistent_shape(self):
        if self.adapter == 'INDEPENDENT_REFERENCE':
            if self.complete_pairs is not None or min(self.group_zero_units, self.group_one_units) < 2 or self.rows != self.group_zero_units + self.group_one_units:
                raise ValueError('independent input summary is inconsistent')
        elif self.complete_pairs is None or self.group_zero_units or self.group_one_units or self.rows != 2 * self.complete_pairs:
            raise ValueError('paired input summary is inconsistent')
        return self


def inspect_numeric_input(raw, adapter='INDEPENDENT_REFERENCE'):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_INPUT:
        raise ValueError('a bounded nonempty byte input is required')
    if adapter == 'INDEPENDENT_REFERENCE':
        values, labels = read_numeric_bytes(raw)
        rows, zero, one, pairs = len(values), labels.count(0), labels.count(1), None
    elif adapter == 'PAIRED_DIFFERENCE':
        differences = read_paired_bytes(raw)
        rows, zero, one, pairs = 2 * len(differences), 0, 0, len(differences)
    else:
        raise ValueError('unknown numeric input adapter')
    return NumericInputSummary(adapter=adapter, input_sha256=hashlib.sha256(raw).hexdigest(),
        input_bytes=len(raw), rows=rows, group_zero_units=zero, group_one_units=one,
        complete_pairs=pairs, utf8_bom=raw.startswith(b'\xef\xbb\xbf'), limitations=(
            'Input shape and finite values do not establish independent sampling units, exchangeability, or biological validity.',
            'No control was executed and no scientific outcome was assigned. Raw measurements and identifiers are omitted.',
            'The hash identifies these exact input bytes; it is not anonymization or authenticated provenance.',
        ))
