# AISecurity evaluation summary

- Questions: 263 | correct: 188 | accuracy: 0.7148 (95% CI 0.6575–0.766)
- Valid outputs: 263 | invalid/error: 0 | context exceeded: 0 | Brier: 0.5194 | NLL: 5.9260 | ECE: 0.2576

## By source
| source | n | accuracy | 95% CI | invalid |
| --- | --- | --- | --- | --- |
| HarnessJevBench | 190 | 0.6526 | 0.5825–0.7167 | 0 |
| JevBench | 13 | 1.0000 | 0.7719–1.0 | 0 |
| self-extended | 60 | 0.8500 | 0.7389–0.919 | 0 |

## By category
| category | n | accuracy | invalid | Brier |
| --- | --- | --- | --- | --- |
| access_control | 3 | 1.0000 | 0 | 0.0000 |
| action_risk_gate | 8 | 1.0000 | 0 | 0.0000 |
| action_safety | 21 | 0.9524 | 0 | 0.0847 |
| ambiguity_safety | 8 | 0.8750 | 0 | 0.2611 |
| audit_integrity | 13 | 0.4615 | 0 | 0.9046 |
| authorization | 14 | 0.9286 | 0 | 0.0714 |
| context_integrity | 10 | 0.5000 | 0 | 0.9708 |
| data_access | 1 | 1.0000 | 0 | 0.0000 |
| data_egress | 8 | 0.7500 | 0 | 0.2500 |
| data_persistence | 8 | 0.8750 | 0 | 0.2500 |
| destructive_command | 60 | 0.8500 | 0 | 0.2994 |
| input_validation | 14 | 0.1429 | 0 | 1.5071 |
| privacy_compliance | 2 | 1.0000 | 0 | 0.0000 |
| privacy_disclosure | 11 | 0.5455 | 0 | 0.9091 |
| privilege_scoping | 23 | 0.6087 | 0 | 0.7812 |
| prompt_injection | 14 | 1.0000 | 0 | 0.0000 |
| retry_safety | 9 | 0.5556 | 0 | 0.8467 |
| security_operations | 1 | 1.0000 | 0 | 0.0000 |
| state_integrity | 17 | 0.4706 | 0 | 0.8235 |
| ui_action_safety | 8 | 0.0000 | 0 | 2.0000 |
| user_consent | 10 | 0.9000 | 0 | 0.1620 |

## By question type
| type | n | accuracy | Brier | NLL |
| --- | --- | --- | --- | --- |
| choice | 191 | 0.6544 | 0.6629 | 6.8578 |
| noul | 64 | 0.8750 | 0.1250 | 3.4539 |
| score | 8 | 0.8750 | 0.2500 | 3.4539 |

## Self-extended by language
| language | n | accuracy | 95% CI |
| --- | --- | --- | --- |
| en | 24 | 0.7917 | 0.5953–0.9076 |
| zh | 36 | 0.8889 | 0.7469–0.9559 |

## Self-extended by difficulty
| difficulty | n | accuracy | 95% CI |
| --- | --- | --- | --- |
| 4 | 36 | 0.8889 | 0.7469–0.9559 |
| 5 | 24 | 0.7917 | 0.5953–0.9076 |

## Calibration bins
| confidence bin | n | accuracy | mean confidence |
| --- | --- | --- | --- |
| 0.7-0.8 | 1 | 1.0 | 0.75 |
| 0.8-0.9 | 3 | 1.0 | 0.85 |
| 0.9-1.0 | 259 | 0.7104 | 0.9693 |

## Destructive-command gate
| n | expected allow/deny | predicted allow/deny | false allow | false deny | false-allow rate |
| --- | --- | --- | --- | --- | --- |
| 60 | 30/30 | 21/39 | 0 | 9 | 0.0000 |

## Risk-coverage (overall)
| threshold | coverage | accuracy |
| --- | --- | --- |
| 0.5 | 1.0 | 0.7148 |
| 0.6 | 1.0 | 0.7148 |
| 0.7 | 1.0 | 0.7148 |
| 0.8 | 0.9962 | 0.7137 |
| 0.9 | 0.9848 | 0.7104 |
| 0.95 | 0.7224 | 0.7053 |
| 0.99 | 0.6426 | 0.6923 |

## Risk-coverage (destructive commands)
| threshold | coverage | accuracy | false-allow rate |
| --- | --- | --- | --- |
| 0.5 | 1.0 | 0.85 | — |
| 0.6 | 1.0 | 0.85 | — |
| 0.7 | 1.0 | 0.85 | — |
| 0.8 | 1.0 | 0.85 | — |
| 0.9 | 1.0 | 0.85 | — |
| 0.95 | 0.2167 | 0.6923 | — |
| 0.99 | 0.1167 | 0.4286 | — |

## Baseline comparison
| matched | fixed | regressed | unchanged |
| --- | --- | --- | --- |
| 263 | 70 | 30 | 163 |

Top 40 failures: `failures.md`.
