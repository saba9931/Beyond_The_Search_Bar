# Coding rules (how text becomes numbers)

Coding is done by fixed text rules in the notebook, not by hand, so anyone can re-run it and get the same numbers.

| Variable | Rule |
|---|---|
| `<retailer>_mention` | The retailer name appears in the answer text (case-insensitive). Retailers coded: Sephora, Nykaa, Tira, Purplle, Amazon, Myntra. Hypotheses are tested only for Sephora India, Nykaa and Tira (Tira is reported, not tested); Purplle, Amazon and Myntra are counted as other retailers. |
| `<retailer>_cited` | A source link in the answer belongs to that retailer's website (for example `sephora.`, `nykaa.`). |
| `first_pos_<retailer>` | Where the name first appears in the answer, from 0 (start) to 1 (end). |
| `n_domains` | Number of distinct websites in the source links. |
| `words` | Answer length in words. |

Known limits of the rules:
- A brand that is sold at Sephora is **not** counted as Sephora; only the name "Sephora" counts.
- "Nykaa" as a product brand (Nykaa Cosmetics) is counted as Nykaa, because the rule matches the name; this can overstate Nykaa slightly.
- The word must appear in the answer text. A link alone is coded as `_cited`, not `_mention`.
- Primary analysis uses only unbranded prompts (`include_in_primary_unbranded = yes`); the branded comparison prompt (B20E) is excluded.
- Planned for the final report: hand-check a random 20% of answers against the rules and report agreement.
