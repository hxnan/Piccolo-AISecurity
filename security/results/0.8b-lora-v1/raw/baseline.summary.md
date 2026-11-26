# AISecurity evaluation summary

- Questions: 233 | correct: 142 | accuracy: 0.6094 (95% CI 0.5455–0.6698)
- Valid outputs: 233 | invalid/error: 0 | context exceeded: 0 | Brier: 0.5060 | NLL: 1.2888 | ECE: 0.2313

## By source
| source | n | accuracy | 95% CI | invalid |
| --- | --- | --- | --- | --- |
| HarnessJevBench | 190 | 0.5474 | 0.4764–0.6165 | 0 |
| JevBench | 13 | 0.6923 | 0.4237–0.8732 | 0 |
| self-extended | 30 | 0.9667 | 0.8333–0.9941 | 0 |

## By category
| category | n | accuracy | invalid | Brier |
| --- | --- | --- | --- | --- |
| access_control | 3 | 0.6667 | 0 | 0.3508 |
| action_risk_gate | 8 | 1.0000 | 0 | 0.0360 |
| action_safety | 21 | 0.6667 | 0 | 0.4497 |
| ambiguity_safety | 8 | 0.3750 | 0 | 0.9576 |
| audit_integrity | 13 | 0.7692 | 0 | 0.3345 |
| authorization | 14 | 0.7143 | 0 | 0.1776 |
| context_integrity | 10 | 0.4000 | 0 | 0.8290 |
| data_access | 1 | 1.0000 | 0 | 0.0291 |
| data_egress | 8 | 0.7500 | 0 | 0.2041 |
| data_persistence | 8 | 0.5000 | 0 | 0.4172 |
| destructive_command | 30 | 0.9667 | 0 | 0.0217 |
| input_validation | 14 | 0.5000 | 0 | 0.6858 |
| privacy_compliance | 2 | 0.5000 | 0 | 0.8477 |
| privacy_disclosure | 11 | 0.4545 | 0 | 0.6701 |
| privilege_scoping | 23 | 0.4348 | 0 | 0.9660 |
| prompt_injection | 14 | 0.8571 | 0 | 0.1049 |
| retry_safety | 9 | 0.3333 | 0 | 1.1141 |
| security_operations | 1 | 0.0000 | 0 | 1.0654 |
| state_integrity | 17 | 0.2353 | 0 | 0.7053 |
| ui_action_safety | 8 | 0.2500 | 0 | 1.1477 |
| user_consent | 10 | 0.7000 | 0 | 0.4054 |

## By question type
| type | n | accuracy | Brier | NLL |
| --- | --- | --- | --- | --- |
| choice | 131 | 0.4809 | 0.7705 | 1.8599 |
| noul | 94 | 0.7660 | 0.1649 | 0.5707 |
| score | 8 | 0.8750 | 0.1827 | 0.3737 |

## Self-extended by language
| language | n | accuracy | 95% CI |
| --- | --- | --- | --- |
| en | 15 | 0.9333 | 0.7018–0.9881 |
| zh | 15 | 1.0000 | 0.7961–1.0 |

## Self-extended by difficulty
| difficulty | n | accuracy | 95% CI |
| --- | --- | --- | --- |
| 1 | 2 | 1.0000 | 0.3424–1.0 |
| 2 | 2 | 0.5000 | 0.0945–0.9055 |
| 3 | 2 | 1.0000 | 0.3424–1.0 |
| 4 | 2 | 1.0000 | 0.3424–1.0 |
| 5 | 2 | 1.0000 | 0.3424–1.0 |
| 6 | 2 | 1.0000 | 0.3424–1.0 |
| 7 | 2 | 1.0000 | 0.3424–1.0 |
| 8 | 2 | 1.0000 | 0.3424–1.0 |
| 9 | 2 | 1.0000 | 0.3424–1.0 |
| 10 | 2 | 1.0000 | 0.3424–1.0 |
| 11 | 2 | 1.0000 | 0.3424–1.0 |
| 12 | 2 | 1.0000 | 0.3424–1.0 |
| 13 | 2 | 1.0000 | 0.3424–1.0 |
| 14 | 2 | 1.0000 | 0.3424–1.0 |
| 15 | 2 | 1.0000 | 0.3424–1.0 |

## Calibration bins
| confidence bin | n | accuracy | mean confidence |
| --- | --- | --- | --- |
| 0.2-0.3 | 1 | 1.0 | 0.202 |
| 0.3-0.4 | 1 | 0.0 | 0.3073 |
| 0.4-0.5 | 8 | 0.0 | 0.4506 |
| 0.5-0.6 | 28 | 0.3929 | 0.5517 |
| 0.6-0.7 | 23 | 0.4348 | 0.6431 |
| 0.7-0.8 | 19 | 0.4211 | 0.7513 |
| 0.8-0.9 | 29 | 0.5517 | 0.8557 |
| 0.9-1.0 | 124 | 0.7742 | 0.9747 |

## Destructive-command gate
| n | expected allow/deny | predicted allow/deny | false allow | false deny | false-allow rate |
| --- | --- | --- | --- | --- | --- |
| 30 | 14/16 | 15/15 | 1 | 0 | 0.0625 |

False-allow records: ais-x-del-en-01

## Risk-coverage (overall)
| threshold | coverage | accuracy |
| --- | --- | --- |
| 0.5 | 0.9571 | 0.6323 |
| 0.6 | 0.8369 | 0.6667 |
| 0.7 | 0.7382 | 0.6977 |
| 0.8 | 0.6567 | 0.732 |
| 0.9 | 0.5322 | 0.7742 |
| 0.95 | 0.412 | 0.8021 |
| 0.99 | 0.2361 | 0.8182 |

## Risk-coverage (destructive commands)
| threshold | coverage | accuracy | false-allow rate |
| --- | --- | --- | --- |
| 0.5 | 1.0 | 0.9667 | 0.0625 |
| 0.6 | 0.9333 | 1.0 | 0.0000 |
| 0.7 | 0.9333 | 1.0 | 0.0000 |
| 0.8 | 0.9333 | 1.0 | 0.0000 |
| 0.9 | 0.7333 | 1.0 | 0.0000 |
| 0.95 | 0.6667 | 1.0 | 0.0000 |
| 0.99 | 0.3 | 1.0 | 0.0000 |

Top 40 failures: `failures.md`.
