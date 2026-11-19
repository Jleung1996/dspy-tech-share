"""The six core concepts.

Structure per concept, deliberately identical so the six read as one family:
  what        what it is, in plain language
  parts       what goes into it - the ingredients
  simple      a small, easy-to-follow example (not from this project)
  simple_note one line saying what the example shows
  real        the same idea in our benchmark pipeline, with real output
  limit       where it bites
  extra       optional deeper material (tables)
"""

CONCEPTS = {
    "signatures": {
        "title": "Signatures",
        "blurb": "Specify what you want, not how",
        "api": "dspy.Signature · InputField · OutputField",
        "icon": "ic-doc",
        "what": "A signature is a <b>typed description of one task</b>. It says which inputs go "
                "in, which outputs must come out, and what type each one is. It is a Pydantic "
                "model underneath, so the reply is validated against the declared types instead "
                "of being passed along as loose text. The class docstring is the instruction - "
                "the one string an optimiser may rewrite.",
        "parts": '''<table class="ctab">
<tr><th>ingredient</th><th>what it does</th></tr>
<tr><td>the docstring</td><td>the instruction. This is the only part an optimiser may rewrite.</td></tr>
<tr><td><code>InputField</code></td><td>a value the caller supplies. Never generated.</td></tr>
<tr><td><code>OutputField</code></td><td>a value the model must produce. Validated on parse.</td></tr>
<tr><td>types</td><td><code>str</code>, <code>int</code>, <code>Literal[...]</code>, nested models,
    <code>list[...]</code>. A literal turns "pick a category" into a closed set.</td></tr>
<tr><td>field order</td><td>preserved, and it is the order the model sees. Inputs come first.</td></tr>
</table>''',
        "simple": '''class Sentiment(dspy.Signature):
    """Is this product review positive or negative?"""
    review: str = dspy.InputField()
    label: Literal["positive", "negative"] = dspy.OutputField()

classify = dspy.Predict(Sentiment)
classify(review="Battery dies in an hour.")''',
        "simple_note": "Nothing here is a prompt. The docstring is the task, the two fields are "
                       "the contract, and <code>Literal</code> means the model cannot answer "
                       "'mixed' - the parser would reject it.",
        "real": '''<p>Our benchmark task, in full:</p>
<pre>class SelectEquityBenchmarks(dspy.Signature):
    """Pick three defensible benchmarks for one holding."""
    holding: str = dspy.InputField(desc="equity, with exposure facts")
    risk_level: str = dspy.InputField(desc="pre-mapped upstream")
    shortlist: str = dspy.InputField(desc="permitted benchmark ids")
    look_through_analysis: str = dspy.OutputField()
    selections: list[PickModel] = dspy.OutputField()</pre>
<p style="margin-top:10px">And what that produces for NVIDIA:</p>
<pre class="out">Prediction(
  look_through_analysis='US semiconductor exposure; valuation and exposure
                         currency both USD, so no wrapper adjustment.',
  selections=[PickModel(benchmark_id='EQ_AMD', role='dominant_sleeve', ...),
              PickModel(benchmark_id='EQ_TSM', role='dominant_sleeve', ...),
              PickModel(benchmark_id='IDX_SOX', role='diversifier', ...)]
)</pre>
<p style="margin-top:10px">Two things are <b>absent</b> on purpose. There is no <code>name</code>
field, so the catalogue name is a dictionary lookup and cannot be paraphrased. And there is no
numeric field, so the model has nowhere to put an invented return.</p>''',
        "limit": "Types guarantee the shape, never the truth: a field typed <code>str</code> can "
                 "hold a confident wrong answer. And every field you declare is one more thing "
                 "the model must produce on every single call.",
        "extra": '''<h4>There is no "avoid" case, and that is worth saying out loud</h4>
<p>A signature is not a technique you opt into - it is what a DSPy call <em>is</em>. Even
<code>dspy.Predict("question -> answer")</code> builds one behind the scenes from that string. So
the decision is not <i>whether</i>, but three others: <b>which fields</b>, <b>how tight the
types</b>, and <b>when to stop adding</b>.</p>''',
    },
    "modules": {
        "title": "Modules",
        "blurb": "Structure your program logically",
        "api": "dspy.Predict · ChainOfThought · ReAct · RLM · BestOfN · Refine",
        "icon": "ic-route",
        "what": "A module is the <b>strategy</b> wrapped around a signature. The signature says "
                "what the task is; the module decides how to get there - one direct call, think "
                "first then answer, or a loop that calls tools. Swapping the module never changes "
                "the task definition, which is what makes strategy cheap to trial.",
        "parts": '''<table class="ctab">
<tr><th>module</th><th>what it adds</th><th>calls</th></tr>
<tr><td><code>Predict</code></td><td>nothing - one straight call</td><td>1</td></tr>
<tr><td><code>ChainOfThought</code></td><td>a reasoning field before the answer</td><td>1</td></tr>
<tr><td><code>ReAct</code></td><td>a loop: choose a tool, read the result, repeat</td><td>1 per turn</td></tr>
<tr><td><code>BestOfN</code></td><td>N samples, keep the best by your reward function</td><td>N</td></tr>
<tr><td><code>Refine</code></td><td>N samples, feed the failure back in as a hint</td><td>N</td></tr>
</table>''',
        "simple": '''# the same signature, three strategies
dspy.Predict(Sentiment)(review=text)          # answer straight away
dspy.ChainOfThought(Sentiment)(review=text)   # reason, then answer
dspy.BestOfN(dspy.Predict(Sentiment), N=5,
             reward_fn=is_confident, threshold=1.0)(review=text)''',
        "simple_note": "One task, three different amounts of effort and cost. The signature was "
                       "written once and never touched.",
        "real": '''<p>We used <code>ChainOfThought</code>, because picking benchmarks is judgement rather
than extraction - a direct call kept returning the first plausible index.</p>
<pre>program = dspy.ChainOfThought(build_signature())
pred = program(holding=..., risk_level=..., shortlist=...)</pre>
<p style="margin-top:10px">The cost of that choice, measured: one extra reasoning field per call,
and the reasoning is <b>not auditable</b> - it reads sensibly whether or not the picks are right.
In 3.5 it is also no longer a plain string; it is <code>dspy.Reasoning | None</code>.</p>''',
        "limit": "Each step up costs tokens and latency; <code>BestOfN</code> at N=5 is five times "
                 "the bill. And a module changes <em>how</em> the model reasons, never what it "
                 "knows - no strategy recovers a fact that was missing from the input.",
        "extra": "",
    },
    "tools": {
        "title": "Tools",
        "blurb": "Interact with the outside world",
        "api": "dspy.Tool · dspy.ReAct · MCP · PythonInterpreter",
        "icon": "ic-robot",
        "what": "<b>You write the tool; the model only decides when to call it.</b> A tool is an "
                "ordinary Python function - your code, your side effects, your permissions. The "
                "model picks which function to call, with which arguments, reads the result, and "
                "decides whether to call another. Your function's docstring is what the model "
                "sees, so in DSPy a docstring is prompt text.",
        "parts": '''<table class="ctab">
<tr><th>ingredient</th><th>what it does</th></tr>
<tr><td>the function</td><td>anything callable. Typed arguments become the argument schema.</td></tr>
<tr><td>the docstring</td><td>the description the model reads. Vague docstring, vague tool.</td></tr>
<tr><td>a <code>ReAct</code> module</td><td>the loop that decides when to stop calling.</td></tr>
<tr><td>a turn budget</td><td>what stops it looping forever. Always set one.</td></tr>
</table>''',
        "simple": '''def get_weather(city: str) -> str:
    """Current weather for a city."""
    return api.weather(city)

agent = dspy.ReAct("question -> answer", tools=[get_weather])
agent(question="Do I need a coat in Tokyo?")''',
        "simple_note": "The model never writes this function. It reads the docstring, decides the "
                       "function is relevant, supplies the argument, and reads what comes back.",
        "real": '''<p>We did <b>not</b> use tools in the run you are looking at, and that was a cost
rather than a design win.</p>
<p style="margin-top:8px">The task read only what was supplied in the prompt: an id, a name, a
sector, a country. The enrichment most likely to move the score - industry codes and measured
co-movement per candidate - is exactly what a tool supplies.</p>
<pre>def co_movement(asset_id: str, candidate_id: str) -> float:
    """Trailing 2y correlation of daily returns, market-adjusted."""
    return prices.residual_corr(asset_id, candidate_id)</pre>
<p style="margin-top:10px">With that tool the model could check a candidate instead of guessing
from its name. Without it, the only lever left was the wording of the instruction - which is
precisely where the optimiser plateaued.</p>''',
        "limit": "Tools are capability you pre-wrote, so they cannot cover a case you did not "
                 "foresee. Every call can fail, and failures compound inside a loop. And every "
                 "tool is an attack surface, because the model chooses the arguments.",
        "extra": '''<h4>Programmable, or generated?</h4>
<table class="ctab">
<tr><th>you need...</th><th>who writes it</th><th>use</th></tr>
<tr><td>a capability you can write today; only the <i>when</i> is uncertain</td>
    <td><b>you</b></td><td>a plain function + <code>dspy.ReAct</code></td></tr>
<tr><td>the model to compute something by writing and running code</td>
    <td><b>the model</b></td><td><code>dspy.RLM</code></td></tr>
<tr><td>a fixed sequence you know in advance</td>
    <td><b>you</b></td><td>just call it - no model, no tool</td></tr>
</table>
<p>The test is one question: can you write the function today? If yes, it is a tool. If the
function itself is the hard part, you want code generation.</p>''',
    },
    "adapters": {
        "title": "Adapters",
        "blurb": "Customizable prompt formatters",
        "api": "XMLAdapter · ChatAdapter · JSONAdapter",
        "icon": "ic-align",
        "what": "The adapter is the layer between a signature and tokens. It renders the "
                "instructions, the field schema and any demos into an actual prompt, then parses "
                "the reply back into your declared types. The same signature through two adapters "
                "is two different prompts and two different parsers - so the adapter is part of "
                "the system, not a formatting detail.",
        "parts": '''<table class="ctab">
<tr><th>ingredient</th><th>what it does</th></tr>
<tr><td>instructions</td><td>the signature docstring, placed as the system message.</td></tr>
<tr><td>field schema</td><td>names, types and descriptions, rendered into the prompt.</td></tr>
<tr><td>demos</td><td>few-shot examples an optimiser selected, if any.</td></tr>
<tr><td>the parser</td><td>turns the reply back into typed objects. This is what rejects bad
    shapes, and what triggers a retry.</td></tr>
</table>''',
        "simple": '''dspy.Predict(Sentiment)     # built once
# with XMLAdapter the model is asked for:   <label>negative</label>
# with ChatAdapter it is asked for:         [[ ## label ## ]] negative
# with JSONAdapter it is asked for:         {"label": "negative"}''',
        "simple_note": "Identical signature. The only difference is what the model is told to "
                       "emit, and how strictly the reply is parsed.",
        "real": '''<p>This one was not academic - the adapter decided whether the project ran at all.</p>
<pre class="out">same signature, same model (deepseek/deepseek-flash):
  JSONAdapter   -> LMInvalidRequestError: response_format unavailable
  XMLAdapter    -> 30 cases run, 7 failed to parse
  ChatAdapter   -> 5/5 parse on exactly those failing cases</pre>
<p style="margin-top:10px">Switching XML to Chat took parse failures from 23% to 3% without
changing one character of the task definition. The first version of the run was measuring the
adapter, not the prompt.</p>''',
        "limit": "3.5 changed the default from Chat to XML, so upgrading silently changes every "
                 "prompt you already have; anything optimised before the upgrade must be "
                 "re-measured. And providers that reject <code>response_format</code> need the "
                 "JSON fallback explicitly disabled.",
        "extra": "",
    },
    "optimizers": {
        "title": "Optimizers",
        "blurb": "Optimize your program, ML-style",
        "api": "dspy.GEPA · MIPROv2 · BootstrapFewShot · COPRO · SIMBA",
        "icon": "ic-wand",
        "what": "An optimiser proposes changes, scores each one with your metric, and keeps only "
                "what wins. Every optimiser tunes one or more of exactly three knobs - the "
                "<b>instructions</b>, the <b>demos</b>, or the model <b>weights</b>. Nothing else "
                "is in the search space; the schema, the gates and your evaluation set stay "
                "frozen, which is what stops it cheating.",
        "parts": '''<table class="ctab">
<tr><th>ingredient</th><th>what it does</th></tr>
<tr><td>your metric</td><td>the only definition of better. Also the budget unit.</td></tr>
<tr><td>a trainset</td><td>cases it may optimise against.</td></tr>
<tr><td>a valset</td><td>cases it uses to choose between candidates. Keep it separate.</td></tr>
<tr><td>a proposer</td><td>writes new instructions. For GEPA this is a second model.</td></tr>
<tr><td>a budget</td><td><code>max_metric_calls</code>. This, not a prompt count, is what bounds
    the run.</td></tr>
</table>''',
        "simple": '''# the cheapest optimiser: keep a few good examples as demos
opt = dspy.BootstrapFewShot(metric=metric, max_bootstrapped_demos=3)
better = opt.compile(student=program, trainset=trainset)''',
        "simple_note": "No reflection model, so it costs a fraction of GEPA. It only selects "
                       "demos - it never rewrites your instruction.",
        "real": '''<p>We ran <code>GEPA</code>, which rewrites the instruction and reads your metric's
feedback while doing it.</p>
<pre class="out">21 iterations, 14 proposals written, 120 metric calls
v0  0.635   the prompt a human wrote
v1  0.738   kept
v2  0.767   kept  <- best
v3..v14     all worse than v2, discarded

12 of 14 proposals did not beat the human prompt</pre>
<p style="margin-top:10px">The improvement is real but narrow: GEPA fixed three of ten held-out
cases to a perfect score and left the other seven untouched. It could not help where the input
was the limitation rather than the wording.</p>''',
        "limit": "Hundreds of model calls, and most candidates come back worse than where you "
                 "started. An optimiser cannot add a fact the model lacks, cannot reorder the "
                 "shortlist it was given, and cannot fix a metric that rewards the wrong thing.",
        "extra": '''<h4>They are not interchangeable</h4>
<table class="ctab">
<tr><th>optimiser</th><th>tunes</th><th>reach for it when</th></tr>
<tr><td><b>GEPA</b></td><td>instructions</td>
    <td>your metric returns feedback text, not just a number</td></tr>
<tr><td>MIPROv2</td><td>instructions + demos</td>
    <td>both look weak and you have budget</td></tr>
<tr><td>BootstrapFewShot</td><td>demos</td>
    <td>first thing to try; costs almost nothing</td></tr>
<tr><td>BootstrapRS</td><td>demos, random search</td>
    <td>demo quality varies between draws</td></tr>
<tr><td>COPRO</td><td>instructions only</td>
    <td>fast shallow sweep without a feedback metric</td></tr>
<tr><td>SIMBA</td><td>instructions, mini-batch</td>
    <td>failures share a pattern you can name</td></tr>
<tr><td>BootstrapFinetune</td><td>weights</td>
    <td>prompt-only has plateaued and the model is tunable</td></tr>
<tr><td>BetterTogether</td><td>prompt, then weights</td>
    <td>you tried both separately and suspect they compose</td></tr>
</table>
<p>All of them return a new program and leave the original untouched, so the same student can be
compiled three ways and compared.</p>''',
    },
    "metrics": {
        "title": "Metrics",
        "blurb": "Define what to optimize against",
        "api": "any callable · dspy.Evaluate · SemanticF1",
        "icon": "ic-ruler",
        "what": "A metric is a function taking <code>(gold, prediction)</code> and returning a "
                "number - or, far better, a number <em>and a sentence of feedback</em>. The number "
                "decides keep or discard. The sentence is what the optimiser's reflection step "
                "reads, and it is the whole reason a rewrite can be targeted rather than random. "
                "The optimiser's budget is counted in <b>calls to this function</b>.",
        "parts": '''<table class="ctab">
<tr><th>ingredient</th><th>what it does</th></tr>
<tr><td><code>gold</code></td><td>the labelled example: what the right answer is.</td></tr>
<tr><td><code>pred</code></td><td>what the program produced this time.</td></tr>
<tr><td><code>trace</code></td><td>optional. Lets a metric behave one way at evaluation time and
    another inside an optimiser.</td></tr>
<tr><td>the return value</td><td><code>bool</code>, <code>float</code>, or
    <code>Prediction(score, feedback)</code>.</td></tr>
<tr><td><code>feedback</code></td><td>the sentence GEPA reads. Omit it and reflection has nothing
    to work from.</td></tr>
</table>''',
        "simple": '''def exact(gold, pred, trace=None):
    return gold.answer.strip().lower() == pred.answer.strip().lower()''',
        "simple_note": "The simplest legal metric: True or False per example, averaged into a "
                       "percentage. It works - but it gives the optimiser no reason, so reflection "
                       "can only guess what to change.",
        "real": '''<p>Ours is four layers, applied in this order:</p>
<pre>1. hard gates      wrong count / unknown id / duplicate   -> score 0
2. tiered credit    peer 1.0 + adjacent 0.5, divided by 3
3. soft penalties   -0.12 per broken rule (word limit, banned word, ...)
4. feedback text    "peer=1 adjacent=2 wrong=0. Prefer same-industry peers."</pre>
<p style="margin-top:10px">And the sentence that actually drove the optimisation:</p>
<pre class="out">EQ_NVDA: scored 0.55 with ['IDX_SOX', 'ETF_XLK', 'IDX_SPX'].
peer=1 adjacent=2 wrong=0. Prefer same-industry peers over broad indices;
acceptable examples were ['EQ_AMD', 'EQ_ASML', 'EQ_AVGO'].</pre>
<p style="margin-top:10px">Everything after <code>peer=1</code> is guidance a scalar score could
never carry. Drop it and the optimiser is not merely weakened - GEPA substitutes
<i>"This trajectory got a score of 0.55"</i>, and the loop stops learning.</p>''',
        "limit": "The metric becomes the objective, so any hole in it gets exploited, and an "
                 "automated search finds holes faster than a human does. Ours is also a proxy: it "
                 "scores 0 on a genuine peer it cannot see, and carries roughly ±0.08 of noise on "
                 "ten cases.",
        "extra": '''<h4>What makes a metric trustworthy</h4>
<table class="ctab">
<tr><th>property</th><th>fails like this</th></tr>
<tr><td><b>Discriminative</b></td><td>every candidate scores 0.9 - no gradient, nothing to climb</td></tr>
<tr><td><b>Ungameable</b></td><td>a junk answer scores well, and the optimiser finds it</td></tr>
<tr><td><b>Aligned</b></td><td>it improves while the real outcome gets worse</td></tr>
<tr><td><b>Cheap</b></td><td>you cannot afford 120 calls, so you optimise blind</td></tr>
<tr><td><b>Stable</b></td><td>the same input scores differently on reruns; you chase noise</td></tr>
</table>''',
    },
}
