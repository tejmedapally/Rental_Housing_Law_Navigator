# Contract: Change cases

**File**: `output/changes.json`  
**Input**: `data_and_code_base/dev/change_tests.json`  
**Template**: `data_and_code_base/submission_templates/changes.json`

## Envelope

```json
{
  "T1": {
    "affected_address_ids": ["A0002"],
    "notes": "Why these addresses are affected."
  },
  "T3": {
    "affected_address_ids": ["A0001"],
    "conflict_flag_address_ids": ["A0001"],
    "notes": "Why these addresses are flagged."
  }
}
```

The file contains T1, T2, T3, T4, and T5. Address ids are a subset of the sample. Each list is sorted by id and has no duplicates.

## Expected sets

Legal city and state come from `output/geocodes.json`.

| Test | `affected_address_ids` | `conflict_flag_address_ids` |
|---|---|---|
| T1 | Every sample address whose `legal_state` is `CA` | Omitted |
| T2 | Every sample address whose `legal_city` is Hoboken or Jersey City. Newark is absent | Omitted |
| T3 | Every sample address whose `legal_state` is `NJ` | The subset whose `legal_city` is Jersey City or Hoboken |
| T4 | Every sample address whose `legal_state` is `MA` | Omitted |
| T5 | Empty array | Omitted |

`notes` for T4 states that both bills are pending and the set is who would be affected if they were enacted. `notes` for T5 states that the ballot question is failed and no rent cap is reported for Boston or Cambridge.

T2's notes name both local bans and state that neither applies in Newark.
