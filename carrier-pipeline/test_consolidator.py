"""
basic tests for the normalizer. mostly wrote these after AZIM broke twice
and i got tired of manually verifying the same edge cases.
"""
import pytest
from datetime import date


# mock what the consolidator produces after normalization
def normalize_carrier_a(raw_row):
    """pipe-delimited, dates as MM/DD/YYYY"""
    from datetime import datetime
    return {
        'carrier_code': 'CARRIER_A',
        'load_id': raw_row.get('LOAD_NUMBER', '').strip(),
        'trailer_id': raw_row.get('TRAILER', '').strip(),
        'origin_facility': raw_row.get('ORIGIN', '').strip()[:4].upper() or None,
        'destination_facility': raw_row.get('DEST', '').strip()[:4].upper() or None,
        'pickup_date': datetime.strptime(raw_row['PU_DATE'], '%m/%d/%Y').date() if raw_row.get('PU_DATE') else None,
        'current_stage': 'IN_TRANSIT' if raw_row.get('NEXT_VRID') else 'AT_DESTINATION',
    }


class TestCarrierANormalization:

    def test_basic_row(self):
        row = {'LOAD_NUMBER': 'LD-99012', 'TRAILER': 'TRL-445', 'ORIGIN': 'CHI1',
               'DEST': 'PHX2', 'PU_DATE': '06/15/2026', 'NEXT_VRID': ''}
        result = normalize_carrier_a(row)
        assert result['load_id'] == 'LD-99012'
        assert result['destination_facility'] == 'PHX2'
        assert result['current_stage'] == 'AT_DESTINATION'

    def test_mid_leg_forces_in_transit(self):
        """if NEXT_VRID is populated, trailer is mid-leg — NOT at destination.
        this was the RRD-011 bug. 760+ loads/day were wrong before this fix."""
        row = {'LOAD_NUMBER': 'LD-44001', 'TRAILER': 'TRL-102', 'ORIGIN': 'DAL3',
               'DEST': 'PHX2', 'PU_DATE': '06/18/2026', 'NEXT_VRID': 'VR-8812'}
        result = normalize_carrier_a(row)
        assert result['current_stage'] == 'IN_TRANSIT'

    def test_blank_destination_is_none(self):
        """structural blank — mid-leg loads dont have a dest. this is expected,
        not a bug. threshold is 100/day before we alert."""
        row = {'LOAD_NUMBER': 'LD-55002', 'TRAILER': 'TRL-200', 'ORIGIN': 'CHI1',
               'DEST': '', 'PU_DATE': '06/20/2026', 'NEXT_VRID': 'VR-1234'}
        result = normalize_carrier_a(row)
        assert result['destination_facility'] is None

    def test_whitespace_handling(self):
        """carriers send trailing spaces constantly. strip before anything else."""
        row = {'LOAD_NUMBER': '  LD-77003  ', 'TRAILER': 'TRL-300 ', 'ORIGIN': ' ATL1  ',
               'DEST': 'MEM2   ', 'PU_DATE': '06/22/2026', 'NEXT_VRID': ''}
        result = normalize_carrier_a(row)
        assert result['load_id'] == 'LD-77003'
        assert result['origin_facility'] == 'ATL1'
        assert result['destination_facility'] == 'MEM2'
