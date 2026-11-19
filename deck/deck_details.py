"""Click-through content for the capability tiles on page 1.

Each entry is grounded in the DSPy 3.5 documentation: what the feature does, a
runnable-shaped example, when it earns its keep, when it does not, and the limit
you should state out loud rather than discover in production.

The `limit` field is the important one. Every tool here has a failure mode, and a
tech share that only shows upside is a sales pitch.
"""

DETAILS = {
    "align": {
        "title": "Structured answers",
        "api": "dspy.Signature · dspy.InputField / dspy.OutputField",
        "icon": "ic-align",
        "what": "You declare the fields you want and their types. The model's reply is "
                "converted back into those types, so downstream code gets real data instead "
                "of a paragraph it has to scrape.",
        "code": '''class Triage(dspy.Signature):
    """Route a support ticket to the right team."""
    ticket: str = dspy.InputField()
    urgency: Literal["low", "high"] = dspy.OutputField()
    team: str = dspy.OutputField()

classify = dspy.Predict(Triage)
out = classify(ticket="Refund not received")
print(out.urgency)          # "high" - a real value, not text''',
        "good": "The output feeds code: a database row, a decision, a report. You need a "
                "field to be present every single time.",
        "bad": "Open-ended exploration where you do not yet know what the useful fields "
               "are. You will just constrain the model to the wrong shape.",
        "limit": "The type guarantees the shape, never the truth. A field typed str can "
                 "still be a wrong answer, and a validator that checks format will happily "
                 "pass a plausible lie.",
    },
    "brain": {
        "title": "Reason first",
        "api": "dspy.ChainOfThought",
        "icon": "ic-brain",
        "what": "The same task with one extra step: work through the reasoning, then give "
                "the answer. The reasoning is produced before the output field, so it "
                "conditions the answer.",
        "code": '''qa = dspy.ChainOfThought("question -> answer")
pred = qa(question="Which benchmark best fits a fabless GPU designer?")
print(pred.reasoning)   # dspy.Reasoning | None in 3.5
print(pred.answer)

# 3.5: reasoning is native, not always text. Opt into a text field:
#   dspy.ChainOfThought("q -> a", rationale_field_type=str)''',
        "good": "Judgement calls, comparisons, anything where the first instinct is often "
                "wrong and a little deliberation helps.",
        "bad": "Plain extraction or classification with an obvious answer. You pay for "
               "tokens that change nothing.",
        "limit": "The reasoning is not audited. It reads plausibly whether or not the "
                 "answer is right, so a confident rationale is not evidence. In 3.5 it is "
                 "also no longer guaranteed to be a plain string.",
    },
    "robot": {
        "title": "Use tools",
        "api": "dspy.ReAct · dspy.Tool · MCP",
        "icon": "ic-robot",
        "what": "You pass ordinary Python functions. The model decides which to call, "
                "reads the result, and repeats until it can answer.",
        "code": '''def search(query: str) -> list[str]:
    """Search the internal knowledge base."""
    return kb.query(query, k=3)

def fx_rate(pair: str) -> float:
    """Live FX rate for a currency pair."""
    return treasury.rate(pair)

agent = dspy.ReAct("question -> answer", tools=[search, fx_rate])
res = agent(question="What is the USD exposure of this portfolio?")
print(res.history.messages, res.termination_reason)''',
        "good": "The answer needs data that is not in the prompt: live prices, a database, "
                "a calculation the model cannot do reliably.",
        "bad": "Everything needed is already in the supplied context. Tools just add "
               "latency and new ways to fail.",
        "limit": "Each tool call can fail, and failures compound inside a loop. You need a "
                 "turn budget and a way to stop. 3.5 changed ReAct's output shape from a "
                 "trajectory dict to structured History - old traces need recompiling.",
    },
    "calc": {
        "title": "Compute, not guess",
        "api": "dspy.RLM · PythonInterpreter",
        "icon": "ic-calc",
        "what": "The model writes Python and runs it in a sandbox to produce the answer, "
                "rather than predicting digits. Generated code can call a sub-model "
                "mid-execution.",
        "code": '''rlm = dspy.RLM("question, cashflows -> answer", max_iters=20)
res = rlm(question="What is the IRR of these cashflows?",
          cashflows=[-100, 30, 40, 50])
print(res.answer)

# Sandbox is Deno/WASM: no filesystem or network by default.
# Cost knobs: max_iters, max_llm_calls, max_output_chars''',
        "good": "Arithmetic, table arithmetic, anything where being roughly right is the "
                "same as being wrong. This is the biggest single win over plain prompting.",
        "bad": "Text tasks. You pay interpreter start-up and add a fragile code path for no "
               "benefit.",
        "limit": "Needs a Deno runtime available. Generated code can fail or loop, and the "
                 "sandbox is isolated by design, so it cannot reach your real data unless "
                 "you pass it in.",
    },
    "layers": {
        "title": "Several tries",
        "api": "dspy.BestOfN · dspy.Refine",
        "icon": "ic-layers",
        "what": "Generate N candidate answers, score each with your own function, keep the "
                "best. Refine goes further: it feeds the failure back in as a hint for the "
                "next attempt.",
        "code": '''def reward(args, pred) -> float:
    return 1.0 if schema_ok(pred) and cited(pred) else 0.0

best = dspy.BestOfN(module=generate, N=5, reward_fn=reward, threshold=1.0)
refine = dspy.Refine(module=generate, N=3, reward_fn=reward, threshold=1.0)

# Both force temperature=1.0 and vary rollout_id, so each sample differs.''',
        "good": "A single generation is high-variance and you have a cheap way to tell good "
                "from bad. The reward function is the whole value.",
        "bad": "A deterministic task, or when you cannot score a candidate without a human. "
               "Then you are paying N times for noise.",
        "limit": "Cost and latency are N times, and a weak reward function will reliably "
                 "pick the wrong candidate with high confidence. Cheap reward, expensive "
                 "mistake.",
    },
    "steps": {
        "title": "Chain steps",
        "api": "class MyProgram(dspy.Module)",
        "icon": "ic-steps",
        "what": "Break the job into named sub-steps and call them in ordinary Python: "
                "extract, then check, then summarise. Each step is inspectable and testable "
                "on its own.",
        "code": '''class FactCheck(dspy.Module):
    def __init__(self):
        self.find = dspy.ChainOfThought("article -> claims: list[str]")
        self.verify = dspy.ChainOfThought("claim, source -> verdict")

    def forward(self, article):
        found = self.find(article=article)
        return [self.verify(claim=c, source=article)
                for c in found.claims]

print(FactCheck()(article=news))''',
        "good": "A task with genuinely different stages, especially when one stage is "
                "reliable and another is not.",
        "bad": "A single prompt already does it fine. Chaining adds tokens and failure "
               "points for nothing.",
        "limit": "Errors compound: a 90%-accurate step run three times in sequence is about "
                 "73% accurate overall. It is also more tokens, not fewer.",
    },
    "ruler": {
        "title": "Measure it",
        "api": "dspy.Evaluate · metric functions",
        "icon": "ic-ruler",
        "what": "Any function taking (gold, pred) and returning a number, bool, or a "
                "score-with-feedback. Evaluate runs it over a labelled set in parallel and "
                "returns one score plus per-example detail.",
        "code": '''def metric(gold, pred, trace=None):
    return gold.answer.strip().lower() == pred.answer.strip().lower()

evaluate = dspy.Evaluate(devset=devset, metric=metric,
                         num_threads=8, display_progress=True)
result = evaluate(program)
print(result.score)            # one number
for ex, pred, s in result.results[:3]:
    print(s, pred.answer)      # and the detail to explain it''',
        "good": "Comparing two prompts, two models, or a before and after. It converts "
                "'feels better' into a number two people can argue about.",
        "bad": "No labelled set exists, or correctness is genuinely a matter of taste. Then "
               "you are measuring the judge's taste, not the system.",
        "limit": "The metric becomes the objective, so any hole in it gets exploited. Ours "
                 "is a proxy with hand-chosen weights; see the limits section below.",
    },
    "wand": {
        "title": "Rewrite the prompt",
        "api": "dspy.GEPA · MIPROv2 · BootstrapFewShot · COPRO",
        "icon": "ic-wand",
        "what": "A second model reads the cases you failed, with a note on why, and writes "
                "new instructions. The candidate is kept only if the score improves.",
        "code": '''optimizer = dspy.GEPA(metric=metric, auto="light",
                       reflection_lm=dspy.LM("deepseek/deepseek-flash"))
optimized = optimizer.compile(program, trainset=trainset, valset=valset)
optimized.save("benchmarks.v2.json")

# GEPA only rewrites Signature.instructions. Field names, descs and
# prefixes are untouched, so your schema stays exactly as you wrote it.''',
        "good": "You have a metric you trust and a prompt written before you understood "
                "the failures. Most valuable when failures cluster on judgement.",
        "bad": "No metric, or a metric that is trivially gameable. The optimiser will find "
               "the game faster than you will notice it.",
        "limit": "Hundreds of model calls per run, and most candidates are worse than what "
                 "you started with - in our run, 12 of 14 were no better, 6 clearly worse. "
                 "It needs a feedback-rich metric, and it cannot fix a missing fact.",
    },
    "swap": {
        "title": "Swap models",
        "api": "dspy.LM · dspy.configure · dspy.context",
        "icon": "ic-swap",
        "what": "The model is configuration, not code. Point at a different provider or a "
                "cheaper tier without editing a single prompt.",
        "code": '''lm = dspy.LM("deepseek/deepseek-flash")
dspy.configure(lm=lm)                 # global default

with dspy.context(lm=dspy.LM("openai/gpt-4o-mini")):
    pred = program(question=q)        # scoped override

# 3.5: model_type="auto" picks chat vs responses per provider.
# Pin dspy.LM(..., model_type="chat") for chat-only endpoints.''',
        "good": "Multi-provider estates, cost tiering, and local-versus-hosted decisions. "
                "This is where hand-tuned prompts usually break first.",
        "bad": "Expecting identical output after a swap. You get a different distribution, "
               "not a cheaper copy.",
        "limit": "Prompts are model-specific. After switching you must recompile and "
                 "re-measure - the 3.5 default adapter change alone altered prompts for "
                 "everyone upgrading.",
    },
}
