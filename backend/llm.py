"""Groq client + prompt construction for grounded generation.

Chosen for inference speed (custom LPU hardware) -- most relevant for the
chatbot, where response latency is directly part of the UX.
"""
import os

from groq import Groq

MODEL = "openai/gpt-oss-120b"

_client = None


def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client


def format_fighter_stats(fighter):
    if not fighter:
        return "No stats available."
    return (
        f"{fighter['name']} ({fighter.get('record') or 'record unknown'})\n"
        f"- Style: {fighter.get('style') or 'unknown'}, "
        f"current win streak: {fighter.get('win_streak', 'unknown')}\n"
        f"- Age: {fighter.get('age', 'unknown')}, "
        f"Height: {fighter.get('height_inches', '?')}in, "
        f"Reach: {fighter.get('reach_inches', '?')}in, "
        f"Stance: {fighter.get('stance') or 'unknown'}\n"
        f"- Striking: {fighter.get('sig_strikes_landed_per_min', '?')} landed/min "
        f"@ {fighter.get('sig_strike_accuracy_pct', '?')}% accuracy, "
        f"{fighter.get('sig_strike_defense_pct', '?')}% defense\n"
        f"- Grappling: {fighter.get('takedown_avg_per_15min', '?')} takedowns/15min "
        f"@ {fighter.get('takedown_accuracy_pct', '?')}% accuracy, "
        f"{fighter.get('submission_avg_per_15min', '?')} submission attempts/15min"
    )


def format_citations(chunks):
    if not chunks:
        return "No fan/analyst commentary was found for this fight."
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        byline = f" -- {chunk['author']}" if chunk.get("author") else ""
        lines.append(f"[{i}] ({chunk['source']}{byline}): \"{chunk['text']}\"")
    return "\n".join(lines)


PREDICTION_SYSTEM_PROMPT = """You are a confident, decisive MMA analyst producing a fight \
prediction for a UFC prediction app. You're given each fighter's real stats and real fan/\
analyst commentary retrieved for this specific fight. Ground your prediction in that \
material: reference specific stats by name, and reference commentary using its [N] \
citation number when you use it. Do not invent statistics or quotes that weren't given to \
you. If the commentary is sparse or absent, rely on the stats and say so rather than \
making things up.

This prediction is generated once and shown to every user who views this fight, so commit \
to a real, decisive read rather than hedging both ways -- pick a side and defend it. Avoid \
wishy-washy language ("could go either way", "hard to say", "it's a toss-up"); if the \
matchup is genuinely close, say so once and still land on a pick with a specific reason \
you're leaning that way. Give: a clear pick (who wins and ideally how), a confidence level \
as a specific percentage that reflects how one-sided the stats/commentary actually are (a \
close matchup should read as ~55-65%, not equivocate at 50% -- reserve 80%+ for a real \
statistical mismatch), and 2-4 sentences of reasoning."""


def build_prediction_prompt(fight, chunks):
    fighter_red = fight["fighter_red"]
    fighter_blue = fight["fighter_blue"]
    return (
        f"Fight: {fighter_red['name'] if fighter_red else fight.get('fighter_red_name')} vs "
        f"{fighter_blue['name'] if fighter_blue else fight.get('fighter_blue_name')} "
        f"({fight.get('weight_class') or 'weight class unknown'}) at {fight['event']['event_name']}\n\n"
        f"--- Fighter 1 ---\n{format_fighter_stats(fighter_red)}\n\n"
        f"--- Fighter 2 ---\n{format_fighter_stats(fighter_blue)}\n\n"
        f"--- Fan/analyst commentary ---\n{format_citations(chunks)}\n\n"
        f"Give your prediction."
    )


def generate_prediction(fight, chunks):
    client = get_client()
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": PREDICTION_SYSTEM_PROMPT},
            {"role": "user", "content": build_prediction_prompt(fight, chunks)},
        ],
        temperature=0.2,
    )
    return completion.choices[0].message.content


CHAT_SYSTEM_PROMPT = """You are a chatbot for a UFC prediction app, grounded in real fan \
and analyst commentary retrieved for the user's question. Answer using the commentary \
provided, citing it by its [N] number when you use it. If the retrieved commentary \
doesn't actually answer the question, say so honestly instead of making something up."""


def build_chat_prompt(question, chunks):
    return (
        f"User question: {question}\n\n"
        f"--- Retrieved commentary ---\n{format_citations(chunks)}\n\n"
        f"Answer the question using the commentary above where it's relevant."
    )


def generate_chat_response(question, chunks):
    client = get_client()
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "user", "content": build_chat_prompt(question, chunks)},
        ],
        temperature=0.5,
    )
    return completion.choices[0].message.content
