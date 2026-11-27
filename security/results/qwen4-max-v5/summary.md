# AISecurity evaluation summary

- Questions: 263 | correct: 206 | accuracy: 0.7833 (95% CI 0.7296–0.8288)
- Valid outputs: 258 | invalid/error: 5 | context exceeded: 0 | Brier: 0.3743 | NLL: 4.2383 | ECE: 0.1944

## By source
| source | n | accuracy | 95% CI | invalid |
| --- | --- | --- | --- | --- |
| HarnessJevBench | 190 | 0.7211 | 0.6534–0.78 | 5 |
| JevBench | 13 | 1.0000 | 0.7719–1.0 | 0 |
| self-extended | 60 | 0.9333 | 0.8407–0.9738 | 0 |

## By category
| category | n | accuracy | invalid | Brier |
| --- | --- | --- | --- | --- |
| access_control | 3 | 1.0000 | 0 | 0.0000 |
| action_risk_gate | 8 | 1.0000 | 0 | 0.0000 |
| action_safety | 21 | 0.8571 | 2 | 0.1054 |
| ambiguity_safety | 8 | 1.0000 | 0 | 0.0006 |
| audit_integrity | 13 | 0.5385 | 2 | 0.6887 |
| authorization | 14 | 0.9286 | 0 | 0.0721 |
| context_integrity | 10 | 0.7000 | 0 | 0.5784 |
| data_access | 1 | 1.0000 | 0 | 0.0000 |
| data_egress | 8 | 1.0000 | 0 | 0.0000 |
| data_persistence | 8 | 1.0000 | 0 | 0.0000 |
| destructive_command | 60 | 0.9333 | 0 | 0.1344 |
| input_validation | 14 | 0.1429 | 0 | 1.6157 |
| privacy_compliance | 2 | 1.0000 | 0 | 0.0000 |
| privacy_disclosure | 11 | 0.6364 | 0 | 0.7273 |
| privilege_scoping | 23 | 0.5217 | 0 | 0.9450 |
| prompt_injection | 14 | 1.0000 | 0 | 0.0000 |
| retry_safety | 9 | 0.8889 | 0 | 0.2222 |
| security_operations | 1 | 1.0000 | 0 | 0.0038 |
| state_integrity | 17 | 0.4706 | 1 | 0.7360 |
| ui_action_safety | 8 | 0.7500 | 0 | 0.5000 |
| user_consent | 10 | 0.9000 | 0 | 0.2005 |

## By question type
| type | n | accuracy | Brier | NLL |
| --- | --- | --- | --- | --- |
| choice | 191 | 0.7330 | 0.4869 | 4.9868 |
| noul | 64 | 0.9062 | 0.0938 | 2.5925 |
| score | 8 | 1.0000 | 0.0000 | 0.0000 |

## Self-extended by language
| language | n | accuracy | 95% CI |
| --- | --- | --- | --- |
| en | 24 | 0.9583 | 0.7976–0.9926 |
| zh | 36 | 0.9167 | 0.7817–0.9713 |

## Self-extended by difficulty
| difficulty | n | accuracy | 95% CI |
| --- | --- | --- | --- |
| 4 | 36 | 0.9444 | 0.8186–0.9846 |
| 5 | 24 | 0.9167 | 0.7415–0.9768 |

## Calibration bins
| confidence bin | n | accuracy | mean confidence |
| --- | --- | --- | --- |
| 0.8-0.9 | 3 | 1.0 | 0.85 |
| 0.9-1.0 | 255 | 0.7961 | 0.991 |

## Destructive-command gate
| n | expected allow/deny | predicted allow/deny | false allow | false deny | false-allow rate |
| --- | --- | --- | --- | --- | --- |
| 60 | 30/30 | 26/34 | 0 | 4 | 0.0000 |

## Risk-coverage (overall)
| threshold | coverage | accuracy |
| --- | --- | --- |
| 0.5 | 1.0 | 0.7984 |
| 0.6 | 1.0 | 0.7984 |
| 0.7 | 1.0 | 0.7984 |
| 0.8 | 1.0 | 0.7984 |
| 0.9 | 0.9884 | 0.7961 |
| 0.95 | 0.9651 | 0.7992 |
| 0.99 | 0.814 | 0.8095 |

## Risk-coverage (destructive commands)
| threshold | coverage | accuracy | false-allow rate |
| --- | --- | --- | --- |
| 0.5 | 1.0 | 0.9333 | — |
| 0.6 | 1.0 | 0.9333 | — |
| 0.7 | 1.0 | 0.9333 | — |
| 0.8 | 1.0 | 0.9333 | — |
| 0.9 | 1.0 | 0.9333 | — |
| 0.95 | 1.0 | 0.9333 | — |
| 0.99 | 0.7667 | 0.913 | — |

## Baseline comparison
| matched | fixed | regressed | unchanged |
| --- | --- | --- | --- |
| 263 | 83 | 25 | 155 |

Top 40 failures: `failures.md`.
