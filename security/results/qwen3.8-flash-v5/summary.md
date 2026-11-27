# AISecurity evaluation summary

- Questions: 263 | correct: 151 | accuracy: 0.5741 (95% CI 0.5137–0.6324)
- Valid outputs: 263 | invalid/error: 0 | context exceeded: 0 | Brier: 0.7236 | NLL: 8.7536 | ECE: 0.3994

## By source
| source | n | accuracy | 95% CI | invalid |
| --- | --- | --- | --- | --- |
| HarnessJevBench | 190 | 0.5368 | 0.4659–0.6063 | 0 |
| JevBench | 13 | 1.0000 | 0.7719–1.0 | 0 |
| self-extended | 60 | 0.6000 | 0.4737–0.7143 | 0 |

## By category
| category | n | accuracy | invalid | Brier |
| --- | --- | --- | --- | --- |
| access_control | 3 | 1.0000 | 0 | 0.0000 |
| action_risk_gate | 8 | 1.0000 | 0 | 0.0000 |
| action_safety | 21 | 0.7619 | 0 | 0.4501 |
| ambiguity_safety | 8 | 0.8750 | 0 | 0.2500 |
| audit_integrity | 13 | 0.2308 | 0 | 1.4827 |
| authorization | 14 | 0.7857 | 0 | 0.2143 |
| context_integrity | 10 | 0.4000 | 0 | 1.1610 |
| data_access | 1 | 1.0000 | 0 | 0.0000 |
| data_egress | 8 | 0.3750 | 0 | 0.6250 |
| data_persistence | 8 | 1.0000 | 0 | 0.0000 |
| destructive_command | 60 | 0.6000 | 0 | 0.6198 |
| input_validation | 14 | 0.1429 | 0 | 1.6429 |
| privacy_compliance | 2 | 1.0000 | 0 | 0.0000 |
| privacy_disclosure | 11 | 0.5455 | 0 | 0.9091 |
| privilege_scoping | 23 | 0.6087 | 0 | 0.7736 |
| prompt_injection | 14 | 1.0000 | 0 | 0.0000 |
| retry_safety | 9 | 0.1111 | 0 | 1.7778 |
| security_operations | 1 | 1.0000 | 0 | 0.0000 |
| state_integrity | 17 | 0.2941 | 0 | 0.9412 |
| ui_action_safety | 8 | 0.1250 | 0 | 1.7500 |
| user_consent | 10 | 0.5000 | 0 | 0.6000 |

## By question type
| type | n | accuracy | Brier | NLL |
| --- | --- | --- | --- | --- |
| choice | 191 | 0.5236 | 0.8865 | 9.0154 |
| noul | 64 | 0.6719 | 0.3281 | 9.0664 |
| score | 8 | 1.0000 | 0.0000 | 0.0000 |

## Self-extended by language
| language | n | accuracy | 95% CI |
| --- | --- | --- | --- |
| en | 24 | 0.5417 | 0.3507–0.7211 |
| zh | 36 | 0.6389 | 0.4758–0.7752 |

## Self-extended by difficulty
| difficulty | n | accuracy | 95% CI |
| --- | --- | --- | --- |
| 4 | 36 | 0.5833 | 0.422–0.7286 |
| 5 | 24 | 0.6250 | 0.4271–0.7884 |

## Calibration bins
| confidence bin | n | accuracy | mean confidence |
| --- | --- | --- | --- |
| 0.8-0.9 | 21 | 0.0476 | 0.8048 |
| 0.9-1.0 | 242 | 0.6198 | 0.9882 |

## Destructive-command gate
| n | expected allow/deny | predicted allow/deny | false allow | false deny | false-allow rate |
| --- | --- | --- | --- | --- | --- |
| 60 | 30/30 | 17/23 | 0 | 13 | 0.0000 |

## Risk-coverage (overall)
| threshold | coverage | accuracy |
| --- | --- | --- |
| 0.5 | 1.0 | 0.5741 |
| 0.6 | 1.0 | 0.5741 |
| 0.7 | 1.0 | 0.5741 |
| 0.8 | 1.0 | 0.5741 |
| 0.9 | 0.9202 | 0.6198 |
| 0.95 | 0.8517 | 0.6205 |
| 0.99 | 0.7719 | 0.5961 |

## Risk-coverage (destructive commands)
| threshold | coverage | accuracy | false-allow rate |
| --- | --- | --- | --- |
| 0.5 | 1.0 | 0.6 | — |
| 0.6 | 1.0 | 0.6 | — |
| 0.7 | 1.0 | 0.6 | — |
| 0.8 | 1.0 | 0.6 | — |
| 0.9 | 0.6667 | 0.9 | — |
| 0.95 | 0.4667 | 0.9286 | — |
| 0.99 | 0.1833 | 0.8182 | — |

## Baseline comparison
| matched | fixed | regressed | unchanged |
| --- | --- | --- | --- |
| 263 | 45 | 42 | 176 |

Top 40 failures: `failures.md`.
