# AISecurity evaluation summary

- Questions: 233 | correct: 148 | accuracy: 0.6352 (95% CI 0.5717–0.6943)
- Valid outputs: 233 | invalid/error: 0 | context exceeded: 0 | Brier: 0.5483 | NLL: 1.8334 | ECE: 0.2857

## By source
| source | n | accuracy | 95% CI | invalid |
| --- | --- | --- | --- | --- |
| HarnessJevBench | 190 | 0.5632 | 0.4921–0.6317 | 0 |
| JevBench | 13 | 0.8462 | 0.5777–0.9567 | 0 |
| self-extended | 30 | 1.0000 | 0.8865–1.0 | 0 |

## By category
| category | n | accuracy | invalid | Brier |
| --- | --- | --- | --- | --- |
| access_control | 3 | 0.6667 | 0 | 0.3326 |
| action_risk_gate | 8 | 1.0000 | 0 | 0.0297 |
| action_safety | 21 | 0.7143 | 0 | 0.4263 |
| ambiguity_safety | 8 | 0.5000 | 0 | 0.9781 |
| audit_integrity | 13 | 0.7692 | 0 | 0.3088 |
| authorization | 14 | 0.7143 | 0 | 0.2198 |
| context_integrity | 10 | 0.5000 | 0 | 0.8425 |
| data_access | 1 | 1.0000 | 0 | 0.0002 |
| data_egress | 8 | 0.7500 | 0 | 0.2345 |
| data_persistence | 8 | 0.5000 | 0 | 0.5639 |
| destructive_command | 30 | 1.0000 | 0 | 0.0059 |
| input_validation | 14 | 0.5714 | 0 | 0.7937 |
| privacy_compliance | 2 | 0.5000 | 0 | 0.8134 |
| privacy_disclosure | 11 | 0.5455 | 0 | 0.7074 |
| privilege_scoping | 23 | 0.4348 | 0 | 1.0479 |
| prompt_injection | 14 | 0.8571 | 0 | 0.1150 |
| retry_safety | 9 | 0.3333 | 0 | 1.1383 |
| security_operations | 1 | 1.0000 | 0 | 0.1454 |
| state_integrity | 17 | 0.2353 | 0 | 0.8754 |
| ui_action_safety | 8 | 0.1250 | 0 | 1.4995 |
| user_consent | 10 | 0.7000 | 0 | 0.4167 |

## By question type
| type | n | accuracy | Brier | NLL |
| --- | --- | --- | --- | --- |
| choice | 131 | 0.5267 | 0.8176 | 2.5947 |
| noul | 94 | 0.7660 | 0.2020 | 0.8928 |
| score | 8 | 0.8750 | 0.2081 | 0.4204 |

## Self-extended by language
| language | n | accuracy | 95% CI |
| --- | --- | --- | --- |
| en | 15 | 1.0000 | 0.7961–1.0 |
| zh | 15 | 1.0000 | 0.7961–1.0 |

## Self-extended by difficulty
| difficulty | n | accuracy | 95% CI |
| --- | --- | --- | --- |
| 1 | 2 | 1.0000 | 0.3424–1.0 |
| 2 | 2 | 1.0000 | 0.3424–1.0 |
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
| 0.2-0.3 | 1 | 1.0 | 0.2015 |
| 0.4-0.5 | 4 | 0.5 | 0.4736 |
| 0.5-0.6 | 11 | 0.5455 | 0.5523 |
| 0.6-0.7 | 8 | 0.375 | 0.6553 |
| 0.7-0.8 | 21 | 0.3333 | 0.7529 |
| 0.8-0.9 | 20 | 0.25 | 0.8569 |
| 0.9-1.0 | 168 | 0.7381 | 0.9905 |

## Destructive-command gate
| n | expected allow/deny | predicted allow/deny | false allow | false deny | false-allow rate |
| --- | --- | --- | --- | --- | --- |
| 30 | 14/16 | 14/16 | 0 | 0 | 0.0000 |

## Risk-coverage (overall)
| threshold | coverage | accuracy |
| --- | --- | --- |
| 0.5 | 0.9785 | 0.636 |
| 0.6 | 0.9313 | 0.6406 |
| 0.7 | 0.897 | 0.6507 |
| 0.8 | 0.8069 | 0.6862 |
| 0.9 | 0.721 | 0.7381 |
| 0.95 | 0.6824 | 0.7484 |
| 0.99 | 0.5622 | 0.7863 |

## Risk-coverage (destructive commands)
| threshold | coverage | accuracy | false-allow rate |
| --- | --- | --- | --- |
| 0.5 | 1.0 | 1.0 | 0.0000 |
| 0.6 | 1.0 | 1.0 | 0.0000 |
| 0.7 | 0.9667 | 1.0 | 0.0000 |
| 0.8 | 0.9333 | 1.0 | 0.0000 |
| 0.9 | 0.9333 | 1.0 | 0.0000 |
| 0.95 | 0.9333 | 1.0 | 0.0000 |
| 0.99 | 0.8 | 1.0 | 0.0000 |

## Baseline comparison
| matched | fixed | regressed | unchanged |
| --- | --- | --- | --- |
| 233 | 11 | 5 | 217 |

Top 40 failures: `failures.md`.
