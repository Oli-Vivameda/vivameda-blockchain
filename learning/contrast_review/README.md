# Owner-selected token contrast — research, not automatic training

Prepared 17 October 2026. Two owner-selected examples were received for a runner /
collapse comparison. Exact identities, owner feedback, public API captures and case
rows remain private server-side. No individual live alert is published here.

Current status: public-source capture and method review completed; frozen membership
and original retained alert context still need the owner-run read-only export. No
causal explanation, feature separation, new entry rule or trained weights is claimed.
A two-case comparison is exploratory and selected after the outcomes were known.

## Compare what was knowable

For the earliest retained ALERT per mint, recover score/regime and recorded entry
context, launch timing, the latest <=120s pre-alert snapshot, liquidity/cap, five-minute
buy count share and volume acceleration. These are reconstructed retained features;
capture-time availability and original Telegram delivery are not established by the
case table. Compare only screening records checked before the alert, at the same
alert level, fresh within 300 seconds and bound to the exact mint/chain/pair. A later
report never backfills an earlier UNKNOWN. Missing retained reviews remain missing.

The scanner's existing admission policy requires three PASS checks: token controls,
liquidity control and trading mechanics. Any explicit REJECT blocks admission, but
UNKNOWN wallet links, developer history, holder ownership and wallet age do not.
Thus an alert is not proof that all wallet/insider risks were cleared. The separate
learning journal's all-seven PASS rule is stricter; neither policy is changed here.

Registered questions, before private case comparison:

- Was one alert a recovery after an earlier spike rather than an early continuation?
- Did liquidity depth and replenishment support independent new demand, or did a
  shrinking quote reserve leave holders competing for exits?
- Were buyers growing in number, or were trade counts concentrated/recycled? Trade
  counts are not unique people; high volume alone does not establish organic demand.
- Did linked wallets or the creator sell before/after the alert? A transfer is not a
  sale and related addresses do not by themselves prove common control or bundling.
- Was collapse caused by authenticated LP removal, a large sale, or fading demand?
  A lower USD-liquidity display alone cannot distinguish these mechanisms.

These are hypotheses to investigate, not findings or validated thresholds. Both a
runner and a collapse can have dangerous wallet structure; a peak is not realized
profit and a runner can later collapse too. No automatic rule relaxation/tightening.

## Protected owner export

`export_case.py` uses SQLite mode=ro, PRAGMA query_only, one read transaction, a read
column allowlist and a 20-second bound. First query per identity is only boolean
membership in pl_predictions. Every member is excluded before any case, snapshot or
screening data is opened. Missing membership table fails closed. The authorizer denies
pl_results, prediction bodies/probabilities, model features, all other tables and
writes. If either identity is excluded, no paired learning comparison is eligible.

For nonmembers only, it returns bounded aggregate case context, fresh as-of checks,
5/15/30/60-minute first-after-deadline endpoints (lateness <=180s), coverage/gaps and a
sampled post-alert peak lower bound. No interpolation, lifetime ATH, fills or net PnL.
No case rows are written to the production learning journal, model or frozen ledger.
No service installation, configuration edit or Telegram message is involved.

From the owner's root server terminal, substitute the reviewed SHA-256 and the two
exact mints privately; never publish those arguments during the 24-hour alert delay:

```bash
python3 -B /var/lib/vivameda-engineering/repo/learning/contrast_review/export_case.py --expected-sha256 REVIEWED_SHA256 --mint FIRST_MINT --mint SECOND_MINT
```

14 offline synthetic tests cover frozen exclusion, denied values/writes, unchanged
source DB bytes, earliest ALERT, as-of identity/freshness, missing endpoints, no
interpolation, time bounds, row limits and bootstrap hash refusal. Tests never read
production databases or use the network.

```bash
python3.12 -B -m unittest discover -s learning/contrast_review/tests -v
```

Next: review the owner export; keep frozen identities out of case learning. If both
are eligible and evidence exists, add an explicitly exploratory private case note
with observed differences, counter-evidence and missing facts. Any new screening
feature then needs a separately preregistered prospective shadow test across many
cases. No Qwen fine-tune, numerical weight update or live policy change follows from
this owner-selected pair. The production learning journal remains dormant as directed.
