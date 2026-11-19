"""Render a JavaScript-free version of the deck.

Same content, same CSS, no script at all. Collapsible sections use native
<details>/<summary>, which browsers handle without any JavaScript, so the
walkthrough and all fifteen prompt versions stay navigable.

Everything that was a live widget becomes a static table of the same numbers:
  * score calculator  -> worked examples
  * weight sensitivity-> the same trio at three weightings
  * anatomy stepper   -> all five stages, in order
  * optimiser stepper -> the full kept/dropped table
  * tile modal        -> nine expandable cards
  * version browser   -> fifteen expandable versions with diff and full prompt
"""

from __future__ import annotations

from build_deck import CSS, SPRITE, esc

# SPRITE also carries the interactive deck's noscript banner; this build has
# nothing to warn about, so keep only the SVG symbol definitions.
_SPRITE = SPRITE[SPRITE.index('<svg'):]


DOC_CSS = """
body{overflow:auto;height:auto}
.doc{max-width:1080px;margin:0 auto;padding:0 32px 60px}
.doc header{padding:44px 0 18px;border-bottom:3px solid var(--ink)}
.doc header h1{font-size:38px;margin:0 0 8px}
.doc header p{margin:0;color:var(--muted);font-size:16px;max-width:70ch}
.badge{display:inline-block;margin-top:12px;font-size:11.5px;font-weight:800;
  background:#eef2fb;color:var(--accent);padding:4px 10px;border-radius:6px}
.toc{margin:22px 0 8px;padding:16px 20px;background:var(--panel);border:1px solid var(--line);
  border-radius:12px;font-size:13.5px}
.toc b{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.1em;
  color:var(--muted);margin-bottom:8px}
.toc ol{margin:0;padding-left:18px;columns:2;column-gap:32px}
.toc li{margin-bottom:4px}
.toc a{color:var(--accent);text-decoration:none}
.toc a:hover{text-decoration:underline}
article{padding-top:26px}
article > h2.pagetitle{font-size:13px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--accent);margin:0 0 4px}
article > h3.deckh{font-size:30px;margin:0 0 10px;letter-spacing:-.02em}
.doc h2.sec{font-size:15px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);
  margin:34px 0 10px;padding-top:8px;border-top:1px solid var(--line)}
.doc p{font-size:14.5px;color:#39445c;line-height:1.6;margin:0 0 10px}
.doc .lede{font-size:16.5px;color:var(--muted)}
.dl{opacity:1!important;animation:none!important}
details{border:1px solid var(--line);border-radius:11px;background:var(--panel);margin:10px 0}
details[open]{box-shadow:0 2px 10px rgba(16,24,40,.05)}
summary{cursor:pointer;padding:12px 16px;font-weight:700;font-size:14px;list-style:none;
  display:flex;align-items:center;gap:10px;flex-wrap:wrap}
summary::-webkit-details-marker{display:none}
summary::before{content:"+";font-family:var(--mono);color:var(--accent);font-weight:800;width:12px}
details[open] summary::before{content:"-"}
summary .summeta{margin-left:auto;font-weight:600;font-size:12px;color:var(--muted);
  font-family:var(--mono)}
.details-body{padding:0 16px 16px}
.tilecard{border-left:3px solid var(--line)}
.tilecard.hot{border-left-color:var(--accent)}
.stage{border-left:3px solid var(--accent);padding:2px 0 2px 16px;margin:18px 0}
.stage .staget{font-weight:800;font-size:15px;margin-bottom:4px}
.stage .staget span{color:var(--accent);font-family:var(--mono);margin-right:8px}
.simplefoot{font-size:12.5px;color:#5b6478;margin:6px 0 0;padding-left:12px;
  border-left:2px solid #e3e7ef;line-height:1.5}
pre.code{background:#0f1526;color:#d7dcea;border-radius:9px;padding:12px 14px;
  font-family:var(--mono);font-size:11.5px;line-height:1.6;overflow:auto;white-space:pre-wrap;margin:6px 0 0}
.details-body pre{background:#0f1526;color:#d7dcea;border-radius:9px;padding:12px 14px;
  font-family:var(--mono);font-size:11.5px;line-height:1.6;overflow:auto;white-space:pre-wrap;margin:6px 0 0}
.limitbox{background:#fffbeb;border:1px solid #f5e6b8;border-radius:9px;padding:11px 13px;
  font-size:13px;color:#6b5a1e;line-height:1.5;margin-top:6px}
table.plain{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0 4px}
table.plain th,table.plain td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line)}
table.plain th{font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
table.plain td.n{font-variant-numeric:tabular-nums;font-weight:700;white-space:nowrap}
.keep{color:#0b7a5c;font-weight:700}
.dropped{color:#b42318}
.baseline{color:var(--accent);font-weight:700}
.code{margin:8px 0 0}
footer{margin-top:46px;padding-top:16px;border-top:1px solid var(--line);
  font-size:12.5px;color:var(--muted)}
@media print{ details{page-break-inside:avoid} details[open] summary::before{content:"-"} }
"""


def tbl(headers, rows, cls="plain"):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td class='{c}'>{v}</td>" if c else f"<td>{v}</td>"
                         for c, v in row) + "</tr>"
        for row in rows
    )
    return f"<table class='{cls}'><tr>{head}</tr>{body}</table>"


def diff_html(rows):
    out = []
    for op, text in rows or []:
        cls = {"+": "add", "-": "del", "@": "hunk"}.get(op, "ctx")
        shown = text if len(text) <= 200 else text[:200] + "\u2026"
        out.append(f'<span class="dl {cls}">{esc(shown)}</span>')
    return '<div class="code">' + ("".join(out) or '<span class="dl ctx">no textual change</span>') + "</div>"


def render(payload) -> str:
    versions = payload["versions"]
    base = payload["base"]
    details = payload["details"]
    calc = payload["calculator"]
    opt = payload["optimizer"]
    rules = payload["rules_detail"]
    an = payload["anatomy"]
    base_rows = payload["baseline_rows"]

    # ---------- page 1 ----------
    mech = payload["rules"]["mechanical"]
    optn = payload["rules"]["optimisable"]

    p1 = f"""
<article id="p1">
  <h2 class="pagetitle">Page 1</h2>
  <h3 class="deckh">What DSPy is, and what it can do</h3>
  <p class="lede">A Python toolkit for LLM systems: you describe the job, and a scoring test decides
  whether a change to the instructions helped.</p>

  <h2 class="sec">The problem it solves</h2>
  <p>You write a prompt. It works in the demo. Then you change the model, add a rule, or tune it for
  one more client, and you cannot tell whether it got better or worse. Every change is a guess judged
  by eyeballing a few outputs. DSPy's answer is to stop treating the prompt as the thing you edit and
  start treating it as an output you measure.</p>
  {tbl(["", "hand-prompted", "with a score"],
       [[("", "prompt v1"), ("", "?"), ("", "0.61")],
        [("", "prompt v2"), ("", "?"), ("", "0.77")],
        [("", "prompt v3"), ("", "?"), ("", "0.58")]])}
  <p>Same three prompts. The only difference is a test that returns a number.</p>

  <h2 class="sec">How the framework is shaped</h2>
  <p>Five pieces, in order. The plain name is what it means; the grey name is what you would type.</p>
  {tbl(["step", "plain name", "what it is", "DSPy name"],
       [[("", "1"), ("", "The task"), ("", "what goes in, what comes out"), ("mono2", "Signature")],
        [("", "2"), ("", "The method"), ("", "one answer, or reason first, or use tools"), ("mono2", "Module")],
        [("", "3"), ("", "The pipeline"), ("", "steps joined together in Python"), ("mono2", "Module subclass")],
        [("", "4"), ("", "The score"), ("", "a test that says right or wrong"), ("mono2", "Metric")],
        [("", "5"), ("", "The editor"), ("", "rewrites the instructions to raise the score"), ("mono2", "Optimiser")]])}
  <p><b>Closest familiar thing: a compiler.</b> You write what you want in a readable form; a compiler
  produces the low-level instructions. DSPy does that for prompts. Unlike a compiler, the "correct
  output" has to come from your own test score, which is why the score is the hard part.</p>

  <h2 class="sec">A single call, end to end</h2>
  {tbl(["move", "what happens"],
       [[("", "1. Declare"), ("", "The fields you want, with types, plus one sentence saying what the job is.")],
        [("", "2. Build prompt"), ("", "A formatter turns that declaration into instructions for the model.")],
        [("", "3. Model answers"), ("", "One API call to whichever model you configured.")],
        [("", "4. Parse"), ("", "The text is converted back into real data: lists, numbers, fixed options.")],
        [("", "5. Typed object"), ("", "You ask for result.answer. A wrong shape raises instead of passing silently.")]])}
  <p>No prompt is stored in your code. It is built fresh each call from your declaration plus whatever
  the editor last wrote, which is why changing model does not throw away your work.</p>

  <h2 class="sec">What it can do</h2>
  <p>Each entry expands. Open one for the function, a code example, when to use it, when not to, and
  its limitation.</p>
"""
    for key, c in (payload.get("concepts") or {}).items():
        # what / parts / simple_note / real / limit / extra are authored HTML
        p1 += f"""
<details class="tilecard"><summary>{esc(c['title'])} &mdash; {esc(c['blurb'])}
<span class="summeta">{esc(c['api'])}</span></summary>
<div class="details-body">
  <h2 class="sec" style="margin-top:6px">What it is</h2><p>{c['what']}</p>
  <h2 class="sec">What goes into it</h2>{c['parts']}
  <h2 class="sec">A simple example</h2>
  <pre class="code">{esc(c['simple'])}</pre>
  <p class="simplefoot">{c['simple_note']}</p>
  <h2 class="sec">In our case</h2>{c['real']}
  <h2 class="sec">Limitation</h2>
  <div class="limitbox"><b>Limitation.</b> {c['limit']}</div>
  {c.get('extra', '')}
</div></details>"""

    p1 += f"""
  <h2 class="sec">The trade</h2>
  {tbl(["good fit", "bad fit"],
       [[("", "The job splits into steps, correctness is checkable by code, and you expect to change models."),
         ("", "You will run it five times, or nobody can define correct, or a plain function already answers it.")]])}

  <h2 class="sec">What our own measurement cannot tell you</h2>
  {tbl(["limit", "why it matters"],
       [[("", "Cannot resolve small gains"),
         ("", "10 held-out cases puts roughly plus or minus 0.08 of standard error on the mean. A +0.03 change is noise.")],
        [("", "Only scores what we listed"),
         ("", "ASML is a genuine semiconductor peer but sits in a different industry code, so no signal we have can see it.")],
        [("", "The weights are our judgement"),
         ("", "Peer 1.0 / adjacent 0.5 / wrong -1.5 was chosen, not derived. Change them and the ranking can change.")],
        [("", "Part of it is circular"),
         ("", "Some labels come from the same taxonomy the scorer uses. Agreement confirms consistency, not correctness.")]])}
</article>"""

    # ---------- page 2 ----------
    tiers = calc["tiers"]
    ex = calc["examples"]
    combos = calc["combos"]
    def pick(*ids):
        return combos["|".join(sorted(ids))]

    worked = [
        ("EQ_AMD, EQ_TSM, IDX_SOX", "three true peers", pick("EQ_AMD", "EQ_TSM", "IDX_SOX")),
        ("EQ_AMD, EQ_TSM, IDX_SPX", "two peers, one broad", pick("EQ_AMD", "EQ_TSM", "IDX_SPX")),
        ("EQ_AMD, IDX_SOX, ETF_XLK", "one peer, two references", pick("EQ_AMD", "IDX_SOX", "ETF_XLK")),
        ("EQ_AMD, EQ_TSM, EQ_CRM", "two peers, one wrong pick", pick("EQ_AMD", "EQ_TSM", "EQ_CRM")),
        ("IDX_SOX, ETF_XLK, IDX_SPX", "no peer at all", pick("IDX_SOX", "ETF_XLK", "IDX_SPX")),
        ("EQ_CRM, EQ_COP, CASH_USD", "all three wrong", pick("EQ_CRM", "EQ_COP", "CASH_USD")),
    ]
    worked_rows = [
        [("mono2", ids), ("", note), ("n", f"{r['score']:.3f}"),
         ("", f"{r['peers']} / {r['adj']} / {r['wrong']}")]
        for ids, note, r in worked
    ]

    sens = calc["sensitivity"]
    sens_key = "|".join(sorted(["EQ_AMD", "EQ_TSM", "EQ_CRM"]))
    sens_rows = [[("", f"penalty {w}"), ("n", f"{sens[w][sens_key]:.3f}")]
                 for w in ("0.5", "1.5", "3.0")]

    p2 = f"""
<article id="p2">
  <h2 class="pagetitle">Page 2</h2>
  <h3 class="deckh">The setup, and what DSPy does with it</h3>
  <p class="lede">One real task: given an equity, pick three defensible benchmark references.
  NVDA should get AMD or TSMC, not Salesforce.</p>

  <h2 class="sec">1. What we hand to DSPy</h2>
  {tbl(["artifact", "size", "what it becomes"],
       [[("", "Catalogue"), ("n", str(payload['pack'])),
         ("", f"{payload['pack']} instruments with sector, industry, region, currency. The model may not invent an id outside it. Becomes the shortlist input.")],
        [("", "Labelled cases"), ("n", str(payload['cases'])),
         ("", f"{payload['cases']} assets with hand-curated truth in four tiers. {payload['eval_cases']} are held out. Becomes the trainset and the held-out set.")],
        [("", "Metric"), ("n", "1 fn"),
         ("", "Turns one answer into a score plus a sentence of feedback. Becomes the objective.")]])}
  <p>DSPy adds three things we did not write: the signature (shape of the answer), the program (the
  call), and the optimiser (the rewriting loop).</p>

  <h2 class="sec">2. Where the metric came from</h2>
  <p>Nobody hands you a metric. It is built, mostly from failure analysis. Four steps:
  start from the cost, curate truth in tiers, pick weights openly, automate the checks.</p>
  {tbl(["tier", "count", "examples for NVDA", "credit"],
       [[("", "peer"), ("n", str(tiers['peer'])), ("mono2", ex['peer']), ("n", "+1.0")],
        [("", "adjacent"), ("n", str(tiers['adjacent'])), ("mono2", ex['adjacent']), ("n", "+0.5")],
        [("", "hard negative"), ("n", str(tiers['hard'])), ("mono2", ex['hard']), ("n", "-1.5")],
        [("", "unrelated"), ("n", str(tiers['unrelated'])), ("mono2", ex['unrelated']), ("n", "-1.5")]])}
  <p><b>Hard negatives are the ones that matter.</b> Anyone can reject oil for a chip company. Only a
  real analysis rejects a software company for a chip company, which is why five Salesforce-class ids
  sit in their own tier. Nothing here was inferred by a model.</p>
  <p>The same three picks (AMD + TSM + CRM) under three different penalties, which is why the weights
  are published rather than buried:</p>
  {tbl(["wrong-pick penalty", "score for AMD + TSM + CRM"], sens_rows)}
  <p>At 0.5 a peer-less answer still scores respectably. At 3.0 it collapses. Same answer, different
  metric, different conclusion.</p>

  <h2 class="sec">3. What a score actually is</h2>
  <p>The score is not a similarity rating. It is a small additive rule over the three ids returned:
  peer 1.0, adjacent 0.5, wrong -1.5, divided by three, then penalised for duplicate exposure.</p>
  {tbl(["picks", "what they are", "score", "peers / adj / wrong"], worked_rows)}
  <p>All 84 combinations were scored with the real metric. This table is a sample.</p>

  <h2 class="sec">4. Anatomy of one full iteration - how v1 was produced</h2>
"""
    for i, stage in enumerate(an, 1):
        p2 += f"""
<div class="stage"><div class="staget"><span>{i}</span>{esc(stage['title'])}</div>
<div class="details-body" style="padding-left:0">{stage['body']}</div></div>"""

    opt_rows = []
    for e in opt:
        cls = {"kept": "keep", "dropped": "dropped", "baseline": "baseline"}.get(e["status"], "")
        delta = e["score"] - base
        opt_rows.append([
            ("mono2", e["label"]),
            ("n", f"{e['score']:.3f}"),
            ("", "base" if e["status"] == "baseline" else f"{delta:+.3f}"),
            (cls, e["status"]),
        ])

    p2 += f"""
  <h2 class="sec">5. What the optimiser actually did</h2>
  <p>Fourteen proposals. <b>Two improved on the human prompt, twelve did not.</b></p>
  {tbl(["version", "score", "vs baseline", "outcome"], opt_rows)}

  <h2 class="sec">6. 22 rules, two very different fates</h2>
  <p><b>{mech} enforced by code</b> and <b>{optn} left to the optimiser.</b> A rule in prose is a hope;
  a rule in code is a guarantee.</p>
  {tbl(["how", "rule enforced by code"],
       [[("mono2", esc(r['mech'])), ("", esc(r['rule']))] for r in rules["mechanical"]])}
  <p>The only rules the optimiser may rewrite:</p>
  <ol>{''.join('<li>' + esc(r) + '</li>' for r in rules['optimisable'])}</ol>

  <h2 class="sec">7. The baseline on held-out cases</h2>
  <p>v0 scored <b>{(base or 0):.3f}</b> over {len(base_rows)} cases at temperature 0. For each:
  the three ids it returned, how many were true peers, how many were wrong-sector.</p>
  {tbl(["asset", "score", "peers", "wrong", "picks returned"],
       [[("", r['asset'].replace('EQ_', '')), ("n", f"{float(r['score']):.2f}"),
         ("n", f"{r['peers']}/3"), ("n", str(r['wrong'])), ("mono2", esc(r['picks']))]
        for r in base_rows])}
  <p>The failure mode is not wrongness, it is <b>templating</b>: nine of ten answers were one peer
  plus one sector ETF plus the S&amp;P 500.</p>
</article>"""

    # ---------- page 3 ----------
    p3 = f"""
<article id="p3">
  <h2 class="pagetitle">Page 3</h2>
  <h3 class="deckh">The prompt, version by version</h3>
  <p class="lede">Every version below was written by GEPA's reflection step, then scored on the same
  held-out cases. Open one for its diff against the previous version and its full text.</p>
  <p>Baseline <b>{(base or 0):.3f}</b>. Best <b>{(payload['best'] or 0):.3f}</b>. Fifteen versions,
  of which two beat the human prompt.</p>
"""
    for i, v in enumerate(versions):
        score = v["score"]
        delta = "" if (score is None or base is None or i == 0) else f"{score - base:+.3f}"
        head = f"<b>{v['label']}</b> {esc(v.get('note', ''))}"
        meta = (f"{score:.3f} {delta}" if score is not None else "not scored")
        meta += f" · {v['words']}w · {v['chars']}c"
        p3 += f"""
<details{" open" if i <= 1 else ""}><summary>{head}<span class="summeta">{meta}</span></summary>
<div class="details-body">
  <h2 class="sec" style="margin-top:4px">What changed from {esc(versions[i-1]['label']) if i else 'nothing (this is the start)'}</h2>
  {diff_html(v.get('diff'))}
  <h2 class="sec">Full prompt</h2>
  <div class="code">{esc(v['text'])}</div>
</div></details>"""

    p3 += "</article>"

    # ---------- page 4 ----------
    toy = payload.get("toy") or {}
    full = toy.get("full") or {}
    promoted = "".join(
        f"<tr><td class='mono2'>{esc(k)}</td><td class='tn'>{v:.2f}</td></tr>"
        for k, v in sorted(full.items(), key=lambda kv: -kv[1])
    )
    p4 = f"""
<article id="p4">
  <h2 class="pagetitle">Page 4</h2>
  <h3 class="deckh">How the optimiser works</h3>
  <p class="lede">Neither optimiser is doing anything mystical: write a candidate prompt, score it,
  keep it if it is better. They differ in <em>when</em> the prompt is written, and in <em>what
  counts as better</em>.</p>

  <h2 class="sec">1. The loop</h2>
  <p><b>Training set</b> &mdash; the cases the optimiser rewrites the instruction against.<br>
  <b>Validation set</b> &mdash; ranks the survivors; this decides which prompt is best.<br>
  <b>Test set</b> &mdash; never enters the search. It only produces the number we report.</p>
  <p class="note">The optimiser only ever ranks on validation. If the test set were used for
  ranking, the reported score would belong to the winner that same test set chose.</p>

  <h2 class="sec">2. MIPROv2 &mdash; generate, rank cheaply, promote the survivors</h2>
  <ol class="steps4">
    <li><b>Generate</b> every candidate up front, before any scoring.</li>
    <li><b>Score cheaply</b> &mdash; one random minibatch of the validation set per trial.</li>
    <li><b>Rank by the average</b> of the noisy draws, not one lucky batch.</li>
    <li><b>Promote</b> the leader to a full evaluation on the whole validation set, every six
      trials, and feed that result back to the search.</li>
    <li><b>Return</b> the program with the best full-evaluation score.</li>
  </ol>
  <p><b>Instruction candidates</b> are written by an LLM proposer guided by a dataset summary and a
  random tip, once, up front. <b>Demo sets</b> are constructed: zero-shot, labelled-only,
  bootstrapped, then shuffled bootstrapped sets with random sizes. The pairing is <b>searched</b>
  by Optuna, not picked at random. The only purely random draw per trial is which validation cases
  land in the minibatch. At <code>auto="light"</code> with demos enabled that is
  <b>3 instructions &times; 6 demo sets = 18 combinations</b>.</p>
  <p class="note">Minibatch mode only engages above <b>50 validation cases</b>. With our 3-case
  valset, every MIPROv2 trial would already be a full evaluation.</p>

  <h2 class="sec">Toy run &mdash; watch one candidate swing</h2>
  <p>Twelve candidates, ten validation cases, three drawn per trial. Trial 2 and trial 4 are the
  <b>same candidate on different batches</b>:</p>
  <table class="ctab">
    <tr><th>#</th><th>candidate</th><th>3 cases drawn from val</th><th>score</th></tr>
    {toy.get('rows', '')}
  </table>
  <p style="margin-top:12px">I3+D2 scores 1.00 in trial 2 and 0.33 in trial 4. Its average, 0.667,
  ties it with I2+D2, so the cheap stage cannot separate them. The full evaluation can:</p>
  <table class="ctab">
    <tr><th>promoted candidate</th><th>full validation score</th></tr>
    {promoted}
  </table>
  <p class="note">I2+D2 wins at 0.90 after ranking equal second. The minibatch leader, I3+D1 at
  0.833, lands mid-pack at 0.60. The cheap rank was a filter, never the answer.</p>

  <h2 class="sec">3. GEPA &mdash; write, read, rewrite</h2>
  <ol class="steps4">
    <li><b>Sample a minibatch</b> (default 3 cases) and run the current candidate with trace capture.</li>
    <li><b>Score it.</b> The metric returns a number <em>and a sentence</em>. That sentence is the
      input to the next step, and it is why the metric has to say why.</li>
    <li><b>Reflect.</b> A second model reads the failures and rewrites the instruction &mdash; a
      targeted edit, not a paraphrase.</li>
    <li><b>Accept on the Pareto frontier.</b> A child is kept if it beats its parent on
      <em>any</em> case, not just on average.</li>
  </ol>
  <p>A plain average rewards a prompt that is mediocre everywhere. Per-case tracking keeps one that
  is excellent on semiconductors and bad on utilities, because it may still contribute later. In our
  run that produced a prompt which fixed three held-out cases and left seven untouched.</p>

  <h2 class="sec">4. Side by side</h2>
  <p><b>MIPROv2</b>: writes its candidates up front, Optuna scores the pairs, keeps the highest
  average, selects from a fixed grid.<br>
  <b>GEPA</b>: writes one instruction, reads the critique, writes the next one, and keeps a child
  if it wins <em>anywhere</em> &mdash; a reflection search rather than a grid.</p>
  <p class="note">Both return a new program and leave yours untouched. Both are bounded by the same
  thing: the metric. Neither can add a fact the model does not have.</p>
</article>"""


    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSPy tech share (static, no JavaScript)</title>
<style>{CSS}{DOC_CSS}</style></head>
<body class="doc">
{_SPRITE}
<header>
  <h1>DSPy: a tech share</h1>
  <p>How a benchmark-selection prompt became something measurable, and what an optimiser did with it.</p>
  <span class="badge">STATIC VERSION · NO JAVASCRIPT · SINGLE FILE</span>
</header>
<nav class="toc"><b>Contents</b><ol>
  <li><a href="#p1">What DSPy is and what it can do</a></li>
  <li><a href="#p2">The setup, and what DSPy does with it</a></li>
  <li><a href="#p3">The prompt, version by version</a></li>
  <li><a href="#p4">How the optimiser works</a></li>
</ol></nav>
<main>
{p1}
{p2}
{p3}
{p4}
</main>
<footer>
  Static build of the interactive deck. Same content, no script: collapsible sections use native
  HTML details elements. Model deepseek/deepseek-flash, optimiser GEPA. Open in any browser; print
  to PDF with Ctrl-P.
</footer>
</body></html>"""
