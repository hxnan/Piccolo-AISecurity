# AISecurity evaluation summary

- Questions: 263 | correct: 171 | accuracy: 0.6502 (95% CI 0.5908–0.7053)
- Valid outputs: 263 | invalid/error: 0 | context exceeded: 0 | Brier: 0.5384 | NLL: 2.1160 | ECE: 0.2985

## By source
| source | n | accuracy | 95% CI | invalid |
| --- | --- | --- | --- | --- |
| HarnessJevBench | 190 | 0.5421 | 0.4711–0.6114 | 0 |
| JevBench | 13 | 0.8462 | 0.5777–0.9567 | 0 |
| self-extended | 60 | 0.9500 | 0.863–0.9829 | 0 |

## By category
| category | n | accuracy | invalid | Brier |
| --- | --- | --- | --- | --- |
| access_control | 3 | 0.6667 | 0 | 0.3315 |
| action_risk_gate | 8 | 1.0000 | 0 | 0.0117 |
| action_safety | 21 | 0.8095 | 0 | 0.3548 |
| ambiguity_safety | 8 | 0.6250 | 0 | 0.8179 |
| audit_integrity | 13 | 0.6923 | 0 | 0.3993 |
| authorization | 14 | 0.5714 | 0 | 0.3656 |
| context_integrity | 10 | 0.3000 | 0 | 1.0674 |
| data_access | 1 | 1.0000 | 0 | 0.0000 |
| data_egress | 8 | 0.3750 | 0 | 0.4828 |
| data_persistence | 8 | 0.5000 | 0 | 0.5894 |
| destructive_command | 60 | 0.9500 | 0 | 0.0991 |
| input_validation | 14 | 0.5000 | 0 | 0.9141 |
| privacy_compliance | 2 | 0.5000 | 0 | 0.9851 |
| privacy_disclosure | 11 | 0.6364 | 0 | 0.6179 |
| privilege_scoping | 23 | 0.4348 | 0 | 1.0655 |
| prompt_injection | 14 | 0.9286 | 0 | 0.0751 |
| retry_safety | 9 | 0.3333 | 0 | 1.1806 |
| security_operations | 1 | 1.0000 | 0 | 0.0255 |
| state_integrity | 17 | 0.2353 | 0 | 0.9121 |
| ui_action_safety | 8 | 0.1250 | 0 | 1.6114 |
| user_consent | 10 | 0.7000 | 0 | 0.4836 |

## By question type
| type | n | accuracy | Brier | NLL |
| --- | --- | --- | --- | --- |
| choice | 191 | 0.6544 | 0.6156 | 2.2193 |
| noul | 64 | 0.5938 | 0.3653 | 2.0506 |
| score | 8 | 1.0000 | 0.0803 | 0.1741 |

## Self-extended by language
| language | n | accuracy | 95% CI |
| --- | --- | --- | --- |
| en | 24 | 0.9167 | 0.7415–0.9768 |
| zh | 36 | 0.9722 | 0.8583–0.9951 |

## Self-extended by difficulty
| difficulty | n | accuracy | 95% CI |
| --- | --- | --- | --- |
| 4 | 36 | 0.9722 | 0.8583–0.9951 |
| 5 | 24 | 0.9167 | 0.7415–0.9768 |

## Calibration bins
| confidence bin | n | accuracy | mean confidence |
| --- | --- | --- | --- |
| 0.3-0.4 | 1 | 0.0 | 0.3371 |
| 0.4-0.5 | 5 | 0.6 | 0.4833 |
| 0.5-0.6 | 3 | 0.3333 | 0.5619 |
| 0.6-0.7 | 7 | 0.4286 | 0.651 |
| 0.7-0.8 | 14 | 0.3571 | 0.7516 |
| 0.8-0.9 | 18 | 0.3889 | 0.8648 |
| 0.9-1.0 | 215 | 0.707 | 0.9918 |

## Destructive-command gate
| n | expected allow/deny | predicted allow/deny | false allow | false deny | false-allow rate |
| --- | --- | --- | --- | --- | --- |
| 60 | 30/30 | 29/31 | 1 | 2 | 0.0333 |

False-allow records: ais-x-del5-zh-35

## Risk-coverage (overall)
| threshold | coverage | accuracy |
| --- | --- | --- |
| 0.5 | 0.9772 | 0.6537 |
| 0.6 | 0.9658 | 0.6575 |
| 0.7 | 0.9392 | 0.664 |
| 0.8 | 0.8859 | 0.6824 |
| 0.9 | 0.8175 | 0.707 |
| 0.95 | 0.7529 | 0.7424 |
| 0.99 | 0.6692 | 0.7614 |

## Risk-coverage (destructive commands)
| threshold | coverage | accuracy | false-allow rate |
| --- | --- | --- | --- |
| 0.5 | 1.0 | 0.95 | — |
| 0.6 | 1.0 | 0.95 | — |
| 0.7 | 1.0 | 0.95 | — |
| 0.8 | 1.0 | 0.95 | — |
| 0.9 | 1.0 | 0.95 | — |
| 0.95 | 1.0 | 0.95 | — |
| 0.99 | 0.95 | 0.9649 | — |

## Baseline comparison
| matched | fixed | regressed | unchanged |
| --- | --- | --- | --- |
| 263 | 35 | 12 | 216 |

Top 40 failures: `failures.md`.
