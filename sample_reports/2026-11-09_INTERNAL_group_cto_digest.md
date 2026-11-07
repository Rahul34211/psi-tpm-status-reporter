# Internal Digest for Group CTO: Mon 09 Nov 2026
*Internal only. Do not forward to clients.*

## Portfolio

| Project | Client | RAG | Next milestone | Date | Open items | Overdue |
|---|---|---|---|---|---|---|
| Kavach | Nirmal Finance | 🔴 RED | Client UAT starts | Thu 12 Nov 2026 | 7 | 0 |
| Ledger | Sagar Publications | 🟠 AMBER | Sprint 4 exit: duplicate fix + regression test | Fri 13 Nov 2026 | 4 | 0 |

## Kavach: 🔴 RED
**Main problem:** 4/50 test calls gave a wrong EMI amount (cause unknown); 2 calls dropped at ~40 s; new telephone-provider IPs need client approval (3 working days, ends Thu); AI test cost 40% over budget; Meera on leave Wed-Fri; Arjun double-booked.
**Date note:** CONDITIONAL. Go/no-go for UAT Wed 11 Nov 4 PM; fallback UAT Fri 13 Nov; go-live Mon 16 Nov.

| ID | Type | Description | P x I | Score | Owner | Due | Visibility |
|---|---|---|---|---|---|---|---|
| KAV-01 | Issue | Wrong EMI amount in 4 of 50 test calls (8%); root cause unknown. | High x Critical | 12 | Arjun | Tue 10 Nov 2026 ⏰ ≤3 days | Client |
| KAV-03 | Issue | Telephone provider changed IPs; client network approval takes 3 working days (Mon to Thu). | High x Critical | 12 | Dev | Wed 11 Nov 2026 ⏰ ≤3 days | Client |
| KAV-06 | Risk | Arjun is double-booked: Kavach go-live prep Thu-Fri, Ledger fix (1 day) and Kavach bug work Mon-Tue. Dev is half-time. | High x High | 9 | TPM | Mon 09 Nov 2026 ⏰ ≤3 days | Internal |
| KAV-05 | Risk | Meera (AI/ML) on leave Wed-Fri while the wrong-EMI cause may still be open. | High x High | 9 | TPM | Tue 10 Nov 2026 ⏰ ≤3 days | Internal |
| KAV-04 | Issue | AI cost for test calls is 40% over budget; cause unknown. | High x High | 9 | TPM | Wed 11 Nov 2026 ⏰ ≤3 days | Internal |
| KAV-02 | Issue | 2 of 50 test calls ended at ~40 seconds. | Medium x High | 6 | Meera | Tue 10 Nov 2026 ⏰ ≤3 days | Client |
| KAV-07 | Risk | Client Managing Director joins the go-live call; a visible failure damages trust. | Medium x High | 6 | TPM | Fri 13 Nov 2026 | Internal |

## Ledger: 🟠 AMBER
**Main problem:** 1,200 duplicate customers in test migration (likely phone-format differences); Friday report missed; WhatsApp birthday offers requested outside scope; Arjun is shared with Kavach.
**Date note:** Baseline Fri 13 Nov (assumed sprint end). Forecast Wed 18 Nov because the fix is scheduled after Kavach go-live prep.

| ID | Type | Description | P x I | Score | Owner | Due | Visibility |
|---|---|---|---|---|---|---|---|
| LED-03 | Risk | WhatsApp birthday offers requested for go-live; not in migration scope. | High x High | 9 | TPM | Wed 11 Nov 2026 ⏰ ≤3 days | Client |
| LED-01 | Issue | 1,200 duplicate customers in test migration; likely phone formats (+91, 0, spaces). | High x High | 9 | Arjun | Wed 18 Nov 2026 | Client |
| LED-02 | Issue | Friday's weekly status report was not sent; COO escalated. | High x Medium | 6 | TPM | Mon 09 Nov 2026 ⏰ ≤3 days | Client |
| LED-04 | Risk | Sprint 4 exit (baseline Fri 13 Nov) slips about 3 working days because the dedup fix is after Kavach go-live prep. | Medium x Medium | 4 | TPM | Mon 09 Nov 2026 ⏰ ≤3 days | Client |

## Owner load (open items)
- TPM: 7  ← check capacity
- Arjun: 2
- Dev: 1
- Meera: 1

## Due in the next 3 days (or overdue)
- Mon 09 Nov 2026: KAV-06 Arjun is double-booked: Kavach go-live prep Thu-Fri, Ledger fix (1 day) and Kava (TPM)
- Mon 09 Nov 2026: LED-02 Friday's weekly status report was not sent; COO escalated. (TPM)
- Mon 09 Nov 2026: LED-04 Sprint 4 exit (baseline Fri 13 Nov) slips about 3 working days because the dedup (TPM)
- Tue 10 Nov 2026: KAV-01 Wrong EMI amount in 4 of 50 test calls (8%); root cause unknown. (Arjun)
- Tue 10 Nov 2026: KAV-05 Meera (AI/ML) on leave Wed-Fri while the wrong-EMI cause may still be open. (TPM)
- Tue 10 Nov 2026: KAV-02 2 of 50 test calls ended at ~40 seconds. (Meera)
- Wed 11 Nov 2026: KAV-03 Telephone provider changed IPs; client network approval takes 3 working days (Mo (Dev)
- Wed 11 Nov 2026: KAV-04 AI cost for test calls is 40% over budget; cause unknown. (TPM)
- Wed 11 Nov 2026: LED-03 WhatsApp birthday offers requested for go-live; not in migration scope. (TPM)

